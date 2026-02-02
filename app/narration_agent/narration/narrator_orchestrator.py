"""Narrator orchestrator for task planning and control flow."""

import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from app.utils.ids import generate_timestamp
from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.narration_agent.spec_loader import load_text


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

    def __init__(self) -> None:
        self.base_prompt = load_text("narration/00_narrator_orchestrator.md").strip()

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

    def build_plan_llm(
        self,
        llm_client: LLMClient,
        narration_input: Dict[str, Any],
        fallback_plan: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        prompt = self.base_prompt or "You are the narration orchestrator."
        allowed_paths = self._allowed_output_paths(narration_input)
        format_prompt = (
            "Return ONLY valid JSON with this structure:\n"
            "{\n"
            '  "tasks": [\n'
            "    {\n"
            '      "output_ref": "n0.production_summary",\n'
            '      "agent": "writer_n0"\n'
            "    }\n"
            "  ],\n"
            '  "plan_notes": ""\n'
            "}\n"
            "Rules:\n"
            "- Allowed agents: writer_n0, writer_n1, writer_n2, writer_n3, writer_n4, writer_n5\n"
            f"- Allowed output_ref values: {', '.join(allowed_paths) if allowed_paths else '[]'}\n"
            "- Do NOT add extra keys.\n"
            "- If nothing should be written now, return an empty tasks list.\n"
        )
        llm_response = llm_client.complete(
            LLMRequest(
                model=llm_client.default_model,
                messages=[
                    {"role": "system", "content": f"{prompt}\n\n{format_prompt}"},
                    {
                        "role": "user",
                        "content": json.dumps(
                            self._build_llm_payload(narration_input),
                            ensure_ascii=True,
                            indent=2,
                        ),
                    },
                ],
                temperature=0.2,
            )
        )
        raw_content = llm_response.content.strip()
        parsed = self._parse_json_payload(raw_content)
        if not parsed:
            return fallback_plan, {}, {"raw_output": raw_content, "used_llm": False, "reason": "invalid_json"}
        raw_tasks = parsed.get("tasks")
        if isinstance(raw_tasks, list) and len(raw_tasks) == 0:
            plan = self._build_plan_from_tasks(
                source_state_id=fallback_plan.get("source_state_id", ""),
                tasks=[],
            )
            return plan, {}, {"raw_output": raw_content, "used_llm": True, "reason": "empty_tasks"}
        tasks = self._normalize_tasks(raw_tasks, allowed_paths)
        if not tasks:
            return fallback_plan, {}, {"raw_output": raw_content, "used_llm": False, "reason": "missing_tasks"}
        plan = self._build_plan_from_tasks(
            source_state_id=fallback_plan.get("source_state_id", ""),
            tasks=tasks,
        )
        return plan, {}, {"raw_output": raw_content, "used_llm": True, "reason": "ok"}

    def _build_llm_payload(self, narration_input: Dict[str, Any]) -> Dict[str, Any]:
        source_state = narration_input.get("source_state_payload") or {}
        if not isinstance(source_state, dict):
            source_state = {}
        return {
            "source_state": source_state,
            "suggested_strata": narration_input.get("target_strata") or [],
            "suggested_paths": narration_input.get("target_paths") or [],
            "allowed_paths": self._allowed_output_paths(narration_input),
        }

    def _allowed_output_paths(self, narration_input: Dict[str, Any]) -> List[str]:
        target_strata = narration_input.get("target_strata") or []
        if not isinstance(target_strata, list) or not target_strata:
            target_strata = ["n0", "n1", "n2", "n3", "n4", "n5"]
        allowed_paths: List[str] = []
        if "n0" in target_strata:
            allowed_paths.extend([f"n0.{section}" for section in self._N0_SECTIONS])
        for strata in ("n1", "n2", "n3", "n4", "n5"):
            if strata in target_strata:
                allowed_paths.append(strata)
        return allowed_paths

    def _parse_json_payload(self, payload: str) -> Dict[str, Any]:
        if not payload:
            return {}
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            trimmed = payload.strip()
            start = trimmed.find("{")
            end = trimmed.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(trimmed[start : end + 1])
                    return parsed if isinstance(parsed, dict) else {}
                except json.JSONDecodeError:
                    return {}
        return {}

    def _normalize_tasks(
        self, raw_tasks: Any, allowed_paths: List[str]
    ) -> List[Dict[str, Any]]:
        if not isinstance(raw_tasks, list):
            return []
        allowed_agents = {"writer_n0", "writer_n1", "writer_n2", "writer_n3", "writer_n4", "writer_n5"}
        normalized: List[Dict[str, Any]] = []
        seen_outputs = set()
        for entry in raw_tasks:
            if not isinstance(entry, dict):
                continue
            output_ref = entry.get("output_ref")
            if not isinstance(output_ref, str):
                continue
            output_ref = output_ref.strip()
            if allowed_paths and output_ref not in allowed_paths:
                continue
            agent = entry.get("agent")
            if not isinstance(agent, str) or agent.strip() not in allowed_agents:
                agent = self._infer_agent(output_ref)
            agent = agent.strip()
            if agent not in allowed_agents:
                continue
            if output_ref in seen_outputs:
                continue
            seen_outputs.add(output_ref)
            normalized.append({"output_ref": output_ref, "agent": agent})
        return normalized

    def _infer_agent(self, output_ref: str) -> str:
        if output_ref.startswith("n0."):
            return "writer_n0"
        if output_ref.startswith("n1."):
            return "writer_n1"
        if output_ref.startswith("n2."):
            return "writer_n2"
        if output_ref.startswith("n3."):
            return "writer_n3"
        if output_ref.startswith("n4."):
            return "writer_n4"
        if output_ref.startswith("n5."):
            return "writer_n5"
        if output_ref in {"n1", "n2", "n3", "n4", "n5"}:
            return f"writer_{output_ref}"
        return "writer_n0"

    def _build_plan_from_tasks(self, source_state_id: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        plan_tasks = []
        last_task_id = ""
        task_counter: Dict[str, int] = {}
        for task in tasks:
            output_ref = task.get("output_ref", "")
            base_id = f"task_{output_ref.replace('.', '_')}" if output_ref else "task_writer"
            task_counter[base_id] = task_counter.get(base_id, 0) + 1
            task_id = base_id if task_counter[base_id] == 1 else f"{base_id}_{task_counter[base_id]}"
            plan_tasks.append(
                {
                    "id": task_id,
                    "agent": task.get("agent", ""),
                    "input_ref": "state_01_abc",
                    "output_ref": output_ref,
                    "depends_on": [last_task_id] if last_task_id else [],
                }
            )
            last_task_id = task_id
        return {
            "plan_id": plan_id,
            "created_at": generate_timestamp(),
            "source_state_id": source_state_id,
            "tasks": plan_tasks,
        }

