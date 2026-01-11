# N0 Narrative Node (R2R RAG)

Purpose
- Minimal local node that loads the N0 system prompt and uses R2R for SRC_NARRATOLOGY RAG.
- Uses OpenAI API for chat completions.

Files
- `agentic/r2r_ingest_src.py`: ingest SRC_NARRATOLOGY docs into R2R.
- `agentic/n0_narrative_node.py`: run the N0 narrative node with R2R search.
- `agentic/system_prompt_narrative_global.md`: system prompt used by the node.

Environment Variables
- `OPENAI_API_KEY` (required)
- `OPENAI_CHAT_MODEL` (default: gpt-4o)
- `R2R_API_BASE` (default: http://localhost:7272)
- `RAG_TOP_K` (default: 5)
- `N0_USER_REQUEST` (default: "Definir le cadre de production du projet.")

Usage
1) Install R2R (from local repo):
   `pip install -e agentic/r2r/R2R/py`

2) Start R2R server (new terminal):
   `OPENAI_API_KEY=... python -m r2r.serve`

3) Ingest SRC docs:
   `python agentic/r2r_ingest_src.py`

4) Run node:
   `N0_USER_REQUEST="Votre demande" python agentic/n0_narrative_node.py`

Notes
- Ingestion stores metadata `doc_type=SRC` and `source_file`.
- Retrieval is filtered to SRC documents only.
