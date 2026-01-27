# Bac à sable agents IA

Ce dossier sert à comprendre les **concepts de base** des agents IA via des
exemples simples et modifiables. Le but est pédagogique : chaque agent illustre
un mécanisme précis (stratégie, contrôle, routage, etc.).

## Concepts clés (version courte)
- **Agent** : une boucle `observer -> décider -> agir` avec un objectif.
- **Politique** : la règle de décision (ici, du simple prompt au plan+exécution).
- **Outils** : fonctions externes que l’agent peut appeler (ici, très minimal).
- **Mémoire** : contexte injecté dans le prompt (ici, basique).
- **Contrats** : entrées/sorties claires pour éviter l’ambiguïté.

## Environnement (repris de `agentic/`)
- `OPENAI_API_KEY` **obligatoire**
- `OPENAI_CHAT_MODEL` (défaut : `gpt-4o`)

Ces variables sont déjà utilisées par `agentic/runtime/llm_client.py`, que ce
bac à sable réutilise pour éviter de nouvelles dépendances.

## Démarrage rapide
```bash
export OPENAI_API_KEY=...   # requis
export OPENAI_CHAT_MODEL=gpt-4o
python /home/theoub02/code/MCP_Narrations/sandbox_agents/run_demo.py
```

## Fichiers
- `agents/base.py` : interface minimale et type de résultat.
- `agents/echo_agent.py` : agent sans LLM (contrôle de flux).
- `agents/simple_llm_agent.py` : agent “one-shot”.
- `agents/planner_executor_agent.py` : planification puis exécution.
- `agents/router_agent.py` : route une demande vers un agent spécialisé.
- `run_demo.py` : exécute quelques exemples.

## À faire ensuite
- Ajouter des **contrats JSON** (schémas) par agent.
- Introduire des **outils** (ex: validateur, index, calculs).
- Tester un **orchestrateur** qui fusionne des sorties partielles.
