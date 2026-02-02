# redactor.md - Redactor (writing sub-agent)

## Role
- Rewrite state fields tagged in `_redaction`.
- Apply length constraints from `_redaction_constraints`.

## Available context
- `state_structure_01_abc.json` (ownership + redaction + constraints)
- `state_01_abc.json` (state to enrich)
- `context_builder/context_pack_structure.json`
- `strategy_finder/strategy_card_structure.json`

## Expected input
- `context_pack.json` compliant with `context_builder/context_pack_structure.json`

## Expected output (structure)
- `target_patch`: content of the target section only.
- `open_questions`: remaining questions if blocked (optional).

## Rules
- Process fields **one by one**, in the order provided by `_redaction`.
- Only modify fields tagged `true` in `_redaction`.
- Respect `min_chars` / `max_chars` for each field.
- Do not add information not present in the state.
- Preserve the user's intent and tone.
- Only write the target section (`target_path`) provided by the context pack.

## Sub-agents
- None (the writer orchestrator prepares the context and strategy).

## Logical flow
1) read `_redaction` and `_redaction_constraints`
2) write only the target section using the provided context + strategy
3) return `target_patch`

## Example (sequence)
1) read `_redaction` and `_redaction_constraints`
2) rewrite `core.summary`
3) rewrite `core.detailed_summary`
4) return the updated state
