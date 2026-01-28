# 10_strategy_finder.md — Sous-agent "Strategy Finder" (RAG)

## Role
- Choisir une strategie de redaction a partir d'une bibliotheque de textes.
- Produire une fiche de strategie applicable au champ cible.

## Entree attendue
- `context_pack.json`
- Bibliotheque (ex: `agent_architecture/knowledge/writing_library/`)

## Sortie attendue
- `strategy_card.json` conforme a `strategy_card_structure.json`

## Regles
- Referencer les sources utilisees (titre, page ou passage).
- Ne pas inventer de styles non couverts par la bibliotheque.
- Adapter la strategie au champ cible et aux contraintes.
