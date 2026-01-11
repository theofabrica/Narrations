# Agentic Runtime (Draft)

Goal
- Minimal runtime to instantiate GPT agents from prompt .md files.
- Use R2R for SRC_NARRATOLOGY retrieval.
- Orchestrate narrative + canonizer flows per level.

Modules
- `config.py`: env + paths.
- `llm_client.py`: OpenAI chat wrapper.
- `rag_client.py`: R2R search wrapper (SRC only).
- `agents.py`: Narrative + Canonizer agents.
- `orchestrators/`: N1..N4 orchestration skeletons.
- `runner_n1.py`: example runner for N1.

Environment
- `OPENAI_API_KEY` (required)
- `OPENAI_CHAT_MODEL` (default: gpt-4o)
- `R2R_API_BASE` (default: http://localhost:7272)

Notes
- Narrative agent uses `agentic/system_prompt_narrative_global.md` as default.
- Canonizer agent uses `agentic/system_prompt_canonizer.md`.
- Orchestrators build briefs and pass a JSON template to canonizer.

Example
```
export OPENAI_API_KEY=...
export PROJECT_ID=satire_trump_greenland_clip_001
export USER_REQUEST="Construire la bible N1."
export N1_TEMPLATE_PATH=/path/to/n1_template.json
python -m agentic.runtime.runner_n1
```
