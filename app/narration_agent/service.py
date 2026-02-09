"""Service layer for narration_agent API integration."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from app.narration_agent.chat.chat_service import get_chat_memory, run_chat_flow
from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.narration.narration_service import run_narration_flow
from app.narration_agent.spec_loader import load_text
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


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_state_empty(state: Dict[str, Any]) -> bool:
    if not isinstance(state, dict):
        return True
    data = state.get("data")
    if not isinstance(data, dict):
        return True
    production_summary = data.get("production_summary", {})
    art_direction = data.get("art_direction", {})
    sound_direction = data.get("sound_direction", {})
    if any(
        isinstance(section, dict)
        for section in (production_summary, art_direction, sound_direction)
    ):
        summary = production_summary.get("summary", "") if isinstance(production_summary, dict) else ""
        art_description = (
            art_direction.get("description", "") if isinstance(art_direction, dict) else ""
        )
        sound_description = (
            sound_direction.get("description", "") if isinstance(sound_direction, dict) else ""
        )
        return not (
            _has_text(summary)
            and _has_text(art_description)
            and _has_text(sound_description)
        )
    return not _has_meaningful_value(data)


def handle_chat_message(
    project_id: str,
    message: str,
    session_id: Optional[str] = None,
    auto_create: bool = True,
    mode: Optional[str] = None,
    target_path: Optional[str] = None,
    actual_text: Optional[str] = None,
    edited_text: Optional[str] = None,
    edit_session_id: Optional[str] = None,
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
    final_snapshot = chat_result.get("final_state_snapshot")
    mode_value = mode.strip().lower() if isinstance(mode, str) else ""
    edit_summary = ""
    resolved_edit_session_id = ""
    if isinstance(final_snapshot, dict) and isinstance(target_path, str) and target_path.strip():
        enriched_snapshot = {**final_snapshot, "target_path": target_path.strip()}
        if isinstance(actual_text, str) and actual_text.strip():
            enriched_snapshot["actual_text"] = actual_text
        if isinstance(edited_text, str) and edited_text.strip():
            enriched_snapshot["edited_text"] = edited_text
        if mode_value in {"edit", "propagate", "create"}:
            enriched_snapshot["mode"] = mode_value
        if mode_value == "edit":
            resolved_edit_session_id = edit_session_id or f"edit_{uuid.uuid4().hex}"
            prior_messages = memory_store.load_edit_messages(project_id, resolved_edit_session_id)
            prior_messages.append({"role": "user", "content": message})
            assistant_message = chat_result.get("assistant_message") or ""
            if isinstance(assistant_message, str) and assistant_message.strip():
                prior_messages.append(
                    {"role": "assistant", "content": assistant_message.strip()}
                )
            edit_summary = _summarize_edit_chat(
                llm_client=llm_client,
                messages=prior_messages[-12:],
                target_path=target_path.strip(),
                actual_text=actual_text or "",
                edited_text=edited_text or "",
            )
            memory_store.save_edit_messages(
                project_id,
                resolved_edit_session_id,
                prior_messages,
                meta={
                    "target_path": target_path.strip(),
                    "edit_summary": edit_summary,
                },
            )
            if edit_summary:
                enriched_snapshot["edit_instructions"] = edit_summary
        chat_result["final_state_snapshot"] = enriched_snapshot
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
        and chat_result["pending_rounds"] < 1
        else False
    )

    return {
        "project_id": project_id,
        "session_id": chat_result["session_id"],
        "edit_session_id": resolved_edit_session_id,
        "edit_summary": edit_summary,
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
    mode: Optional[str] = None,
    target_path: Optional[str] = None,
    actual_text: Optional[str] = None,
    edited_text: Optional[str] = None,
    edit_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Backward-compatible alias for handle_chat_message."""
    return handle_chat_message(
        project_id=project_id,
        message=message,
        session_id=session_id,
        auto_create=auto_create,
        mode=mode,
        target_path=target_path,
        actual_text=actual_text,
        edited_text=edited_text,
        edit_session_id=edit_session_id,
    )


def _summarize_edit_chat(
    *,
    llm_client: LLMClient,
    messages: List[Dict[str, str]],
    target_path: str,
    actual_text: str,
    edited_text: str,
) -> str:
    prompt = load_text("chat/01c_orchestrator_translator.md").strip()
    if not prompt:
        prompt = (
            "You are agent 1c. Summarize the edit chat into precise edit instructions.\n"
            "Return ONLY valid JSON: {\"edit_summary\": \"...\"}"
        )
    payload = {
        "edit_summary_mode": True,
        "target_path": target_path,
        "actual_text": actual_text,
        "edited_text": edited_text,
        "messages": messages,
    }
    llm_response = llm_client.complete(
        LLMRequest(
            model=llm_client.default_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True, indent=2)},
            ],
            temperature=0.2,
        )
    )
    raw_content = llm_response.content.strip()
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw_content[start : end + 1])
            except json.JSONDecodeError:
                return ""
        else:
            return ""
    if isinstance(parsed, dict):
        summary = parsed.get("edit_summary", "")
        return summary.strip() if isinstance(summary, str) else ""
    return ""
