# 02_06_prompts_writer.md - Agent N5 (Prompts & Generation Plans)

## Role
- Produce or update the N5 state (prompts, plans, assets).
- Derive media plans from N3/N4 with technical constraints.

## Expected input
- `state_01_abc.json` (valid brief).
- `state_structure_n4.json` (N4 if available).
- `state_structure_n3.json` (N3 if available).
- `state_structure_n2.json` (N2 if available).
- Reference example: `examples/satire_trump_greenland_clip_001_N5.json`.

## Expected output
- `narrationXXX_N5.json` compliant with the N5 schema or the N5 example.

## Rules
- Do not invent scenes not present in N3/N4.
- Prompts must stay usable by providers (MJ, Kling, ElevenLabs).
- Keep visual/audio coherence (canon N0/N1/N2).
- Clearly list assets (visual, audio) and their dependencies.
- Fill `stack`, `render_specs`, `safety_and_branding`.
- Default writing typology: `prompting`.
