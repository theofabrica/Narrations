"""Service layer for narration_agent API integration."""

from __future__ import annotations

import json
import threading
import uuid
from typing import Any, Dict, Optional

from app.narration_agent.chat_memory_store import ChatMemoryStore
from app.narration_agent.llm_client import LLMClient
from app.narration_agent.super_orchestrator import SuperOrchestrator
from app.narration_agent.task_runner import TaskRunner
from app.utils.ids import generate_timestamp
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


def _has_pending_questions(state: Dict[str, Any]) -> bool:
    pending = state.get("pending_questions") if isinstance(state, dict) else None
    return isinstance(pending, list) and len(pending) > 0


def _write_plan_log(
    project_id: str,
    session_id: str,
    label: str,
    payload: Dict[str, Any],
) -> None:
    def _worker() -> None:
        try:
            root = get_project_root(project_id)
            log_dir = root / "orchestrator_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            safe_label = "".join(c for c in label if c.isalnum() or c in ("-", "_")).strip()
            safe_label = safe_label or "plan"
            filename = f"{generate_timestamp()}_{safe_label}.json"
            content = {
                "project_id": project_id,
                "session_id": session_id,
                "label": label,
                "logged_at": generate_timestamp(),
                **payload,
            }
            (log_dir / filename).write_text(
                json.dumps(content, indent=2, ensure_ascii=True), encoding="utf-8"
            )
        except Exception:
            return

    threading.Thread(target=_worker, daemon=True).start()


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

    project_empty = empty_strata.get("n0", True)
    creation_mode = project_empty
    resolved_session_id = session_id or f"sess_{uuid.uuid4().hex}"
    next_action = "chat_clarification" if project_empty else "edit_mode"
    prior_snapshot = (
        _CHAT_MEMORY.load_state_snapshot(project_id, resolved_session_id)
        if resolved_session_id
        else {}
    )
    pending_questions = (
        prior_snapshot.get("pending_questions", [])
        if isinstance(prior_snapshot, dict)
        else []
    )
    if not isinstance(pending_questions, list):
        pending_questions = []
    meta = _CHAT_MEMORY.load_meta(project_id, resolved_session_id)
    pending_rounds = meta.get("pending_rounds", 0) if isinstance(meta, dict) else 0
    if not isinstance(pending_rounds, int):
        pending_rounds = 0
    last_trigger = meta.get("last_trigger", "auto") if isinstance(meta, dict) else "auto"
    if message.strip() and pending_questions:
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
    orchestrator = SuperOrchestrator()
    result = orchestrator.build_task_plan(
        source_state_id=resolved_session_id,
        message=message,
        project_empty=project_empty,
        empty_strata=empty_strata,
        pending_questions=pending_questions,
        pending_rounds=pending_rounds,
        include_1c=False,
        chat_mode=last_trigger,
    )
    llm_client = LLMClient()
    llm_result, llm_meta = orchestrator.build_task_plan_llm(
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
    _write_plan_log(
        project_id=project_id,
        session_id=resolved_session_id,
        label="super_orchestrator_llm",
        payload={
            "used_llm": llm_meta.get("used_llm"),
            "reason": llm_meta.get("reason"),
            "raw_output": llm_meta.get("raw_output", "")[:8000],
        },
    )
    result = llm_result
    _write_plan_log(
        project_id=project_id,
        session_id=resolved_session_id,
        label="chat_plan",
        payload={
            "task_plan": result.task_plan,
            "task_context": result.task_context,
            "next_action": result.next_action,
        },
    )
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
        chat_1c_bundle = orchestrator.build_chat_1c_task_plan(
            source_state_id=resolved_session_id
        )
        chat_1c_task_plan = chat_1c_bundle.get("task_plan") or {}
        chat_1c_context = chat_1c_bundle.get("task_context") or {}
        input_payload = ""
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

    narration_input = None
    narration_task_plan = None
    narration_runner_input = None
    narration_task_context = None
    narration_run_result = None
    if isinstance(final_state_snapshot, dict) and trigger in {"build_brief", "use_memory"}:
        has_pending_questions = _has_pending_questions(final_state_snapshot)
        allow_narration = not has_pending_questions or pending_rounds >= 2
        brief = final_state_snapshot.get("brief") if isinstance(final_state_snapshot, dict) else {}
        target_strata = (
            brief.get("target_strata") if isinstance(brief, dict) else None
        )
        target_paths = (
            brief.get("target_paths") if isinstance(brief, dict) else None
        )
        if not isinstance(target_strata, list):
            target_strata = []
        if not isinstance(target_paths, list):
            target_paths = []
        if creation_mode:
            target_strata = ["n0"]
            target_paths = []
        if allow_narration:
            narration_input = {
                "narration_id": resolved_session_id,
                "source_state_ref": "",
                "source_state_payload": final_state_snapshot,
                "target_strata": target_strata,
                "target_paths": target_paths,
                "storage_root": str(get_project_root(project_id)),
                "config": {"create_if_missing": True},
            }
            narration_bundle = SuperOrchestrator().build_narration_task_plan(narration_input)
            narration_task_plan = narration_bundle.get("task_plan")
            narration_runner_input = narration_bundle.get("runner_input")
            narration_task_context = narration_bundle.get("task_context")
            _write_plan_log(
                project_id=project_id,
                session_id=resolved_session_id,
                label="narration_plan",
                payload={
                    "task_plan": narration_task_plan,
                    "task_context": narration_task_context,
                    "runner_input": narration_runner_input,
                },
            )
            if narration_task_plan:
                narration_run_result = runner.run_task_plan(
                    task_plan=narration_task_plan,
                    project_id=project_id,
                    session_id=resolved_session_id,
                    task_context=narration_task_context or {},
                )

    return {
        "project_id": project_id,
        "session_id": resolved_session_id,
        "message_echo": message,
        "project_empty": project_empty,
        "creation_mode": creation_mode,
        "empty_strata": empty_strata,
        "next_action": result.next_action,
        "assistant_message": assistant_message,
        "assistant_state_json": assistant_state_json,
        "chat_trigger": trigger,
        "narration_input": narration_input,
        "narration_task_plan": narration_task_plan,
        "narration_runner_input": narration_runner_input,
        "narration_task_context": narration_task_context,
        "narration_run_result": narration_run_result,
        "task_plan": result.task_plan,
        "has_pending_questions": (
            _has_pending_questions(final_state_snapshot)
            if isinstance(final_state_snapshot, dict) and pending_rounds < 2
            else False
        ),
        "pending_rounds": pending_rounds,
    }
