# 00_super_orchestrator.md - Super orchestrator (layer 0)

## Role
- Orchestrate the global flow (conversation, clarification, writing, business orchestration).
- Decide when to run 1a/1b/1c, the writer, then the narration orchestrator.
- Manage the task queue (`task_queue.json`) and delegate execution to the runner.
- Handle the "project creation" case (N0-N5 empty) by triggering a framing chat.

## Primary inputs
- User message + conversation history.
- `state_structure_01_abc.json` (current state).
- `agent_architecture/hyperparameters.json`.
- `super_orchestrator_input_schema.json`.
- Current project state (presence or absence of N0-N5 states).

## Primary outputs
- Updated state.
- Task plan (via layer 2).
- Progress state (minimal log).
- `super_orchestrator_output_schema.json`.
- `task_queue.json` (passed to the runner).

## Global flow (Option B)
1) Run 1a -> 1b -> 1c
2) If `missing` is not empty, run 1a again (loop)
3) If `_redaction` is active, run 10_writer_agent
4) Pass the brief to layer 2 (narration orchestrator)
5) Run task execution

## Project creation case
- If N0-N5 are empty or missing, open a framing chat.
- The chat feeds layer 1, then layer 2 progressively fills N0-N5.
- As long as missing blocks N0-N5, keep the clarification loop.

## Rules
- Do not force the next step if `missing` is not empty.
- Keep a minimal trace of decisions (plan + state).
