# 01c_orchestrator_translator.md - Translator agent (layer 1c)

## Role
- Transform 1b output into a structured orchestration brief.
- Normalize the request for the orchestrator.

## Available context
- `objectives`, `constraints`, `hypotheses`, `missing`, `clarifications` (from 1b)
- `orchestrator_expected_format` (schema or internal contract)
- `agent_architecture/hyperparameters.json`: `missing_sensitivity` shared by 1a/1b/1c.

## Expected input
- `output_1b` (full 1b structure)

## Expected output (structure)
The JSON schema is external and versioned:
- `state_structure_01_abc.json`

1c must produce a **JSON patch** limited to the `brief` section and `pending_questions`.

```json
{
  "completed_steps": ["1a", "1b", "1c"],
  "missing": [],
  "brief": {
    "primary_objective": "",
    "secondary_objectives": [],
    "constraints": [],
    "hypotheses": [],
    "target_level": "",
    "priorities": []
  },
  "pending_questions": []
}
```

## Rules
- Do not invent information.
- If `missing` or `clarifications` exist, propagate them into `pending_questions`.
- Update `missing` according to `missing_sensitivity` if needed.
- Stay concise and factual.
- Refer to `_ownership` in `state_structure_01_abc.json`.
- Never produce `core` or `thinker`.

## Example
**Input**: output_1b

**Output**:
```json
{
  "completed_steps": ["1a", "1b", "1c"],
  "missing": [
    "Exact topic",
    "Target duration"
  ],
  "brief": {
    "primary_objective": "Produce a short narration with a satirical tone",
    "secondary_objectives": [],
    "constraints": ["Duration to define", "Topic to define"],
    "hypotheses": [],
    "target_level": "n1",
    "priorities": ["Clarify topic and duration"]
  },
  "pending_questions": ["Exact topic", "Target duration"]
}
```
