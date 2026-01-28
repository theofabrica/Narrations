"""Runner that executes task plans sequentially or in parallel."""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.narration_agent.chat_memory_store import ChatMemoryStore
from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.spec_loader import load_json, load_text
from app.utils.ids import generate_timestamp


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

    def run_task_plan(
        self,
        task_plan: Dict[str, Any],
        project_id: str,
        session_id: str,
        task_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        tasks = task_plan.get("tasks") or []
        results: List[Dict[str, Any]] = []
        outputs: Dict[str, Dict[str, Any]] = {}
        state_snapshot = self._initialize_state()
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
            output_ref = task.get("output_ref") or ""
            if output_ref:
                outputs[output_ref] = {
                    **result,
                    "state_snapshot": state_snapshot,
                }
            results.append(
                {
                    "task_id": task.get("id"),
                    "status": "done",
                    "output_ref": task.get("output_ref"),
                    "error": "",
                    "output": result,
                }
            )
        return {
            "plan_id": task_plan.get("plan_id"),
            "status": "completed",
            "results": results,
            "completed_at": generate_timestamp(),
        }

    def _initialize_state(self) -> Dict[str, Any]:
        template = load_json("chat_agent/state_structure_01_abc.json") or {}
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

    def _build_system_prompt(self, project_empty: bool, empty_strata: Dict[str, bool]) -> str:
        empty_list = [key.upper() for key, is_empty in empty_strata.items() if is_empty]
        empty_summary = ", ".join(empty_list) if empty_list else "none"
        base_prompt = load_text("chat_agent/01a_chat.md").strip()
        runtime_prompt = (
            "Runtime context:\n"
            f"- Project empty: {'yes' if project_empty else 'no'}\n"
            f"- Empty strata: {empty_summary}\n"
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
            "- do not include `thinker`, `brief`, `pending_questions`."
        )
        return f"{base_prompt}\n\n{runtime_prompt}\n{format_prompt}"

    def _build_thinker_prompt(self) -> str:
        base_prompt = load_text("chat_agent/01b_thinker.md").strip()
        if not base_prompt:
            base_prompt = (
                "You are agent 1b (thinker). Reframe the request and extract "
                "objectives, constraints, hypotheses. Stay factual, no invention."
            )
        return base_prompt

    def _build_translator_prompt(self) -> str:
        base_prompt = load_text("chat_agent/01c_orchestrator_translator.md").strip()
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

        session_messages = self.memory_store.load_messages(project_id, session_id)
        session_messages.append({"role": "user", "content": message})

        system_prompt = self._build_system_prompt(project_empty, empty_strata)
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

    def _split_user_and_json(self, content: str) -> tuple[str, str]:
        json_block = self._extract_json_block(content)
        if not json_block:
            return content.strip(), ""
        before, _, _ = content.partition("```json")
        user_text = before.replace("Reponse utilisateur:", "").replace("User response:", "").strip()
        return user_text or content.strip(), json_block

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
        json_block = self._extract_json_block(raw_content)
        return {
            "assistant_message": raw_content,
            "assistant_state_json": json_block or raw_content,
        }

    def _run_chat_1c(
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
