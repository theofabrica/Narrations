"""Narrator orchestrator for task planning and control flow."""

import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

from app.utils.ids import generate_timestamp


@dataclass
class Task:
    id: str
    agent: str
    input_ref: str
    output_ref: str
    depends_on: List[str]


@dataclass
class TaskPlan:
    plan_id: str
    created_at: str
    source_state_id: str
    tasks: List[Task]


class NarratorOrchestrator:
    """Produce task plans for N0-N5 generation."""

    _N0_SECTIONS = (
        "production_summary",
        "art_direction",
        "sound_direction",
    )

    def build_plan(self, narration_input: Dict[str, Any]) -> Dict[str, Any]:
        source_state = narration_input.get("source_state_payload") or {}
        source_state_id = (
            source_state.get("state_id")
            or narration_input.get("narration_id")
            or f"sess_{uuid.uuid4().hex}"
        )
        target_strata = narration_input.get("target_strata") or []
        target_paths = narration_input.get("target_paths") or []
        if not isinstance(target_strata, list):
            target_strata = []
        if not isinstance(target_paths, list):
            target_paths = []

        tasks: List[Task] = []
        last_task_id = ""

        def add_task(task_id: str, agent: str, output_ref: str, depends: List[str]) -> None:
            tasks.append(
                Task(
                    id=task_id,
                    agent=agent,
                    input_ref="state_01_abc",
                    output_ref=output_ref,
                    depends_on=depends,
                )
            )

        if "n0" in target_strata:
            requested_sections = {
                path.split(".", 1)[1]
                for path in target_paths
                if isinstance(path, str) and path.startswith("n0.")
            }
            sections = [
                section
                for section in self._N0_SECTIONS
                if not requested_sections or section in requested_sections
            ]
            for section in sections:
                task_id = f"task_n0_{section}"
                depends = [last_task_id] if last_task_id else []
                add_task(task_id, "writer_n0", f"n0.{section}", depends)
                last_task_id = task_id

        for strata in ("n1", "n2", "n3", "n4", "n5"):
            if strata not in target_strata:
                continue
            task_id = f"task_{strata}"
            depends = [last_task_id] if last_task_id else []
            add_task(task_id, f"writer_{strata}", f"{strata}", depends)
            last_task_id = task_id

        plan = TaskPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            created_at=generate_timestamp(),
            source_state_id=source_state_id,
            tasks=tasks,
        )
        return {
            "plan_id": plan.plan_id,
            "created_at": plan.created_at,
            "source_state_id": plan.source_state_id,
            "tasks": [
                {
                    "id": task.id,
                    "agent": task.agent,
                    "input_ref": task.input_ref,
                    "output_ref": task.output_ref,
                    "depends_on": task.depends_on,
                }
                for task in plan.tasks
            ],
        }
