# 00_runner.md — Runner global (couche 0)

## Role
- Signaler l'etat d'execution des taches.
- Ne pas gerer la file de taches (deleguee au super-orchestrateur).

## Entree attendue
- `task_plan.json` conforme a `02_narration/02_00_task_plan_structure.json`.
- `runner_input_schema.json`.

## Sortie attendue
- `runner_output_schema.json` (resultats par tache + statuts).
- `task_queue.json` (liste de taches + etat d'execution).

## Regles
- Ne pas modifier le plan.
- Executer en sequence ou parallele selon `depends_on`.
- Remonter l'etat de chaque tache (status + sorties).
