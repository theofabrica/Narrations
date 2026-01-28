# 02_06_prompts_writer.md — Agent N5 (Prompts & Generation Plans)

## Role
- Produire ou mettre a jour le state N5 (prompts, plans, assets).
- Deriver des plans media a partir de N3/N4 avec contraintes techniques.

## Entree attendue
- `state_01_abc.json` (brief valide).
- `state_structure_n4.json` (N4 si disponible).
- `state_structure_n3.json` (N3 si disponible).
- `state_structure_n2.json` (N2 si disponible).
- Exemple de reference : `examples/satire_trump_greenland_clip_001_N5.json`.

## Sortie attendue
- `narrationXXX_N5.json` conforme au schema N5 ou a l'exemple N5.

## Regles
- Ne pas inventer de scenes non presentes en N3/N4.
- Les prompts doivent rester exploitables par les providers (MJ, Kling, ElevenLabs).
- Garder la coherence visuelle/sonore (canon N0/N1/N2).
- Lister clairement les assets (visuels, audio) et leurs dependances.
- Renseigner `stack`, `render_specs`, `safety_and_branding`.
