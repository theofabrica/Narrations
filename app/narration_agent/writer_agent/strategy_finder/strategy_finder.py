"""Strategy finder to select writing strategy from the library index."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from app.config.settings import settings
from app.utils.ids import generate_timestamp
from app.utils.project_storage import get_data_root, get_project_root

from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.spec_loader import load_json
from app.narration_agent.writer_agent.strategy_finder.library_rag import LibraryRAG


@dataclass
class StrategyCard:
    strategy_id: str
    target_path: str
    writing_typology: str
    library_item_ids: List[str]
    style_guidelines: List[str]
    structure_guidelines: List[str]
    strategy_text: str
    source_refs: List[str]
    notes: str


class StrategyFinder:
    """Select a strategy card based on context pack and library index."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self._library_index = load_json("writer_agent/strategy_finder/library/index.json") or {}
        self._rag = LibraryRAG()

    def build_strategy(self, context_pack: Dict[str, Any]) -> Dict[str, Any]:
        context_pack = dict(context_pack) if isinstance(context_pack, dict) else {}
        target_path = context_pack.get("target_path", "")
        writing_typology = context_pack.get("writing_typology", "")
        language = context_pack.get("style_constraints", {}).get("language", "") or ""
        project_id = context_pack.get("project_id", "")
        use_conversation_id = self._should_use_rag_conversation_id(str(target_path))
        if isinstance(project_id, str) and project_id.strip() and use_conversation_id:
            rag_conversation_id = self._resolve_rag_conversation_id(project_id, target_path)
            if rag_conversation_id:
                context_pack["rag_conversation_id"] = rag_conversation_id
        else:
            context_pack.pop("rag_conversation_id", None)

        candidates = self._filter_library_items(writing_typology, language)
        rag_hits, retrieval_variants = self._retrieve_with_semantic_variants(
            context_pack=context_pack,
            target_path=str(target_path),
            limit=10,
        )
        if (
            isinstance(project_id, str)
            and project_id.strip()
            and use_conversation_id
            and self._should_rotate_rag_conversation_id(
                getattr(self._rag, "last_response_debug", {}),
                getattr(self._rag, "last_error", ""),
            )
        ):
            rotated_id = self._rotate_rag_conversation_id(project_id, str(target_path))
            if rotated_id:
                context_pack["rag_conversation_id"] = rotated_id
        vetted_hits, evidence_report = self._validate_rag_hits(context_pack, rag_hits)
        if isinstance(evidence_report, dict):
            evidence_report["retrieval_variants"] = retrieval_variants
        strategy_hits = [hit for hit in vetted_hits if isinstance(hit, dict)]
        strategy_hits.sort(
            key=lambda row: float(row.get("score", 0) or 0),
            reverse=True,
        )

        library_item_ids = self._dedupe_preserve_order(
            [str(hit.get("id")) for hit in strategy_hits if hit.get("id")]
        )
        if not library_item_ids:
            library_item_ids = self._dedupe_preserve_order(
                [str(item.get("id")) for item in candidates if item.get("id")]
            )
        source_refs = []
        for hit in strategy_hits:
            title = hit.get("title", "").strip()
            author = hit.get("author", "").strip()
            excerpt = hit.get("excerpt", "").strip()
            summary = hit.get("summary", "").strip()
            concepts = self._normalize_key_concepts(
                raw_concepts=hit.get("key_concepts", []),
                summary=summary,
                excerpt=excerpt,
                limit=6,
            )
            if title or author or excerpt or summary:
                ref = f"{title} - {author}".strip(" -")
                detail = summary or excerpt
                if detail:
                    ref = f"{ref}: {detail}" if ref else detail
                if isinstance(concepts, list) and concepts:
                    ref = f"{ref} | Concepts: {', '.join(concepts[:6])}"
                source_refs.append(ref)
        if not source_refs:
            source_refs = [
                f"{item.get('title', '').strip()} - {item.get('author', '').strip()}"
                for item in candidates
            ]

        rag_mode = getattr(self._rag, "last_mode", "unknown")
        rag_hit_count = getattr(self._rag, "last_hit_count", len(rag_hits))
        evidence_mode = evidence_report.get("status", "unknown")
        notes = (
            "Auto-selected based on writing typology and language."
            f" rag_mode={rag_mode}, rag_hits={rag_hit_count},"
            f" evidence_mode={evidence_mode}, evidence_kept={len(strategy_hits)}."
        )
        self._write_rag_log(
            context_pack=context_pack,
            target_path=target_path,
            writing_typology=writing_typology,
            rag_mode=rag_mode,
            rag_hit_count=rag_hit_count,
            rag_error_detail=getattr(self._rag, "last_error", ""),
            rag_reason=getattr(self._rag, "last_reason", ""),
            rag_policy_path=getattr(self._rag, "last_policy_path", []),
            rag_retry=getattr(self._rag, "last_retry", ""),
            rag_conversation_id=context_pack.get("rag_conversation_id", ""),
            evidence_report=evidence_report,
            library_item_ids=library_item_ids,
            source_refs=source_refs,
        )
        self._update_rag_metrics(
            project_id=project_id,
            rag_mode=rag_mode,
            rag_reason=getattr(self._rag, "last_reason", ""),
        )

        card = StrategyCard(
            strategy_id=f"{writing_typology or 'general'}_v1",
            target_path=target_path,
            writing_typology=writing_typology,
            library_item_ids=library_item_ids,
            style_guidelines=[],
            structure_guidelines=[],
            strategy_text="",
            source_refs=[ref for ref in source_refs if ref.strip(" -")],
            notes=notes,
        )
        strategy_question = context_pack.get("strategy_question", "")
        strategy_payload = self._build_strategy_payload(
            context_pack, card, strategy_question, strategy_hits
        )
        strategy_text = self._build_strategy_output(
            context_pack, card, strategy_question, strategy_hits
        )
        card.strategy_text = strategy_text
        self._write_strategy_log(
            context_pack, card, strategy_question, strategy_payload, evidence_report
        )
        return {
            "strategy_id": card.strategy_id,
            "target_path": card.target_path,
            "writing_typology": card.writing_typology,
            "library_item_ids": card.library_item_ids,
            "strategy_text": card.strategy_text,
            "source_refs": card.source_refs,
            "notes": card.notes,
        }

    def _filter_library_items(self, writing_typology: str, language: str) -> List[Dict[str, Any]]:
        items = self._library_index.get("items", [])
        if not isinstance(items, list):
            return []

        def matches(item: Dict[str, Any]) -> bool:
            if writing_typology:
                typologies = item.get("writing_typologies", [])
                if writing_typology not in typologies:
                    return False
            if language:
                if item.get("language") != language:
                    return False
            return True

        filtered = [item for item in items if isinstance(item, dict) and matches(item)]
        return filtered if filtered else [item for item in items if isinstance(item, dict)]

    def _retrieve_with_semantic_variants(
        self,
        *,
        context_pack: Dict[str, Any],
        target_path: str,
        limit: int,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        base_pack = dict(context_pack) if isinstance(context_pack, dict) else {}
        strategy_question = str(base_pack.get("strategy_question", "") or "").strip()
        if not strategy_question:
            hits = self._rag.retrieve(base_pack, limit=limit)
            return hits if isinstance(hits, list) else [], {"enabled": False, "reasons": ["no_strategy_question"]}
        if not self._target_supports_semantic_variants(target_path):
            hits = self._rag.retrieve(base_pack, limit=limit)
            return hits if isinstance(hits, list) else [], {"enabled": False, "reasons": ["target_not_enabled"]}

        variants = self._semantic_question_variants(strategy_question, target_path=target_path)
        seen: set[str] = set()
        merged_hits: List[Dict[str, Any]] = []
        per_variant: List[Dict[str, Any]] = []
        configured_max_variants = getattr(settings, "RAG_VARIANT_MAX", None)
        if isinstance(configured_max_variants, int) and configured_max_variants > 0:
            max_variants = max(1, configured_max_variants)
        else:
            max_variants = max(1, self._env_int("RAG_VARIANT_MAX", 4))
        target_cap = self._target_variant_cap(target_path)
        variants = variants[: max(1, min(max_variants, target_cap))]
        configured_budget_s = getattr(settings, "RAG_VARIANT_TOTAL_BUDGET_S", None)
        if isinstance(configured_budget_s, int) and configured_budget_s > 0:
            total_budget_s = max(1, configured_budget_s)
        else:
            total_budget_s = max(1, self._env_int("RAG_VARIANT_TOTAL_BUDGET_S", 180))
        started_at = time.monotonic()
        stopped_early = ""
        for idx, variant in enumerate(variants):
            elapsed_s = time.monotonic() - started_at
            if elapsed_s >= total_budget_s:
                stopped_early = "time_budget_exceeded"
                break
            request_pack = dict(base_pack)
            request_pack["strategy_question"] = variant
            # Diversify retrieval across calls; avoid conversation carry-over bias.
            if idx > 0:
                request_pack.pop("rag_conversation_id", None)
            call_started = time.monotonic()
            variant_hits = self._rag.retrieve(request_pack, limit=limit)
            elapsed_ms = int((time.monotonic() - call_started) * 1000)
            rows = variant_hits if isinstance(variant_hits, list) else []
            added = 0
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = self._rag_hit_dedupe_key(row)
                if key in seen:
                    continue
                seen.add(key)
                merged_hits.append(row)
                added += 1
            per_variant.append(
                {
                    "variant_index": idx + 1,
                    "question": variant,
                    "elapsed_ms": elapsed_ms,
                    "rag_mode": getattr(self._rag, "last_mode", ""),
                    "rag_reason": getattr(self._rag, "last_reason", ""),
                    "rag_error": getattr(self._rag, "last_error", ""),
                    "raw_hits": len(rows),
                    "added_unique_hits": added,
                }
            )

        merged_hits.sort(
            key=lambda row: float(row.get("score", 0) or 0),
            reverse=True,
        )
        return merged_hits[: max(1, limit)], {
            "enabled": True,
            "variant_count": len(variants),
            "time_budget_s": total_budget_s,
            "max_variants": max_variants,
            "elapsed_total_ms": int((time.monotonic() - started_at) * 1000),
            "stopped_early": stopped_early,
            "per_variant": per_variant,
            "merged_unique_count": len(merged_hits),
            "returned_count": min(len(merged_hits), max(1, limit)),
        }

    def _env_int(self, key: str, default: int) -> int:
        raw = os.environ.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def _target_supports_semantic_variants(self, target_path: str) -> bool:
        value = str(target_path or "").strip()
        return (
            value.startswith("n0.narrative_presentation")
            or value.startswith("n0.production_summary")
            or value.startswith("n0.art_direction")
            or value.startswith("n0.sound_direction")
        )

    def _target_variant_cap(self, target_path: str) -> int:
        value = str(target_path or "").strip()
        if value.startswith("n0.art_direction") or value.startswith("n0.sound_direction"):
            return max(1, self._env_int("RAG_VARIANT_MAX_ART_SOUND", 1))
        return max(1, self._env_int("RAG_VARIANT_MAX_NARRATIVE", 4))

    def _semantic_question_variants(self, strategy_question: str, *, target_path: str) -> List[str]:
        base = " ".join(str(strategy_question or "").split()).strip()
        if not base:
            return []
        value = str(target_path or "").strip()
        if value.startswith("n0.art_direction"):
            candidates = [
                base,
                f"{base} Focus on visual language: palette, lighting, texture, composition, framing, and movement.",
                f"{base} Prioritize actionable art direction choices, style coherence, and distinctive visual identity.",
                f"{base} Retrieve complementary visual guidance with non-overlapping evidence across sources.",
            ]
        elif value.startswith("n0.sound_direction"):
            candidates = [
                base,
                f"{base} Focus on sonic language: timbre, rhythm, ambience, motifs, silence, and spatialization.",
                f"{base} Prioritize actionable sound direction decisions and coherence between music, ambience, and effects.",
                f"{base} Retrieve complementary sonic guidance with non-overlapping evidence across sources.",
            ]
        else:
            candidates = [
                base,
                f"{base} Focus on method-level narrative guidance and concrete writing moves.",
                f"{base} Prioritize causal structure, stakes, conflict progression, and turning points.",
                f"{base} Retrieve complementary guidance with non-overlapping evidence across sources.",
            ]
        out: List[str] = []
        seen: set[str] = set()
        for item in candidates:
            text = " ".join(item.split()).strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            out.append(text)
        return out[:4]

    def _rag_hit_dedupe_key(self, hit: Dict[str, Any]) -> str:
        source_path = str(hit.get("source_path", "") or "")
        source_file = str(hit.get("source_file", "") or "")
        summary = self._trim_text(str(hit.get("summary", "") or ""), 200).lower()
        excerpt = self._trim_text(str(hit.get("excerpt", "") or ""), 260).lower()
        title = str(hit.get("title", "") or "").strip().lower()
        return f"{source_path}|{source_file}|{title}|{summary}|{excerpt}"

    def _validate_rag_hits(
        self, context_pack: Dict[str, Any], rag_hits: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not isinstance(rag_hits, list) or not rag_hits:
            return [], {
                "status": "no_hits",
                "kept_count": 0,
                "raw_count": 0,
                "thresholds": {"overall_min": 0.32, "relevance_min": 0.12},
                "details": [],
            }

        evidence_terms = self._build_evidence_terms(context_pack)
        target_terms = self._target_guidance_terms(context_pack.get("target_path", ""))
        ranked: List[Dict[str, Any]] = []
        for idx, hit in enumerate(rag_hits):
            if not isinstance(hit, dict):
                continue
            summary = str(hit.get("summary") or "").strip()
            excerpt = str(hit.get("excerpt") or "").strip()
            text = f"{summary}\n{excerpt}".strip().lower()
            relevance = self._term_overlap_score(text, evidence_terms)
            actionability = self._term_overlap_score(text, target_terms)
            specificity = self._specificity_score(text)
            overall = round((0.55 * relevance) + (0.30 * actionability) + (0.15 * specificity), 4)
            ranked.append(
                {
                    "index": idx,
                    "hit": hit,
                    "scores": {
                        "overall": overall,
                        "relevance": round(relevance, 4),
                        "actionability": round(actionability, 4),
                        "specificity": round(specificity, 4),
                    },
                    "title": str(hit.get("title", "")),
                    "author": str(hit.get("author", "")),
                    "source_path": str(hit.get("source_path", "")),
                }
            )

        semantic_scores = self._semantic_evidence_scores(context_pack, ranked)
        score_mode = "heuristic"
        if semantic_scores:
            for item in ranked:
                sem = semantic_scores.get(item["index"], {})
                if not isinstance(sem, dict):
                    continue
                sem_rel = self._clamp01(sem.get("relevance", item["scores"]["relevance"]))
                sem_act = self._clamp01(sem.get("actionability", item["scores"]["actionability"]))
                # Keep semantic scoring, but avoid hard-zero actionability cascades.
                sem_act = max(0.15, sem_act)
                item["scores"]["relevance"] = round(sem_rel, 4)
                item["scores"]["actionability"] = round(sem_act, 4)
                item["scores"]["overall"] = round(
                    (0.60 * sem_rel) + (0.25 * sem_act) + (0.15 * item["scores"]["specificity"]),
                    4,
                )
            score_mode = "semantic_llm"

        ranked.sort(key=lambda item: item["scores"]["overall"], reverse=True)
        for item in ranked:
            item["evidence_role"] = self._classify_evidence_role(
                target_path=str(context_pack.get("target_path", "")),
                scores=item.get("scores", {}),
                hit=item.get("hit", {}),
            )
        target_path = str(context_pack.get("target_path", ""))
        if self._uses_loose_evidence_filter(target_path):
            accepted = ranked[:10]
            accepted_hits: List[Dict[str, Any]] = []
            for item in accepted:
                raw_hit = item.get("hit", {})
                if not isinstance(raw_hit, dict):
                    continue
                scored_hit = dict(raw_hit)
                scores = item.get("scores", {})
                if isinstance(scores, dict):
                    scored_hit["score"] = float(scores.get("overall", scored_hit.get("score", 0)) or 0)
                    scored_hit["evidence_relevance"] = float(scores.get("relevance", 0) or 0)
                    scored_hit["evidence_actionability"] = float(scores.get("actionability", 0) or 0)
                    scored_hit["evidence_specificity"] = float(scores.get("specificity", 0) or 0)
                scored_hit["evidence_role"] = str(item.get("evidence_role", "domain_context"))
                accepted_hits.append(scored_hit)
            details = []
            accepted_indexes = {int(item.get("index", -1)) for item in accepted if isinstance(item, dict)}
            for item in ranked[:8]:
                details.append(
                    {
                        "index": item["index"],
                        "title": item["title"],
                        "author": item["author"],
                        "source_path": item["source_path"],
                        "scores": item["scores"],
                        "evidence_role": str(item.get("evidence_role", "")),
                        "accepted": item.get("index") in accepted_indexes,
                    }
                )
            report = {
                "status": "ok" if accepted_hits else "no_hits",
                "score_mode": score_mode,
                "kept_count": len(accepted_hits),
                "raw_count": len(ranked),
                "thresholds": {
                    "overall_min": 0.0,
                    "relevance_min": 0.0,
                    "rescue_relevance_min": 0.0,
                },
                "evidence_mix": {"enabled": False, "policy": "loose_topk_no_abstract_filter"},
                "details": details,
            }
            return accepted_hits, report
        thresholds = self._evidence_thresholds_for_target(
            context_pack.get("target_path", "")
        )
        overall_min = thresholds["overall_min"]
        relevance_min = thresholds["relevance_min"]
        abstract_overall_floor = 0.22
        accepted = []
        for item in ranked:
            scores = item.get("scores", {})
            overall_score = float(scores.get("overall", 0.0) or 0.0)
            relevance_score = float(scores.get("relevance", 0.0) or 0.0)
            role = str(item.get("evidence_role", ""))
            if relevance_score < relevance_min:
                continue
            if overall_score >= overall_min:
                accepted.append(item)
                continue
            if role == "abstract_function" and overall_score >= abstract_overall_floor:
                accepted.append(item)
        accepted, evidence_mix = self._apply_evidence_mix_policy(
            target_path=str(context_pack.get("target_path", "")),
            ranked=ranked,
            accepted=accepted,
            overall_min=overall_min,
            relevance_min=relevance_min,
            final_limit=10,
        )
        accepted_hits: List[Dict[str, Any]] = []
        for item in accepted[:10]:
            raw_hit = item.get("hit", {})
            if not isinstance(raw_hit, dict):
                continue
            scored_hit = dict(raw_hit)
            scores = item.get("scores", {})
            if isinstance(scores, dict):
                scored_hit["score"] = float(scores.get("overall", scored_hit.get("score", 0)) or 0)
                scored_hit["evidence_relevance"] = float(scores.get("relevance", 0) or 0)
                scored_hit["evidence_actionability"] = float(scores.get("actionability", 0) or 0)
                scored_hit["evidence_specificity"] = float(scores.get("specificity", 0) or 0)
            scored_hit["evidence_role"] = str(item.get("evidence_role", ""))
            accepted_hits.append(scored_hit)

        status = "ok" if accepted_hits else "degraded_no_valid_evidence"
        if not accepted_hits and ranked:
            # Controlled rescue rule: accept top-1 when relevance is close
            # and the source belongs to the allowed target library.
            top = ranked[0]
            top_hit = top.get("hit", {})
            top_relevance = float(top["scores"].get("relevance", 0.0) or 0.0)
            top_source_path = (
                str(top_hit.get("source_path", ""))
                if isinstance(top_hit, dict)
                else ""
            )
            rescue_relevance_min = max(0.14, relevance_min - 0.10)
            if (
                self._is_allowed_source_for_target(context_pack, top_source_path)
                and top_relevance >= rescue_relevance_min
            ):
                accepted_hits = [top_hit]
                status = "rescued_top1"
            else:
                # Degraded mode: keep only strongest candidate for continuity.
                accepted_hits = [top_hit]

        details = []
        accepted_indexes = {int(item.get("index", -1)) for item in accepted if isinstance(item, dict)}
        for item in ranked[:8]:
            details.append(
                {
                    "index": item["index"],
                    "title": item["title"],
                    "author": item["author"],
                    "source_path": item["source_path"],
                    "scores": item["scores"],
                    "evidence_role": str(item.get("evidence_role", "")),
                    "accepted": item.get("index") in accepted_indexes,
                }
            )
        report = {
            "status": status,
            "score_mode": score_mode,
            "kept_count": len(accepted_hits),
            "raw_count": len(ranked),
            "thresholds": {
                "overall_min": overall_min,
                "relevance_min": relevance_min,
                "rescue_relevance_min": max(0.14, relevance_min - 0.10),
            },
            "evidence_mix": evidence_mix,
            "details": details,
        }
        return accepted_hits, report

    def _classify_evidence_role(
        self, target_path: str, scores: Dict[str, Any], hit: Dict[str, Any]
    ) -> str:
        if not isinstance(scores, dict):
            scores = {}
        if not isinstance(hit, dict):
            hit = {}
        relevance = float(scores.get("relevance", 0.0) or 0.0)
        actionability = float(scores.get("actionability", 0.0) or 0.0)
        specificity = float(scores.get("specificity", 0.0) or 0.0)
        if target_path.startswith("n0.art_direction") or target_path.startswith("n0.sound_direction"):
            if relevance >= 0.12:
                return "domain_context"
            return "mixed_or_unknown"
        text = f"{hit.get('summary', '')}\n{hit.get('excerpt', '')}".lower()
        abstract_cues = [
            "stakes",
            "causal",
            "cause",
            "effect",
            "progression",
            "arc",
            "turning point",
            "conflict",
            "objective",
            "payoff",
            "setup",
            "dramatic",
            "structure",
            "function",
            "sequence",
        ]
        abstract_hits = sum(1 for cue in abstract_cues if cue in text)
        if abstract_hits >= 2 or actionability >= 0.30:
            return "abstract_function"
        if (
            target_path.startswith("n0.narrative_presentation")
            or target_path.startswith("n0.production_summary")
        ) and relevance >= 0.25 and actionability < 0.22:
            return "story_context"
        if relevance >= 0.22 and specificity >= 0.20:
            return "story_context"
        return "mixed_or_unknown"

    def _apply_evidence_mix_policy(
        self,
        *,
        target_path: str,
        ranked: List[Dict[str, Any]],
        accepted: List[Dict[str, Any]],
        overall_min: float,
        relevance_min: float,
        final_limit: int,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if not (
            target_path.startswith("n0.narrative_presentation")
            or target_path.startswith("n0.production_summary")
        ):
            return accepted, {"enabled": False}
        if not ranked:
            return accepted, {"enabled": True, "selected_counts": {}, "pool_counts": {}}

        strict_pool = [
            item
            for item in ranked
            if float(item.get("scores", {}).get("overall", 0.0) or 0.0) >= overall_min
            and float(item.get("scores", {}).get("relevance", 0.0) or 0.0) >= relevance_min
        ]
        soft_pool = [
            item
            for item in ranked
            if float(item.get("scores", {}).get("relevance", 0.0) or 0.0) >= max(0.12, relevance_min - 0.02)
        ]
        pool = strict_pool if strict_pool else soft_pool
        if not pool:
            return accepted, {"enabled": True, "selected_counts": {}, "pool_counts": {}}

        def by_role(items: List[Dict[str, Any]], role: str) -> List[Dict[str, Any]]:
            return [row for row in items if str(row.get("evidence_role", "")) == role]

        selected: List[Dict[str, Any]] = []
        selected_idx: set[int] = set()

        def push(items: List[Dict[str, Any]], take: int) -> None:
            for item in items:
                idx = int(item.get("index", -1))
                if idx in selected_idx:
                    continue
                selected.append(item)
                selected_idx.add(idx)
                if len(selected) >= take:
                    break

        abstract_pool = by_role(pool, "abstract_function")
        context_pool = by_role(pool, "story_context")
        mixed_pool = by_role(pool, "mixed_or_unknown")

        push(abstract_pool, 2)
        if len(selected) < final_limit:
            push(context_pool, len(selected) + 1)
        if len(selected) < final_limit:
            push(abstract_pool, final_limit)
        if len(selected) < final_limit:
            push(mixed_pool, final_limit)
        if len(selected) < final_limit:
            push(pool, final_limit)

        selected = selected[: max(1, final_limit)]
        if not selected:
            selected = accepted[: max(1, final_limit)] if accepted else pool[: max(1, final_limit)]

        # If strict pool contains too few abstract hits, allow near-threshold abstract rescue
        # to better satisfy mix intent without dropping relevance floor.
        injected_abstract_count = 0
        selected_abstract = len(by_role(selected, "abstract_function"))
        if selected_abstract < 2:
            near_abstract_candidates = [
                item
                for item in ranked
                if str(item.get("evidence_role", "")) == "abstract_function"
                and int(item.get("index", -1)) not in selected_idx
                and float(item.get("scores", {}).get("relevance", 0.0) or 0.0) >= relevance_min
                and float(item.get("scores", {}).get("overall", 0.0) or 0.0)
                >= max(0.0, overall_min - 0.05)
            ]
            near_abstract_candidates.sort(
                key=lambda row: float(row.get("scores", {}).get("overall", 0.0) or 0.0),
                reverse=True,
            )
            for candidate in near_abstract_candidates:
                if len(by_role(selected, "abstract_function")) >= 2:
                    break
                replace_pos = -1
                for pos in range(len(selected) - 1, -1, -1):
                    role = str(selected[pos].get("evidence_role", ""))
                    if role != "abstract_function":
                        replace_pos = pos
                        break
                if replace_pos < 0:
                    break
                selected[replace_pos] = candidate
                selected_idx.add(int(candidate.get("index", -1)))
                injected_abstract_count += 1

        selected_counts = {
            "abstract_function": len(by_role(selected, "abstract_function")),
            "story_context": len(by_role(selected, "story_context")),
            "mixed_or_unknown": len(by_role(selected, "mixed_or_unknown")),
        }
        pool_counts = {
            "abstract_function": len(abstract_pool),
            "story_context": len(context_pool),
            "mixed_or_unknown": len(mixed_pool),
        }
        return selected, {
            "enabled": True,
            "policy": "n0_narrative_min_abstract_mix",
            "target_min_abstract": 2,
            "final_limit": int(max(1, final_limit)),
            "pool_counts": pool_counts,
            "selected_counts": selected_counts,
            "near_threshold_abstract_injections": int(injected_abstract_count),
            "pool_mode": "strict" if strict_pool else "soft_relevance",
        }

    def _dedupe_preserve_order(self, values: List[str]) -> List[str]:
        out: List[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
        return out

    def _semantic_evidence_scores(
        self, context_pack: Dict[str, Any], ranked: List[Dict[str, Any]]
    ) -> Dict[int, Dict[str, float]]:
        if not self.llm_client or not ranked:
            return {}
        candidates: List[Dict[str, Any]] = []
        for item in ranked[:8]:
            hit = item.get("hit", {})
            if not isinstance(hit, dict):
                continue
            title = str(hit.get("title", "")).strip()
            author = str(hit.get("author", "")).strip()
            summary = self._trim_text(str(hit.get("summary", "") or ""), 700)
            excerpt = self._trim_text(str(hit.get("excerpt", "") or ""), 700)
            text = summary if summary else excerpt
            candidates.append(
                {
                    "index": item.get("index"),
                    "title": title,
                    "author": author,
                    "text": text,
                }
            )
        if not candidates:
            return {}
        system_prompt = (
            "You evaluate retrieval evidence quality for a writing strategy task.\n"
            "Return ONLY valid JSON with this schema:\n"
            '{ "scores": [ { "index": 0, "relevance": 0.0, "actionability": 0.0 } ] }\n'
            "- relevance: semantic match to target_path + strategy_question + project_summary.\n"
            "- actionability: how useful the evidence is for concrete writing guidance.\n"
            "- Scores are floats in [0,1].\n"
            "- Do not add any fields."
        )
        user_payload = {
            "target_path": str(context_pack.get("target_path", "")),
            "writing_typology": str(context_pack.get("writing_typology", "")),
            "strategy_question": str(context_pack.get("strategy_question", "")),
            "project_summary": self._trim_text(str(context_pack.get("core_summary", "")), 500),
            "candidates": candidates,
        }
        try:
            response = self.llm_client.complete(
                LLMRequest(
                    model=self.llm_client.default_model,
                    system_prompt=system_prompt,
                    user_prompt=json.dumps(user_payload, ensure_ascii=True, indent=2),
                    temperature=0.0,
                    max_tokens=700,
                )
            )
        except Exception:
            return {}
        parsed = self._parse_semantic_scores(response.content)
        if not parsed:
            return {}
        return parsed

    def _parse_semantic_scores(self, content: str) -> Dict[int, Dict[str, float]]:
        if not isinstance(content, str) or not content.strip():
            return {}
        text = content.strip()
        parsed: Dict[str, Any] | None = None
        try:
            parsed = json.loads(text)
        except Exception:
            if "```" in text:
                blocks = re.split(r"```+", text)
                for block in blocks:
                    candidate = block.strip()
                    if not candidate:
                        continue
                    if "\n" in candidate and candidate.split("\n", 1)[0].strip().lower() in {
                        "json",
                        "text",
                        "plain",
                    }:
                        candidate = candidate.split("\n", 1)[1].strip()
                    try:
                        parsed = json.loads(candidate)
                        break
                    except Exception:
                        continue
        if not isinstance(parsed, dict):
            return {}
        raw_scores = parsed.get("scores", [])
        if not isinstance(raw_scores, list):
            return {}
        out: Dict[int, Dict[str, float]] = {}
        for row in raw_scores:
            if not isinstance(row, dict):
                continue
            idx = row.get("index")
            if not isinstance(idx, int):
                continue
            out[idx] = {
                "relevance": self._clamp01(row.get("relevance", 0.0)),
                "actionability": self._clamp01(row.get("actionability", 0.0)),
            }
        return out

    def _evidence_thresholds_for_target(self, target_path: str) -> Dict[str, float]:
        if not isinstance(target_path, str):
            return {"overall_min": 0.34, "relevance_min": 0.14}
        if target_path.startswith("n0.narrative_presentation") or target_path.startswith(
            "n0.production_summary"
        ):
            return {"overall_min": 0.25, "relevance_min": 0.14}
        if target_path.startswith("n0.art_direction"):
            return {"overall_min": 0.40, "relevance_min": 0.22}
        if target_path.startswith("n0.sound_direction"):
            return {"overall_min": 0.40, "relevance_min": 0.22}
        if target_path.startswith("n1.characters"):
            return {"overall_min": 0.36, "relevance_min": 0.18}
        return {"overall_min": 0.34, "relevance_min": 0.14}

    def _is_allowed_source_for_target(self, context_pack: Dict[str, Any], source_path: str) -> bool:
        if not isinstance(source_path, str) or not source_path.strip():
            return False
        allowed_prefixes = context_pack.get("library_filename_prefixes", [])
        if not isinstance(allowed_prefixes, list) or not allowed_prefixes:
            return True
        source_upper = source_path.upper()
        for prefix in allowed_prefixes:
            pref = str(prefix).strip().upper()
            if not pref:
                continue
            if pref in source_upper:
                return True
        return False

    def _clamp01(self, value: Any) -> float:
        try:
            f = float(value)
        except Exception:
            return 0.0
        return max(0.0, min(1.0, f))

    def _uses_loose_evidence_filter(self, target_path: str) -> bool:
        value = str(target_path or "").strip()
        return value.startswith("n0.art_direction") or value.startswith("n0.sound_direction")

    def _build_evidence_terms(self, context_pack: Dict[str, Any]) -> List[str]:
        chunks: List[str] = []
        for key in ("strategy_question", "core_summary", "writing_typology", "target_path"):
            value = context_pack.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip().lower())
        return self._tokenize(" ".join(chunks))

    def _target_guidance_terms(self, target_path: str) -> List[str]:
        base = ["write", "guidance", "method", "structure", "clarity", "stake", "arc"]
        if not isinstance(target_path, str):
            return base
        if target_path.startswith("n0.narrative_presentation") or target_path.startswith(
            "n0.production_summary"
        ):
            return base + ["summary", "factual", "stakeholders", "conflict", "theme"]
        if target_path.startswith("n0.art_direction"):
            return base + ["visual", "aesthetic", "palette", "lighting", "composition"]
        if target_path.startswith("n0.sound_direction"):
            return base + ["sound", "music", "ambience", "sfx", "rhythm", "timbre"]
        if target_path.startswith("n1.characters"):
            return base + ["character", "role", "motivation", "backstory", "appearance"]
        return base

    def _tokenize(self, text: str) -> List[str]:
        if not isinstance(text, str) or not text.strip():
            return []
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "into",
            "your",
            "their",
            "have",
            "has",
            "was",
            "are",
            "you",
            "its",
        }
        tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
        uniq: List[str] = []
        for token in tokens:
            if token in stop_words:
                continue
            if token not in uniq:
                uniq.append(token)
        return uniq

    def _term_overlap_score(self, text: str, terms: List[str]) -> float:
        if not text or not terms:
            return 0.0
        cap = max(1, min(len(terms), 14))
        matched = sum(1 for term in terms[:40] if term in text)
        return min(1.0, matched / cap)

    def _specificity_score(self, text: str) -> float:
        if not text:
            return 0.0
        tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
        if not tokens:
            return 0.0
        unique_ratio = len(set(tokens)) / max(1, len(tokens))
        length_boost = min(1.0, len(text) / 700.0)
        score = (0.65 * unique_ratio) + (0.35 * length_boost)
        return max(0.0, min(1.0, score))

    def _default_style_guidelines(self, writing_typology: str) -> List[str]:
        if writing_typology == "summary":
            return ["Concise", "Objective", "No new information"]
        if writing_typology == "pitch":
            return ["Punchy", "Clear stakes", "One-paragraph arc"]
        if writing_typology == "character":
            return ["Concrete traits", "Actionable descriptors", "Consistent tone"]
        if writing_typology == "scene":
            return ["Visual clarity", "Action-driven", "Maintain continuity"]
        if writing_typology == "prompting":
            return ["Tool-ready", "Precise tokens", "Avoid ambiguity"]
        return ["Clear", "Consistent", "No invention"]

    def _default_structure_guidelines(self, writing_typology: str) -> List[str]:
        if writing_typology == "summary":
            return ["Single paragraph, 8-12 sentences", "Lead with the core idea", "Keep to target length"]
        if writing_typology == "pitch":
            return ["Protagonist", "Goal", "Obstacle", "Stakes"]
        if writing_typology == "character":
            return ["Role", "Function", "Description", "Visual markers"]
        if writing_typology == "scene":
            return ["Situation", "Action", "Outcome", "Continuity note"]
        if writing_typology == "prompting":
            return ["Goal", "Prompt", "Inputs/Outputs", "Notes"]
        return ["Structured", "Ordered", "Concise"]

    def _build_strategy_output(
        self,
        context_pack: Dict[str, Any],
        card: StrategyCard,
        strategy_question: Any,
        rag_hits: List[Dict[str, Any]],
    ) -> str:
        llm_text = self._build_strategy_output_llm(
            context_pack=context_pack,
            card=card,
            strategy_question=strategy_question,
            rag_hits=rag_hits,
        )
        if not llm_text:
            llm_text = self._build_strategy_text_fallback(context_pack, card)
        strategy_text = self._normalize_strategy_text(llm_text, min_len=0, max_len=3800)
        return strategy_text

    def _build_strategy_output_llm(
        self,
        context_pack: Dict[str, Any],
        card: StrategyCard,
        strategy_question: Any,
        rag_hits: List[Dict[str, Any]],
    ) -> str:
        if not self.llm_client:
            return ""
        payload = self._build_strategy_payload(context_pack, card, strategy_question, rag_hits)
        system_prompt = (
            "You are a strategy finder. Your job is to synthesize an editorial writing strategy "
            "for a redactor based on the provided context and library sources.\n"
            "Return ONLY valid JSON with this schema:\n"
            '{ "strategy_text": "" }\n'
            "- strategy_text must be in English and structured as numbered steps (1., 2., 3., ...).\n"
            "- The number of steps MUST equal expected_steps from payload.\n"
            "- Keep source order exactly as provided in payload.sources (sorted by score).\n"
            "- Step i MUST be grounded in payload.sources[i-1] (summary + excerpt + key_concepts).\n"
            "- Use every provided source exactly once, no omission and no reordering.\n"
            "- Each step must be explicit and action-oriented.\n"
            "- Focus strictly on the library sources and the provided context.\n"
            "- Every step must be directly traceable to its provided source summary/excerpt/key_concepts.\n"
            "- Do not introduce frameworks, methods, or terminology absent from provided sources.\n"
            "- Focus on narrative content only: plot, characters, stakes, themes, and arc.\n"
            "- Exclude production, direction, technical aspects, art direction, sound, duration, and audience/market reception.\n"
            "- Do NOT mention author names, book titles, or sources.\n"
            "- Do NOT restate the input context verbatim or list fields.\n"
            "- Do NOT quote or repeat the strategy question.\n"
            "- Preserve concrete concepts from each source.\n"
            "- Return JSON only (no markdown, no bullets)."
        )
        user_prompt = json.dumps(payload, ensure_ascii=True, indent=2)
        try:
            response = self.llm_client.complete(
                LLMRequest(
                    model=self.llm_client.default_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.0,
                    max_tokens=2400,
                )
            )
        except Exception:
            return ""
        return self._extract_strategy_payload(response.content)

    def _build_strategy_payload(
        self,
        context_pack: Dict[str, Any],
        card: StrategyCard,
        strategy_question: Any,
        rag_hits: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        target_current = context_pack.get("target_current")
        allowed_fields = context_pack.get("allowed_fields", [])
        writing_mode = context_pack.get("writing_mode", "")

        filtered_current = target_current
        if isinstance(target_current, dict) and isinstance(allowed_fields, list) and allowed_fields:
            filtered_current = {
                key: value for key, value in target_current.items() if key in allowed_fields
            }

        # Decide creation vs edit based on the actual target text field(s),
        # not on other auto-filled fields (e.g. aspect_ratio).
        if writing_mode == "create":
            mode = "write"
            existing_excerpt = ""
        elif writing_mode == "edit":
            existing_excerpt = self._extract_existing_excerpt(filtered_current, limit=420)
            mode = "edit" if existing_excerpt else "write"
        else:
            existing_excerpt = self._extract_existing_excerpt(filtered_current, limit=420)
            mode = "edit" if existing_excerpt else "write"
        sources = []
        ordered_hits = [
            hit for hit in rag_hits if isinstance(hit, dict)
        ]
        ordered_hits.sort(
            key=lambda row: float(row.get("score", 0) or 0),
            reverse=True,
        )
        for rank_idx, hit in enumerate(ordered_hits, start=1):
            if not isinstance(hit, dict):
                continue
            summary = hit.get("summary") or hit.get("excerpt") or ""
            excerpt = str(hit.get("excerpt", "") or "")
            raw_key_concepts = hit.get("key_concepts", [])
            if isinstance(raw_key_concepts, list):
                key_concepts = [str(item) for item in raw_key_concepts]
            else:
                key_concepts = []
            sources.append(
                {
                    "rank": rank_idx,
                    "title": hit.get("title", ""),
                    "author": hit.get("author", ""),
                    "summary": str(summary),
                    "excerpt": excerpt,
                    "key_concepts": key_concepts,
                    "score": float(hit.get("score", 0) or 0),
                    "evidence_role": str(hit.get("evidence_role", "")),
                    "evidence_relevance": float(hit.get("evidence_relevance", 0) or 0),
                    "evidence_actionability": float(hit.get("evidence_actionability", 0) or 0),
                    "evidence_specificity": float(hit.get("evidence_specificity", 0) or 0),
                }
            )
        return {
            "target_path": card.target_path,
            "writing_typology": card.writing_typology,
            "mode": mode,
            "strategy_question": strategy_question if isinstance(strategy_question, str) else "",
            "project_summary": self._trim_text(str(context_pack.get("core_summary", "")), 240),
            "primary_objective": self._trim_text(
                str(context_pack.get("brief_primary_objective", "")), 200
            ),
            "constraints": context_pack.get("brief_constraints", []),
            "redaction_constraints": context_pack.get("redaction_constraints", {}),
            "existing_excerpt": existing_excerpt,
            "expected_steps": len(sources),
            "sources": sources,
        }

    def _extract_existing_excerpt(self, target_current: Any, limit: int) -> str:
        if isinstance(target_current, str) and target_current.strip():
            return self._trim_text(target_current, limit)
        if isinstance(target_current, dict):
            parts = []
            for key, value in target_current.items():
                if isinstance(value, str) and value.strip():
                    parts.append(f"{key}: {value.strip()}")
            return self._trim_text(" | ".join(parts), limit)
        return ""

    def _trim_text(self, text: str, limit: int) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        if len(cleaned) <= limit:
            return cleaned
        snippet = cleaned[:limit].rsplit(" ", 1)[0].strip()
        return f"{snippet}..." if snippet else f"{cleaned[:limit]}..."

    def _normalize_key_concepts(
        self,
        raw_concepts: Any,
        summary: str,
        excerpt: str,
        limit: int = 6,
    ) -> List[str]:
        concepts: List[str] = []
        if isinstance(raw_concepts, list):
            for item in raw_concepts:
                text = " ".join(str(item or "").split()).strip(" -:;,.")
                if text:
                    concepts.append(text)
        # Do not summarize concepts: keep full phrases, only deduplicate.
        if not concepts:
            for source_text in (summary, excerpt):
                if not isinstance(source_text, str) or not source_text.strip():
                    continue
                chunks = re.split(r"[.;:!?]\s+|\n+", source_text)
                for chunk in chunks:
                    candidate = " ".join(chunk.split()).strip(" -:;,.")
                    if candidate:
                        concepts.append(candidate)

        unique: List[str] = []
        seen: set[str] = set()
        for item in concepts:
            cleaned = " ".join(str(item or "").split()).strip(" -:;,.")
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(cleaned)
            if len(unique) >= max(1, limit):
                break
        return unique

    def _extract_strategy_payload(self, content: str) -> str:
        if not content:
            return ""
        text = content.strip()
        parsed = self._try_parse_json(text)
        if parsed is None and "```" in text:
            blocks = re.split(r"```+", text)
            if len(blocks) >= 2:
                fenced = blocks[1].strip()
                if "\n" in fenced and fenced.split("\n", 1)[0].strip().lower() in {
                    "json",
                    "text",
                    "plain",
                }:
                    fenced = fenced.split("\n", 1)[1].strip()
                parsed = self._try_parse_json(fenced)
                if parsed is None:
                    text = fenced
        if isinstance(parsed, dict):
            strategy_text = parsed.get("strategy_text", "")
        else:
            strategy_text = text
        return self._clean_strategy_text(strategy_text)

    def _try_parse_json(self, text: str) -> Dict[str, Any] | None:
        if not text or not text.strip().startswith("{"):
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _clean_strategy_text(self, text: Any) -> str:
        if not isinstance(text, str):
            return ""
        cleaned = text.strip()
        if cleaned.lower().startswith("strategy_text"):
            parts = cleaned.split(":", 1)
            if len(parts) == 2:
                cleaned = parts[1].strip()
        if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 2:
            cleaned = cleaned[1:-1].strip()
        return cleaned

    def _build_strategy_text_fallback(
        self,
        context_pack: Dict[str, Any],
        card: StrategyCard,
    ) -> str:
        sentences: List[str] = []
        target_label = card.target_path or "the requested section"
        sentences.append(
            f"This strategy targets {target_label} and must guide precise, usable writing."
        )
        if card.writing_typology:
            sentences.append(f"Writing typology: {card.writing_typology}.")
        core_summary = context_pack.get("core_summary", "")
        brief_primary = context_pack.get("brief_primary_objective", "")
        if isinstance(core_summary, str) and core_summary.strip():
            sentences.append(f"Project summary: {core_summary.strip()}.")
        elif isinstance(brief_primary, str) and brief_primary.strip():
            sentences.append(f"Primary objective: {brief_primary.strip()}.")
        constraints = context_pack.get("brief_constraints", [])
        if isinstance(constraints, list) and constraints:
            constraints_line = ", ".join([str(item) for item in constraints if str(item).strip()])
            if constraints_line:
                sentences.append(f"Constraints: {constraints_line}.")
        if card.source_refs:
            sentences.append(
                "Anchor sources are available but must remain implicit in the guidance."
            )
        sentences.append(
            "Prioritize factual specificity, continuity with the current state, and no invention."
        )
        sentences.append(
            "Use concrete language, short sentences, and verbs over qualifiers."
        )
        sentences.append(
            "Deliver text that is directly usable downstream, without extra interpretation."
        )

        paragraph = " ".join(sentences)
        return " ".join(paragraph.split())

    def _normalize_strategy_text(self, text: str, min_len: int, max_len: int) -> str:
        if not text:
            return ""
        padding_pool = [
            "If information is missing, keep the wording generic instead of adding new facts.",
            "Avoid decorative adjectives and keep the phrasing sober and factual.",
            "Keep the narrative focus on the role of the section within the project and its concrete function.",
            "Use explicit constraints as anchors for what must be stated or omitted.",
            "Maintain coherence with the project summary and declared intentions.",
            "Ground guidance in the retrieved sources and avoid claims not supported by them.",
            "When relevant, articulate the expected reader effect and functional purpose of the section.",
            "Favor concrete nouns and actions over abstract claims or meta-commentary.",
            "Preserve continuity with existing project tone, scope, and deliverables.",
            "Prefer disciplined structure over descriptive flourish to keep the text actionable.",
            "Keep the strategy focused on how to write, not on re-explaining the content.",
        ]
        if len(text) < min_len:
            idx = 0
            while len(text) < min_len and padding_pool:
                text = f"{text} {padding_pool[idx % len(padding_pool)]}"
                idx += 1
        if len(text) > max_len:
            text = self._trim_to_limit(text, max_len)
        return text

    def _trim_to_limit(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        snippet = text[:limit]
        last_period = snippet.rfind(". ")
        if last_period > 200:
            return snippet[: last_period + 1].strip()
        return snippet.strip()

    def _write_strategy_log(
        self,
        context_pack: Dict[str, Any],
        card: StrategyCard,
        strategy_question: Any,
        strategy_payload: Dict[str, Any],
        evidence_report: Dict[str, Any],
    ) -> None:
        project_id = context_pack.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            return
        try:
            root = get_project_root(project_id)
            strata = ""
            if isinstance(card.target_path, str) and card.target_path.strip():
                strata = card.target_path.split(".", 1)[0].strip().lower()
            if not re.fullmatch(r"n[0-9]+", strata or ""):
                strata = "misc"
            log_dir = root / "strategy_logs" / strata
            log_dir.mkdir(parents=True, exist_ok=True)
            safe_target = "".join(
                c for c in (card.target_path or "strategy") if c.isalnum() or c in ("-", "_", ".")
            ).strip()
            safe_target = safe_target.replace(".", "_") if safe_target else "strategy"
            filename = f"{generate_timestamp()}_{safe_target}.json"
            payload = {
                "project_id": project_id,
                "target_path": card.target_path,
                "writing_typology": card.writing_typology,
                "strategy_id": card.strategy_id,
                "strategy_question": strategy_question if isinstance(strategy_question, str) else "",
                "strategy_context_payload": strategy_payload
                if isinstance(strategy_payload, dict)
                else {},
                "evidence_report": evidence_report if isinstance(evidence_report, dict) else {},
                "strategy_text": card.strategy_text,
                "library_item_ids": card.library_item_ids,
                "source_refs": card.source_refs,
                "notes": card.notes,
                "logged_at": generate_timestamp(),
            }
            (log_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
            )
        except Exception:
            return

    def _write_rag_log(
        self,
        context_pack: Dict[str, Any],
        target_path: str,
        writing_typology: str,
        rag_mode: str,
        rag_hit_count: int,
        rag_error_detail: str,
        rag_reason: str,
        rag_policy_path: List[str],
        rag_retry: str,
        rag_conversation_id: str,
        evidence_report: Dict[str, Any],
        library_item_ids: List[str],
        source_refs: List[str],
    ) -> None:
        project_id = context_pack.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            return
        try:
            root = get_project_root(project_id)
            log_dir = root / "rag_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            safe_target = "".join(
                c for c in (target_path or "rag") if c.isalnum() or c in ("-", "_", ".")
            ).strip()
            safe_target = safe_target.replace(".", "_") if safe_target else "rag"
            filename = f"{generate_timestamp()}_{safe_target}.json"
            warning = ""
            if rag_mode != "agentic":
                warning = f"rag_mode={rag_mode}"
            elif rag_hit_count <= 0:
                warning = "rag_hits=0"
            payload = {
                "project_id": project_id,
                "target_path": target_path,
                "writing_typology": writing_typology,
                "rag_mode": rag_mode,
                "rag_hits": rag_hit_count,
                "error_detail": rag_error_detail if isinstance(rag_error_detail, str) else "",
                "rag_reason": rag_reason if isinstance(rag_reason, str) else "",
                "rag_policy_path": rag_policy_path if isinstance(rag_policy_path, list) else [],
                "rag_retry": rag_retry if isinstance(rag_retry, str) else "",
                "rag_conversation_id": rag_conversation_id
                if isinstance(rag_conversation_id, str)
                else "",
                "client_available": bool(getattr(self._rag, "_client", None)),
                "r2r_base": getattr(self._rag, "_base_url", ""),
                "rag_input_context_pack_compact": self._compact_context_for_rag_log(context_pack),
                "rag_request_payload": (
                    getattr(self._rag, "last_request_payload", {})
                    if isinstance(getattr(self._rag, "last_request_payload", {}), dict)
                    else {}
                ),
                "rag_response_debug": (
                    getattr(self._rag, "last_response_debug", {})
                    if isinstance(getattr(self._rag, "last_response_debug", {}), dict)
                    else {}
                ),
                "evidence_report": evidence_report if isinstance(evidence_report, dict) else {},
                "library_item_ids": library_item_ids,
                "source_refs": source_refs,
                "warning": warning,
                "readable_report": self._build_readable_rag_report(
                    target_path=target_path,
                    writing_typology=writing_typology,
                    context_compact=self._compact_context_for_rag_log(context_pack),
                    request_payload=(
                        getattr(self._rag, "last_request_payload", {})
                        if isinstance(getattr(self._rag, "last_request_payload", {}), dict)
                        else {}
                    ),
                    response_debug=(
                        getattr(self._rag, "last_response_debug", {})
                        if isinstance(getattr(self._rag, "last_response_debug", {}), dict)
                        else {}
                    ),
                    evidence_report=evidence_report if isinstance(evidence_report, dict) else {},
                    library_item_ids=library_item_ids,
                    source_refs=source_refs,
                    rag_mode=rag_mode,
                    rag_reason=rag_reason,
                ),
                "logged_at": generate_timestamp(),
            }
            (log_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
            )
        except Exception:
            return

    def _compact_context_for_rag_log(self, context_pack: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(context_pack, dict):
            return {}
        compact = {
            "target_path": context_pack.get("target_path", ""),
            "writing_typology": context_pack.get("writing_typology", ""),
            "strategy_question": self._trim_text(str(context_pack.get("strategy_question", "")), 500),
            "core_summary": self._trim_text(str(context_pack.get("core_summary", "")), 500),
            "brief_video_type": context_pack.get("brief_video_type", ""),
            "brief_target_duration_s": context_pack.get("brief_target_duration_s", 0),
            "brief_target_duration_text": context_pack.get("brief_target_duration_text", ""),
            "redaction_constraints": context_pack.get("redaction_constraints", {}),
            "allowed_fields": context_pack.get("allowed_fields", []),
            "writing_mode": context_pack.get("writing_mode", ""),
            "library_filename_prefixes": context_pack.get("library_filename_prefixes", []),
            "rag_conversation_id": context_pack.get("rag_conversation_id", ""),
        }
        return compact

    def _build_readable_rag_report(
        self,
        *,
        target_path: str,
        writing_typology: str,
        context_compact: Dict[str, Any],
        request_payload: Dict[str, Any],
        response_debug: Dict[str, Any],
        evidence_report: Dict[str, Any],
        library_item_ids: List[str],
        source_refs: List[str],
        rag_mode: str,
        rag_reason: str,
    ) -> Dict[str, Any]:
        query_text = str(request_payload.get("query_text", "")).strip()
        query_architecture = str(request_payload.get("query_text_architecture", "")).strip()
        query_context_object = str(request_payload.get("query_context_object", "")).strip()
        if not query_text:
            terms = request_payload.get("query_terms", [])
            if isinstance(terms, list) and terms:
                query_text = " ".join([str(term) for term in terms if str(term).strip()])
        context_input = ""
        if query_context_object:
            context_input = query_context_object
        elif "CONTEXT_INPUT:" in query_text:
            _, _, suffix = query_text.partition("CONTEXT_INPUT:")
            context_input = suffix.strip()
        elif "TASK_INPUT:" in query_text:
            # Backward compatibility with older logs/query payloads.
            _, _, suffix = query_text.partition("TASK_INPUT:")
            context_input = suffix.strip()
        readable = {
            "summary": {
                "status": str(evidence_report.get("status", "")),
                "rag_mode": rag_mode,
                "rag_reason": rag_reason,
                "kept_sources": int(evidence_report.get("kept_count", 0) or 0),
                "raw_sources": int(evidence_report.get("raw_count", 0) or 0),
            },
            "inputs": {
                "target_path": target_path,
                "writing_typology": writing_typology,
                "strategy_question": str(context_compact.get("strategy_question", "")),
                "core_summary": str(context_compact.get("core_summary", "")),
            },
            "task": {
                "query_text": query_text,
                "query_architecture": query_architecture,
                "query_context_object": query_context_object,
                "context_input": context_input,
                "writing_mode": str(context_compact.get("writing_mode", "")),
                "allowed_fields": context_compact.get("allowed_fields", []),
                "redaction_constraints": context_compact.get("redaction_constraints", {}),
            },
            "retrieval": {
                "path": str(request_payload.get("path", "")),
                "engine_mode": str(request_payload.get("mode", "")),
                "fallback_origin": str(request_payload.get("fallback_origin", "")),
                "fallback_exception_class": str(
                    request_payload.get("fallback_exception_class", "")
                ),
                "fallback_exception": str(request_payload.get("fallback_exception", "")),
                "fallback_from_request_payload": request_payload.get(
                    "fallback_from_request_payload", {}
                ),
                "search_settings": request_payload.get("search_settings", {}),
                "library_filename_prefixes": context_compact.get("library_filename_prefixes", []),
                "candidate_files": request_payload.get("allowed_filenames", []),
                "candidate_files_count": len(request_payload.get("allowed_filenames", []) or []),
                "agent_response_debug": {
                    "raw_agent_message": str(response_debug.get("raw_agent_message", "")),
                    "raw_citations_count": int(response_debug.get("raw_citations_count", 0) or 0),
                    "parsed_agent_items_count": int(
                        response_debug.get("parsed_agent_items_count", 0) or 0
                    ),
                    "merged_hits_count": int(response_debug.get("merged_hits_count", 0) or 0),
                    "fallback_origin": str(response_debug.get("fallback_origin", "")),
                    "fallback_exception_class": str(
                        response_debug.get("fallback_exception_class", "")
                    ),
                    "fallback_exception": str(response_debug.get("fallback_exception", "")),
                    "exploratory_error": str(response_debug.get("exploratory_error", "")),
                },
            },
            "evidence": {
                "score_mode": str(evidence_report.get("score_mode", "")),
                "thresholds": evidence_report.get("thresholds", {}),
                "mix": evidence_report.get("evidence_mix", {}),
                "details": evidence_report.get("details", []),
            },
            "output": {
                "library_item_ids": library_item_ids,
                "source_refs_count": len(source_refs),
                "source_refs_preview": source_refs[:3],
            },
        }
        return readable

    def _resolve_rag_conversation_id(self, project_id: str, target_path: str) -> str:
        key = self._rag_conversation_key(target_path)
        legacy_key = self._legacy_rag_conversation_key(target_path)
        path = self._rag_meta_path(project_id)
        payload = self._read_json_file(path)
        conversations = payload.get("conversations", {}) if isinstance(payload, dict) else {}
        if not isinstance(conversations, dict):
            conversations = {}
        existing = conversations.get(key)
        if isinstance(existing, str):
            existing_uuid = self._to_uuid_or_empty(existing)
            if existing_uuid and self._rag.conversation_exists(existing_uuid, target_path=target_path):
                return existing_uuid
        if legacy_key != key:
            legacy_existing = conversations.get(legacy_key)
            if isinstance(legacy_existing, str):
                legacy_uuid = self._to_uuid_or_empty(legacy_existing)
                if legacy_uuid and self._rag.conversation_exists(legacy_uuid, target_path=target_path):
                    conversations[key] = legacy_uuid
                    next_payload = {
                        "project_id": project_id,
                        "updated_at": generate_timestamp(),
                        "conversations": conversations,
                    }
                    self._write_json_file(path, next_payload)
                    return legacy_uuid
        new_uuid = self._rag.create_conversation(name=f"{project_id}:{key}", target_path=target_path)
        if not new_uuid:
            return ""
        conversations[key] = new_uuid
        next_payload = {
            "project_id": project_id,
            "updated_at": generate_timestamp(),
            "conversations": conversations,
        }
        self._write_json_file(path, next_payload)
        return new_uuid

    def _rag_conversation_key(self, target_path: str) -> str:
        if not isinstance(target_path, str):
            return "path:default"
        normalized = re.sub(r"[^a-z0-9._-]+", "_", target_path.strip().lower())
        normalized = re.sub(r"_+", "_", normalized).strip("._-")
        return f"path:{normalized or 'default'}"

    def _should_use_rag_conversation_id(self, target_path: str) -> bool:
        return bool(str(target_path or "").strip())

    def _legacy_rag_conversation_key(self, target_path: str) -> str:
        if not isinstance(target_path, str) or not target_path.strip():
            return "default"
        head = target_path.split(".", 1)[0].strip().lower()
        if re.fullmatch(r"n[0-9]+", head):
            return head
        return "default"

    def _should_rotate_rag_conversation_id(self, response_debug: Any, last_error: str) -> bool:
        if isinstance(response_debug, dict) and bool(response_debug.get("conversation_not_found")):
            return True
        haystack = " ".join(
            [
                str(last_error or ""),
                str((response_debug or {}).get("fallback_exception", ""))
                if isinstance(response_debug, dict)
                else "",
            ]
        ).lower()
        return "conversation" in haystack and "not found" in haystack

    def _rotate_rag_conversation_id(self, project_id: str, target_path: str) -> str:
        key = self._rag_conversation_key(target_path)
        path = self._rag_meta_path(project_id)
        payload = self._read_json_file(path)
        conversations = payload.get("conversations", {}) if isinstance(payload, dict) else {}
        if not isinstance(conversations, dict):
            conversations = {}
        new_uuid = self._rag.create_conversation(name=f"{project_id}:{key}", target_path=target_path)
        if not new_uuid:
            return ""
        conversations[key] = new_uuid
        next_payload = {
            "project_id": project_id,
            "updated_at": generate_timestamp(),
            "conversations": conversations,
        }
        self._write_json_file(path, next_payload)
        return new_uuid

    def _rag_meta_path(self, project_id: str) -> Path:
        root = get_project_root(project_id)
        safe_project = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_project:
            safe_project = "default"
        return root / "metadata" / f"{safe_project}_RAG_META.json"

    def _to_uuid_or_empty(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        candidate = value.strip()
        if not candidate:
            return ""
        try:
            parsed = uuid.UUID(candidate)
        except Exception:
            return ""
        return str(parsed)

    def _update_rag_metrics(self, project_id: str, rag_mode: str, rag_reason: str) -> None:
        if not isinstance(project_id, str) or not project_id:
            return
        system_path = get_data_root() / "_system" / "rag_metrics.json"
        project_path = get_project_root(project_id) / "rag_metrics.json"
        self._apply_metric_update(system_path, rag_mode, rag_reason)
        self._apply_metric_update(project_path, rag_mode, rag_reason)

    def _apply_metric_update(self, path: Path, rag_mode: str, rag_reason: str) -> None:
        payload = self._read_json_file(path)
        if not isinstance(payload, dict):
            payload = {}
        total = payload.get("total_requests", 0)
        if not isinstance(total, int):
            total = 0
        total += 1
        modes = payload.get("modes", {})
        if not isinstance(modes, dict):
            modes = {}
        reasons = payload.get("reasons", {})
        if not isinstance(reasons, dict):
            reasons = {}
        mode_key = rag_mode if isinstance(rag_mode, str) and rag_mode else "unknown"
        reason_key = rag_reason if isinstance(rag_reason, str) and rag_reason else "unknown"
        modes[mode_key] = int(modes.get(mode_key, 0)) + 1
        reasons[reason_key] = int(reasons.get(reason_key, 0)) + 1
        fallback_count = sum(
            int(count)
            for mode, count in modes.items()
            if isinstance(mode, str) and mode.startswith("fallback")
        )
        fallback_rate = round(fallback_count / total, 4) if total > 0 else 0.0
        next_payload = {
            **payload,
            "total_requests": total,
            "modes": modes,
            "reasons": reasons,
            "fallback_rate": fallback_rate,
            "updated_at": generate_timestamp(),
            "signature": hashlib.sha256(
                f"{total}|{mode_key}|{reason_key}|{generate_timestamp()}".encode("utf-8")
            ).hexdigest()[:16],
        }
        self._write_json_file(path, next_payload)

    def _read_json_file(self, path: Path) -> Dict[str, Any]:
        try:
            if not path.exists():
                return {}
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                return {}
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}

    def _write_json_file(self, path: Path, payload: Dict[str, Any]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        except Exception:
            return
