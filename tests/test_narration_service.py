from __future__ import annotations

from app.narration_agent.narration import narration_service


class DummyRunner:
    def __init__(self):
        self.calls = []

    def run_task_plan(self, **kwargs):
        self.calls.append(kwargs)
        return {"results": []}


def test_run_narration_flow_skips_when_pending_questions(monkeypatch):
    runner = DummyRunner()
    state = {"pending_questions": ["missing info"], "brief": {}}

    result = narration_service.run_narration_flow(
        project_id="demo",
        session_id="sess_demo",
        final_state_snapshot=state,
        creation_mode=True,
        pending_rounds=0,
        trigger="build_brief",
        runner=runner,
    )

    assert result["narration_task_plan"] is None
    assert result["narration_run_result"] is None
    assert result["has_pending_questions"] is True
    assert runner.calls == []


def test_run_narration_flow_runs_when_allowed(monkeypatch, tmp_path):
    runner = DummyRunner()
    state = {"pending_questions": [], "brief": {"target_strata": ["n0"], "target_paths": []}}
    plan = {
        "plan_id": "plan_123",
        "tasks": [{"id": "t1", "output_ref": "n0.narrative_presentation"}],
    }

    monkeypatch.setattr(
        narration_service, "get_project_root", lambda project_id: tmp_path / project_id
    )
    monkeypatch.setattr(
        narration_service.NarratorOrchestrator,
        "build_plan",
        lambda self, payload: plan,
    )

    result = narration_service.run_narration_flow(
        project_id="demo",
        session_id="sess_demo",
        final_state_snapshot=state,
        creation_mode=True,
        pending_rounds=0,
        trigger="build_brief",
        runner=runner,
    )

    assert result["narration_task_plan"] == plan
    assert result["narration_run_result"] == {"results": []}
    assert result["has_pending_questions"] is False
    assert runner.calls
