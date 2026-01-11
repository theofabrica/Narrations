# SRC Indexing Plan

Scope
- Index `SRC_NARRATOLOGY__*.txt` and `PM_*` documents.
- Keep `N0_*` and `CORE_*` available as direct context (no RAG).

Chunking
- Chunk size: 800-1200 tokens.
- Overlap: 100-150 tokens.
- Split by headings where possible.

Metadata
- `source_file`
- `section_title`
- `doc_type` (SRC or PM)

Retrieval Policy
- Default top_k: 4-6
- Use `doc_type` filter by level:
  - N2 uses SRC
  - N4 uses PM

Quality Checks
- Ensure at least 1 SRC concept is retrieved for N2.
- Ensure PM_* only drives N4 parameters.
