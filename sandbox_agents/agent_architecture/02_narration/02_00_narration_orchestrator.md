# 02_00_narration_orchestrator.md — Orchestrateur narration (couche 2)

## Role
- Orchestrer la narration a partir du brief (state).
- Coordonner les sous-agents de la couche 2.

## Entree attendue
- `state_01_abc.json` (section `brief` remplie).
- `02_00_narration_input_schema.json` (point d'entree).

## Sortie attendue
- `task_plan.json` conforme a `02_00_task_plan_structure.json`.

## Sous-agents
- `02_00_task_planner.md` : construit la liste de taches.

## Regles
- Ne pas modifier le brief.
- Deleguer la construction du plan au Task Planner.
