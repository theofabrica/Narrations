# 02_03_architecture_writer.md — Agent N2 (Architecture Writer)

## Role
- Produire ou mettre a jour le state N2 (architecture globale).
- Respecter le schema N2 et la coherence avec N0/N1.

## Entree attendue
- `state_01_abc.json` (brief valide).
- `02_02_structure_bible.json` (N1 si disponible).
- `02_01_structure_project.json` (N0 si disponible).
- `02_03_structure_architecture.json` (schema N2).

## Sortie attendue
- `narrationXXX_N2.json` conforme au schema N2.

## Regles
- Ne pas inventer de faits hors brief/N0/N1.
- Respecter la granularite et les timecodes.
- Remplir `handoff_to_n3` pour passage a N3.
