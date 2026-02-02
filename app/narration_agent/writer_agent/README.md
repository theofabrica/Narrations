# 10_writer_agent - Architecture

## Overview
The writer agent orchestrates controlled writing for fields tagged in `_redaction`.
It pilots three sub-agents to prepare context, select strategy, and redact.

## Sub-agents
- **Context Builder** (`context_builder/context_builder.md`)
- **Strategy Finder (RAG)** (`strategy_finder/strategy_finder.md`)
- **Redactor** (`redactor/redactor.md`)

## Structures
- `context_builder/context_pack_structure.json`
- `strategy_finder/strategy_card_structure.json`
- `context_builder/context_pack_structure.md` (field details)
- `strategy_finder/strategy_card_structure.md` (field details)
- `n_rules/n0_rules.json` (declarative N0 rules)
- `strategy_finder/library/index.json` (library catalog with typologies)

## Flow
1) Build a `context_pack.json`.
2) Select a strategy via RAG.
3) Redact the field according to the strategy.
