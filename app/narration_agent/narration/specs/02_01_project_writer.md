# 02_01_project_writer.md - Agent N0 (Project Writer)

## Role
- Produce or update the N0 state (project layer).
- Respect the N0 schema and production constraints.

## Expected input
- `state_01_abc.json` (valid brief).
- `02_00_task_plan_structure.json` (if a task plan is provided).
- `state_structure_n0.json` (N0 schema).
- `context_builder/context_pack_structure.json` (writer interface).

## Expected output
- `narrationXXX_N0.json` compliant with the N0 schema.

## Rules
- Do not invent constraints not present in the brief.
- Keep the existing N0 format and fields.
- Stay consistent with tone and deliverables.
- In project creation, the orchestrator plans one task per N0 section
  (e.g. `narrative_presentation`, `art_direction`, `sound_direction`).
- Each writer task outputs only the target section; the code merges into N0.
- The writer receives only the `context_pack` and returns only `target_patch`.
- Declarative N0 rules live in `writer_agent/n_rules/n0_rules.json`.
- Order of operations for N0:
  1) Auto-fill (no LLM) from `state_01_abc`:
     - `narrative_presentation.production_type`
     - `narrative_presentation.target_duration`
     - `narrative_presentation.aspect_ratio` (default `16:9` if missing)
  2) Update context with 1c, N1 (if any), and N0 fields above.
  3) Ask Strategy Finder for `narrative_presentation.summary` (global story strategy).
  4) Write `narrative_presentation.summary` with rule (English):
     "Tell the summary as a visual story, like a storyteller who takes time to narrate a beautiful scene."
  5) Update context with the new summary.
  6) Write `art_direction.description` (no new strategy) with rule (English):
     "Describe the aesthetic style precisely and highlight what makes it distinctive."
  7) Update context with the new art description.
  8) Write `sound_direction.description` (no new strategy) with rule (English):
     "Describe the sonic and musical style precisely and highlight what makes it distinctive."
  9) After sound is written, infer:
     - `narrative_presentation.visual_style`
     - `narrative_presentation.tone`
- Ignore `deliverables` (defaults are already true).
- Ignore `references` fields.
- Length constraints live in `writer_agent/n_rules/n0_rules.json` and are enforced at runtime.
- Writing typology by section:
  - `narrative_presentation`: `summary`
  - `art_direction`: `style`
  - `sound_direction`: `style`
