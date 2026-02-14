"""Writer orchestrator that pilots context, strategy, and redactor."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.narration.state_merger import merge_target_patch
from app.narration_agent.spec_loader import load_json, load_text
from app.narration_agent.writer_agent.context_builder.context_builder import ContextBuilder
from app.narration_agent.writer_agent.prompt_compiler import RedactorPromptCompiler
from app.narration_agent.writer_agent.strategy_finder.strategy_finder import StrategyFinder
from app.narration_agent.writer_agent.n_rules.n0_rules import (
    infer_n0_deliverables,
    infer_n0_production_summary,
    infer_n0_visual_style_tone,
)
from app.narration_agent.writer_agent.redactor.redactor import Redactor
from app.utils.project_storage import get_project_root


@dataclass
class WritingPlan:
    target_path: str
    base_patch: Dict[str, Any] = field(default_factory=dict)
    allowed_fields: Optional[List[str]] = None
    redaction_constraints: Dict[str, int] = field(default_factory=dict)
    use_strategy: bool = True
    skip_llm: bool = False
    extra_rule: str = ""
    strategy_role: str = ""
    strategy_hints: List[str] = field(default_factory=list)
    redaction_rules: List[str] = field(default_factory=list)
    quality_criteria: List[str] = field(default_factory=list)
    writer_self_question: str = ""
    strategy_finder_question: str = ""
    library_filename_prefixes: List[str] = field(default_factory=list)
    context_group_specs: List[Dict[str, Any]] = field(default_factory=list)
    rule_mode: str = ""


@dataclass
class AgenticDecision:
    action: str
    reason: str
    raw_output: str = ""


@dataclass
class AgenticEvaluation:
    score: float
    passed: bool
    issues: List[str]
    rewrite: bool
    needs_strategy: bool
    raw_output: str = ""


@dataclass
class RedactionCycleResult:
    parsed: bool
    filtered_patch: Dict[str, Any]
    open_questions: List[str]
    raw_output: str
    warning: str = ""
    meta_violations: List[Dict[str, Any]] = field(default_factory=list)
    length_violations: List[Dict[str, int]] = field(default_factory=list)
    attempts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class WriterRunResult:
    status: str
    target_path: str
    target_patch: Dict[str, Any]
    open_questions: List[str]
    context_pack: Dict[str, Any]
    strategy_card: Dict[str, Any]
    warning: str = ""
    raw_output: str = ""
    error: str = ""
    agentic_trace: List[Dict[str, Any]] = field(default_factory=list)


class WriterOrchestrator:
    @staticmethod
    def _normalize_target_path(target_path: str) -> str:
        value = str(target_path or "").strip()
        if value.startswith("n0.production_summary"):
            return value.replace("n0.production_summary", "n0.narrative_presentation", 1)
        return value

    def _context_pack_for_redactor(self, context_pack: Dict[str, Any]) -> Dict[str, Any]:
        """Remove debug-only keys that must never be fed back to the redactor."""
        if not isinstance(context_pack, dict):
            return {}
        # Prevent "prompt-in-prompt" feedback loops:
        # redaction_attempts contains previous prompts and debug logs.
        cleaned = {**context_pack}
        cleaned.pop("redaction_attempts", None)

        # Reduce large state blobs for the redactor (keep sparse lists instead).
        # ContextBuilder provides *_non_empty lists; fall back to removing heavy keys.
        if "dependencies_non_empty" in cleaned:
            cleaned["dependencies"] = cleaned.get("dependencies_non_empty", [])
        cleaned.pop("dependencies_non_empty", None)

        if "target_strata_non_empty" in cleaned:
            cleaned["target_strata_data"] = cleaned.get("target_strata_non_empty", [])
        cleaned.pop("target_strata_non_empty", None)

        # Schema is rarely useful for text redaction and is often empty/noisy.
        cleaned.pop("target_schema", None)

        # Keep only non-empty values in target_current (but preserve existing text).
        target_current = cleaned.get("target_current")
        if isinstance(target_current, dict):
            filtered_current = {}
            for k, v in target_current.items():
                if isinstance(v, str):
                    if v.strip():
                        filtered_current[k] = v
                elif v is None:
                    continue
                elif isinstance(v, (list, dict)):
                    if v:
                        filtered_current[k] = v
                else:
                    filtered_current[k] = v
            cleaned["target_current"] = filtered_current

        # Prune N1 full blobs inside context_groups payload (keep only non-empty leaves).
        groups = cleaned.get("context_groups")
        if isinstance(groups, list):
            new_groups = []
            for g in groups:
                if not isinstance(g, dict):
                    continue
                payload = g.get("payload")
                if isinstance(payload, dict) and isinstance(payload.get("n1"), dict):
                    try:
                        from app.narration_agent.writer_agent.context_builder.context_builder import (
                            _collect_non_empty_fields,
                        )
                    except Exception:
                        _collect_non_empty_fields = None  # type: ignore
                    if _collect_non_empty_fields:
                        payload = {**payload}
                        payload["n1"] = _collect_non_empty_fields(payload.get("n1"), base_path="n1")
                        g = {**g, "payload": payload}
                new_groups.append(g)
            cleaned["context_groups"] = new_groups
        return cleaned

    """Build a deterministic writing plan and run the redactor."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.context_builder = ContextBuilder()
        self.strategy_finder = StrategyFinder(llm_client)
        self.redactor = Redactor(llm_client)
        self.n0_rules = self._load_n0_rules()
        self.n1_rules = self._load_n1_rules()

    def run(
        self,
        project_id: str,
        target_path: str,
        source_state: Dict[str, Any],
    ) -> WriterRunResult:
        target_path = self._normalize_target_path(target_path)
        context_pack = self.context_builder.build(project_id, source_state, target_path)
        target_current = context_pack.payload.get("target_current")
        if not isinstance(target_current, dict):
            target_current = {}

        plan = self._build_plan(target_path, source_state, target_current)
        if plan.redaction_constraints:
            context_pack.payload["redaction_constraints"] = plan.redaction_constraints
        context_pack.payload["rules"] = self._build_rules_payload(plan)
        context_pack.payload["allowed_fields"] = plan.allowed_fields or []
        context_pack.payload["writing_mode"] = (
            "create" if self._is_target_text_empty(plan.allowed_fields, target_current) else "edit"
        )
        if plan.rule_mode:
            context_pack.payload["rule_mode"] = plan.rule_mode
        if plan.writer_self_question:
            context_pack.payload["writer_self_question"] = plan.writer_self_question
        if plan.strategy_finder_question:
            context_pack.payload["strategy_finder_question"] = plan.strategy_finder_question
        if plan.library_filename_prefixes:
            context_pack.payload["library_filename_prefixes"] = plan.library_filename_prefixes

        if plan.base_patch:
            try:
                merge_target_patch(project_id, target_path, plan.base_patch)
            except Exception as exc:
                return WriterRunResult(
                    status="error",
                    target_path=target_path,
                    target_patch=plan.base_patch,
                    open_questions=[],
                    context_pack=context_pack.payload,
                    strategy_card={},
                    error=str(exc),
                )
            target_current = self._merge_patch(target_current, plan.base_patch)
            context_pack.payload["target_current"] = target_current

        if plan.skip_llm:
            return WriterRunResult(
                status="done",
                target_path=target_path,
                target_patch=plan.base_patch,
                open_questions=[],
                context_pack=context_pack.payload,
                strategy_card={},
            )

        existing_fields = self._extract_existing_fields(plan.allowed_fields, target_current)
        if self._agentic_enabled():
            return self._run_agentic(
                project_id=project_id,
                target_path=target_path,
                source_state=source_state,
                plan=plan,
                context_pack=context_pack.payload,
                target_current=target_current,
                existing_fields=existing_fields,
            )
        return self._run_deterministic(
            project_id=project_id,
            target_path=target_path,
            source_state=source_state,
            plan=plan,
            context_pack=context_pack.payload,
            target_current=target_current,
            existing_fields=existing_fields,
        )

    def _is_target_text_empty(
        self, allowed_fields: Optional[List[str]], target_current: Any
    ) -> bool:
        """Decide creation vs edit based on the actual target text field(s).

        Important: other pre-filled fields (e.g. aspect_ratio) must not force edit mode.
        """
        if not allowed_fields:
            # Fallback: if the whole target section has meaningful text, treat as edit.
            if isinstance(target_current, str):
                return not bool(target_current.strip())
            if isinstance(target_current, dict):
                return not any(
                    isinstance(value, str) and value.strip()
                    for value in target_current.values()
                )
            return True
        if not isinstance(target_current, dict):
            return True
        for field in allowed_fields:
            value = target_current.get(field)
            if isinstance(value, str) and value.strip():
                return False
        return True

    def _run_deterministic(
        self,
        project_id: str,
        target_path: str,
        source_state: Dict[str, Any],
        plan: WritingPlan,
        context_pack: Dict[str, Any],
        target_current: Dict[str, Any],
        existing_fields: Dict[str, str],
    ) -> WriterRunResult:
        strategy_card: Dict[str, Any] = {}
        if plan.use_strategy:
            strategy_question = self._resolve_strategy_question(
                target_path=target_path,
                plan=plan,
                context_pack=context_pack,
                existing_fields=existing_fields,
            )
            if strategy_question:
                context_pack["strategy_question"] = strategy_question
            context_pack["context_groups"] = self._build_context_groups(
                context_pack=context_pack,
                plan=plan,
            )
            strategy_card = self._resolve_strategy_card(
                project_id=project_id,
                target_path=target_path,
                context_pack=context_pack,
                strategy_question=strategy_question,
            )
        context_pack["strategy_card"] = strategy_card

        redaction_result = self._redact_with_validations(
            target_path=target_path,
            context_pack=context_pack,
            plan=plan,
            existing_fields=existing_fields,
        )
        context_pack["redaction_attempts"] = redaction_result.attempts
        if not redaction_result.parsed:
            return WriterRunResult(
                status="partial",
                target_path=target_path,
                target_patch=plan.base_patch,
                open_questions=[],
                context_pack=context_pack,
                strategy_card=strategy_card,
                warning="invalid_json",
                raw_output=redaction_result.raw_output,
            )

        merged_patch = self._merge_patch(plan.base_patch, redaction_result.filtered_patch)
        if merged_patch:
            try:
                merge_target_patch(project_id, target_path, merged_patch)
            except Exception as exc:
                return WriterRunResult(
                    status="error",
                    target_path=target_path,
                    target_patch=merged_patch,
                    open_questions=redaction_result.open_questions,
                    context_pack=context_pack,
                    strategy_card=strategy_card,
                    raw_output=redaction_result.raw_output,
                    error=str(exc),
                )

        if target_path == "n0.sound_direction":
            extra_patch = infer_n0_visual_style_tone(project_id, source_state)
            if extra_patch:
                try:
                    merge_target_patch(project_id, "n0.narrative_presentation", extra_patch)
                except Exception:
                    pass

        return WriterRunResult(
            status="done",
            target_path=target_path,
            target_patch=merged_patch,
            open_questions=redaction_result.open_questions,
            context_pack=context_pack,
            strategy_card=strategy_card,
            raw_output=redaction_result.raw_output,
            warning=redaction_result.warning,
        )

    def _run_agentic(
        self,
        project_id: str,
        target_path: str,
        source_state: Dict[str, Any],
        plan: WritingPlan,
        context_pack: Dict[str, Any],
        target_current: Dict[str, Any],
        existing_fields: Dict[str, str],
    ) -> WriterRunResult:
        strategy_card: Dict[str, Any] = {}
        strategy_question = ""
        if plan.use_strategy:
            strategy_question = self._resolve_strategy_question(
                target_path=target_path,
                plan=plan,
                context_pack=context_pack,
                existing_fields=existing_fields,
            )
            if strategy_question:
                context_pack["strategy_question"] = strategy_question
            context_pack["context_groups"] = self._build_context_groups(
                context_pack=context_pack,
                plan=plan,
            )
            strategy_card = self._resolve_strategy_card(
                project_id=project_id,
                target_path=target_path,
                context_pack=context_pack,
                strategy_question=strategy_question,
            )
        context_pack["strategy_card"] = strategy_card
        agentic_trace: List[Dict[str, Any]] = []
        last_patch: Dict[str, Any] = {}
        last_open_questions: List[str] = []
        last_raw_output = ""
        last_meta_violations: List[Dict[str, Any]] = []
        last_length_violations: List[Dict[str, int]] = []
        last_score: Optional[float] = None
        last_eval: Optional[AgenticEvaluation] = None
        warning_message = ""

        max_iterations = self._agentic_max_iterations()
        score_threshold = self._agentic_score_threshold()

        for iteration in range(1, max_iterations + 1):
            decision = self._agentic_decide_action(
                target_path=target_path,
                has_strategy=bool(strategy_card),
                has_draft=bool(last_patch),
                last_score=last_score,
                score_threshold=score_threshold,
                meta_violations=last_meta_violations,
                length_violations=last_length_violations,
                last_eval=last_eval,
                iteration=iteration,
                max_iterations=max_iterations,
            )
            action = decision.action
            if action not in {
                "build_strategy",
                "refresh_context",
                "redact",
                "evaluate",
                "stop",
            }:
                action = "redact"
            if not last_patch and action in {"evaluate", "stop"}:
                action = "redact"
            if action == "build_strategy" and not plan.use_strategy:
                action = "redact"
            if (
                last_eval
                and last_eval.needs_strategy
                and plan.use_strategy
                and not self._lock_strategy_refresh(target_path, strategy_card)
            ):
                action = "build_strategy"
            if last_eval and last_eval.rewrite and action == "stop":
                action = "redact"

            if action == "refresh_context":
                refreshed = self.context_builder.build(project_id, source_state, target_path)
                context_pack = refreshed.payload
                if plan.redaction_constraints:
                    context_pack["redaction_constraints"] = plan.redaction_constraints
                context_pack["rules"] = self._build_rules_payload(plan)
                context_pack["strategy_card"] = strategy_card
                if isinstance(target_current, dict):
                    context_pack["target_current"] = target_current

            if action == "build_strategy" and plan.use_strategy:
                if self._lock_strategy_refresh(target_path, strategy_card):
                    action = "redact"
                else:
                    if not strategy_question:
                        strategy_question = self._resolve_strategy_question(
                            target_path=target_path,
                            plan=plan,
                            context_pack=context_pack,
                            existing_fields=existing_fields,
                        )
                    if strategy_question:
                        context_pack["strategy_question"] = strategy_question
                    context_pack["context_groups"] = self._build_context_groups(
                        context_pack=context_pack,
                        plan=plan,
                    )
                    strategy_card = self.strategy_finder.build_strategy(context_pack)
                    context_pack["strategy_card"] = strategy_card

            if action in {"redact", "build_strategy", "refresh_context"}:
                redaction_result = self._redact_with_validations(
                    target_path=target_path,
                    context_pack=context_pack,
                    plan=plan,
                    existing_fields=existing_fields,
                )
                context_pack["redaction_attempts"] = redaction_result.attempts
                last_raw_output = redaction_result.raw_output
                last_open_questions = redaction_result.open_questions
                last_meta_violations = redaction_result.meta_violations
                last_length_violations = redaction_result.length_violations
                if not redaction_result.parsed:
                    warning_message = "invalid_json"
                else:
                    last_patch = redaction_result.filtered_patch
                    warning_message = redaction_result.warning or warning_message
                    if last_patch:
                        target_current = self._merge_patch(target_current, last_patch)
                        context_pack["target_current"] = target_current
                        existing_fields = self._extract_existing_fields(
                            plan.allowed_fields, target_current
                        )

            if action == "evaluate" or last_patch:
                last_eval = self._evaluate_candidate(
                    target_path=target_path,
                    candidate_patch=last_patch,
                    context_pack=context_pack,
                    constraints=plan.redaction_constraints,
                    meta_violations=last_meta_violations,
                    length_violations=last_length_violations,
                )
                last_score = last_eval.score

            agentic_trace.append(
                {
                    "iteration": iteration,
                    "action": action,
                    "reason": decision.reason,
                    "score": last_score,
                    "passed": last_eval.passed if last_eval else False,
                    "needs_strategy": last_eval.needs_strategy if last_eval else False,
                    "rewrite": last_eval.rewrite if last_eval else False,
                    "meta_violations": last_meta_violations,
                    "length_violations": last_length_violations,
                }
            )

            if (
                last_eval
                and last_score is not None
                and last_score >= score_threshold
                and not last_meta_violations
                and not last_length_violations
                and last_eval.passed
            ):
                break

            if iteration == max_iterations:
                warning_message = warning_message or "agentic_stop_max_iters"

        if not last_patch:
            return WriterRunResult(
                status="partial",
                target_path=target_path,
                target_patch=plan.base_patch,
                open_questions=[],
                context_pack=context_pack,
                strategy_card=strategy_card,
                warning=warning_message or "no_redaction",
                raw_output=last_raw_output,
                agentic_trace=agentic_trace,
            )

        merged_patch = self._merge_patch(plan.base_patch, last_patch)
        if merged_patch:
            try:
                merge_target_patch(project_id, target_path, merged_patch)
            except Exception as exc:
                return WriterRunResult(
                    status="error",
                    target_path=target_path,
                    target_patch=merged_patch,
                    open_questions=last_open_questions,
                    context_pack=context_pack,
                    strategy_card=strategy_card,
                    raw_output=last_raw_output,
                    error=str(exc),
                    agentic_trace=agentic_trace,
                )

        if target_path == "n0.sound_direction":
            extra_patch = infer_n0_visual_style_tone(project_id, source_state)
            if extra_patch:
                try:
                    merge_target_patch(project_id, "n0.narrative_presentation", extra_patch)
                except Exception:
                    pass

        return WriterRunResult(
            status="done",
            target_path=target_path,
            target_patch=merged_patch,
            open_questions=last_open_questions,
            context_pack=context_pack,
            strategy_card=strategy_card,
            raw_output=last_raw_output,
            warning=warning_message,
            agentic_trace=agentic_trace,
        )

    def _resolve_strategy_question(
        self,
        *,
        target_path: str,
        plan: WritingPlan,
        context_pack: Dict[str, Any],
        existing_fields: Dict[str, str],
    ) -> str:
        if (
            isinstance(plan.strategy_finder_question, str)
            and plan.strategy_finder_question.strip()
        ):
            return self._render_strategy_finder_question(
                plan.strategy_finder_question.strip(), context_pack
            )
        return self._build_strategy_question(
            target_path=target_path,
            context_pack=context_pack,
            rule=self._build_rules_payload(plan),
            has_existing=bool(existing_fields),
        )

    def _resolve_strategy_card(
        self,
        *,
        project_id: str,
        target_path: str,
        context_pack: Dict[str, Any],
        strategy_question: str,
    ) -> Dict[str, Any]:
        cached = self._load_recent_strategy_card(
            project_id=project_id,
            target_path=target_path,
            context_pack=context_pack,
            strategy_question=strategy_question,
        )
        if cached:
            context_pack["strategy_card_reused"] = True
            return cached
        context_pack["strategy_card_reused"] = False
        return self.strategy_finder.build_strategy(context_pack)

    def _lock_strategy_refresh(self, target_path: str, strategy_card: Dict[str, Any]) -> bool:
        if not isinstance(strategy_card, dict) or not strategy_card:
            return False
        return self._strategy_reuse_enabled_for_target(target_path)

    def _strategy_reuse_enabled_for_target(self, target_path: str) -> bool:
        value = str(target_path or "").strip()
        return (
            value.startswith("n0.narrative_presentation")
            or value.startswith("n0.production_summary")
            or value.startswith("n0.art_direction")
            or value.startswith("n0.sound_direction")
        )

    def _load_recent_strategy_card(
        self,
        *,
        project_id: str,
        target_path: str,
        context_pack: Dict[str, Any],
        strategy_question: str,
    ) -> Dict[str, Any]:
        if not self._strategy_reuse_enabled_for_target(target_path):
            return {}
        try:
            root = get_project_root(project_id)
        except Exception:
            return {}
        strata = str(target_path or "").split(".", 1)[0].strip().lower()
        if not re.fullmatch(r"n[0-9]+", strata or ""):
            strata = "misc"
        log_dir = root / "strategy_logs" / strata
        if not log_dir.exists():
            return {}
        safe_target = "".join(
            c for c in (target_path or "strategy") if c.isalnum() or c in ("-", "_", ".")
        ).strip()
        safe_target = safe_target.replace(".", "_") if safe_target else "strategy"
        candidates: List[Path] = sorted(
            [p for p in log_dir.glob(f"*_{safe_target}.json") if p.is_file()],
            reverse=True,
        )
        if not candidates:
            return {}
        current_summary = str(context_pack.get("core_summary", "") or "").strip()
        current_typology = str(context_pack.get("writing_typology", "") or "").strip()
        current_constraints = context_pack.get("redaction_constraints", {})
        for path in candidates:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            if str(payload.get("target_path", "")).strip() != str(target_path).strip():
                continue
            if str(payload.get("writing_typology", "")).strip() != current_typology:
                continue
            logged_question = str(payload.get("strategy_question", "") or "").strip()
            if strategy_question and logged_question and logged_question != strategy_question:
                continue
            logged_ctx = payload.get("strategy_context_payload", {})
            if not isinstance(logged_ctx, dict):
                logged_ctx = {}
            logged_summary = str(logged_ctx.get("project_summary", "") or "").strip()
            if current_summary and logged_summary and logged_summary != current_summary:
                continue
            logged_constraints = logged_ctx.get("redaction_constraints", {})
            if (
                isinstance(current_constraints, dict)
                and isinstance(logged_constraints, dict)
                and current_constraints
                and logged_constraints
                and logged_constraints != current_constraints
            ):
                continue
            strategy_text = str(payload.get("strategy_text", "") or "").strip()
            if not strategy_text:
                continue
            return {
                "strategy_id": str(payload.get("strategy_id", "") or "cached_strategy"),
                "target_path": str(payload.get("target_path", "") or target_path),
                "writing_typology": str(payload.get("writing_typology", "") or current_typology),
                "library_item_ids": payload.get("library_item_ids", [])
                if isinstance(payload.get("library_item_ids"), list)
                else [],
                "strategy_text": strategy_text,
                "source_refs": payload.get("source_refs", [])
                if isinstance(payload.get("source_refs"), list)
                else [],
                "notes": (
                    str(payload.get("notes", "") or "").strip()
                    + " strategy_reused_from_log=true"
                ).strip(),
            }
        return {}

    def _extract_existing_fields(
        self, allowed_fields: Optional[List[str]], target_current: Any
    ) -> Dict[str, str]:
        existing_fields: Dict[str, str] = {}
        if allowed_fields and isinstance(target_current, dict):
            for field in allowed_fields:
                value = target_current.get(field)
                if isinstance(value, str) and value.strip():
                    existing_fields[field] = value.strip()
        if not existing_fields and isinstance(target_current, str) and target_current.strip():
            existing_fields["text"] = target_current.strip()
        return existing_fields

    def _redact_with_validations(
        self,
        target_path: str,
        context_pack: Dict[str, Any],
        plan: WritingPlan,
        existing_fields: Dict[str, str],
    ) -> RedactionCycleResult:
        mode_hint = ""
        existing_block = ""
        if existing_fields:
            mode_hint = (
                "Editing mode:\n"
                "- Update the existing text to satisfy the user request, context, and strategy.\n"
                "- Do NOT rewrite from scratch. Preserve structure and key phrasing when possible.\n"
                "- Only change what is necessary to satisfy constraints or requests.\n"
            )
            existing_block = (
                "Existing content to revise (do not discard):\n"
                f"{json.dumps(existing_fields, ensure_ascii=True, indent=2)}\n"
            )
        else:
            mode_hint = (
                "Creation mode:\n"
                "- The target field is empty. Write the full text from scratch.\n"
            )

        system_prompt = self._build_writer_prompt(target_path)
        allowed_hint = ""
        if plan.allowed_fields:
            allowed_hint = (
                f"- Only write these fields inside the target section: {', '.join(plan.allowed_fields)}.\n"
            )
        rules = context_pack.get("rules") if isinstance(context_pack, dict) else {}
        redaction_rules = []
        if isinstance(rules, dict):
            redaction_rules = rules.get("redaction_rules") or []
        redaction_rules_line = ""
        if isinstance(redaction_rules, list) and redaction_rules:
            rules_text = "; ".join([str(item) for item in redaction_rules if str(item).strip()])
            if rules_text:
                redaction_rules_line = f"- Redaction rules: {rules_text}.\n"
        redactor_context_pack = self._context_pack_for_redactor(context_pack)
        compiler = RedactorPromptCompiler()
        user_prompt = compiler.build_initial_user_prompt(
            target_path=target_path,
            context_pack=redactor_context_pack,
            allowed_fields=plan.allowed_fields,
            redaction_rules=redaction_rules if isinstance(redaction_rules, list) else [],
            extra_rule=str(plan.extra_rule or ""),
            writer_self_question=str(plan.writer_self_question or ""),
            writing_mode_hint=(mode_hint or "").strip(),
            existing_fields=existing_fields if isinstance(existing_fields, dict) else {},
        )

        redaction = self.redactor.redact(system_prompt=system_prompt, user_prompt=user_prompt)
        raw_content = redaction.raw_output
        parsed = redaction.parsed
        base_attempt = {
            "phase": "initial",
            "prompt_debug": {
                "system_prompt_chars": len(system_prompt),
                "user_prompt_chars": len(user_prompt),
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            },
            "context_groups_debug": self._summarize_context_groups_for_log(
                context_pack, per_group_preview_chars=900
            ),
            "char_counts": {},
            "length_violations": [],
            "meta_violations": [],
        }
        if not isinstance(parsed, dict):
            return RedactionCycleResult(
                parsed=False,
                filtered_patch={},
                open_questions=[],
                raw_output=raw_content,
                warning="invalid_json",
                attempts=[base_attempt],
            )

        target_patch = self._coerce_target_patch(parsed, plan.allowed_fields)
        open_questions = parsed.get("open_questions") if isinstance(parsed, dict) else []
        filtered_patch: Dict[str, Any] = {}
        if isinstance(target_patch, dict):
            normalized_patch = self._normalize_target_patch_keys(
                target_patch, plan.allowed_fields
            )
            filtered_patch = (
                self._filter_allowed_fields(normalized_patch, plan.allowed_fields)
                if plan.allowed_fields
                else normalized_patch
            )
        warning_message = ""
        meta_violations = self._collect_meta_violations(filtered_patch, plan.allowed_fields)
        length_violations = self._collect_length_violations(
            filtered_patch, plan.redaction_constraints, plan.allowed_fields
        )
        base_attempt["char_counts"] = self._compute_char_counts(
            filtered_patch, plan.allowed_fields
        )
        base_attempt["length_violations"] = length_violations
        base_attempt["meta_violations"] = meta_violations
        attempts: List[Dict[str, Any]] = [base_attempt]
        max_retries = self._redactor_max_retries()
        if (meta_violations or length_violations) and max_retries > 0:
            retry_prompt = self._build_retry_prompt(
                context_pack=context_pack,
                target_path=target_path,
                plan=plan,
                length_violations=length_violations,
                meta_violations=meta_violations,
                existing_patch=filtered_patch,
                allowed_hint=allowed_hint,
            )
            retry = self.redactor.redact(system_prompt=system_prompt, user_prompt=retry_prompt)
            raw_content = retry.raw_output
            retry_parsed = retry.parsed
            if isinstance(retry_parsed, dict):
                retry_patch = retry_parsed.get("target_patch")
                if isinstance(retry_patch, dict):
                    normalized_retry = self._normalize_target_patch_keys(
                        retry_patch, plan.allowed_fields
                    )
                    filtered_patch = (
                        self._filter_allowed_fields(normalized_retry, plan.allowed_fields)
                        if plan.allowed_fields
                        else normalized_retry
                    )
                    meta_violations = self._collect_meta_violations(
                        filtered_patch, plan.allowed_fields
                    )
                    length_violations = self._collect_length_violations(
                        filtered_patch, plan.redaction_constraints, plan.allowed_fields
                    )
                    attempts.append(
                        {
                            "phase": "retry",
                            "prompt_debug": {
                                "system_prompt_chars": len(system_prompt),
                                "user_prompt_chars": len(retry_prompt),
                                "system_prompt": system_prompt,
                                "user_prompt": retry_prompt,
                            },
                            "context_groups_debug": self._summarize_context_groups_for_log(
                                context_pack, per_group_preview_chars=900
                            ),
                            "char_counts": self._compute_char_counts(
                                filtered_patch, plan.allowed_fields
                            ),
                            "length_violations": length_violations,
                            "meta_violations": meta_violations,
                        }
                    )
            if meta_violations or length_violations:
                if meta_violations and length_violations:
                    warning_message = "length_and_meta_violation"
                elif meta_violations:
                    warning_message = "meta_violation"
                else:
                    warning_message = "length_violation"
        elif meta_violations or length_violations:
            if meta_violations and length_violations:
                warning_message = "length_and_meta_violation"
            elif meta_violations:
                warning_message = "meta_violation"
            else:
                warning_message = "length_violation"
        return RedactionCycleResult(
            parsed=True,
            filtered_patch=filtered_patch,
            open_questions=open_questions if isinstance(open_questions, list) else [],
            raw_output=raw_content,
            warning=warning_message,
            meta_violations=meta_violations,
            length_violations=length_violations,
            attempts=attempts,
        )

    def _truncate_for_log(
        self,
        text: str,
        max_chars: int,
        *,
        head: bool = True,
        tail: bool = True,
    ) -> str:
        if not isinstance(text, str):
            return ""
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text
        if head and not tail:
            return text[:max_chars] + "\n...<truncated>..."
        if tail and not head:
            return "...<truncated>...\n" + text[-max_chars:]
        # head+tail
        half = max_chars // 2
        return text[:half] + "\n...<truncated>...\n" + text[-half:]

    def _summarize_context_groups_for_log(
        self, context_pack: Dict[str, Any], per_group_preview_chars: int = 600
    ) -> List[Dict[str, Any]]:
        """Log-friendly summary of context_groups payloads."""
        groups = context_pack.get("context_groups") if isinstance(context_pack, dict) else None
        if not isinstance(groups, list):
            return []
        out: List[Dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            payload = group.get("payload")
            try:
                payload_json = json.dumps(payload, ensure_ascii=True, indent=2)
            except Exception:
                payload_json = str(payload)
            out.append(
                {
                    "name": group.get("name", ""),
                    "weight": group.get("weight", None),
                    "sources": group.get("sources", []),
                    "payload_chars": len(payload_json) if isinstance(payload_json, str) else 0,
                    "payload_preview": self._truncate_for_log(
                        payload_json if isinstance(payload_json, str) else "",
                        per_group_preview_chars,
                    ),
                }
            )
        return out

    def _compute_char_counts(
        self, patch: Dict[str, Any], allowed_fields: Optional[List[str]]
    ) -> Dict[str, int]:
        """Return char counts for relevant string fields in a patch."""
        if not isinstance(patch, dict):
            return {}
        fields = allowed_fields or list(patch.keys())
        counts: Dict[str, int] = {}
        for field in fields:
            value = patch.get(field)
            if isinstance(value, str):
                counts[field] = len(value.strip())
        return counts

    def _agentic_decide_action(
        self,
        target_path: str,
        has_strategy: bool,
        has_draft: bool,
        last_score: Optional[float],
        score_threshold: float,
        meta_violations: List[Dict[str, Any]],
        length_violations: List[Dict[str, int]],
        last_eval: Optional[AgenticEvaluation],
        iteration: int,
        max_iterations: int,
    ) -> AgenticDecision:
        state = self._build_agentic_state(
            target_path=target_path,
            has_strategy=has_strategy,
            has_draft=has_draft,
            last_score=last_score,
            score_threshold=score_threshold,
            meta_violations=meta_violations,
            length_violations=length_violations,
            last_eval=last_eval,
            iteration=iteration,
            max_iterations=max_iterations,
        )
        system_prompt = (
            "You are a writing orchestration controller. Decide the NEXT action for the writer agent.\n"
            "Return ONLY JSON with keys: action, reason.\n"
            "Valid actions: build_strategy, refresh_context, redact, evaluate, stop.\n"
            "If there is no draft yet, do NOT choose stop or evaluate.\n"
            "If constraints are violated, prioritize redact.\n"
            "If score >= threshold and no violations, choose stop.\n"
        )
        user_prompt = f"State (JSON):\n{json.dumps(state, ensure_ascii=True, indent=2)}"

        raw_output = ""
        action = "redact"
        reason = "fallback"
        try:
            llm_response = self.llm_client.complete(
                LLMRequest(
                    model=self.llm_client.default_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.2,
                )
            )
            raw_output = llm_response.content.strip()
            json_block = self._extract_json_block(raw_output) or raw_output
            parsed = self._parse_json_payload(json_block, raw_output) or {}
            if isinstance(parsed, dict):
                action = str(parsed.get("action") or "").strip().lower() or action
                reason = str(parsed.get("reason") or "").strip() or reason
        except Exception:
            action = "redact"
            reason = "controller_error_fallback"

        if action not in {"build_strategy", "refresh_context", "redact", "evaluate", "stop"}:
            action = "redact"
        if not has_draft and action in {"evaluate", "stop"}:
            action = "redact"
            reason = "no_draft_force_redact"
        if (meta_violations or length_violations) and action == "stop":
            action = "redact"
            reason = "violations_force_redact"

        return AgenticDecision(action=action, reason=reason, raw_output=raw_output)

    def _evaluate_candidate(
        self,
        target_path: str,
        candidate_patch: Dict[str, Any],
        context_pack: Dict[str, Any],
        constraints: Dict[str, int],
        meta_violations: List[Dict[str, Any]],
        length_violations: List[Dict[str, int]],
    ) -> AgenticEvaluation:
        min_chars = int(constraints.get("min_chars") or 0)
        max_chars = int(constraints.get("max_chars") or 0)
        rules = context_pack.get("rules") if isinstance(context_pack, dict) else {}
        quality_criteria = rules.get("quality_criteria") if isinstance(rules, dict) else []
        redaction_rules = rules.get("redaction_rules") if isinstance(rules, dict) else []
        evaluation_input = {
            "target_path": target_path,
            "writing_typology": context_pack.get("writing_typology", ""),
            "min_chars": min_chars,
            "max_chars": max_chars,
            "core_summary": context_pack.get("core_summary", ""),
            "brief_constraints": context_pack.get("brief_constraints", []),
            "deterministic_meta_violations": meta_violations,
            "deterministic_length_violations": length_violations,
            "quality_criteria": quality_criteria if isinstance(quality_criteria, list) else [],
            "redaction_rules": redaction_rules if isinstance(redaction_rules, list) else [],
            "draft_patch": candidate_patch,
        }
        system_prompt = (
            "You are a strict writing evaluator. Score the draft from 0.0 to 1.0.\n"
            "Return ONLY JSON with keys: score, pass, issues, rewrite, needs_strategy.\n"
            "pass should be true only if constraints are met and the draft is coherent.\n"
            "Use quality_criteria and redaction_rules if provided.\n"
            "If there are deterministic violations, pass must be false.\n"
        )
        user_prompt = f"Evaluate this draft:\n{json.dumps(evaluation_input, ensure_ascii=True, indent=2)}"

        raw_output = ""
        score = 0.0
        passed = False
        issues: List[str] = []
        rewrite = True
        needs_strategy = False
        try:
            llm_response = self.llm_client.complete(
                LLMRequest(
                    model=self.llm_client.default_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.2,
                )
            )
            raw_output = llm_response.content.strip()
            json_block = self._extract_json_block(raw_output) or raw_output
            parsed = self._parse_json_payload(json_block, raw_output) or {}
            if isinstance(parsed, dict):
                score = float(parsed.get("score") or score)
                passed = bool(parsed.get("pass") or False)
                issues = parsed.get("issues") if isinstance(parsed.get("issues"), list) else []
                rewrite = bool(parsed.get("rewrite") or False)
                needs_strategy = bool(parsed.get("needs_strategy") or False)
        except Exception:
            raw_output = raw_output or ""

        score = max(0.0, min(1.0, score))
        if meta_violations or length_violations:
            passed = False
            score = min(score, 0.3)

        return AgenticEvaluation(
            score=score,
            passed=passed,
            issues=[str(item) for item in issues if str(item)],
            rewrite=rewrite,
            needs_strategy=needs_strategy,
            raw_output=raw_output,
        )

    def _build_agentic_state(
        self,
        target_path: str,
        has_strategy: bool,
        has_draft: bool,
        last_score: Optional[float],
        score_threshold: float,
        meta_violations: List[Dict[str, Any]],
        length_violations: List[Dict[str, int]],
        last_eval: Optional[AgenticEvaluation],
        iteration: int,
        max_iterations: int,
    ) -> Dict[str, Any]:
        return {
            "target_path": target_path,
            "has_strategy": has_strategy,
            "has_draft": has_draft,
            "last_score": last_score,
            "score_threshold": score_threshold,
            "meta_violations_count": len(meta_violations),
            "length_violations_count": len(length_violations),
            "last_eval": {
                "passed": last_eval.passed,
                "score": last_eval.score,
                "rewrite": last_eval.rewrite,
                "needs_strategy": last_eval.needs_strategy,
                "issues": last_eval.issues,
            }
            if last_eval
            else {},
            "iteration": iteration,
            "max_iterations": max_iterations,
        }

    def _extract_json_block(self, content: str) -> str:
        if "```json" not in content:
            return ""
        _, _, rest = content.partition("```json")
        json_block = rest
        if "```" in rest:
            json_block, _, _ = rest.partition("```")
        return json_block.strip()

    def _parse_json_payload(self, payload: str, fallback: str) -> Optional[Dict[str, Any]]:
        if payload:
            try:
                parsed = json.loads(payload)
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                pass
        trimmed = fallback.strip()
        if not trimmed:
            return None
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(trimmed[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None

    def _agentic_enabled(self) -> bool:
        return self._env_flag("WRITER_AGENTIC_ENABLED", True)

    def _agentic_max_iterations(self) -> int:
        return self._env_int("WRITER_AGENTIC_MAX_ITERS", 3, min_value=1)

    def _agentic_score_threshold(self) -> float:
        return self._env_float("WRITER_AGENTIC_SCORE_THRESHOLD", 0.75, min_value=0.0, max_value=1.0)

    def _redactor_max_retries(self) -> int:
        return self._env_int("WRITER_REDACTOR_MAX_RETRIES", 0, min_value=0, max_value=3)

    def _env_flag(self, name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    def _env_int(
        self, name: str, default: int, min_value: int = 1, max_value: Optional[int] = None
    ) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except ValueError:
            return default
        value = max(min_value, value)
        if max_value is not None:
            value = min(max_value, value)
        return value

    def _env_float(
        self,
        name: str,
        default: float,
        min_value: float = 0.0,
        max_value: Optional[float] = None,
    ) -> float:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = float(raw)
        except ValueError:
            return default
        value = max(min_value, value)
        if max_value is not None:
            value = min(max_value, value)
        return value

    def _build_plan(
        self,
        target_path: str,
        source_state: Dict[str, Any],
        target_current: Dict[str, Any],
    ) -> WritingPlan:
        plan = WritingPlan(target_path=target_path)
        if not target_path:
            return plan

        if target_path.startswith("n0."):
            if target_path in {"n0.narrative_presentation", "n0.production_summary"}:
                plan.base_patch = infer_n0_production_summary(source_state, target_current)
            elif target_path == "n0.deliverables":
                plan.base_patch = infer_n0_deliverables(source_state, target_current)
            rule = self.n0_rules.get(target_path, {})
            self._apply_declarative_rules(plan, rule, target_current, source_state)
            # Safety fallback: narrative presentation must always be redacted into "summary".
            # This protects runtime behavior if rules are not loaded as expected.
            if target_path in {"n0.narrative_presentation", "n0.production_summary"}:
                if not plan.allowed_fields:
                    plan.allowed_fields = ["summary"]
                if not plan.redaction_constraints:
                    plan.redaction_constraints = {"min_chars": 2000, "max_chars": 3000}
                if not plan.strategy_finder_question:
                    plan.strategy_finder_question = (
                        "Find in the documents rules and guidance to write a clear, factual narrative presentation."
                    )
                if not plan.library_filename_prefixes:
                    plan.library_filename_prefixes = ["SRC_NARRATOLOGY"]
        elif target_path == "n1" or target_path.startswith("n1."):
            rule = self._resolve_n1_rule(target_path)
            self._apply_declarative_rules(plan, rule, target_current, source_state)

        return plan

    def _load_n0_rules(self) -> Dict[str, Any]:
        rules = load_json("writer_agent/n_rules/n0_rules.json") or {}
        return rules if isinstance(rules, dict) else {}

    def _load_n1_rules(self) -> Dict[str, Any]:
        rules = load_json("writer_agent/n_rules/n1_rules.json") or {}
        return rules if isinstance(rules, dict) else {}

    def _resolve_n1_rule(self, target_path: str) -> Dict[str, Any]:
        if not isinstance(target_path, str) or not target_path.strip():
            return self.n1_rules.get("n1", {})
        direct = self.n1_rules.get(target_path)
        if isinstance(direct, dict):
            return direct
        normalized = re.sub(r"\[\d+\]", "[]", target_path.strip())
        wildcard_rule = self.n1_rules.get(normalized)
        if isinstance(wildcard_rule, dict):
            return wildcard_rule
        return self.n1_rules.get("n1", {})

    def _apply_declarative_rules(
        self,
        plan: WritingPlan,
        rule: Any,
        target_current: Dict[str, Any],
        source_state: Dict[str, Any],
    ) -> None:
        if not isinstance(rule, dict):
            return
        # 1) Apply base allowed_fields first (needed to infer mode).
        allowed_fields = rule.get("allowed_fields")
        if isinstance(allowed_fields, list) and allowed_fields:
            plan.allowed_fields = [str(item) for item in allowed_fields if str(item)]

        # 2) Overlay mode-specific rules (create vs edit vs propagate) if present.
        mode_rules = None
        if isinstance(rule.get("modes"), dict):
            inferred_mode = self._infer_rule_mode(plan, target_current, source_state, rule)
            plan.rule_mode = inferred_mode
            mode_rules = rule.get("modes", {}).get(inferred_mode)
        if isinstance(mode_rules, dict):
            rule = {**rule, **mode_rules}

        # 3) Apply final rule fields.
        allowed_fields = rule.get("allowed_fields")
        if isinstance(allowed_fields, list) and allowed_fields:
            plan.allowed_fields = [str(item) for item in allowed_fields if str(item)]
        redaction_constraints = rule.get("redaction_constraints")
        if isinstance(redaction_constraints, dict):
            plan.redaction_constraints = {
                key: int(value)
                for key, value in redaction_constraints.items()
                if isinstance(key, str) and isinstance(value, (int, float))
            }
        if isinstance(rule.get("use_strategy"), bool):
            plan.use_strategy = bool(rule["use_strategy"])
        if isinstance(rule.get("skip_llm"), bool):
            plan.skip_llm = bool(rule["skip_llm"])
        if isinstance(rule.get("extra_rule"), str):
            plan.extra_rule = rule["extra_rule"]
        if isinstance(rule.get("strategy_role"), str):
            plan.strategy_role = rule["strategy_role"]
        if isinstance(rule.get("strategy_hints"), list):
            plan.strategy_hints = [str(item) for item in rule["strategy_hints"] if str(item)]
        if isinstance(rule.get("redaction_rules"), list):
            plan.redaction_rules = [str(item) for item in rule["redaction_rules"] if str(item)]
        if isinstance(rule.get("quality_criteria"), list):
            plan.quality_criteria = [str(item) for item in rule["quality_criteria"] if str(item)]
        if isinstance(rule.get("writer_self_question"), str):
            plan.writer_self_question = rule["writer_self_question"]
        strategy_finder = rule.get("strategy_finder")
        if isinstance(strategy_finder, dict):
            question = strategy_finder.get("question")
            if isinstance(question, str):
                plan.strategy_finder_question = question
            prefixes = strategy_finder.get("library_filename_prefixes")
            if isinstance(prefixes, list):
                plan.library_filename_prefixes = [str(p) for p in prefixes if str(p).strip()]
        context_aggregation = rule.get("context_aggregation")
        if isinstance(context_aggregation, dict):
            groups = context_aggregation.get("groups")
            if isinstance(groups, list):
                plan.context_group_specs = [g for g in groups if isinstance(g, dict)]

    def _infer_rule_mode(
        self,
        plan: WritingPlan,
        target_current: Dict[str, Any],
        source_state: Dict[str, Any],
        rule: Dict[str, Any],
    ) -> str:
        """Infer the rule mode: create vs edit vs propagate.

        - create: the actual target text field(s) are empty ("")
        - edit: the user explicitly requested changes for this target_path (via brief.target_paths)
        - propagate: edit-like rewrite without a user request (context changed upstream)
        """
        modes = rule.get("modes", {}) if isinstance(rule, dict) else {}
        if self._is_target_text_empty(plan.allowed_fields, target_current):
            return "create"
        brief = source_state.get("brief") if isinstance(source_state, dict) else {}
        target_paths = brief.get("target_paths") if isinstance(brief, dict) else []
        requested = False
        if isinstance(target_paths, list) and plan.target_path:
            for entry in target_paths:
                if not isinstance(entry, str):
                    continue
                path = entry.strip()
                if not path:
                    continue
                if path == plan.target_path or path.startswith(plan.target_path + "."):
                    requested = True
                    break
        if requested:
            return "edit"
        # If propagate mode exists, prefer it when the target wasn't explicitly requested.
        if isinstance(modes, dict) and "propagate" in modes:
            return "propagate"
        return "edit"

    def _build_context_groups(self, context_pack: Dict[str, Any], plan: WritingPlan) -> List[Dict[str, Any]]:
        """Build weighted context groups for the LLM (rules-driven)."""
        if not isinstance(context_pack, dict):
            return []
        target_path = context_pack.get("target_path", "")
        target_data = context_pack.get("target_strata_data", {})
        if not isinstance(target_data, dict):
            target_data = {}
        dependencies = context_pack.get("dependencies", {})
        if not isinstance(dependencies, dict):
            dependencies = {}

        def get_n0_summary() -> str:
            prod = target_data.get("narrative_presentation")
            if not isinstance(prod, dict):
                prod = target_data.get("production_summary", {})
            if isinstance(prod, dict):
                value = prod.get("summary", "")
                return value.strip() if isinstance(value, str) else ""
            n0_state = dependencies.get("n0") if isinstance(dependencies, dict) else {}
            if isinstance(n0_state, dict):
                n0_data = n0_state.get("data") if isinstance(n0_state, dict) else {}
                if isinstance(n0_data, dict):
                    n0_prod = n0_data.get("narrative_presentation")
                    if not isinstance(n0_prod, dict):
                        n0_prod = n0_data.get("production_summary", {})
                    if isinstance(n0_prod, dict):
                        value = n0_prod.get("summary", "")
                        return value.strip() if isinstance(value, str) else ""
            return ""

        def build_family_payload() -> Dict[str, Any]:
            payload: Dict[str, Any] = {}
            for key, value in target_data.items():
                payload[key] = value
            if target_path == "n0.art_direction":
                payload.pop("art_direction", None)
            if target_path == "n0.sound_direction":
                payload.pop("sound_direction", None)
            return payload

        chat_indications_payload = {
            "brief_primary_objective": context_pack.get("brief_primary_objective", ""),
            "brief_project_title": context_pack.get("brief_project_title", ""),
            "brief_video_type": context_pack.get("brief_video_type", ""),
            "brief_target_duration_s": context_pack.get("brief_target_duration_s", 0),
            "brief_constraints": context_pack.get("brief_constraints", []),
            "brief_priorities": context_pack.get("brief_priorities", []),
            "thinker_constraints": context_pack.get("thinker_constraints", []),
            "core_summary": context_pack.get("core_summary", ""),
        }
        neighbours_payload_full = {
            "chat_state_1abc": chat_indications_payload,
            "n1": (dependencies.get("n1") or {}),
        }

        groups = []
        specs = plan.context_group_specs or []
        if not specs:
            return groups
        for spec in specs:
            name = str(spec.get("name") or "").strip()
            weight = spec.get("weight", 0)
            try:
                weight_f = float(weight)
            except Exception:
                weight_f = 0.0
            group_payload: Any = {}
            sources = spec.get("sources", [])
            if not isinstance(sources, list):
                sources = []
            sources = [str(s) for s in sources if str(s).strip()]

            if name == "actual_text" or "actual_text" in sources:
                # Only keep text fields (allowed_fields) when possible.
                if plan.allowed_fields and isinstance(target_current, dict):
                    group_payload = {
                        key: value
                        for key, value in target_current.items()
                        if key in plan.allowed_fields and isinstance(value, str)
                    }
                else:
                    group_payload = target_current
            elif name == "chat_indications" or "chat_indications" in sources:
                group_payload = chat_indications_payload
            elif name == "father":
                group_payload = {"n0.narrative_presentation.summary": get_n0_summary()}
            elif name == "family":
                group_payload = build_family_payload()
            elif name == "neighbours":
                # Neighbours can be either full (chat + n1) or N1-only, depending on sources.
                if sources == ["n1"] or (len(sources) == 1 and sources[0] == "n1"):
                    group_payload = dependencies.get("n1") or {}
                else:
                    group_payload = neighbours_payload_full
            else:
                group_payload = {}
            groups.append(
                {
                    "name": name,
                    "weight": max(0.0, min(1.0, weight_f)),
                    "description": str(spec.get("description") or ""),
                    "payload": group_payload,
                }
            )
        # Highest weight first for readability.
        groups.sort(key=lambda g: float(g.get("weight") or 0), reverse=True)
        return groups

    def _build_rules_payload(self, plan: WritingPlan) -> Dict[str, Any]:
        return {
            "strategy_role": plan.strategy_role,
            "strategy_hints": plan.strategy_hints,
            "redaction_rules": plan.redaction_rules,
            "quality_criteria": plan.quality_criteria,
            "extra_rule": plan.extra_rule,
        }

    def _build_strategy_question(
        self,
        target_path: str,
        context_pack: Dict[str, Any],
        rule: Any,
        has_existing: bool,
    ) -> str:
        role = ""
        strategy_hints: List[str] = []
        if isinstance(rule, dict):
            role = str(rule.get("strategy_role") or "").strip()
            hints_value = rule.get("strategy_hints")
            if isinstance(hints_value, list):
                strategy_hints = [str(item) for item in hints_value if str(item).strip()]
        if not role:
            role = f"the section '{target_path}'"
        mode = "edit" if has_existing else "write"
        writing_typology = context_pack.get("writing_typology", "")
        core_summary = context_pack.get("core_summary", "")
        brief_primary = context_pack.get("brief_primary_objective", "")
        constraints = context_pack.get("brief_constraints", [])

        lines = [
            f"I need to {mode} {role} for a film project.",
        ]
        if writing_typology:
            lines.append(f"Writing typology: {writing_typology}.")
        if isinstance(core_summary, str) and core_summary.strip():
            lines.append(f"Project narrative presentation: {core_summary.strip()}.")
        elif isinstance(brief_primary, str) and brief_primary.strip():
            lines.append(f"Primary objective: {brief_primary.strip()}.")
        if isinstance(constraints, list) and constraints:
            constraints_line = ", ".join([str(item) for item in constraints if str(item).strip()])
            if constraints_line:
                lines.append(f"Constraints: {constraints_line}.")
        if strategy_hints:
            lines.append(f"Strategy hints: {'; '.join(strategy_hints)}.")
        lines.append(
            "Can you propose a writing strategy (principles, structure, watchpoints) "
            "for the redactor who must produce this text in this context?"
        )
        return " ".join(lines)

    def _render_strategy_finder_question(
        self, template: str, context_pack: Dict[str, Any]
    ) -> str:
        if not isinstance(template, str) or not template.strip():
            return ""
        project_id = str(context_pack.get("project_id", "")).strip() or "current_project"
        video_type = (
            str(context_pack.get("brief_video_type", "")).strip() or "unspecified_video_type"
        )
        duration = self._strategy_duration_label(context_pack)
        summary = self._strategy_summary_label(context_pack)
        replacements = {
            "project_id": project_id,
            "video_type": video_type,
            "duration": duration,
            "summary": summary,
        }
        rendered = template
        for key, value in replacements.items():
            # Replace only explicit placeholders to avoid accidental substitutions
            # in regular text (e.g. replacing "summary" inside "production summary").
            rendered = rendered.replace(f'"{key}"', f'"{value}"')
            rendered = rendered.replace(f"{{{key}}}", value)
            rendered = rendered.replace(f"<{key}>", value)
            rendered = rendered.replace(f"${{{key}}}", value)
        return " ".join(rendered.split())

    def _strategy_summary_label(self, context_pack: Dict[str, Any]) -> str:
        summary = str(context_pack.get("core_summary", "")).strip()
        if not summary:
            return "narrative presentation unavailable"
        cleaned = " ".join(summary.split())
        if len(cleaned) <= 340:
            return cleaned
        clipped = cleaned[:340]
        if " " in clipped:
            clipped = clipped.rsplit(" ", 1)[0]
        return clipped + "..."

    def _strategy_duration_label(self, context_pack: Dict[str, Any]) -> str:
        duration_text = str(context_pack.get("brief_target_duration_text", "")).strip()
        if duration_text:
            return duration_text
        raw_seconds = context_pack.get("brief_target_duration_s", 0)
        try:
            seconds = int(raw_seconds)
        except Exception:
            seconds = 0
        if seconds <= 0:
            return "unspecified duration"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts: List[str] = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if secs and not hours:
            parts.append(f"{secs} second{'s' if secs > 1 else ''}")
        return " ".join(parts) if parts else f"{seconds} seconds"

    def _build_writer_prompt(self, target_path: str) -> str:
        analyst_targets = {
            "n1.characters.main_characters",
            "n1.characters.secondary_characters",
            "n1.characters.background_characters",
        }
        prompt_path = (
            "writer_agent/redactor/redactor_analyst.md"
            if target_path in analyst_targets
            else "writer_agent/redactor/redactor.md"
        )
        base_prompt = load_text(prompt_path).strip()
        if not base_prompt:
            base_prompt = "You are a redactor. Produce a patch for the target section only."
        # IMPORTANT: keep the system prompt stable and "role-level".
        # N0/N1-specific rules belong in the user prompt (context_pack + declarative rules),
        # not appended here (to avoid outdated/contradictory instructions).
        return base_prompt

    def _merge_patch(self, base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        if not base and not patch:
            return {}
        merged = {**base}
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_patch(merged.get(key, {}), value)
            else:
                merged[key] = value
        return merged

    def _filter_allowed_fields(
        self, patch: Dict[str, Any], allowed_fields: Optional[List[str]]
    ) -> Dict[str, Any]:
        if not allowed_fields:
            return patch
        return {key: value for key, value in patch.items() if key in allowed_fields}

    def _coerce_target_patch(
        self, parsed: Dict[str, Any], allowed_fields: Optional[List[str]]
    ) -> Dict[str, Any] | None:
        if not isinstance(parsed, dict):
            return None
        target_patch = parsed.get("target_patch")
        if isinstance(target_patch, dict):
            # Narrative safety: many model outputs return nested objects instead of target_patch.summary.
            if allowed_fields == ["summary"] and "summary" not in target_patch:
                nested_summary = self._extract_narrative_summary_text(target_patch)
                if isinstance(nested_summary, str) and nested_summary.strip():
                    return {"summary": nested_summary.strip()}
            return target_patch
        if not allowed_fields or len(allowed_fields) != 1:
            return None
        expected_key = allowed_fields[0]
        if expected_key in parsed:
            value = parsed.get(expected_key)
            if isinstance(value, (int, float)):
                return {expected_key: int(value)}
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed.isdigit():
                    return {expected_key: int(trimmed)}
                return {expected_key: trimmed}
        for key in ("text", "content"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return {expected_key: value}
        string_fields = {k: v for k, v in parsed.items() if isinstance(v, str)}
        if len(string_fields) == 1:
            _, value = next(iter(string_fields.items()))
            return {expected_key: value}
        return None

    def _extract_narrative_summary_text(self, payload: Dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return ""
        # Common malformed shapes returned by the model for narrative presentation.
        candidates: List[Any] = [
            payload.get("summary"),
            (((payload.get("core") or {}).get("narrative_presentation") or {}).get("summary")),
            (
                ((payload.get("core") or {}).get("narrative_presentation") or {}).get(
                    "narrative_foundation"
                )
            ),
            (((payload.get("narrative_presentation") or {}).get("summary"))),
            (((payload.get("narrative_presentation") or {}).get("narrative_foundation"))),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        return ""

    def _normalize_target_patch_keys(
        self, patch: Dict[str, Any], allowed_fields: Optional[List[str]]
    ) -> Dict[str, Any]:
        if not isinstance(patch, dict) or not patch:
            return patch
        if not allowed_fields or len(allowed_fields) != 1:
            return patch
        expected_key = allowed_fields[0]
        if expected_key in patch:
            return patch
        # Common mistake for numeric tasks: the model returns the full target path
        # as a key (e.g. {"n1.characters.main_characters.number": 2}).
        if len(patch) == 1:
            only_key, only_value = next(iter(patch.items()))
            if isinstance(only_key, str):
                last_segment = only_key.split(".")[-1].strip()
                if last_segment == expected_key:
                    return {expected_key: only_value}
        # If the redactor returned a single text field, map it deterministically.
        string_fields = {k: v for k, v in patch.items() if isinstance(v, str)}
        if len(string_fields) == 1:
            _, value = next(iter(string_fields.items()))
            return {expected_key: value}
        return patch

    def _collect_meta_violations(
        self, patch: Dict[str, Any], allowed_fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        if not isinstance(patch, dict):
            return []
        fields = allowed_fields or list(patch.keys())
        triggers = [
            "the narrative presentation",
            "this narrative presentation",
            "narrative presentation should",
            "the narrative presentation is",
            "the redactor",
            "writing strategy",
            "style guidelines",
            "structure guidelines",
            "watchpoints",
            "keep to target length",
            "single paragraph",
            "8-12 sentences",
            "by adhering to",
            "according to robert",
            "mckee",
            "lavandier",
        ]
        violations: List[Dict[str, Any]] = []
        for field in fields:
            value = patch.get(field)
            if not isinstance(value, str):
                continue
            lowered = value.lower()
            matches = [trigger for trigger in triggers if trigger in lowered]
            if matches:
                violations.append({"field": field, "matches": matches})
        return violations

    def _collect_length_violations(
        self,
        patch: Dict[str, Any],
        constraints: Dict[str, int],
        allowed_fields: Optional[List[str]],
    ) -> List[Dict[str, int]]:
        if not isinstance(patch, dict):
            return []
        if not isinstance(constraints, dict):
            return []
        min_chars = int(constraints.get("min_chars") or 0)
        max_chars = int(constraints.get("max_chars") or 0)
        if min_chars <= 0 and max_chars <= 0:
            return []
        fields = allowed_fields or list(patch.keys())
        violations: List[Dict[str, int]] = []
        for field in fields:
            value = patch.get(field)
            if not isinstance(value, str):
                continue
            length = len(value.strip())
            if min_chars and length < min_chars:
                violations.append(
                    {"field": field, "length": length, "min": min_chars, "max": max_chars}
                )
            elif max_chars and length > max_chars:
                violations.append(
                    {"field": field, "length": length, "min": min_chars, "max": max_chars}
                )
        return violations

    def _build_retry_prompt(
        self,
        context_pack: Dict[str, Any],
        target_path: str,
        plan: WritingPlan,
        length_violations: List[Dict[str, int]],
        meta_violations: List[Dict[str, Any]],
        existing_patch: Dict[str, Any],
        allowed_hint: str,
    ) -> str:
        length_lines = ""
        if length_violations:
            length_lines = "\n".join(
                [
                    f"- {item.get('field')}: {item.get('length')} chars "
                    f"(min {item.get('min')}, max {item.get('max')})."
                    for item in length_violations
                ]
            )
        meta_lines = ""
        if meta_violations:
            meta_lines = "\n".join(
                [
                    f"- {item.get('field')}: remove meta-writing phrases "
                    f"(matches: {', '.join(item.get('matches', [])[:6])})."
                    for item in meta_violations
                ]
            )
        rules = context_pack.get("rules") if isinstance(context_pack, dict) else {}
        redaction_rules = []
        if isinstance(rules, dict):
            redaction_rules = rules.get("redaction_rules") or []
        redaction_rules_line = ""
        if isinstance(redaction_rules, list) and redaction_rules:
            rules_text = "; ".join([str(item) for item in redaction_rules if str(item).strip()])
            if rules_text:
                redaction_rules_line = f"- Redaction rules: {rules_text}.\n"
        existing_block = (
            "Existing content to revise (do not discard):\n"
            f"{json.dumps(existing_patch, ensure_ascii=True, indent=2)}\n"
        )
        correction_mode = "Correction mode:\n"
        if length_violations:
            correction_mode += "- Adjust the existing content to satisfy min/max character constraints.\n"
        if meta_violations:
            correction_mode += (
                "- Remove any meta-writing language or references to strategy, sources, or guidelines.\n"
                "- Do NOT mention the narrative presentation as an object or the act of summarizing.\n"
            )
        redactor_context_pack = self._context_pack_for_redactor(context_pack)
        compiler = RedactorPromptCompiler()
        return compiler.build_retry_user_prompt(
            target_path=target_path,
            context_pack=redactor_context_pack,
            allowed_fields=plan.allowed_fields,
            redaction_rules=redaction_rules if isinstance(redaction_rules, list) else [],
            extra_rule=str(plan.extra_rule or ""),
            length_violations=length_violations,
            meta_violations=meta_violations,
            existing_patch=existing_patch,
        )
