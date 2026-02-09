# context_pack_structure.md - Field clarification

The `context_builder/context_pack_structure.json` file is a context container with no new information.
Each field comes from the state, N schemas, or knowledge sources (strategy).

## Fields
- `target_path`: path of the target field to write (e.g. `data.production_summary`).
- `target_section_name`: short name of the section (e.g. `production_summary`).
- `writing_typology`: writing task type used to guide strategy selection.
- `strategy_question`: explicit question to orient the strategy finder.
- `target_current`: current content of the target section.
- `target_schema`: schema excerpt for the target section.
- `source_state_id`: source state identifier (e.g. `s0001`).
- `project_id`: project identifier (if known).
- `core_summary`: short summary from the state (if available).
- `thinker_constraints`: constraints from the `thinker` section.
- `brief_constraints`: constraints from the `brief` section.
- `brief_primary_objective`: primary objective (brief).
- `brief_target_duration_s`: target duration in seconds (numeric).
- `brief_secondary_objectives`: secondary objectives (brief).
- `brief_priorities`: priorities (brief).
- `missing`: list of missing elements detected.
- `pending_questions`: questions to ask the user.
- `dependencies`: references to N0-N5 states if available, plus optional inline data.
  - `n0_ref`..`n5_ref`: file references
  - `n0`..`n5`: inline state data when loaded
- `style_constraints`: language, tone, format.
- `strategy_card`: strategy card provided by the Strategy Finder.
- `redaction_constraints`: length bounds for the target field.
- `rules`: declarative rules for the target segment.
  - `strategy_role`: role label used to frame strategy questions.
  - `strategy_hints`: hints to orient strategy generation.
  - `redaction_rules`: concrete writing rules for the target segment.
  - `quality_criteria`: criteria used to evaluate the draft.
  - `extra_rule`: legacy single-line rule for prompts.
- `do_not_invent`: safety boolean (true = do not invent).

## Rules
- No field should contain new information.
- The pack only structures what is already known.
- The redactor must produce only `target_path`.
