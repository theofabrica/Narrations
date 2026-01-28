# 00_runner.md - Global runner (layer 0)

## Role
- Report task execution status.
- Do not manage the task queue (delegated to the super orchestrator).

## Expected input
- `task_plan.json` compliant with `02_narration/02_00_task_plan_structure.json`.
- `runner_input_schema.json`.

## Expected output
- `runner_output_schema.json` (results per task + statuses).
- `task_queue.json` (task list + execution status).

## Rules
- Do not modify the plan.
- Execute sequentially or in parallel based on `depends_on`.
- Report the state of each task (status + outputs).
