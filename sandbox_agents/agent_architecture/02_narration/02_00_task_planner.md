# 02_00_task_planner.md — Sous-agent planificateur (couche 2)

## Role
- Transformer le brief (state) en plan de taches.
- Router vers les agents specialises selon le niveau (N0-N5).

## Entree attendue
- `state_01_abc.json` (section `brief` remplie).

## Sortie attendue
- `task_plan.json` conforme a `02_00_task_plan_structure.json`.

## Regles
- Respecter le niveau cible (n0-n5).
- Declarer toutes les dependances explicites entre taches.
- Favoriser le parallelisme si possible.

## Exemple (sequence)
1) Lire `brief` + `intentions`
2) Generer un plan de taches
3) Renvoyer le plan a `02_00_narration_orchestrator`
