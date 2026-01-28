# 10_writer_agent — Architecture

## Vue d'ensemble
L'agent redacteur travaille sur les champs tagues dans `_redaction`.
Il s'appuie sur deux sous-agents pour produire une redaction controllee.

## Sous-agents
- **Context Builder** (`10_context_builder.md`)
- **Strategy Finder (RAG)** (`10_strategy_finder.md`)

## Structures
- `context_pack_structure.json`
- `strategy_card_structure.json`
- `context_pack_structure.md` (details des champs)
- `strategy_card_structure.md` (details des champs)

## Flux
1) Identifier un champ cible via `_redaction`.
2) Construire un `context_pack.json`.
3) Selectionner une strategie via RAG.
4) Rediger le champ selon la strategie.
