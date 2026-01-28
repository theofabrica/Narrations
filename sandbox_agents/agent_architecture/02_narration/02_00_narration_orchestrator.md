# 02_00_narration_orchestrator.md — Orchestrateur narration (couche 2)

## Role
- Orchestrer la narration a partir du brief (state).
- Coordonner les sous-agents de la couche 2.
- Remplir les states N0-N5 (creation ou edition) a partir du brief.

## Entree attendue
- `state_01_abc.json` (section `brief` remplie).
- `02_00_narration_input_schema.json` (point d'entree).

## Sortie attendue
- `task_plan.json` conforme a `02_00_task_plan_structure.json`.
- States N0-N5 mis a jour si le plan est execute.

## Mapping avec super-orchestrateur et runner
- `02_00` produit un `task_plan` (plan brut) conforme a `02_00_task_plan_structure.json`.
- Le super-orchestrateur emballe ce plan pour le runner :
  - `runner_input.task_plan_payload` = `task_plan` (objet complet).
  - `runner_input.task_plan_ref` = optionnel (si stockage externe).
  - `runner_input.execution_mode` = `sequential` ou `parallel` selon les dependances.
  - `runner_input.started_at` = timestamp de lancement.
- Le runner ne consomme pas le plan brut directement : il attend ce wrapper d'entree.

## Regles
- Ne pas modifier le brief.
- Produire la liste de taches et les dependances directement.
- En mode projet vide, ajouter une tache initiale d'identification du projet.
- Le `project_id` est rempli par le code applicatif a partir du nom du dossier.
- Si les states N0-N5 sont vides (nouveau projet), lancer une boucle de generation:
  - generer N0, puis N1, puis N2, puis N3, puis N4, puis N5.
  - pour N0, creer une tache par section (ex: `production_summary`, `deliverables`,
    `art_direction`, `sound_direction`) et les executer via le writer.
  - arreter si un niveau ne peut pas etre rempli (manques).
- Si les states ne sont pas vides, passer en mode edition (detaille ulterieurement).
