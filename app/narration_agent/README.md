# narration_agent (runtime applicatif)

## Objectif
Fournir un runtime applicatif pour executer la logique agentique definie dans
`sandbox_agents/agent_architecture`.

## Environnement Python
Le projet utilise un venv commun au repo : `.venv/`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer le runtime
```bash
source .venv/bin/activate
python -m app.narration_agent --model gpt-4o
```

## Notes
- Les appels LLM sont a brancher dans `llm_client.py`.
- Le flux complet est documente dans `ARCHITECTURE.md`.
- La memoire de chat est stockee dans `data/{project_id}/chat_states/`.
- Specs locales :
  - `super_orchestrator/`
  - `chat_agent/`
