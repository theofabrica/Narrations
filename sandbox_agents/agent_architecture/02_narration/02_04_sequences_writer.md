# 02_04_sequences_writer.md — Agent N3 (Sequences & Scenes)

## Role
- Produire ou mettre a jour le state N3 (units/sequences/scenes).
- Detailing des sequences/scenes a partir du brief et des couches N0/N1/N2.

## Entree attendue
- `state_01_abc.json` (brief valide).
- `state_structure_n0.json` (N0 si disponible).
- `state_structure_n1.json` (N1 si disponible).
- `state_structure_n2.json` (N2 si disponible).
- Exemple de reference : `examples/satire_trump_greenland_clip_001_N3.json`.

## Sortie attendue
- `narrationXXX_N3.json` conforme au schema N3 ou a l'exemple N3.

## Regles
- Ne pas inventer de faits hors brief/N0/N1/N2.
- Respecter la granularite (G2/G3) et la duree cible.
- Garder la coherence de ton, style visuel et style sonore.
- Les IDs d'unites doivent rester stables pour le passage en N4/N5.
- Remplir `dependencies` avec les versions/updated_at des strates source.
