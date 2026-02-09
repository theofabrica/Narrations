"""Helpers to sanitize chat states for narration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.utils.project_storage import read_strata


def sanitize_for_narration(state: Dict[str, Any], project_id: Optional[str] = None) -> Dict[str, Any]:
    """Return the minimal, sufficient state payload for the narrator."""
    if not isinstance(state, dict):
        return {}
    completed_steps = state.get("completed_steps")
    if not (isinstance(completed_steps, list) and "1c" in completed_steps):
        return state

    def _get_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    core = _get_dict(state.get("core"))
    thinker = _get_dict(state.get("thinker"))
    brief = _get_dict(state.get("brief"))

    summary = core.get("summary") or state.get("summary", "")
    video_type = brief.get("video_type") or state.get("video_type", "")
    duration_value = brief.get("target_duration_s", state.get("target_duration_s", 0))
    target_duration_s = _coerce_duration_seconds(duration_value)
    target_path = _resolve_target_path(state, brief)
    actual_text = ""
    if isinstance(state.get("actual_text"), str) and state.get("actual_text", "").strip():
        actual_text = str(state.get("actual_text", "")).strip()
    elif target_path:
        actual_text = _resolve_actual_text(project_id, target_path)

    if target_path and actual_text:
        mode = "edit"
    else:
        mode = "create"

    payload: Dict[str, Any] = {
        "summary": str(summary or "").strip(),
        "video_type": str(video_type or "").strip(),
        "target_duration_s": target_duration_s,
        "mode": mode,
    }
    if target_path:
        payload["target_path"] = target_path
    if mode in {"edit", "propagate"} and target_path:
        payload["actual_text"] = actual_text
        edited_text = state.get("edited_text")
        if isinstance(edited_text, str) and edited_text.strip():
            payload["edited_text"] = edited_text.strip()
        edit_instructions = state.get("edit_instructions")
        if isinstance(edit_instructions, str) and edit_instructions.strip():
            payload["edit_instructions"] = edit_instructions.strip()
    return payload


def _coerce_duration_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit():
            return max(0, int(trimmed))
    return 0


def _resolve_target_path(state: Dict[str, Any], brief: Dict[str, Any]) -> str:
    target_path = state.get("target_path")
    if isinstance(target_path, str) and target_path.strip():
        return target_path.strip()
    paths = brief.get("target_paths")
    if isinstance(paths, list) and paths:
        first = paths[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return ""


def _resolve_actual_text(project_id: Optional[str], target_path: str) -> str:
    if not project_id or not target_path:
        return ""
    parts = target_path.split(".")
    if not parts:
        return ""
    strata = parts[0]
    try:
        strata_state = read_strata(project_id, strata)
    except Exception:
        return ""
    data = strata_state.get("data") if isinstance(strata_state, dict) else {}
    if not isinstance(data, dict):
        return ""
    current: Any = data
    for segment in parts[1:]:
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        else:
            return ""
    if isinstance(current, str):
        return current
    return ""
