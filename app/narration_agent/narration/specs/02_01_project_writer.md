# 02_01_project_writer.md - Agent N0 (Project Writer)

## Role
- Produce or update the N0 state (project layer).
- Respect the N0 schema and production constraints.

## Expected input
- `state_01_abc.json` (valid brief).
- `02_00_task_plan_structure.json` (if a task plan is provided).
- `state_structure_n0.json` (N0 schema).
- `context_pack_structure.json` (writer interface).

## Expected output
- `narrationXXX_N0.json` compliant with the N0 schema.

## Rules
- Do not invent constraints not present in the brief.
- Keep the existing N0 format and fields.
- Stay consistent with tone and deliverables.
- In project creation, the orchestrator plans one task per N0 section
  (e.g. `production_summary`, `art_direction`, `sound_direction`).
- Each writer task outputs only the target section; the code merges into N0.
- The writer receives only the `context_pack` and returns only `target_patch`.
- Order of operations for N0:
  1) Auto-fill (no LLM) from `state_01_abc`:
     - `production_summary.production_type`
     - `production_summary.target_duration`
     - `production_summary.aspect_ratio` (default `16:9` if missing)
  2) Update context with 1c, N1 (if any), and N0 fields above.
  3) Ask Strategy Finder for `production_summary.summary` (global story strategy).
  4) Write `production_summary.summary` with rule (English):
     "Tell the summary as a visual story, like a storyteller who takes time to narrate a beautiful scene."
  5) Update context with the new summary.
  6) Write `art_direction.description` (no new strategy) with rule (English):
     "Describe the aesthetic style precisely and highlight what makes it distinctive."
  7) Update context with the new art description.
  8) Write `sound_direction.description` (no new strategy) with rule (English):
     "Describe the sonic and musical style precisely and highlight what makes it distinctive."
  9) After sound is written, infer:
     - `production_summary.visual_style`
     - `production_summary.tone`
- Ignore `deliverables` (defaults are already true).
- Ignore `references` fields.
- Default length guidance (runtime):
  - `production_summary.summary`: 120-320 chars
  - `art_direction.description`: 180-600 chars
  - `sound_direction.description`: 180-600 chars
- Writing typology by section:
  - `production_summary`: `summary`
  - `art_direction`: `style`
  - `sound_direction`: `style`
