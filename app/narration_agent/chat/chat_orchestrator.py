"""Chat orchestrator (layer 0) for chat agent planning."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict

from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.spec_loader import load_text
from app.utils.ids import generate_timestamp


@dataclass
class ChatOrchestratorResult:
    task_plan: Dict[str, Any]
    task_context: Dict[str, Any]
    next_action: str


class ChatOrchestrator:
    """Build chat task plans (1a/1b/1c)."""

    def __init__(self) -> None:
        self.base_prompt = load_text("chat/00_chat_orchestrator.md").strip()

    def build_task_plan(
        self,
        source_state_id: str,
        message: str,
        project_empty: bool,
        empty_strata: Dict[str, bool],
        pending_questions: list[str] | None = None,
        pending_rounds: int = 0,
        include_1c: bool = True,
        chat_mode: str = "auto",
    ) -> ChatOrchestratorResult:
        if not isinstance(pending_questions, list):
            pending_questions = []
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        task_id_1a = "task_chat_1a"
        task_id_1b = "task_chat_1b"
        task_id_1c = "task_chat_1c"
        task_1a = {
            "id": task_id_1a,
            "agent": "chat_1a",
            "input_ref": "chat_memory",
            "output_ref": "chat_1a_output",
            "depends_on": [],
        }
        task_1b = {
            "id": task_id_1b,
            "agent": "chat_1b",
            "input_ref": "chat_1a_output",
            "output_ref": "chat_1b_output",
            "depends_on": [task_id_1a],
        }
        task_plan = {
            "plan_id": plan_id,
            "created_at": generate_timestamp(),
            "source_state_id": source_state_id,
            "tasks": [task_1a, task_1b],
        }
        if include_1c:
            task_1c = {
                "id": task_id_1c,
                "agent": "chat_1c",
                "input_ref": "chat_1b_output",
                "output_ref": "chat_1c_output",
                "depends_on": [task_id_1b],
            }
            task_plan["tasks"].append(task_1c)
        task_context = {
            task_id_1a: {
                "message": message,
                "project_empty": project_empty,
                "empty_strata": empty_strata,
                "pending_questions": pending_questions,
                "pending_rounds": pending_rounds,
                "chat_mode": chat_mode,
            },
            task_id_1b: {},
        }
        if include_1c:
            task_context[task_id_1c] = {}
        next_action = "chat_clarification" if project_empty else "edit_mode"
        return ChatOrchestratorResult(
            task_plan=task_plan,
            task_context=task_context,
            next_action=next_action,
        )

    def build_task_plan_llm(
        self,
        llm_client: LLMClient,
        input_payload: Dict[str, Any],
        fallback: ChatOrchestratorResult,
    ) -> tuple[ChatOrchestratorResult, Dict[str, Any]]:
        prompt = self.base_prompt or "You are the chat orchestrator."
        format_prompt = (
            "Return ONLY valid JSON with this structure:\n"
            "{\n"
            '  "tasks": [ {"agent": "chat_1a"}, {"agent": "chat_1b"}, {"agent": "chat_1c"} ],\n'
            '  "next_action": "chat_clarification" | "edit_mode"\n'
            "}\n"
            "Rules:\n"
            "- Allowed agents: chat_1a, chat_1b, chat_1c\n"
            "- Include chat_1a and chat_1b at minimum.\n"
            "- Include chat_1c only if the context is ready for orchestration.\n"
            "- Do NOT add any extra keys.\n"
        )
        llm_response = llm_client.complete(
            LLMRequest(
                model=llm_client.default_model,
                messages=[
                    {"role": "system", "content": f"{prompt}\n\n{format_prompt}"},
                    {
                        "role": "user",
                        "content": json.dumps(input_payload, ensure_ascii=True, indent=2),
                    },
                ],
                temperature=0.2,
            )
        )
        raw_content = llm_response.content.strip()
        parsed = self._parse_json_payload(raw_content)
        if not parsed:
            return fallback, {"raw_output": raw_content, "used_llm": False, "reason": "invalid_json"}
        raw_tasks = parsed.get("tasks")
        if not isinstance(raw_tasks, list) or not raw_tasks:
            return fallback, {"raw_output": raw_content, "used_llm": False, "reason": "missing_tasks"}
        agents = []
        for entry in raw_tasks:
            agent = entry.get("agent") if isinstance(entry, dict) else entry
            if not isinstance(agent, str):
                continue
            agent = agent.strip()
            if agent and agent not in agents:
                agents.append(agent)
        normalized = self._normalize_chat_agents(agents)
        if not normalized:
            return fallback, {"raw_output": raw_content, "used_llm": False, "reason": "invalid_agents"}
        task_plan = self._build_chat_task_plan(
            source_state_id=fallback.task_plan.get("source_state_id", ""),
            agents=normalized,
        )
        task_context = self._build_chat_task_context(
            fallback=fallback,
            agents=normalized,
        )
        next_action = parsed.get("next_action") or fallback.next_action
        return ChatOrchestratorResult(
            task_plan=task_plan,
            task_context=task_context,
            next_action=next_action,
        ), {"raw_output": raw_content, "used_llm": True, "reason": "ok"}

    def _parse_json_payload(self, payload: str) -> Dict[str, Any]:
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            trimmed = payload.strip()
            start = trimmed.find("{")
            end = trimmed.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(trimmed[start : end + 1])
                    return parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    return {}
        return {}

    def _normalize_chat_agents(self, agents: list[str]) -> list[str]:
        allowed = {"chat_1a", "chat_1b", "chat_1c"}
        filtered = [agent for agent in agents if agent in allowed]
        if "chat_1a" not in filtered:
            filtered.insert(0, "chat_1a")
        if "chat_1b" not in filtered:
            filtered.insert(1, "chat_1b")
        order = ["chat_1a", "chat_1b", "chat_1c"]
        ordered = [agent for agent in order if agent in filtered]
        return ordered

    def _build_chat_task_plan(self, source_state_id: str, agents: list[str]) -> Dict[str, Any]:
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        tasks = []
        last_task_id = ""
        for agent in agents:
            task_id = f"task_{agent}"
            input_ref = "chat_memory"
            output_ref = f"{agent}_output"
            if agent == "chat_1b":
                input_ref = "chat_1a_output"
            elif agent == "chat_1c":
                input_ref = "chat_1b_output"
            task = {
                "id": task_id,
                "agent": agent,
                "input_ref": input_ref,
                "output_ref": output_ref,
                "depends_on": [last_task_id] if last_task_id else [],
            }
            tasks.append(task)
            last_task_id = task_id
        return {
            "plan_id": plan_id,
            "created_at": generate_timestamp(),
            "source_state_id": source_state_id,
            "tasks": tasks,
        }

    def _build_chat_task_context(
        self,
        fallback: ChatOrchestratorResult,
        agents: list[str],
    ) -> Dict[str, Any]:
        task_context: Dict[str, Any] = {}
        for agent in agents:
            task_id = f"task_{agent}"
            if agent == "chat_1a":
                task_context[task_id] = fallback.task_context.get("task_chat_1a", {})
            else:
                task_context[task_id] = {}
        return task_context

    def build_chat_1c_task_plan(self, source_state_id: str) -> Dict[str, Any]:
        task_id = "task_chat_1c"
        task_plan = {
            "plan_id": f"plan_{uuid.uuid4().hex[:12]}",
            "created_at": generate_timestamp(),
            "source_state_id": source_state_id,
            "tasks": [
                {
                    "id": task_id,
                    "agent": "chat_1c",
                    "input_ref": "chat_1b_output",
                    "output_ref": "chat_1c_output",
                    "depends_on": [],
                }
            ],
        }
        return {
            "task_plan": task_plan,
            "runner_input": {
                "plan_id": task_plan.get("plan_id", ""),
                "task_plan_ref": "",
                "task_plan_payload": task_plan,
                "execution_mode": "sequential",
                "started_at": generate_timestamp(),
            },
            "task_context": {
                task_id: {},
            },
        }
