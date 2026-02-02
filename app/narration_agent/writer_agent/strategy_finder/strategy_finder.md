# strategy_finder.md - "Strategy Finder" sub-agent (RAG)

## Role
- Choose a writing strategy from a text library.
- Produce a strategy card applicable to the target field.

## Expected input
- `context_pack.json`
- Library index (e.g. `writer_agent/strategy_finder/library/index.json`)
- Library passages retrieved via the R2R agentic RAG helper

## Expected output
- `strategy_card.json` compliant with `strategy_finder/strategy_card_structure.json`

## Rules
- The Strategy Finder decides which library typologies are ingested into R2R.
- Filter library items by `language` and `writing_typology` when possible.
- Reference the sources used (title + short excerpt when available).
- Do not invent styles not covered by the library.
- Adapt the strategy to the target field and constraints.
- If no matches are found, fall back to all library items.
