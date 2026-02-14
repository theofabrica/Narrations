# 02_00_narration_orchestrator.md - Narration orchestrator (layer 2)

## Role
- Orchestrate narration based on the brief (state).
- Coordinate layer-2 sub-agents.
- Fill N0-N5 states (creation or editing) from the brief.

## Expected input
- `state_01_abc.json` (with the `brief` section filled).
- `02_00_narration_input_schema.json` (entry point).

## Expected output
- `task_plan.json` compliant with `02_00_task_plan_structure.json`.
- Updated N0-N5 states if the plan is executed.

## Mapping with super orchestrator and runner
- `02_00` produces a `task_plan` (raw plan) compliant with `02_00_task_plan_structure.json`.
- The super orchestrator wraps this plan for the runner:
  - `runner_input.task_plan_payload` = `task_plan` (full object).
  - `runner_input.task_plan_ref` = optional (if stored externally).
  - `runner_input.execution_mode` = `sequential` or `parallel` based on dependencies.
  - `runner_input.started_at` = launch timestamp.
- The runner does not consume the raw plan directly; it expects this input wrapper.

## Rules
- Do not modify the brief.
- Produce the task list and dependencies directly.
- In empty-project mode, add an initial task to identify the project.
- `project_id` is filled by application code from the folder name.
- If N0-N5 states are empty (new project), run a generation loop:
  - generate N0, then N1, then N2, then N3, then N4, then N5.
  - for N0, create one task per section (e.g. `narrative_presentation`, `deliverables`,
    `art_direction`, `sound_direction`) and execute them via the writer.
  - stop if a level cannot be filled (missing data).
- If states are not empty, switch to edit mode (detailed later).
- Use `target_strata` and `target_paths` (from 1c brief) to scope the tasks.
