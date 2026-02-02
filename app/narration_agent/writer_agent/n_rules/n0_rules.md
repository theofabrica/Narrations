# n0_rules.md - Declarative N0 rules

This file documents the declarative rules used by the writer orchestrator
for N0 writing. The executable logic (auto-fill, heuristics) remains in
`n_rules/n0_rules.py`.

## Source of truth (machine-readable)
`n_rules/n0_rules.json` contains the declarative configuration:
- `allowed_fields`
- `redaction_constraints` (min/max chars)
- `use_strategy`
- `skip_llm`
- `extra_rule`

## Notes
- N0 auto-fill (production_type, target_duration, aspect_ratio) stays in Python.
- Post-processing (visual_style, tone) stays in Python.
