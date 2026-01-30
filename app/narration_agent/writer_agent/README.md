# 10_writer_agent - Architecture

## Overview
The writer agent works on fields tagged in `_redaction`.
It relies on two sub-agents to produce controlled writing.

## Sub-agents
- **Context Builder** (`10_context_builder.md`)
- **Strategy Finder (RAG)** (`10_strategy_finder.md`)

## Structures
- `context_pack_structure.json`
- `strategy_card_structure.json`
- `context_pack_structure.md` (field details)
- `strategy_card_structure.md` (field details)
- `library/index.json` (library catalog with typologies)

## Flow
1) Identify a target field via `_redaction`.
2) Build a `context_pack.json`.
3) Select a strategy via RAG.
4) Write the field according to the strategy.
