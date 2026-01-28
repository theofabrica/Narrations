# 02_05_timeline_writer.md — Agent N4 (Timeline / Edit list)

## Role
- Produire ou mettre a jour le state N4 (timeline, tracks, segments).
- Traduire N3 en timeline exploitable par montage.

## Entree attendue
- `state_01_abc.json` (brief valide).
- `state_structure_n3.json` (N3 si disponible).
- `state_structure_n2.json` (N2 si disponible).
- Exemple de reference : `examples/satire_trump_greenland_clip_001_N4.json`.

## Sortie attendue
- `narrationXXX_N4.json` conforme au schema N4 ou a l'exemple N4.

## Regles
- Chaque segment reference une source (ex: unit/scene N3).
- Respecter les timecodes et la duree cible globale.
- Conserver une structure multi-tracks (video + audio) meme si audio vide.
- Garder une coherence stricte avec N3 (id, ordre, intentions).
- Renseigner `dependencies` et `notes` si necessaire.
