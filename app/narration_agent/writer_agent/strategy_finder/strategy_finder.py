"""Strategy finder to select writing strategy from the library index."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List

from app.utils.ids import generate_timestamp
from app.utils.project_storage import get_project_root

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
        target_path = context_pack.get("target_path", "")
        writing_typology = context_pack.get("writing_typology", "")
        language = context_pack.get("style_constraints", {}).get("language", "") or ""

        candidates = self._filter_library_items(writing_typology, language)
        rag_hits = self._rag.retrieve(context_pack, limit=3)
        library_item_ids = [hit.get("id") for hit in rag_hits if hit.get("id")]
        if not library_item_ids:
            library_item_ids = [item.get("id") for item in candidates if item.get("id")]
        source_refs = []
        for hit in rag_hits:
            title = hit.get("title", "").strip()
            author = hit.get("author", "").strip()
            excerpt = hit.get("excerpt", "").strip()
            summary = hit.get("summary", "").strip()
            concepts = hit.get("key_concepts", [])
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
        notes = (
            "Auto-selected based on writing typology and language."
            f" rag_mode={rag_mode}, rag_hits={rag_hit_count}."
        )
        self._write_rag_log(
            context_pack=context_pack,
            target_path=target_path,
            writing_typology=writing_typology,
            rag_mode=rag_mode,
            rag_hit_count=rag_hit_count,
            library_item_ids=library_item_ids,
            source_refs=source_refs,
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
        strategy_text = self._build_strategy_output(
            context_pack, card, strategy_question, rag_hits
        )
        card.strategy_text = strategy_text
        self._write_strategy_log(context_pack, card, strategy_question)
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
        strategy_text = self._normalize_strategy_text(llm_text, min_len=1650, max_len=1950)
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
            "- strategy_text must be ONE paragraph in English, 1650-1950 characters.\n"
            "- strategy_text must describe exactly 5 ordered steps (in prose, not bullets).\n"
            "- Each step must be explicit and action-oriented.\n"
            "- Focus strictly on the library sources and the provided context.\n"
            "- Focus on narrative content only: plot, characters, stakes, themes, and arc.\n"
            "- Exclude production, direction, technical aspects, art direction, sound, duration, and audience/market reception.\n"
            "- Do NOT mention author names, book titles, or sources.\n"
            "- Do NOT restate the input context verbatim or list fields.\n"
            "- Do NOT quote or repeat the strategy question.\n"
            "- Use at least two concrete concepts drawn from the provided sources.\n"
            "- If information is missing, keep guidance generic.\n"
            "- Return JSON only (no markdown, no bullets)."
        )
        user_prompt = json.dumps(payload, ensure_ascii=True, indent=2)
        try:
            response = self.llm_client.complete(
                LLMRequest(
                    model=self.llm_client.default_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.2,
                    max_tokens=1600,
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
        for hit in rag_hits:
            if not isinstance(hit, dict):
                continue
            summary = hit.get("summary") or hit.get("excerpt") or ""
            sources.append(
                {
                    "title": hit.get("title", ""),
                    "author": hit.get("author", ""),
                    "summary": self._trim_text(str(summary), 280),
                    "key_concepts": hit.get("key_concepts", [])[:6]
                    if isinstance(hit.get("key_concepts"), list)
                    else [],
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
    ) -> None:
        project_id = context_pack.get("project_id")
        if not isinstance(project_id, str) or not project_id:
            return
        try:
            root = get_project_root(project_id)
            log_dir = root / "strategy_logs"
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
                "client_available": bool(getattr(self._rag, "_client", None)),
                "r2r_base": getattr(self._rag, "_base_url", ""),
                "library_item_ids": library_item_ids,
                "source_refs": source_refs,
                "warning": warning,
                "logged_at": generate_timestamp(),
            }
            (log_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
            )
        except Exception:
            return
