"""Runner that executes task plans sequentially or in parallel."""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.narration_agent.chat.chat_memory_store import ChatMemoryStore
from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.spec_loader import load_json, load_text
from app.narration_agent.chat.ui_translator import UITranslator
from app.narration_agent.writer_agent.writer_orchestrator import WriterOrchestrator
from app.narration_agent.writer_agent.strategy_finder.rag_bootstrap import (
    purge_rag_conversations_now,
)
from app.utils.ids import generate_timestamp
from app.utils.logging import setup_logger
from app.utils.project_storage import get_project_root


@dataclass
class RunnerInput:
    plan_id: str
    task_plan_ref: Optional[str]
    task_plan_payload: Optional[Dict[str, Any]]
    execution_mode: str
    started_at: str


class TaskRunner:
    """Execute tasks based on a runner input wrapper."""

    def __init__(self, llm_client: LLMClient, memory_store: ChatMemoryStore):
        self.llm_client = llm_client
        self.memory_store = memory_store
        self.logger = setup_logger("narration_writer")
        self.ui_translator = UITranslator(llm_client)

    def run_task_plan(
        self,
        task_plan: Dict[str, Any],
        project_id: str,
        session_id: str,
        task_context: Dict[str, Any],
        initial_state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tasks = task_plan.get("tasks") or []
        results: List[Dict[str, Any]] = []
        outputs: Dict[str, Dict[str, Any]] = {}
        state_snapshot = (
            initial_state_snapshot if isinstance(initial_state_snapshot, dict) else self._initialize_state()
        )
        for task in tasks:
            agent = task.get("agent")
            payload = task_context.get(task.get("id") or "", {}) if task_context else {}
            if agent == "chat_1a":
                result = self._run_chat_1a(
                    project_id=project_id,
                    session_id=session_id,
                    payload=payload,
                )
            elif agent == "chat_1b":
                result = self._run_chat_1b(
                    payload=payload,
                    prior_output=outputs.get(task.get("input_ref") or "", {}),
                )
            elif agent == "chat_1c":
                result = self._run_chat_1c(
                    payload=payload,
                    prior_output=outputs.get(task.get("input_ref") or "", {}),
                )
            elif agent and agent.startswith("writer_"):
                result = self._run_writer(
                    project_id=project_id,
                    session_id=session_id,
                    payload=payload,
                    prior_output=outputs.get(task.get("input_ref") or "", {}),
                    target_path=task.get("output_ref") or "",
                    agent_name=agent,
                )
            else:
                result = {"status": "skipped", "reason": "unknown_agent"}
            if result.get("assistant_state_json"):
                patch = self._parse_json_patch(result.get("assistant_state_json", ""))
                if patch:
                    if agent in {"chat_1a", "chat_1b", "chat_1c"}:
                        patch = self.ui_translator.translate_chat_patch(patch)
                    state_snapshot = self._merge_state(state_snapshot, patch)
            if agent == "chat_1a":
                self._mark_completed_step(state_snapshot, "1a")
            elif agent == "chat_1b":
                self._mark_completed_step(state_snapshot, "1b")
            elif agent == "chat_1c":
                self._mark_completed_step(state_snapshot, "1c")
            result_payload = {
                **result,
                "state_snapshot": state_snapshot,
            }
            output_ref = task.get("output_ref") or ""
            if output_ref:
                outputs[output_ref] = result_payload
            results.append(
                {
                    "task_id": task.get("id"),
                    "status": "done",
                    "output_ref": task.get("output_ref"),
                    "error": "",
                    "output": result_payload,
                }
            )
            self._purge_rag_conversations_after_n0_step(
                project_id=project_id,
                agent=agent,
                output_ref=output_ref,
                result=result,
            )
        return {
            "plan_id": task_plan.get("plan_id"),
            "status": "completed",
            "results": results,
            "completed_at": generate_timestamp(),
        }

    def _purge_rag_conversations_after_n0_step(
        self,
        *,
        project_id: str,
        agent: str,
        output_ref: str,
        result: Dict[str, Any],
    ) -> None:
        if agent != "writer_n0":
            return
        if not isinstance(output_ref, str) or not output_ref.startswith("n0."):
            return
        status = str(result.get("status", "")).strip().lower()
        if status not in {"done", "partial"}:
            return
        try:
            purge_info = purge_rag_conversations_now(project_id=project_id)
        except Exception as exc:
            self.logger.warning(
                "Failed to purge R2R conversations after %s: %s",
                output_ref,
                exc,
            )
            return
        self.logger.info(
            "R2R conversations purged after %s: %s",
            output_ref,
            purge_info,
        )

    def _initialize_state(self) -> Dict[str, Any]:
        template = load_json("chat/state_structure_01_abc.json") or {}
        return {key: value for key, value in template.items() if not key.startswith("_")}

    def _parse_json_patch(self, payload: str) -> Dict[str, Any]:
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _merge_state(self, base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in patch.items():
            if key.startswith("_"):
                continue
            if isinstance(value, dict):
                base_value = base.get(key)
                if not isinstance(base_value, dict):
                    base[key] = {}
                base[key] = self._merge_state(base.get(key, {}), value)
                continue
            if value in (None, "", [], {}):
                continue
            base[key] = value
        return base

    def _mark_completed_step(self, state: Dict[str, Any], step: str) -> None:
        completed = state.get("completed_steps")
        if not isinstance(completed, list):
            completed = []
        if step not in completed:
            completed.append(step)
        state["completed_steps"] = completed

    def _build_system_prompt(
        self,
        project_empty: bool,
        empty_strata: Dict[str, bool],
        pending_questions: List[str],
        pending_rounds: int,
        chat_mode: str,
    ) -> str:
        empty_list = [key.upper() for key, is_empty in empty_strata.items() if is_empty]
        empty_summary = ", ".join(empty_list) if empty_list else "none"
        pending_summary = (
            "\n".join([f"- {question}" for question in pending_questions])
            if pending_questions
            else "none"
        )
        base_prompt = load_text("chat/01a_chat.md").strip()
        runtime_prompt = (
            "Runtime context:\n"
            f"- Project empty: {'yes' if project_empty else 'no'}\n"
            f"- Empty strata: {empty_summary}\n"
            f"- Pending questions to resolve: {pending_summary}\n"
            f"- Pending rounds used: {pending_rounds}\n"
            f"- Chat mode: {chat_mode or 'auto'}\n"
        )
        if not base_prompt:
            base_prompt = (
                "You are the 1a dialogue agent for narrative project creation.\n"
                "Goal: clarify the request and ask 1 to 3 questions maximum.\n"
                "Constraints: respond in English, stay brief, do not invent."
            )
        format_prompt = (
            "Required output format:\n"
            "1) A 'User response:' section in natural language.\n"
            "2) A 'JSON for 1b:' section containing a ```json ... ``` block.\n"
            "The JSON is a minimal PATCH aligned with state_structure_01_abc schema:\n"
            "- only `core` + `missing` (+ `completed_steps`).\n"
            "- do not include `thinker`, `brief`, `pending_questions`.\n"
            "Question rules for 1a:\n"
            "- Ask at most 1 question.\n"
            "- If pending questions exist, ask them first and only them (verbatim, max 1).\n"
            "- Do NOT add a project summary before the pending questions.\n"
            "- Do NOT ask for confirmations or say 'if correct'.\n"
            "- If pending rounds used >= 1, ask 0 questions and proceed with best assumptions.\n"
            "Language rules for 1a:\n"
            "- Detect the user's language and respond in that language.\n"
            "- Always write JSON state values in English.\n"
            "- If you mention state content to the user, translate it into the user's language.\n"
            "Fidelity rules for 1a:\n"
            "- `core.summary` MUST be a faithful English translation of all user messages in the session.\n"
            "- Do NOT summarize, do NOT expand, do NOT add new details.\n"
            "- Preserve the user's style and roughly the same amount of text."
        )
        return f"{base_prompt}\n\n{runtime_prompt}\n{format_prompt}"

    def _translation_length_bounds(self, source_chars: int) -> tuple[int, int]:
        """Heuristic bounds to preserve 'quantity' across translations."""
        if source_chars <= 0:
            return 0, 4000
        # For short messages, be more tolerant.
        if source_chars <= 60:
            return max(15, int(source_chars * 0.6)), min(4000, int(source_chars * 1.8) + 20)
        if source_chars <= 200:
            return int(source_chars * 0.75), min(4000, int(source_chars * 1.35))
        # For longer messages, keep closer.
        return int(source_chars * 0.85), min(4000, int(source_chars * 1.2))

    def _parse_duration_seconds(self, value: Any) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return max(0, int(value))
        if not isinstance(value, str):
            return 0
        text = value.strip().lower()
        if not text:
            return 0
        if text.isdigit():
            return max(0, int(text))

        timecode_match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
        if timecode_match:
            hours = 0
            minutes = int(timecode_match.group(1))
            seconds = int(timecode_match.group(2))
            if timecode_match.group(3) is not None:
                hours = minutes
                minutes = seconds
                seconds = int(timecode_match.group(3))
            return hours * 3600 + minutes * 60 + seconds

        # Patterns like "2h30" or "2h 30"
        hm_match = re.search(r"(\d+)\s*h\s*(\d{1,2})?", text)
        if hm_match:
            hours = int(hm_match.group(1))
            minutes = int(hm_match.group(2)) if hm_match.group(2) else 0
            return hours * 3600 + minutes * 60

        # Generic unit parsing
        total_seconds = 0.0
        for number, unit in re.findall(
            r"(\d+(?:[.,]\d+)?)\s*(h|hr|hour|hours|heure|heures|m|min|minute|minutes|s|sec|secs|second|seconds|seconde|secondes)",
            text,
        ):
            value_f = float(number.replace(",", "."))
            if unit.startswith(("h", "hr", "hour", "heure")):
                total_seconds += value_f * 3600
            elif unit.startswith(("m", "min", "minute")):
                total_seconds += value_f * 60
            else:
                total_seconds += value_f
        return int(total_seconds) if total_seconds > 0 else 0

    def _build_brief_inference_text(self, payload: Dict[str, Any]) -> str:
        parts: List[str] = []
        core = payload.get("core") if isinstance(payload, dict) else {}
        thinker = payload.get("thinker") if isinstance(payload, dict) else {}
        brief = payload.get("brief") if isinstance(payload, dict) else {}
        for value in (
            core.get("summary") if isinstance(core, dict) else "",
            core.get("notes") if isinstance(core, dict) else "",
            brief.get("primary_objective") if isinstance(brief, dict) else "",
            brief.get("project_title") if isinstance(brief, dict) else "",
            brief.get("video_type") if isinstance(brief, dict) else "",
        ):
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        for list_value in (
            brief.get("constraints") if isinstance(brief, dict) else [],
            thinker.get("constraints") if isinstance(thinker, dict) else [],
            thinker.get("hypotheses") if isinstance(thinker, dict) else [],
        ):
            if isinstance(list_value, list):
                parts.extend([str(item) for item in list_value if str(item).strip()])
        return " | ".join(parts)

    def _infer_video_type(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        lowered = text.lower()
        mapping = [
            (["advertisement", "ad", "commercial", "pub", "publicite", "publicité"], "ad"),
            (["music video", "clip"], "clip"),
            (["documentary", "docu", "documentaire"], "documentary"),
            (["series", "série", "serie"], "series"),
            (["short film", "court metrage", "court-metrage", "court métrage"], "short film"),
            (["feature film", "long metrage", "long-metrage", "long métrage"], "feature film"),
            (["film", "movie", "cinema", "cinéma"], "film"),
        ]
        for keywords, value in mapping:
            if any(keyword in lowered for keyword in keywords):
                return value
        return ""

    def _normalize_brief_patch(
        self, patch: Dict[str, Any], input_payload: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not isinstance(patch, dict):
            return patch
        brief = patch.get("brief")
        if not isinstance(brief, dict):
            return patch
        brief = {**brief}
        duration_s = self._parse_duration_seconds(brief.get("target_duration_s"))
        if not duration_s:
            duration_s = self._parse_duration_seconds(brief.get("target_duration"))
        brief["target_duration_s"] = duration_s
        brief.pop("target_duration", None)
        video_type = brief.get("video_type", "")
        if not (isinstance(video_type, str) and video_type.strip()):
            if isinstance(input_payload, dict):
                inferred = self._infer_video_type(self._build_brief_inference_text(input_payload))
                if inferred:
                    brief["video_type"] = inferred
        patch = {**patch, "brief": brief}
        return patch

    def _get_nested_str(self, data: Any, path: List[str]) -> str:
        current = data
        for key in path:
            if not isinstance(current, dict):
                return ""
            current = current.get(key)
        return current.strip() if isinstance(current, str) else ""

    def _repair_chat_1a_patch_length(
        self,
        *,
        user_message: str,
        patch: Dict[str, Any],
        min_chars: int,
        max_chars: int,
    ) -> Dict[str, Any]:
        """Ask the model to adjust core.summary length only."""
        system_prompt = (
            "You are a JSON patch fixer.\n"
            "Task: rewrite ONLY patch.core.summary.\n"
            "Rules:\n"
            "- core.summary must be a faithful English translation of the user's message.\n"
            "- Preserve style and roughly the same amount of text.\n"
            "- Length constraint: core.summary must be between min_chars and max_chars.\n"
            "- Do NOT change any other key in the patch.\n"
            "- Return ONLY valid JSON (no markdown, no commentary)."
        )
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "min_chars": min_chars,
                "max_chars": max_chars,
                "current_patch": patch,
            },
            ensure_ascii=True,
            indent=2,
        )
        llm_response = self.llm_client.complete(
            LLMRequest(
                model=self.llm_client.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
        )
        repaired = self._parse_json_payload(payload="", fallback=llm_response.content.strip())
        return repaired or patch

    def _build_thinker_prompt(self) -> str:
        base_prompt = load_text("chat/01b_thinker.md").strip()
        if not base_prompt:
            base_prompt = (
                "You are agent 1b (thinker). Reframe the request and extract "
                "objectives, constraints, hypotheses. Stay factual, no invention."
            )
        return base_prompt

    def _build_translator_prompt(self) -> str:
        base_prompt = load_text("chat/01c_orchestrator_translator.md").strip()
        if not base_prompt:
            base_prompt = (
                "You are agent 1c (translator). Transform 1b output into a "
                "structured orchestration brief. Stay concise."
            )
        return base_prompt

    def _run_chat_1a(
        self, project_id: str, session_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        message = (payload.get("message") or "").strip()
        if not message:
            return {"status": "error", "error": "missing_message"}
        project_empty = bool(payload.get("project_empty"))
        empty_strata = payload.get("empty_strata") or {}
        pending_questions = payload.get("pending_questions") or []
        if not isinstance(pending_questions, list):
            pending_questions = []
        pending_rounds = payload.get("pending_rounds", 0)
        if not isinstance(pending_rounds, int):
            pending_rounds = 0
        chat_mode = payload.get("chat_mode", "auto")

        session_messages = self.memory_store.load_messages(project_id, session_id)
        session_messages.append({"role": "user", "content": message})
        full_user_text = "\n\n".join(
            [
                msg.get("content", "")
                for msg in session_messages
                if isinstance(msg, dict) and msg.get("role") == "user"
            ]
        ).strip()

        system_prompt = self._build_system_prompt(
            project_empty, empty_strata, pending_questions, pending_rounds, chat_mode
        )
        chat_messages = [{"role": "system", "content": system_prompt}]
        chat_messages.extend(session_messages[-12:])

        llm_response = self.llm_client.complete(
            LLMRequest(model=self.llm_client.default_model, messages=chat_messages, temperature=0.4)
        )
        raw_content = llm_response.content.strip()
        user_text, json_payload = self._split_user_and_json(raw_content)

        # Enforce the "quantity-preserving translation" requirement for core.summary.
        if json_payload:
            patch = self._parse_json_payload(payload=json_payload, fallback="") or {}
            summary = self._get_nested_str(patch, ["core", "summary"])
            if summary:
                src_len = len(full_user_text or message.strip())
                out_len = len(summary)
                min_chars, max_chars = self._translation_length_bounds(src_len)
                if src_len and (out_len < min_chars or out_len > max_chars):
                    repaired = self._repair_chat_1a_patch_length(
                        user_message=full_user_text or message,
                        patch=patch,
                        min_chars=min_chars,
                        max_chars=max_chars,
                    )
                    repaired_summary = self._get_nested_str(repaired, ["core", "summary"])
                    repaired_len = len(repaired_summary) if repaired_summary else 0
                    if repaired_summary and (min_chars <= repaired_len <= max_chars):
                        json_payload = json.dumps(repaired, ensure_ascii=True)

        session_messages.append({"role": "assistant", "content": user_text})
        self.memory_store.save_messages(project_id, session_id, session_messages)

        return {
            "assistant_message": user_text,
            "assistant_state_json": json_payload,
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

    def _update_ui_translation(self, project_id: str, target_path: str) -> None:
        strata = target_path.split(".", 1)[0] if target_path else ""
        if strata not in {"n0", "n1"}:
            return
        try:
            self.ui_translator.update_ui_translation(project_id, strata, language="fr")
        except Exception:
            return

    def _write_writer_log(
        self,
        project_id: str,
        session_id: str,
        target_path: str,
        agent_name: str,
        status: str,
        target_patch: Dict[str, Any],
        open_questions: List[str],
        raw_output: str,
        strategy_card: Dict[str, Any],
        context_pack: Optional[Dict[str, Any]] = None,
        agentic_trace: Optional[List[Dict[str, Any]]] = None,
        warning: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        try:
            root = get_project_root(project_id)
            strata = target_path.split(".", 1)[0].strip().lower() if isinstance(target_path, str) else ""
            if not re.fullmatch(r"n[0-9]+", strata or ""):
                strata = "misc"
            log_dir = root / "writer_logs" / strata
            log_dir.mkdir(parents=True, exist_ok=True)
            safe_target = re.sub(r"[^a-zA-Z0-9._-]+", "_", target_path)
            safe_time = re.sub(r"[^a-zA-Z0-9_-]+", "_", generate_timestamp())
            filename = f"{safe_time}_{safe_target}.json"
            context_pack = context_pack if isinstance(context_pack, dict) else {}
            context_groups = context_pack.get("context_groups") if isinstance(context_pack, dict) else []
            if not isinstance(context_groups, list):
                context_groups = []
            context_groups_summary = [
                {
                    "name": g.get("name", ""),
                    "weight": g.get("weight", 0),
                    "description": g.get("description", ""),
                }
                for g in context_groups
                if isinstance(g, dict)
            ]
            payload = {
                "project_id": project_id,
                "session_id": session_id,
                "agent": agent_name,
                "target_path": target_path,
                "status": status,
                "warning": warning or "",
                "error": error or "",
                "target_patch": target_patch or {},
                "open_questions": open_questions or [],
                "writer_debug": {
                    "rule_mode": context_pack.get("rule_mode", ""),
                    "writing_mode": context_pack.get("writing_mode", ""),
                    "allowed_fields": context_pack.get("allowed_fields", []),
                    "writing_typology": context_pack.get("writing_typology", ""),
                    "redaction_constraints": context_pack.get("redaction_constraints", {}),
                    "library_filename_prefixes": context_pack.get("library_filename_prefixes", []),
                    "strategy_finder_question": context_pack.get("strategy_finder_question", ""),
                    "writer_self_question": context_pack.get("writer_self_question", ""),
                    "context_groups": context_groups_summary,
                    "redaction_attempts": context_pack.get("redaction_attempts", []),
                    # Minimal, directly readable subset of chat context (1abc)
                    # that was provided to the redactor via context_pack.
                    "chat_context": {
                        "brief_primary_objective": context_pack.get("brief_primary_objective", ""),
                        "brief_project_title": context_pack.get("brief_project_title", ""),
                        "brief_video_type": context_pack.get("brief_video_type", ""),
                        "brief_target_duration_s": context_pack.get("brief_target_duration_s", 0),
                        "brief_constraints": context_pack.get("brief_constraints", []),
                        "brief_priorities": context_pack.get("brief_priorities", []),
                        "thinker_constraints": context_pack.get("thinker_constraints", []),
                        "core_summary": context_pack.get("core_summary", ""),
                        "pending_questions": context_pack.get("pending_questions", []),
                    },
                },
                "strategy_card": strategy_card or {},
                "agentic_trace": agentic_trace or [],
                "raw_output": raw_output[:8000],
                "logged_at": generate_timestamp(),
            }
            (log_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
            )

            # Also write full redactor prompts as plain-text files (no JSON escaping),
            # so they are readable directly in the editor.
            attempts = context_pack.get("redaction_attempts", [])
            if isinstance(attempts, list) and attempts:
                for attempt in attempts:
                    if not isinstance(attempt, dict):
                        continue
                    phase = str(attempt.get("phase") or "").strip() or "unknown"
                    prompt_debug = attempt.get("prompt_debug")
                    if not isinstance(prompt_debug, dict):
                        continue
                    system_prompt = prompt_debug.get("system_prompt")
                    user_prompt = prompt_debug.get("user_prompt")
                    safe_phase = re.sub(r"[^a-zA-Z0-9._-]+", "_", phase)
                    base = f"{safe_time}_{safe_target}_{safe_phase}"
                    if isinstance(system_prompt, str) and system_prompt:
                        (log_dir / f"{base}_system_prompt.txt").write_text(
                            system_prompt, encoding="utf-8"
                        )
                    if isinstance(user_prompt, str) and user_prompt:
                        (log_dir / f"{base}_user_prompt.txt").write_text(
                            user_prompt, encoding="utf-8"
                        )
        except Exception:
            return

    def _split_user_and_json(self, content: str) -> tuple[str, str]:
        json_block = self._extract_json_block(content)
        if not json_block:
            return content.strip(), ""
        before, _, _ = content.partition("```json")
        user_text = before.replace("Reponse utilisateur:", "").replace("User response:", "").strip()
        return user_text or content.strip(), json_block

    def _extract_trigger(self, content: str) -> str:
        if not content:
            return ""
        match = re.search(
            r"(?im)^\s*##\s*trigger\s*:\s*([a-zA-Z_]+)\s*##\s*$", content
        )
        if not match:
            match = re.search(r"(?im)^\s*trigger\s*:\s*([a-zA-Z_]+)\s*$", content)
        if not match:
            return ""
        trigger = match.group(1).strip().lower()
        if trigger in {"clarify", "chat", "build_brief", "use_memory"}:
            return trigger
        return ""

    def _run_chat_1b(
        self, payload: Dict[str, Any], prior_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        input_payload = (
            prior_output.get("state_snapshot")
            or prior_output.get("assistant_state_json")
            or prior_output.get("assistant_message")
            or payload.get("message")
            or ""
        )
        if isinstance(input_payload, dict):
            input_text = json.dumps(input_payload)
        else:
            input_text = input_payload
        pending_rounds = payload.get("pending_rounds")
        pending_questions = payload.get("pending_questions")
        runtime_lines = []
        if isinstance(pending_rounds, int):
            runtime_lines.append(f"pending_rounds: {pending_rounds}")
        if isinstance(pending_questions, list) and pending_questions:
            runtime_lines.append(
                "pending_questions: " + ", ".join([str(q) for q in pending_questions if str(q)])
            )
        if runtime_lines:
            runtime_block = "Runtime context:\n" + "\n".join(runtime_lines)
            input_text = f"{input_text}\n\n{runtime_block}"
        if not input_text:
            return {"status": "error", "error": "missing_input"}
        system_prompt = self._build_thinker_prompt()
        llm_response = self.llm_client.complete(
            LLMRequest(
                model=self.llm_client.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text},
                ],
                temperature=0.3,
            )
        )
        raw_content = llm_response.content.strip()
        trigger = self._extract_trigger(raw_content)
        json_block = self._extract_json_block(raw_content)
        return {
            "assistant_message": raw_content,
            "assistant_state_json": json_block or raw_content,
            "trigger": trigger,
        }

    def _run_chat_1c(
        self, payload: Dict[str, Any], prior_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        input_payload = payload.get("input_payload")
        if not input_payload:
            input_payload = (
                prior_output.get("state_snapshot")
                or prior_output.get("assistant_state_json")
                or prior_output.get("assistant_message")
                or payload.get("message")
                or ""
            )
        input_payload_dict = input_payload if isinstance(input_payload, dict) else None
        if isinstance(input_payload, dict):
            input_text = json.dumps(input_payload)
        else:
            input_text = input_payload
        if not input_text:
            return {"status": "error", "error": "missing_input"}
        system_prompt = self._build_translator_prompt()
        llm_response = self.llm_client.complete(
            LLMRequest(
                model=self.llm_client.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": input_text},
                ],
                temperature=0.3,
            )
        )
        raw_content = llm_response.content.strip()
        json_block = self._extract_json_block(raw_content)
        if json_block:
            parsed = self._parse_json_payload(json_block, raw_content)
            if isinstance(parsed, dict):
                normalized = self._normalize_brief_patch(parsed, input_payload_dict)
                if normalized != parsed:
                    json_block = json.dumps(normalized, ensure_ascii=True)
        return {
            "assistant_message": raw_content,
            "assistant_state_json": json_block or raw_content,
        }

    def _run_writer(
        self,
        project_id: str,
        session_id: str,
        payload: Dict[str, Any],
        prior_output: Dict[str, Any],
        target_path: str,
        agent_name: str,
    ) -> Dict[str, Any]:
        source_state = (
            payload.get("source_state_payload")
            or payload.get("source_state")
            or payload.get("state_snapshot")
            or prior_output.get("state_snapshot")
            or {}
        )
        if not isinstance(source_state, dict):
            source_state = {}
        if not target_path:
            target_path = payload.get("target_path", "")
        if not target_path:
            return {"status": "error", "error": "missing_target_path"}
        if not source_state:
            return {"status": "error", "error": "missing_source_state"}

        writer_orchestrator = WriterOrchestrator(self.llm_client)
        result = writer_orchestrator.run(
            project_id=project_id,
            target_path=target_path,
            source_state=source_state,
        )
        if result.raw_output:
            self.logger.info(
                "writer_output",
                extra={
                    "agent": agent_name,
                    "project_id": project_id,
                    "target_path": target_path,
                    "content": result.raw_output[:4000],
                },
            )

        if result.status == "error":
            self._write_writer_log(
                project_id=project_id,
                session_id=session_id,
                target_path=target_path,
                agent_name=agent_name,
                status="error",
                target_patch=result.target_patch,
                open_questions=[],
                raw_output=result.raw_output,
                strategy_card=result.strategy_card,
                context_pack=result.context_pack,
                agentic_trace=result.agentic_trace,
                error=result.error,
            )
            return {"status": "error", "error": result.error, "target_patch": result.target_patch}

        if result.status == "partial":
            self._write_writer_log(
                project_id=project_id,
                session_id=session_id,
                target_path=target_path,
                agent_name=agent_name,
                status="partial",
                target_patch=result.target_patch,
                open_questions=[],
                raw_output=result.raw_output,
                strategy_card=result.strategy_card,
                context_pack=result.context_pack,
                agentic_trace=result.agentic_trace,
                warning=result.warning or "invalid_json",
            )
            self._update_ui_translation(project_id, target_path)
            return {
                "status": "partial",
                "target_path": target_path,
                "target_patch": result.target_patch,
                "open_questions": [],
                "context_pack": result.context_pack,
                "strategy_card": result.strategy_card,
                "warning": result.warning or "invalid_json",
                "raw": result.raw_output,
            }

        self._write_writer_log(
            project_id=project_id,
            session_id=session_id,
            target_path=target_path,
            agent_name=agent_name,
            status="done",
            target_patch=result.target_patch,
            open_questions=result.open_questions,
            raw_output=result.raw_output,
            strategy_card=result.strategy_card,
            context_pack=result.context_pack,
            agentic_trace=result.agentic_trace,
        )
        self._update_ui_translation(project_id, target_path)
        return {
            "status": "done",
            "target_path": target_path,
            "target_patch": result.target_patch,
            "open_questions": result.open_questions,
            "context_pack": result.context_pack,
            "strategy_card": result.strategy_card,
        }

