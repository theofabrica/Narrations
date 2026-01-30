# 02_02_bible_writer.md - Agent N1 (Bible Writer)

## Role
- Produce or update the N1 state (bible).
- Respect the N1 structure and coherence with N0.

## Expected input
- `state_01_abc.json` (valid brief).
- `state_structure_n0.json` (existing N0 if available).

## Expected output
- `narrationXXX_N1.json` compliant with the N1 schema (example in `examples/`).

## Rules
- Do not invent facts beyond the brief/N0.
- Fill `hypotheses` and `questions` if gaps remain.
- Keep a tone consistent with N0.
- Default writing typology: `character` (with `pitch` or `theme` when relevant).
