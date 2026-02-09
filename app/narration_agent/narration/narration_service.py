"""Narration flow orchestration for narration_agent."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import re

from app.narration_agent.chat.state_sanitizer import sanitize_for_narration
from app.narration_agent.logging_utils import write_plan_log
from app.narration_agent.narration.narrator_orchestrator import NarratorOrchestrator
from app.narration_agent.task_runner import TaskRunner
from app.utils.ids import generate_timestamp
from app.utils.project_storage import get_project_root, read_strata, write_strata


def has_pending_questions(state: Dict[str, Any]) -> bool:
    pending = state.get("pending_questions") if isinstance(state, dict) else None
    return isinstance(pending, list) and len(pending) > 0


def _sanitize_chat_state_for_narration(
    state: Dict[str, Any], project_id: str
) -> Dict[str, Any]:
    """Ensure the state passed to the narrator contains no pending/missing questions.

    In this app's logic, once 1c has completed, `pending_questions` and `missing`
    must be resolved (thus empty) and are not needed by the narrator.
    We also drop `core.open_questions`, which should be resolved before narration.
    We remove these keys entirely for the payload handed to the narrator.
    """
    return sanitize_for_narration(state, project_id=project_id)


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _get_n0_missing_paths(project_id: str) -> List[str]:
    try:
        state = read_strata(project_id, "n0")
    except FileNotFoundError:
        state = {}
    data = state.get("data") if isinstance(state, dict) else {}
    if not isinstance(data, dict):
        data = {}
    production_summary = data.get("production_summary", {})
    art_direction = data.get("art_direction", {})
    sound_direction = data.get("sound_direction", {})
    summary = production_summary.get("summary", "") if isinstance(production_summary, dict) else ""
    art_description = (
        art_direction.get("description", "") if isinstance(art_direction, dict) else ""
    )
    sound_description = (
        sound_direction.get("description", "") if isinstance(sound_direction, dict) else ""
    )
    missing = []
    if not _has_text(summary):
        missing.append("n0.production_summary")
    if not _has_text(art_description):
        missing.append("n0.art_direction")
    if not _has_text(sound_description):
        missing.append("n0.sound_direction")
    return missing


def _parse_duration_to_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str):
        return 0
    trimmed = value.strip().lower()
    if not trimmed:
        return 0
    if trimmed.isdigit():
        return max(0, int(trimmed))
    hours = re.search(r"(\d+)\s*h", trimmed)
    minutes = re.search(r"(\d+)\s*m", trimmed)
    seconds = re.search(r"(\d+)\s*s", trimmed)
    total = 0
    if hours:
        total += int(hours.group(1)) * 3600
    if minutes:
        total += int(minutes.group(1)) * 60
    if seconds:
        total += int(seconds.group(1))
    return total


def run_n1_flow(
    project_id: str,
    session_id: str,
    runner: TaskRunner,
) -> Dict[str, Any]:
    narration_input = {
        "narration_id": session_id,
        "source_state_ref": "",
        "source_state_payload": {
            "state_id": session_id,
            "mode": "create",
        },
        "target_strata": ["n1"],
        "target_paths": [],
        "storage_root": str(get_project_root(project_id)),
        "config": {"create_if_missing": True},
    }
    narrator = NarratorOrchestrator()
    narration_task_plan = narrator.build_plan(narration_input)
    narration_task_context: Dict[str, Any] = {}
    for task in narration_task_plan.get("tasks", []):
        task_id = task.get("id")
        if not task_id:
            continue
        base_context = {
            "source_state_payload": narration_input.get("source_state_payload") or {},
            "target_path": task.get("output_ref", ""),
        }
        narration_task_context[task_id] = {
            **base_context,
        }
    narration_runner_input = {
        "plan_id": narration_task_plan.get("plan_id", ""),
        "task_plan_ref": "",
        "task_plan_payload": narration_task_plan,
        "execution_mode": "sequential",
        "started_at": generate_timestamp(),
    }
    write_plan_log(
        project_id=project_id,
        session_id=session_id,
        label="narration_plan_n1_ui",
        payload={
            "task_plan": narration_task_plan,
            "task_context": narration_task_context,
            "runner_input": narration_runner_input,
        },
    )
    narration_run_result = runner.run_task_plan(
        task_plan=narration_task_plan,
        project_id=project_id,
        session_id=session_id,
        task_context=narration_task_context or {},
    )
    return {
        "narration_input": narration_input,
        "narration_task_plan": narration_task_plan,
        "narration_runner_input": narration_runner_input,
        "narration_task_context": narration_task_context,
        "narration_run_result": narration_run_result,
    }


def run_narration_flow(
    project_id: str,
    session_id: str,
    final_state_snapshot: Optional[Dict[str, Any]],
    creation_mode: bool,
    pending_rounds: int,
    trigger: str,
    runner: TaskRunner,
) -> Dict[str, Any]:
    narration_input = None
    narration_task_plan = None
    narration_runner_input = None
    narration_task_context = None
    narration_run_result = None
    pending_questions = False

    if isinstance(final_state_snapshot, dict) and trigger in {"build_brief", "use_memory"}:
        # Sanitize the payload passed to the narrator: after 1c, these keys must not be used.
        if isinstance(final_state_snapshot.get("completed_steps"), list) and "1c" in final_state_snapshot.get(
            "completed_steps", []
        ):
            pending = final_state_snapshot.get("pending_questions")
            missing = final_state_snapshot.get("missing")
            pending_count = len(pending) if isinstance(pending, list) else 0
            missing_count = len(missing) if isinstance(missing, list) else 0
            if pending_count or missing_count:
                write_plan_log(
                    project_id=project_id,
                    session_id=session_id,
                    label="chat_state_invariant_violation",
                    payload={
                        "pending_questions_count": pending_count,
                        "missing_count": missing_count,
                        "note": "1c completed but pending_questions/missing not empty; removed for narration payload.",
                    },
                )
        final_state_snapshot = _sanitize_chat_state_for_narration(
            final_state_snapshot, project_id=project_id
        )
        _apply_output_metadata_to_n0(project_id, final_state_snapshot)
        pending_questions = has_pending_questions(final_state_snapshot)
        allow_narration = not pending_questions or pending_rounds >= 1
        target_paths: List[str] = []
        target_strata: List[str] = []
        target_path = ""
        if isinstance(final_state_snapshot, dict):
            target_path = final_state_snapshot.get("target_path", "") or ""
        if isinstance(target_path, str) and target_path.strip():
            target_paths = [target_path.strip()]
            target_strata = [target_path.split(".", 1)[0]]
        else:
            target_strata = ["n0"]
        if not isinstance(target_strata, list):
            target_strata = []
        if not isinstance(target_paths, list):
            target_paths = []
        creation_mode_active = False
        if creation_mode:
            missing_paths = _get_n0_missing_paths(project_id)
            if missing_paths:
                creation_mode_active = True
                target_strata = ["n0"]
                target_paths = list(missing_paths)
        if allow_narration:
            narration_input = {
                "narration_id": session_id,
                "source_state_ref": "",
                "source_state_payload": final_state_snapshot,
                "target_strata": target_strata,
                "target_paths": target_paths,
                "storage_root": str(get_project_root(project_id)),
                "config": {"create_if_missing": True},
            }
            narrator = NarratorOrchestrator()
            fallback_plan = narrator.build_plan(narration_input)
            narration_task_plan = fallback_plan
            llm_meta: Dict[str, Any] = {"used_llm": False, "reason": "creation_mode"}
            if not creation_mode_active:
                narration_task_plan, _, llm_meta = narrator.build_plan_llm(
                    llm_client=runner.llm_client,
                    narration_input=narration_input,
                    fallback_plan=fallback_plan,
                )
            write_plan_log(
                project_id=project_id,
                session_id=session_id,
                label="narration_orchestrator_llm",
                payload={
                    "used_llm": llm_meta.get("used_llm"),
                    "reason": llm_meta.get("reason"),
                    "raw_output": llm_meta.get("raw_output", "")[:8000],
                },
            )
            narration_task_context = {}
            for task in narration_task_plan.get("tasks", []):
                task_id = task.get("id")
                if not task_id:
                    continue
                base_context = {
                    "source_state_payload": narration_input.get("source_state_payload") or {},
                    "target_path": task.get("output_ref", ""),
                }
                narration_task_context[task_id] = {
                    **base_context,
                }
            narration_runner_input = {
                "plan_id": narration_task_plan.get("plan_id", ""),
                "task_plan_ref": "",
                "task_plan_payload": narration_task_plan,
                "execution_mode": "sequential",
                "started_at": generate_timestamp(),
            }
            write_plan_log(
                project_id=project_id,
                session_id=session_id,
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
                    session_id=session_id,
                    task_context=narration_task_context or {},
                )

    return {
        "narration_input": narration_input,
        "narration_task_plan": narration_task_plan,
        "narration_runner_input": narration_runner_input,
        "narration_task_context": narration_task_context,
        "narration_run_result": narration_run_result,
        "has_pending_questions": pending_questions,
    }


def _apply_output_metadata_to_n0(project_id: str, output_state: Dict[str, Any]) -> None:
    if not isinstance(output_state, dict):
        return
    video_type = output_state.get("video_type") if isinstance(output_state, dict) else ""
    duration_s = output_state.get("target_duration_s") if isinstance(output_state, dict) else 0
    if not (isinstance(video_type, str) and video_type.strip()) and not duration_s:
        return

    try:
        n0_state = read_strata(project_id, "n0")
    except FileNotFoundError:
        n0_state = {}
    data = n0_state.get("data") if isinstance(n0_state, dict) else {}
    if not isinstance(data, dict):
        data = {}
    production_summary = data.get("production_summary")
    if not isinstance(production_summary, dict):
        production_summary = {}

    if isinstance(video_type, str) and video_type.strip():
        mapped = _map_video_type_to_production_type(video_type.strip())
        if mapped:
            production_summary["production_type"] = mapped

    duration_seconds = _coerce_duration_seconds(duration_s)
    if duration_seconds > 0:
        production_summary["target_duration"] = _format_duration_timecode(duration_seconds)

    if production_summary:
        data = {**data, "production_summary": production_summary}
        try:
            write_strata(project_id, "n0", data)
        except Exception:
            return


def _map_video_type_to_production_type(value: str) -> str:
    lowered = value.strip().lower()
    mapping = {
        "film": "feature film",
        "feature film": "feature film",
        "long metrage": "feature film",
        "long-metrage": "feature film",
        "long métrage": "feature film",
        "short film": "short film",
        "court metrage": "short film",
        "court-metrage": "short film",
        "court métrage": "short film",
        "ad": "advertisement",
        "advertisement": "advertisement",
        "commercial": "advertisement",
        "pub": "advertisement",
        "publicite": "advertisement",
        "publicité": "advertisement",
        "clip": "clip",
        "music video": "clip",
        "documentary": "documentary",
        "docu": "documentary",
        "documentaire": "documentary",
        "series": "series",
        "serie": "series",
        "série": "series",
    }
    for key, mapped in mapping.items():
        if key in lowered:
            return mapped
    return ""


def _coerce_duration_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str) and value.strip().isdigit():
        return max(0, int(value.strip()))
    return 0


def _format_duration_timecode(seconds: int) -> str:
    if seconds <= 0:
        return ""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
