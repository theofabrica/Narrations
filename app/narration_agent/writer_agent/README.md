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
1) Build a `context_pack.json` (deterministic).
2) Agentic loop decides whether to refresh context, build strategy, redact, and evaluate.
3) Redact the field according to constraints and strategy guidance.
4) Iterate until the score threshold is met or max iterations is reached.

## Agentic configuration (env)
- `WRITER_AGENTIC_ENABLED` (default: true)
- `WRITER_AGENTIC_MAX_ITERS` (default: 3)
- `WRITER_AGENTIC_SCORE_THRESHOLD` (default: 0.75)
