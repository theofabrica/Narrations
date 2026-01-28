# Agent Architecture — Sommaire

## Objectif
Construire une architecture d'agents pour transformer une demande utilisateur en un
state structuré, puis en briefs exploitables par l'orchestrateur.

## Ce qui est prévu
- **Couche 0** : super-orchestrateur (logique globale).
- **Couche 0** : runner global (execution des taches).
- **Couche 1** en 3 etapes : 1a (chat) -> 1b (thinker) -> 1c (translator).
- **Couche 2** : narration (orchestrateur + planificateur).
- **State unique** pour toute la couche 1 : `state_01_abc.json`.
- **Auto-clarification** integree a 1a/1b/1c via le champ global `manques`.
- **Hyperparametres communs** : `missing_sensitivity` pour gerer la detection de manques.
- **Agent redacteur** (niveau 10) avec 2 sous-agents :
  - **Context Builder** : rassemble le contexte utile du state.
  - **Strategy Finder (RAG)** : choisit une strategie de redaction depuis une bibliotheque.

## Ce qui est en place
- `00_super_orchestrator/00_super_orchestrator.md`
- `00_runner/` :
  - `00_runner.md`
  - `runner_input_schema.json`
  - `runner_output_schema.json`
- `01_Chat_agent/` :
  - `01a_chat.md`, `01b_thinker.md`, `01c_orchestrator_translator.md`
  - `state_structure_01_abc.json` avec ownership + tags de redaction
  - `chat_memory/` :
    - index `state_index.json`
    - exemple `s0001/state_01_abc.json`
- `02_narration/` :
  - `02_00_narration_orchestrator.md`
  - `02_00_task_planner.md`
  - `02_00_task_plan_structure.json`
- `knowledge/` :
  - `app_scope.json` (scope minimal de l'application)
- `hyperparameters.json` (a la racine de `agent_architecture`)
- `10_writer_agent/10_writer.md` (premier jet)

## Ce qui reste a faire (prochaine etape)
1) Definir la structure exacte du **pack de contexte** (Context Builder).
2) Definir la structure d'une **fiche strategie** (Strategy Finder / RAG).
3) Preparer la **bibliotheque de textes** (format + emplacement).
4) Preciser les champs tagues par `_redaction` si besoin.
5) Mettre a jour `10_writer_agent` avec ces structures.
