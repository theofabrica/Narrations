"""Runner that executes task plans sequentially or in parallel."""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.narration_agent.chat.chat_memory_store import ChatMemoryStore
from app.narration_agent.narration.context_builder import ContextBuilder
from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.spec_loader import load_json, load_text
from app.narration_agent.narration.state_merger import merge_target_patch
from app.narration_agent.narration.strategy_finder import StrategyFinder
from app.narration_agent.chat.ui_translator import UITranslator
from app.utils.ids import generate_timestamp
from app.utils.logging import setup_logger
from app.utils.project_storage import get_project_root, read_strata


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
        return {
            "plan_id": task_plan.get("plan_id"),
            "status": "completed",
            "results": results,
            "completed_at": generate_timestamp(),
        }

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
            "- Ask at most 2 questions.\n"
            "- If pending questions exist, ask them first and only them (verbatim, max 2).\n"
            "- Do NOT add a project summary before the pending questions.\n"
            "- Do NOT ask for confirmations or say 'if correct'.\n"
            "- If pending rounds used >= 2, ask 0 questions and proceed with best assumptions.\n"
            "Language rules for 1a:\n"
            "- Detect the user's language and respond in that language.\n"
            "- Always write JSON state values in English.\n"
            "- If you mention state content to the user, translate it into the user's language."
        )
        return f"{base_prompt}\n\n{runtime_prompt}\n{format_prompt}"

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
        if strata != "n0":
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
        warning: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        try:
            root = get_project_root(project_id)
            log_dir = root / "writer_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            safe_target = re.sub(r"[^a-zA-Z0-9._-]+", "_", target_path)
            safe_time = re.sub(r"[^a-zA-Z0-9_-]+", "_", generate_timestamp())
            filename = f"{safe_time}_{safe_target}.json"
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
                "strategy_card": strategy_card or {},
                "raw_output": raw_output[:8000],
                "logged_at": generate_timestamp(),
            }
            (log_dir / filename).write_text(
                json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
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

        context_builder = ContextBuilder()
        context_pack = context_builder.build(project_id, source_state, target_path)
        target_current = context_pack.payload.get("target_current")
        if not isinstance(target_current, dict):
            target_current = {}

        base_patch: Dict[str, Any] = {}
        allowed_fields: Optional[List[str]] = None
        skip_llm = False
        use_strategy = True
        extra_rule = ""
        if target_path.startswith("n0."):
            if target_path == "n0.production_summary":
                base_patch = self._infer_n0_production_summary(source_state, target_current)
                allowed_fields = ["summary"]
                context_pack.payload["redaction_constraints"] = {
                    "min_chars": 120,
                    "max_chars": 320,
                }
                extra_rule = (
                    "Writing rule (English): "
                    "Tell the summary as a visual story, like a storyteller who takes time "
                    "to narrate a beautiful scene.\n"
                )
                if base_patch:
                    merge_target_patch(project_id, target_path, base_patch)
                    target_current = self._merge_patch(target_current, base_patch)
                    context_pack.payload["target_current"] = target_current
            elif target_path == "n0.deliverables":
                base_patch = self._infer_n0_deliverables(source_state, target_current)
                skip_llm = True
            elif target_path == "n0.art_direction":
                allowed_fields = ["description"]
                context_pack.payload["redaction_constraints"] = {
                    "min_chars": 180,
                    "max_chars": 600,
                }
                use_strategy = False
                extra_rule = (
                    "Writing rule (English): "
                    "Describe the aesthetic style of the video precisely, highlighting what "
                    "makes it distinctive and recognizable.\n"
                )
            elif target_path == "n0.sound_direction":
                allowed_fields = ["description"]
                context_pack.payload["redaction_constraints"] = {
                    "min_chars": 180,
                    "max_chars": 600,
                }
                use_strategy = False
                extra_rule = (
                    "Writing rule (English): "
                    "Describe the sonic and musical style of the video precisely, highlighting "
                    "what makes it distinctive and recognizable.\n"
                )

        if skip_llm:
            if base_patch:
                merge_target_patch(project_id, target_path, base_patch)
            self._write_writer_log(
                project_id=project_id,
                session_id=session_id,
                target_path=target_path,
                agent_name=agent_name,
                status="done",
                target_patch=base_patch,
                open_questions=[],
                raw_output="",
                strategy_card={},
            )
            self._update_ui_translation(project_id, target_path)
            return {
                "status": "done",
                "target_path": target_path,
                "target_patch": base_patch,
                "open_questions": [],
                "context_pack": context_pack.payload,
                "strategy_card": {},
            }

        if use_strategy:
            strategy_finder = StrategyFinder()
            strategy_card = strategy_finder.build_strategy(context_pack.payload)
        else:
            strategy_card = {}
        context_pack.payload["strategy_card"] = strategy_card

        allowed_hint = ""
        if allowed_fields:
            allowed_hint = (
                f"- Only write these fields inside the target section: {', '.join(allowed_fields)}.\n"
            )

        system_prompt = self._build_writer_prompt(agent_name, target_path)
        user_prompt = (
            "Context pack (JSON):\n"
            f"{json.dumps(context_pack.payload, ensure_ascii=True, indent=2)}\n\n"
            "Return ONLY valid JSON with this structure:\n"
            '{ "target_patch": <object>, "open_questions": [] }\n'
            f"- target_patch must contain ONLY the content for '{target_path}'.\n"
            f"{allowed_hint}"
            f"{extra_rule}"
            "- Respect redaction_constraints.min_chars / max_chars.\n"
            "- Do not invent new information.\n"
        )
        llm_response = self.llm_client.complete(
            LLMRequest(
                model=self.llm_client.default_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
        )
        raw_content = llm_response.content.strip()
        self.logger.info(
            "writer_output",
            extra={
                "agent": agent_name,
                "project_id": project_id,
                "target_path": target_path,
                "content": raw_content[:4000],
            },
        )
        json_block = self._extract_json_block(raw_content) or raw_content
        parsed = self._parse_json_payload(json_block, raw_content)
        if not isinstance(parsed, dict):
            merged_patch = base_patch
            if merged_patch:
                try:
                    merge_target_patch(project_id, target_path, merged_patch)
                except Exception as exc:
                    self._write_writer_log(
                        project_id=project_id,
                        session_id=session_id,
                        target_path=target_path,
                        agent_name=agent_name,
                        status="error",
                        target_patch=merged_patch,
                        open_questions=[],
                        raw_output=raw_content,
                        strategy_card=strategy_card,
                        error=str(exc),
                    )
                    return {"status": "error", "error": str(exc), "target_patch": merged_patch}
            self._write_writer_log(
                project_id=project_id,
                session_id=session_id,
                target_path=target_path,
                agent_name=agent_name,
                status="partial",
                target_patch=merged_patch,
                open_questions=[],
                raw_output=raw_content,
                strategy_card=strategy_card,
                warning="invalid_json",
            )
            self._update_ui_translation(project_id, target_path)
            return {
                "status": "partial",
                "target_path": target_path,
                "target_patch": merged_patch,
                "open_questions": [],
                "context_pack": context_pack.payload,
                "strategy_card": strategy_card,
                "warning": "invalid_json",
                "raw": raw_content,
            }

        target_patch = parsed.get("target_patch") if isinstance(parsed, dict) else None
        open_questions = parsed.get("open_questions") if isinstance(parsed, dict) else []
        filtered_patch: Dict[str, Any] = {}
        if isinstance(target_patch, dict):
            filtered_patch = (
                self._filter_allowed_fields(target_patch, allowed_fields)
                if allowed_fields
                else target_patch
            )
        merged_patch = self._merge_patch(base_patch, filtered_patch)
        if merged_patch:
            try:
                merge_target_patch(project_id, target_path, merged_patch)
            except Exception as exc:
                self._write_writer_log(
                    project_id=project_id,
                    session_id=session_id,
                    target_path=target_path,
                    agent_name=agent_name,
                    status="error",
                    target_patch=merged_patch,
                    open_questions=open_questions if isinstance(open_questions, list) else [],
                    raw_output=raw_content,
                    strategy_card=strategy_card,
                    error=str(exc),
                )
                return {"status": "error", "error": str(exc), "target_patch": merged_patch}

        if target_path == "n0.sound_direction":
            extra_patch = self._infer_n0_visual_style_tone(source_state, project_id)
            if extra_patch:
                try:
                    merge_target_patch(project_id, "n0.production_summary", extra_patch)
                except Exception:
                    pass

        self._write_writer_log(
            project_id=project_id,
            session_id=session_id,
            target_path=target_path,
            agent_name=agent_name,
            status="done",
            target_patch=merged_patch,
            open_questions=open_questions if isinstance(open_questions, list) else [],
            raw_output=raw_content,
            strategy_card=strategy_card,
        )
        self._update_ui_translation(project_id, target_path)
        return {
            "status": "done",
            "target_path": target_path,
            "target_patch": merged_patch,
            "open_questions": open_questions if isinstance(open_questions, list) else [],
            "context_pack": context_pack.payload,
            "strategy_card": strategy_card,
        }

    def _build_writer_prompt(self, agent_name: str, target_path: str) -> str:
        base_prompt = load_text("writer_agent/10_writer.md").strip()
        strata_prompt = ""
        if target_path.startswith("n0"):
            strata_prompt = load_text("narration/specs/02_01_project_writer.md").strip()
        if not base_prompt:
            base_prompt = (
                "You are a writer agent. Produce a patch for the target section only."
            )
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

    def _infer_n0_production_summary(
        self, source_state: Dict[str, Any], target_current: Dict[str, Any]
    ) -> Dict[str, Any]:
        combined_text = self._collect_brief_text(source_state)
        intents = _get_list(source_state, ["core", "intents"])
        production_type = self._pick_from_keywords(
            combined_text,
            intents,
            [
                (["clip", "music video"], "clip"),
                (["advertisement", "ad", "commercial", "pub"], "advertisement"),
                (["documentary", "docu"], "documentary"),
                (["short film", "court-metrage", "short"], "short film"),
                (["feature film", "long metrage", "feature"], "feature film"),
                (["series", "serie"], "series"),
            ],
        )
        target_duration = self._extract_duration(combined_text)
        aspect_ratio = self._extract_aspect_ratio(combined_text)
        if not aspect_ratio:
            aspect_ratio = "16:9"

        patch: Dict[str, Any] = {}
        patch.update(self._apply_if_empty(target_current, "production_type", production_type))
        patch.update(self._apply_if_empty(target_current, "target_duration", target_duration))
        patch.update(self._apply_if_empty(target_current, "aspect_ratio", aspect_ratio))
        return patch

    def _infer_n0_visual_style_tone(
        self, source_state: Dict[str, Any], project_id: str
    ) -> Dict[str, Any]:
        try:
            n0_state = read_strata(project_id, "n0")
        except Exception:
            n0_state = {}
        n0_data = n0_state.get("data") if isinstance(n0_state, dict) else {}
        if not isinstance(n0_data, dict):
            n0_data = {}
        production_summary = n0_data.get("production_summary", {})
        art_desc = (n0_data.get("art_direction", {}) or {}).get("description", "")
        sound_desc = (n0_data.get("sound_direction", {}) or {}).get("description", "")
        combined_text = " | ".join(
            [
                self._collect_brief_text(source_state),
                production_summary.get("summary", "") if isinstance(production_summary, dict) else "",
                art_desc if isinstance(art_desc, str) else "",
                sound_desc if isinstance(sound_desc, str) else "",
            ]
        )
        visual_style = self._pick_from_keywords(
            combined_text,
            [],
            [
                (["futuristic", "futuriste", "cyberpunk"], "futuristic"),
                (["retro", "vintage"], "retro"),
                (["noir", "film noir"], "noir"),
                (["surreal", "surréaliste", "surrealiste"], "surreal"),
                (["minimal", "minimalist", "minimaliste"], "minimal"),
                (["neon", "néon", "neon-lit"], "neon"),
                (["classical", "classique"], "classical"),
                (["documentary", "docu", "documentaire"], "documentary"),
            ],
        )
        tone = self._pick_from_keywords(
            combined_text,
            [],
            [
                (["dramatic", "dramatique"], "dramatic"),
                (["epic", "epique", "épique"], "epic"),
                (["poetic", "poetique", "poétique"], "poetic"),
                (["dark", "sombre"], "dark"),
                (["melancholic", "melancolique", "mélancolique"], "melancholic"),
                (["romantic", "romantique"], "romantic"),
                (["comedic", "comedy", "comedie", "comédie"], "comedic"),
                (["satirical", "satire", "satirique"], "satirical"),
            ],
        )
        patch: Dict[str, Any] = {}
        if isinstance(production_summary, dict):
            patch.update(self._apply_if_empty(production_summary, "visual_style", visual_style))
            patch.update(self._apply_if_empty(production_summary, "tone", tone))
        return patch

    def _infer_n0_deliverables(
        self, source_state: Dict[str, Any], target_current: Dict[str, Any]
    ) -> Dict[str, Any]:
        combined_text = self._collect_brief_text(source_state)
        defaults = {
            "visuals": {"images_enabled": True, "videos_enabled": True},
            "audio_stems": {"dialogue": True, "sfx": True, "music": True},
        }
        current_visuals = target_current.get("visuals") if isinstance(target_current, dict) else {}
        current_audio = target_current.get("audio_stems") if isinstance(target_current, dict) else {}
        visuals = {**defaults["visuals"], **(current_visuals or {})}
        audio = {**defaults["audio_stems"], **(current_audio or {})}

        if self._has_negative(combined_text, ["no video", "sans video", "pas de video"]):
            visuals["videos_enabled"] = False
        if self._has_negative(combined_text, ["no image", "no images", "sans image", "sans images"]):
            visuals["images_enabled"] = False
        if self._has_negative(combined_text, ["no audio", "sans audio"]):
            audio["dialogue"] = False
            audio["sfx"] = False
            audio["music"] = False
        if self._has_negative(combined_text, ["no dialogue", "sans dialogue", "no voice", "sans voix"]):
            audio["dialogue"] = False
        if self._has_negative(combined_text, ["no music", "sans musique"]):
            audio["music"] = False
        if self._has_negative(combined_text, ["no sfx", "sans sfx", "sans bruitage"]):
            audio["sfx"] = False

        if self._has_positive(combined_text, ["image", "photo", "illustration", "affiche"]):
            visuals["images_enabled"] = True
        if self._has_positive(combined_text, ["video", "clip", "film", "animation"]):
            visuals["videos_enabled"] = True
        if self._has_positive(combined_text, ["dialogue", "voice", "voix", "narration"]):
            audio["dialogue"] = True
        if self._has_positive(combined_text, ["music", "musique", "soundtrack"]):
            audio["music"] = True
        if self._has_positive(combined_text, ["sfx", "bruitage", "sound design"]):
            audio["sfx"] = True

        return {"visuals": visuals, "audio_stems": audio}

    def _collect_brief_text(self, source_state: Dict[str, Any]) -> str:
        parts: List[str] = []
        parts.extend(_get_list(source_state, ["core", "intents"]))
        parts.append(_get_str(source_state, ["core", "summary"]))
        parts.append(_get_str(source_state, ["core", "detailed_summary"]))
        parts.append(_get_str(source_state, ["brief", "primary_objective"]))
        parts.extend(_get_list(source_state, ["brief", "secondary_objectives"]))
        parts.extend(_get_list(source_state, ["brief", "constraints"]))
        parts.extend(_get_list(source_state, ["thinker", "constraints"]))
        parts.extend(_get_list(source_state, ["thinker", "hypotheses"]))
        return " | ".join([part for part in parts if part])

    def _pick_from_keywords(
        self,
        text: str,
        intents: List[str],
        mapping: List[tuple[list[str], str]],
    ) -> str:
        haystack = " ".join([text, " ".join(intents)]).lower()
        for keywords, value in mapping:
            for keyword in keywords:
                if keyword in haystack:
                    return value
        return ""

    def _extract_tagged_value(self, text: str, tags: List[str]) -> str:
        if not text:
            return ""
        for tag in tags:
            pattern = re.compile(rf"{re.escape(tag)}\s*[:=-]\s*([^\n|]+)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_duration(self, text: str) -> str:
        if not text:
            return ""
        timecode_match = re.search(r"\b\d{1,2}:\d{2}\b", text)
        if timecode_match:
            return timecode_match.group(0)
        match = re.search(r"\b(\d+)\s*(hours|hour|heures|heure|h)\b", text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}h"
        match = re.search(r"\b(\d+)\s*(minutes|minute|min|m)\b", text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}m"
        match = re.search(r"\b(\d+)\s*(seconds|secondes|sec|s)\b", text, re.IGNORECASE)
        if match:
            return f"{match.group(1)}s"
        return ""

    def _extract_aspect_ratio(self, text: str) -> str:
        if not text:
            return ""
        match = re.search(r"\b(\d{1,2})\s*:\s*(\d{1,2})\b", text)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
        if "vertical" in text.lower() or "portrait" in text.lower():
            return "9:16"
        if "square" in text.lower() or "carré" in text.lower():
            return "1:1"
        return ""

    def _apply_if_empty(self, current: Dict[str, Any], field: str, value: str) -> Dict[str, Any]:
        if not value:
            return {}
        existing = current.get(field)
        if isinstance(existing, str) and existing.strip():
            return {}
        if existing not in (None, "", 0):
            return {}
        return {field: value}

    def _has_negative(self, text: str, patterns: List[str]) -> bool:
        lowered = text.lower()
        return any(pattern in lowered for pattern in patterns)

    def _has_positive(self, text: str, patterns: List[str]) -> bool:
        lowered = text.lower()
        return any(pattern in lowered for pattern in patterns)


def _get_str(source_state: Dict[str, Any], path: List[str]) -> str:
    current: Any = source_state
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current.strip() if isinstance(current, str) else ""


def _get_list(source_state: Dict[str, Any], path: List[str]) -> List[str]:
    current: Any = source_state
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if isinstance(current, list):
        return [str(item).strip() for item in current if str(item).strip()]
    return []
