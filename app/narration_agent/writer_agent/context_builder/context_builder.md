# context_builder.md - "Context Builder" sub-agent

## Role
- Build a context pack for a target state field.
- Do not invent: only extract and organize existing content.

## Expected input
- `state_01_abc.json`
- `state_structure_01_abc.json` (ownership + redaction + constraints)
- `agent_architecture/knowledge/app_scope.json`
- `agent_architecture/hyperparameters.json`
- `target_path` (ex: `core.resume`)

## Expected output
- `context_pack.json` compliant with `context_builder/context_pack_structure.json`

## Rules
- Only include elements present in the state or knowledge.
- Preserve useful wording but stay concise.
- Fill writing constraints linked to the target field.

## Example (flow)
1) read `target_path`
2) extract summary / intents / relevant constraints
3) build `context_pack.json`
