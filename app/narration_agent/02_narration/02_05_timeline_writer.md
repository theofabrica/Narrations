# 02_05_timeline_writer.md - Agent N4 (Timeline / Edit list)

## Role
- Produce or update the N4 state (timeline, tracks, segments).
- Translate N3 into an edit-ready timeline.

## Expected input
- `state_01_abc.json` (valid brief).
- `state_structure_n3.json` (N3 if available).
- `state_structure_n2.json` (N2 if available).
- Reference example: `examples/satire_trump_greenland_clip_001_N4.json`.

## Expected output
- `narrationXXX_N4.json` compliant with the N4 schema or the N4 example.

## Rules
- Each segment references a source (e.g. N3 unit/scene).
- Respect timecodes and the global target duration.
- Keep a multi-track structure (video + audio) even if audio is empty.
- Maintain strict consistency with N3 (id, order, intent).
- Fill `dependencies` and `notes` if needed.
- Default writing typology: `structure`.
