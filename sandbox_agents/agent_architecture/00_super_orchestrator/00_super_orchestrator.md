# 00_super_orchestrator.md — Super-orchestrateur (couche 0)

## Role
- Orchestrer le flux global (conversation, clarification, redaction, orchestration metier).
- Decider quand lancer 1a/1b/1c, le writer, puis l'orchestrateur narration.
- Gerer la file de taches (`task_queue.json`) et deleguer l'execution au runner.

## Entrees principales
- Message utilisateur + historique de conversation.
- `state_01_abc.json` (etat courant).
- `agent_architecture/hyperparameters.json`.
- `super_orchestrator_input_schema.json`.

## Sorties principales
- State mis a jour.
- Plan de taches (via couche 2).
- Etat de progression (log minimal).
- `super_orchestrator_output_schema.json`.
- `task_queue.json` (transmis au runner).

## Flux global (Option B)
1) Lancer 1a -> 1b -> 1c
2) Si `manques` non vides, relancer 1a (boucle)
3) Si `_redaction` actif, lancer 10_writer_agent
4) Passer le brief a la couche 2 (orchestrateur narration)
5) Lancer l'execution des taches

## Regles
- Ne pas forcer l'etape suivante si `manques` n'est pas vide.
- Conserver une trace minimale des decisions (plan + etat).
