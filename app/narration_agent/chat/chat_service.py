"""Chat flow orchestration for narration_agent."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from app.narration_agent.chat.chat_memory_store import ChatMemoryStore
from app.narration_agent.chat.state_sanitizer import sanitize_for_narration
from app.narration_agent.chat.chat_orchestrator import ChatOrchestrator
from app.narration_agent.llm_client import LLMClient
from app.narration_agent.logging_utils import write_plan_log
from app.narration_agent.task_runner import TaskRunner

_CHAT_MEMORY = ChatMemoryStore()


def get_chat_memory() -> ChatMemoryStore:
    return _CHAT_MEMORY


def run_chat_flow(
    project_id: str,
    message: str,
    session_id: Optional[str],
    project_empty: bool,
    empty_strata: Dict[str, bool],
    llm_client: LLMClient,
    runner: TaskRunner,
) -> Dict[str, Any]:
    resolved_session_id = session_id or f"sess_{uuid.uuid4().hex}"
    prior_snapshot = (
        _CHAT_MEMORY.load_state_snapshot(project_id, resolved_session_id)
        if resolved_session_id
        else {}
    )
    pending_questions = (
        prior_snapshot.get("pending_questions", []) if isinstance(prior_snapshot, dict) else []
    )
    if not isinstance(pending_questions, list):
        pending_questions = []
    core_open_questions = []
    core_missing = []
    thinker_missing = []
    thinker_clarifications = []
    if isinstance(prior_snapshot, dict):
        core = prior_snapshot.get("core")
        if isinstance(core, dict):
            core_open_questions = core.get("open_questions") or []
        core_missing = prior_snapshot.get("missing") or []
        thinker = prior_snapshot.get("thinker")
        if isinstance(thinker, dict):
            thinker_missing = thinker.get("missing") or []
            thinker_clarifications = thinker.get("clarifications") or []
    if not isinstance(core_open_questions, list):
        core_open_questions = []
    if not isinstance(core_missing, list):
        core_missing = []
    if not isinstance(thinker_missing, list):
        thinker_missing = []
    if not isinstance(thinker_clarifications, list):
        thinker_clarifications = []
    meta = _CHAT_MEMORY.load_meta(project_id, resolved_session_id)
    pending_rounds = meta.get("pending_rounds", 0) if isinstance(meta, dict) else 0
    if not isinstance(pending_rounds, int):
        pending_rounds = 0
    last_trigger = meta.get("last_trigger", "auto") if isinstance(meta, dict) else "auto"
    awaiting_questions = any(
        [
            pending_questions,
            core_open_questions,
            core_missing,
            thinker_missing,
            thinker_clarifications,
        ]
    )
    if message.strip() and awaiting_questions:
        pending_rounds += 1
    _CHAT_MEMORY.save_meta(
        project_id,
        resolved_session_id,
        {
            **(meta if isinstance(meta, dict) else {}),
            "pending_rounds": pending_rounds,
            "last_trigger": last_trigger,
        },
    )

    chat_orchestrator = ChatOrchestrator()
    result = chat_orchestrator.build_task_plan(
        source_state_id=resolved_session_id,
        message=message,
        project_empty=project_empty,
        empty_strata=empty_strata,
        pending_questions=pending_questions,
        pending_rounds=pending_rounds,
        include_1c=False,
        chat_mode=last_trigger,
    )
    llm_result, llm_meta = chat_orchestrator.build_task_plan_llm(
        llm_client=llm_client,
        input_payload={
            "session_id": resolved_session_id,
            "user_message": message,
            "conversation_history": _CHAT_MEMORY.load_messages(project_id, resolved_session_id),
            "state_ref": "",
            "state_payload": prior_snapshot,
            "config": {
                "missing_sensitivity": 0.5,
                "writer_enabled": True,
                "max_loops": 3,
            },
            "project_empty": project_empty,
            "empty_strata": empty_strata,
            "pending_questions": pending_questions,
            "pending_rounds": pending_rounds,
        },
        fallback=result,
    )
    write_plan_log(
        project_id=project_id,
        session_id=resolved_session_id,
        label="chat_orchestrator_llm",
        payload={
            "used_llm": llm_meta.get("used_llm"),
            "reason": llm_meta.get("reason"),
            "raw_output": llm_meta.get("raw_output", "")[:8000],
        },
    )
    result = llm_result
    write_plan_log(
        project_id=project_id,
        session_id=resolved_session_id,
        label="chat_plan",
        payload={
            "task_plan": result.task_plan,
            "task_context": result.task_context,
            "next_action": result.next_action,
        },
    )

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
    final_state_snapshot: Optional[Dict[str, Any]] = None
    trigger = ""
    last_snapshot: Optional[Dict[str, Any]] = None
    chat_1b_output: Optional[Dict[str, Any]] = None
    has_chat_1c_task = False

    for task in run_result.get("results", []):
        output = task.get("output") or {}
        task_agent = task_agent_map.get(task.get("task_id"))
        if output.get("state_snapshot"):
            last_snapshot = output.get("state_snapshot")
        if task_agent == "chat_1c":
            has_chat_1c_task = True
            if output.get("assistant_state_json"):
                assistant_state_json = output["assistant_state_json"]
            if output.get("state_snapshot"):
                final_state_snapshot = output.get("state_snapshot")
        if task_agent == "chat_1a" and output.get("assistant_message"):
            assistant_message = output["assistant_message"]
        if task_agent == "chat_1b":
            chat_1b_output = output
            trigger = output.get("trigger", "") or trigger

    if not assistant_message:
        for task in run_result.get("results", []):
            output = task.get("output") or {}
            if output.get("assistant_message"):
                assistant_message = output["assistant_message"]
                break

    if not trigger:
        trigger = "build_brief"
    if project_empty and pending_rounds >= 1:
        trigger = "build_brief"
    _CHAT_MEMORY.save_meta(
        project_id,
        resolved_session_id,
        {
            **(meta if isinstance(meta, dict) else {}),
            "pending_rounds": pending_rounds,
            "last_trigger": trigger,
        },
    )

    if not has_chat_1c_task and trigger in {"build_brief", "use_memory"}:
        chat_1c_bundle = chat_orchestrator.build_chat_1c_task_plan(
            source_state_id=resolved_session_id
        )
        chat_1c_task_plan = chat_1c_bundle.get("task_plan") or {}
        chat_1c_context = chat_1c_bundle.get("task_context") or {}
        input_payload: Any = ""
        if trigger == "use_memory":
            input_payload = prior_snapshot or last_snapshot or {}
        elif chat_1b_output:
            input_payload = (
                chat_1b_output.get("assistant_state_json")
                or chat_1b_output.get("assistant_message")
                or ""
            )
        for task_id in chat_1c_context.keys():
            chat_1c_context[task_id]["input_payload"] = input_payload
        chat_1c_result = runner.run_task_plan(
            task_plan=chat_1c_task_plan,
            project_id=project_id,
            session_id=resolved_session_id,
            task_context=chat_1c_context,
            initial_state_snapshot=last_snapshot,
        )
        for task in chat_1c_result.get("results", []):
            output = task.get("output") or {}
            if output.get("assistant_state_json"):
                assistant_state_json = output["assistant_state_json"]
            if output.get("state_snapshot"):
                final_state_snapshot = output.get("state_snapshot")
    else:
        final_state_snapshot = last_snapshot

    if isinstance(final_state_snapshot, dict):
        _CHAT_MEMORY.save_state_snapshot(
            project_id=project_id,
            session_id=resolved_session_id,
            state_snapshot=final_state_snapshot,
        )
        _CHAT_MEMORY.save_output_state_snapshot(
            project_id=project_id,
            session_id=resolved_session_id,
            state_snapshot=sanitize_for_narration(final_state_snapshot, project_id=project_id),
        )

    return {
        "session_id": resolved_session_id,
        "assistant_message": assistant_message,
        "assistant_state_json": assistant_state_json,
        "chat_trigger": trigger,
        "final_state_snapshot": final_state_snapshot,
        "pending_rounds": pending_rounds,
        "next_action": result.next_action,
        "task_plan": result.task_plan,
    }
