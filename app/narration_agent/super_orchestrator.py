"""Super orchestrator (layer 0) for narration runtime."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Dict

from app.narration_agent.spec_loader import load_json
from app.utils.ids import generate_timestamp


@dataclass
class SuperOrchestratorResult:
    task_plan: Dict[str, Any]
    task_context: Dict[str, Any]
    next_action: str


class SuperOrchestrator:
    """Build task plans and decide next action."""

    def __init__(self) -> None:
        self.input_schema = load_json("super_orchestrator/super_orchestrator_input_schema.json")
        self.output_schema = load_json("super_orchestrator/super_orchestrator_output_schema.json")

    def build_task_plan(
        self,
        source_state_id: str,
        message: str,
        project_empty: bool,
        empty_strata: Dict[str, bool],
    ) -> SuperOrchestratorResult:
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
        task_1c = {
            "id": task_id_1c,
            "agent": "chat_1c",
            "input_ref": "chat_1b_output",
            "output_ref": "chat_1c_output",
            "depends_on": [task_id_1b],
        }
        task_plan = {
            "plan_id": plan_id,
            "created_at": generate_timestamp(),
            "source_state_id": source_state_id,
            "tasks": [task_1a, task_1b, task_1c],
        }
        task_context = {
            task_id_1a: {
                "message": message,
                "project_empty": project_empty,
                "empty_strata": empty_strata,
            },
            task_id_1b: {},
            task_id_1c: {},
        }
        next_action = "chat_clarification" if project_empty else "edit_mode"
        return SuperOrchestratorResult(
            task_plan=task_plan,
            task_context=task_context,
            next_action=next_action,
        )
