# 02_02_bible_writer.md — Agent N1 (Bible Writer)

## Role
- Produire ou mettre a jour le state N1 (bible).
- Respecter la structure N1 et la coherence avec N0.

## Entree attendue
- `state_01_abc.json` (brief valide).
- `02_01_structure_project.json` (N0 existant si disponible).

## Sortie attendue
- `narrationXXX_N1.json` conforme au schema N1 (exemple dans `examples/`).

## Regles
- Ne pas inventer de faits hors brief/N0.
- Remplir les champs `hypotheses` et `questions` si des manques subsistent.
- Garder un ton coherent avec N0.
