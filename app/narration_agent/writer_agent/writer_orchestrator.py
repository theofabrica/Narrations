"""Writer orchestrator that pilots context, strategy, and redactor."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.narration_agent.llm_client import LLMClient
from app.narration_agent.narration.state_merger import merge_target_patch
from app.narration_agent.spec_loader import load_json, load_text
from app.narration_agent.writer_agent.context_builder.context_builder import ContextBuilder
from app.narration_agent.writer_agent.strategy_finder.strategy_finder import StrategyFinder
from app.narration_agent.writer_agent.n_rules.n0_rules import (
    infer_n0_deliverables,
    infer_n0_production_summary,
    infer_n0_visual_style_tone,
)
from app.narration_agent.writer_agent.redactor.redactor import Redactor


@dataclass
class WritingPlan:
    target_path: str
    base_patch: Dict[str, Any] = field(default_factory=dict)
    allowed_fields: Optional[List[str]] = None
    redaction_constraints: Dict[str, int] = field(default_factory=dict)
    use_strategy: bool = True
    skip_llm: bool = False
    extra_rule: str = ""


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


class WriterOrchestrator:
    """Build a deterministic writing plan and run the redactor."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.context_builder = ContextBuilder()
        self.strategy_finder = StrategyFinder()
        self.redactor = Redactor(llm_client)
        self.n0_rules = self._load_n0_rules()

    def run(
        self,
        project_id: str,
        target_path: str,
        source_state: Dict[str, Any],
    ) -> WriterRunResult:
        context_pack = self.context_builder.build(project_id, source_state, target_path)
        target_current = context_pack.payload.get("target_current")
        if not isinstance(target_current, dict):
            target_current = {}

        plan = self._build_plan(target_path, source_state, target_current)
        if plan.redaction_constraints:
            context_pack.payload["redaction_constraints"] = plan.redaction_constraints

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

        strategy_card: Dict[str, Any] = {}
        if plan.use_strategy:
            strategy_card = self.strategy_finder.build_strategy(context_pack.payload)
        context_pack.payload["strategy_card"] = strategy_card

        existing_fields: Dict[str, str] = {}
        if plan.allowed_fields and isinstance(target_current, dict):
            for field in plan.allowed_fields:
                value = target_current.get(field)
                if isinstance(value, str) and value.strip():
                    existing_fields[field] = value.strip()
        if not existing_fields and isinstance(target_current, str) and target_current.strip():
            existing_fields["text"] = target_current.strip()

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
        user_prompt = (
            "Context pack (JSON):\n"
            f"{json.dumps(context_pack.payload, ensure_ascii=True, indent=2)}\n\n"
            "Return ONLY valid JSON with this structure:\n"
            '{ "target_patch": <object>, "open_questions": [] }\n'
            f"- target_patch must contain ONLY the content for '{target_path}'.\n"
            f"{allowed_hint}"
            f"{plan.extra_rule}"
            f"{mode_hint}"
            f"{existing_block}"
            "- Respect redaction_constraints.min_chars / max_chars.\n"
            "- Do not invent new information.\n"
        )

        redaction = self.redactor.redact(system_prompt=system_prompt, user_prompt=user_prompt)
        raw_content = redaction.raw_output
        parsed = redaction.parsed
        if not isinstance(parsed, dict):
            return WriterRunResult(
                status="partial",
                target_path=target_path,
                target_patch=plan.base_patch,
                open_questions=[],
                context_pack=context_pack.payload,
                strategy_card=strategy_card,
                warning="invalid_json",
                raw_output=raw_content,
            )

        target_patch = parsed.get("target_patch") if isinstance(parsed, dict) else None
        open_questions = parsed.get("open_questions") if isinstance(parsed, dict) else []
        filtered_patch: Dict[str, Any] = {}
        if isinstance(target_patch, dict):
            filtered_patch = (
                self._filter_allowed_fields(target_patch, plan.allowed_fields)
                if plan.allowed_fields
                else target_patch
            )
        merged_patch = self._merge_patch(plan.base_patch, filtered_patch)
        if merged_patch:
            try:
                merge_target_patch(project_id, target_path, merged_patch)
            except Exception as exc:
                return WriterRunResult(
                    status="error",
                    target_path=target_path,
                    target_patch=merged_patch,
                    open_questions=open_questions if isinstance(open_questions, list) else [],
                    context_pack=context_pack.payload,
                    strategy_card=strategy_card,
                    raw_output=raw_content,
                    error=str(exc),
                )

        if target_path == "n0.sound_direction":
            extra_patch = infer_n0_visual_style_tone(project_id, source_state)
            if extra_patch:
                try:
                    merge_target_patch(project_id, "n0.production_summary", extra_patch)
                except Exception:
                    pass

        return WriterRunResult(
            status="done",
            target_path=target_path,
            target_patch=merged_patch,
            open_questions=open_questions if isinstance(open_questions, list) else [],
            context_pack=context_pack.payload,
            strategy_card=strategy_card,
            raw_output=raw_content,
        )

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
            if target_path == "n0.production_summary":
                plan.base_patch = infer_n0_production_summary(source_state, target_current)
            elif target_path == "n0.deliverables":
                plan.base_patch = infer_n0_deliverables(source_state, target_current)
            rule = self.n0_rules.get(target_path, {})
            self._apply_declarative_rules(plan, rule)

        return plan

    def _load_n0_rules(self) -> Dict[str, Any]:
        rules = load_json("writer_agent/n_rules/n0_rules.json") or {}
        return rules if isinstance(rules, dict) else {}

    def _apply_declarative_rules(self, plan: WritingPlan, rule: Any) -> None:
        if not isinstance(rule, dict):
            return
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

    def _build_writer_prompt(self, target_path: str) -> str:
        base_prompt = load_text("writer_agent/redactor/redactor.md").strip()
        strata_prompt = ""
        if target_path.startswith("n0"):
            strata_prompt = load_text("narration/specs/02_01_project_writer.md").strip()
        if not base_prompt:
            base_prompt = "You are a redactor. Produce a patch for the target section only."
        return "\n\n".join([chunk for chunk in [base_prompt, strata_prompt] if chunk])

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
