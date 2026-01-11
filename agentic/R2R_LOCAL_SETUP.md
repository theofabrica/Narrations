# R2R Local Setup (Python + OpenAI)

Goal
- Run a local R2R instance to index SRC_NARRATOLOGY.
- Use OpenAI embeddings (API key required).

Repo location
- Local clone: `agentic/r2r/R2R`

Install (editable)
1) Create/activate a virtualenv.
2) Install R2R from the local repo:
   `pip install -e agentic/r2r/R2R/py`

Run server
- Start R2R locally:
  `OPENAI_API_KEY=... python -m r2r.serve`

Ingest SRC docs
- `python agentic/r2r_ingest_src.py`

Env vars
- `OPENAI_API_KEY`: required by R2R server.
- `R2R_API_BASE`: optional (default http://localhost:7272).

Troubleshooting
- If the server fails to start, check the R2R logs and verify dependencies.
- If ingestion fails, ensure the server is running and `OPENAI_API_KEY` is set.
