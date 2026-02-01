"""Narration flow orchestration for narration_agent."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.narration_agent.logging_utils import write_plan_log
from app.narration_agent.narration.narrator_orchestrator import NarratorOrchestrator
from app.narration_agent.task_runner import TaskRunner
from app.utils.ids import generate_timestamp
from app.utils.project_storage import get_project_root


def has_pending_questions(state: Dict[str, Any]) -> bool:
    pending = state.get("pending_questions") if isinstance(state, dict) else None
    return isinstance(pending, list) and len(pending) > 0


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
        pending_questions = has_pending_questions(final_state_snapshot)
        allow_narration = not pending_questions or pending_rounds >= 2
        brief = final_state_snapshot.get("brief") if isinstance(final_state_snapshot, dict) else {}
        target_strata = brief.get("target_strata") if isinstance(brief, dict) else None
        target_paths = brief.get("target_paths") if isinstance(brief, dict) else None
        if not isinstance(target_strata, list):
            target_strata = []
        if not isinstance(target_paths, list):
            target_paths = []
        if creation_mode:
            target_strata = ["n0"]
            target_paths = []
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
            narration_task_plan = narrator.build_plan(narration_input)
            narration_task_context = {}
            for task in narration_task_plan.get("tasks", []):
                task_id = task.get("id")
                if not task_id:
                    continue
                narration_task_context[task_id] = {
                    "source_state_payload": narration_input.get("source_state_payload") or {},
                    "target_path": task.get("output_ref", ""),
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
