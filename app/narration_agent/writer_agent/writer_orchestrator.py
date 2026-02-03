"""Writer orchestrator that pilots context, strategy, and redactor."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.narration_agent.llm_client import LLMClient, LLMRequest
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
    strategy_role: str = ""
    strategy_hints: List[str] = field(default_factory=list)
    redaction_rules: List[str] = field(default_factory=list)
    quality_criteria: List[str] = field(default_factory=list)


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
    """Build a deterministic writing plan and run the redactor."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.context_builder = ContextBuilder()
        self.strategy_finder = StrategyFinder(llm_client)
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
        context_pack.payload["rules"] = self._build_rules_payload(plan)

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
            strategy_question = self._build_strategy_question(
                target_path=target_path,
                context_pack=context_pack,
                rule=self._build_rules_payload(plan),
                has_existing=bool(existing_fields),
            )
            if strategy_question:
                context_pack["strategy_question"] = strategy_question
            strategy_card = self.strategy_finder.build_strategy(context_pack)
        context_pack["strategy_card"] = strategy_card

        redaction_result = self._redact_with_validations(
            target_path=target_path,
            context_pack=context_pack,
            plan=plan,
            existing_fields=existing_fields,
        )
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
                    merge_target_patch(project_id, "n0.production_summary", extra_patch)
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
            if last_eval and last_eval.needs_strategy and plan.use_strategy:
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
                strategy_question = self._build_strategy_question(
                    target_path=target_path,
                    context_pack=context_pack,
                    rule=self._build_rules_payload(plan),
                    has_existing=bool(existing_fields),
                )
                if strategy_question:
                    context_pack["strategy_question"] = strategy_question
                strategy_card = self.strategy_finder.build_strategy(context_pack)
                context_pack["strategy_card"] = strategy_card

            if action in {"redact", "build_strategy", "refresh_context"}:
                redaction_result = self._redact_with_validations(
                    target_path=target_path,
                    context_pack=context_pack,
                    plan=plan,
                    existing_fields=existing_fields,
                )
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
                    merge_target_patch(project_id, "n0.production_summary", extra_patch)
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
        user_prompt = (
            "Context pack (JSON):\n"
            f"{json.dumps(context_pack, ensure_ascii=True, indent=2)}\n\n"
            "Return ONLY valid JSON with this structure:\n"
            '{ "target_patch": <object>, "open_questions": [] }\n'
            f"- target_patch must contain ONLY the content for '{target_path}'.\n"
            "- Primary guidance: use strategy_card.strategy_text from the context pack.\n"
            "- Treat strategy_card.strategy_text as guidance only. Do NOT quote or paraphrase it.\n"
            "- Do NOT mention writing strategy, guidelines, sources, or the act of summarizing.\n"
            f"{allowed_hint}"
            f"{redaction_rules_line}"
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
            return RedactionCycleResult(
                parsed=False,
                filtered_patch={},
                open_questions=[],
                raw_output=raw_content,
                warning="invalid_json",
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
        warning_message = ""
        meta_violations = self._collect_meta_violations(filtered_patch, plan.allowed_fields)
        length_violations = self._collect_length_violations(
            filtered_patch, plan.redaction_constraints, plan.allowed_fields
        )
        if meta_violations or length_violations:
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
                    filtered_patch = (
                        self._filter_allowed_fields(retry_patch, plan.allowed_fields)
                        if plan.allowed_fields
                        else retry_patch
                    )
                    meta_violations = self._collect_meta_violations(
                        filtered_patch, plan.allowed_fields
                    )
                    length_violations = self._collect_length_violations(
                        filtered_patch, plan.redaction_constraints, plan.allowed_fields
                    )
            if meta_violations or length_violations:
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
        )

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
            "intents": context_pack.get("intents", []),
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
        if isinstance(rule.get("strategy_role"), str):
            plan.strategy_role = rule["strategy_role"]
        if isinstance(rule.get("strategy_hints"), list):
            plan.strategy_hints = [str(item) for item in rule["strategy_hints"] if str(item)]
        if isinstance(rule.get("redaction_rules"), list):
            plan.redaction_rules = [str(item) for item in rule["redaction_rules"] if str(item)]
        if isinstance(rule.get("quality_criteria"), list):
            plan.quality_criteria = [str(item) for item in rule["quality_criteria"] if str(item)]

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
        intents = context_pack.get("intents", [])
        constraints = context_pack.get("brief_constraints", [])

        lines = [
            f"I need to {mode} {role} for a film project.",
        ]
        if writing_typology:
            lines.append(f"Writing typology: {writing_typology}.")
        if isinstance(core_summary, str) and core_summary.strip():
            lines.append(f"Project summary: {core_summary.strip()}.")
        elif isinstance(brief_primary, str) and brief_primary.strip():
            lines.append(f"Primary objective: {brief_primary.strip()}.")
        if isinstance(intents, list) and intents:
            intents_line = ", ".join([str(item) for item in intents if str(item).strip()])
            if intents_line:
                lines.append(f"Intents: {intents_line}.")
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

    def _collect_meta_violations(
        self, patch: Dict[str, Any], allowed_fields: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        if not isinstance(patch, dict):
            return []
        fields = allowed_fields or list(patch.keys())
        triggers = [
            "the summary",
            "this summary",
            "summary should",
            "the summary is",
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
                "- Do NOT mention the summary as an object or the act of summarizing.\n"
            )
        return (
            "Context pack (JSON):\n"
            f"{json.dumps(context_pack, ensure_ascii=True, indent=2)}\n\n"
            "Return ONLY valid JSON with this structure:\n"
            '{ "target_patch": <object>, "open_questions": [] }\n'
            f"- target_patch must contain ONLY the content for '{target_path}'.\n"
            "- Primary guidance: use strategy_card.strategy_text from the context pack.\n"
            "- Treat strategy_card.strategy_text as guidance only. Do NOT quote or paraphrase it.\n"
            "- Do NOT mention writing strategy, guidelines, sources, or the act of summarizing.\n"
            f"{allowed_hint}"
            f"{redaction_rules_line}"
            f"{plan.extra_rule}"
            f"{correction_mode}"
            "- Preserve meaning and do not add new facts.\n"
            f"{length_lines}\n"
            f"{meta_lines}\n"
            f"{existing_block}"
            "- Respect redaction_constraints.min_chars / max_chars.\n"
            "- Do not invent new information.\n"
        )
