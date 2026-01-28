"""Narration orchestrator for task planning and control flow."""

from dataclasses import dataclass
from typing import Any, Dict, List


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


class NarrationOrchestrator:
    """Produce task plans for N0-N5 generation."""

    def build_plan(self, source_state_id: str) -> TaskPlan:
        raise NotImplementedError("Task planning not wired yet.")
