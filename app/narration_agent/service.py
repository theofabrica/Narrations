"""Service layer for narration_agent API integration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.narration_agent.chat.chat_service import get_chat_memory, run_chat_flow
from app.narration_agent.llm_client import LLMClient
from app.narration_agent.narration.narration_service import run_narration_flow
from app.narration_agent.task_runner import TaskRunner
from app.utils.project_storage import STRATA_FILES, create_project, get_project_root, read_strata


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
    if not isinstance(state, dict):
        return True
    data = state.get("data")
    if not isinstance(data, dict):
        return True
    production_summary = data.get("production_summary", {})
    if not isinstance(production_summary, dict):
        return True
    summary = production_summary.get("summary", "")
    # A project is considered empty only if N0 summary is blank.
    if isinstance(summary, str):
        return not summary.strip()
    return not _has_meaningful_value(summary)


def handle_chat_message(
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

    project_empty = empty_strata.get("n0", True)
    creation_mode = project_empty
    llm_client = LLMClient()
    memory_store = get_chat_memory()
    runner = TaskRunner(llm_client=llm_client, memory_store=memory_store)
    chat_result = run_chat_flow(
        project_id=project_id,
        message=message,
        session_id=session_id,
        project_empty=project_empty,
        empty_strata=empty_strata,
        llm_client=llm_client,
        runner=runner,
    )
    narration_result = run_narration_flow(
        project_id=project_id,
        session_id=chat_result["session_id"],
        final_state_snapshot=chat_result.get("final_state_snapshot"),
        creation_mode=creation_mode,
        pending_rounds=chat_result["pending_rounds"],
        trigger=chat_result["chat_trigger"],
        runner=runner,
    )
    has_pending_questions = (
        narration_result.get("has_pending_questions", False)
        if isinstance(chat_result.get("final_state_snapshot"), dict)
        and chat_result["pending_rounds"] < 2
        else False
    )

    return {
        "project_id": project_id,
        "session_id": chat_result["session_id"],
        "message_echo": message,
        "project_empty": project_empty,
        "creation_mode": creation_mode,
        "empty_strata": empty_strata,
        "next_action": chat_result["next_action"],
        "assistant_message": chat_result["assistant_message"],
        "assistant_state_json": chat_result["assistant_state_json"],
        "chat_trigger": chat_result["chat_trigger"],
        "narration_input": narration_result.get("narration_input"),
        "narration_task_plan": narration_result.get("narration_task_plan"),
        "narration_runner_input": narration_result.get("narration_runner_input"),
        "narration_task_context": narration_result.get("narration_task_context"),
        "narration_run_result": narration_result.get("narration_run_result"),
        "task_plan": chat_result["task_plan"],
        "has_pending_questions": has_pending_questions,
        "pending_rounds": chat_result["pending_rounds"],
    }


def handle_narration_message(
    project_id: str,
    message: str,
    session_id: Optional[str] = None,
    auto_create: bool = True,
) -> Dict[str, Any]:
    """Backward-compatible alias for handle_chat_message."""
    return handle_chat_message(
        project_id=project_id,
        message=message,
        session_id=session_id,
        auto_create=auto_create,
    )
