# 02_04_sequences_writer.md - Agent N3 (Sequences & Scenes)

## Role
- Produce or update the N3 state (units/sequences/scenes).
- Detail sequences/scenes based on the brief and layers N0/N1/N2.

## Expected input
- `state_01_abc.json` (valid brief).
- `state_structure_n0.json` (N0 if available).
- `state_structure_n1.json` (N1 if available).
- `state_structure_n2.json` (N2 if available).
- Reference example: `examples/satire_trump_greenland_clip_001_N3.json`.

## Expected output
- `narrationXXX_N3.json` compliant with the N3 schema or the N3 example.

## Rules
- Do not invent facts beyond brief/N0/N1/N2.
- Respect granularity (G2/G3) and target duration.
- Keep consistency of tone, visual style, and sound style.
- Unit IDs must remain stable for the N4/N5 handoff.
- Fill `dependencies` with versions/updated_at from source strata.
- Default writing typology: `scene`.
