"""Service layer for narration_agent API integration."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from app.narration_agent.chat_memory_store import ChatMemoryStore
from app.narration_agent.llm_client import LLMClient
from app.narration_agent.super_orchestrator import SuperOrchestrator
from app.narration_agent.task_runner import TaskRunner
from app.utils.project_storage import STRATA_FILES, create_project, get_project_root, read_strata

_CHAT_MEMORY = ChatMemoryStore()


def _has_meaningful_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, list):
        return any(_has_meaningful_value(item) for item in value)
    if isinstance(value, dict):
        return any(_has_meaningful_value(item) for item in value.values())
    return True


def _is_state_empty(state: Dict[str, Any]) -> bool:
    data = state.get("data") if isinstance(state, dict) else None
    if data is None:
        return True
    return not _has_meaningful_value(data)


def handle_narration_message(
    project_id: str,
    message: str,
    session_id: Optional[str] = None,
    auto_create: bool = True,
) -> Dict[str, Any]:
    if not project_id:
        raise ValueError("project_id is required")
    if not message or not message.strip():
        raise ValueError("message is required")

    project_root = get_project_root(project_id)
    if not project_root.exists():
        if auto_create:
            create_project(project_id)
        else:
            raise FileNotFoundError(str(project_root))

    empty_strata: Dict[str, bool] = {}
    for strata in STRATA_FILES:
        try:
            state = read_strata(project_id, strata)
        except FileNotFoundError:
            state = {}
        empty_strata[strata] = _is_state_empty(state)

    project_empty = all(empty_strata.values())
    resolved_session_id = session_id or f"sess_{uuid.uuid4().hex}"
    next_action = "chat_clarification" if project_empty else "edit_mode"
    orchestrator = SuperOrchestrator()
    result = orchestrator.build_task_plan(
        source_state_id=resolved_session_id,
        message=message,
        project_empty=project_empty,
        empty_strata=empty_strata,
    )
    llm_client = LLMClient()
    runner = TaskRunner(llm_client=llm_client, memory_store=_CHAT_MEMORY)
    run_result = runner.run_task_plan(
        task_plan=result.task_plan,
        project_id=project_id,
        session_id=resolved_session_id,
        task_context=result.task_context,
    )
    task_agent_map = {
        task.get("id"): task.get("agent") for task in result.task_plan.get("tasks", [])
    }
    assistant_message = ""
    assistant_state_json = ""
    for task in run_result.get("results", []):
        output = task.get("output") or {}
        task_agent = task_agent_map.get(task.get("task_id"))
        if task_agent == "chat_1a" and output.get("assistant_message"):
            assistant_message = output["assistant_message"]
        if task_agent == "chat_1c" and output.get("assistant_state_json"):
            assistant_state_json = output["assistant_state_json"]

    if not assistant_message:
        for task in run_result.get("results", []):
            output = task.get("output") or {}
            if output.get("assistant_message"):
                assistant_message = output["assistant_message"]
                break

    return {
        "project_id": project_id,
        "session_id": resolved_session_id,
        "message_echo": message,
        "project_empty": project_empty,
        "empty_strata": empty_strata,
        "next_action": result.next_action,
        "assistant_message": assistant_message,
        "assistant_state_json": assistant_state_json,
        "task_plan": result.task_plan,
    }
