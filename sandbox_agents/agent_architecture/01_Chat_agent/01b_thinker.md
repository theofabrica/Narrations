# 01b_thinker.md — Agent thinker (couche 1b)

## Role
- Reformuler la demande dans la logique de l'application.
- Extraire objectifs, contraintes, hypotheses.

## Contexte disponible
- `resume_1a` et `questions_ouvertes_1a`
- `objectifs_globaux_app` (optionnel)
- `knowledge/app_scope.json`
- `agent_architecture/hyperparameters.json` : `missing_sensitivity` commun a 1a/1b/1c.

## Entree attendue
- `resume_1a` (texte)
- `questions_ouvertes_1a` (liste)
- `message_utilisateur` (texte brut, optionnel)

## Sortie attendue (structure)
Le schema JSON est externe et versionne :
- `state_structure_01_abc.json`

1b doit mettre a jour `state_01_abc.json` conforme a ce schema.

```json
{
  "state_id": "",
  "state_version": "1abc_v1",
  "completed_steps": ["1a", "1b"],
  "manques": [],
  "core": {},
  "thinker": {
    "objectifs": [],
    "contraintes": [],
    "hypotheses": [],
    "manques": [],
    "clarifications": [],
    "niveau_cible": "",
    "notes": ""
  },
  "brief": {},
  "questions_en_suspens": []
}
```

## Regles
- Ne pas reposer les questions a l'utilisateur.
- Si information manquante, remplir `manques` selon `missing_sensitivity`.
- Si la demande n'est pas alignee avec les attendus du projet, remplir `clarifications`.
- Si `manques` ou `clarifications` non vides, les ajouter a `questions_en_suspens`.
- Rester factuel, pas d'invention.
 - Se referer a `_ownership` dans `state_structure_01_abc.json`.

## Exemple
**Entree** :
- resume_1a: "Demande de narration courte et satirique, sujet a preciser."

**Sortie** :
```json
{
  "state_id": "s0001",
  "state_version": "1abc_v1",
  "completed_steps": ["1a", "1b"],
  "manques": [
    "Sujet exact",
    "Duree cible"
  ],
  "core": {
    "resume": "Demande de narration courte et satirique, sujet a preciser.",
    "questions_ouvertes": [
      "Quel est le sujet exact a traiter ?",
      "Quelle duree visee (30s, 60s, 90s) ?"
    ],
    "intentions": ["narration", "satire"],
    "notes": ""
  },
  "thinker": {
    "objectifs": ["Produire une narration courte au ton satirique"],
    "contraintes": ["Duree a definir", "Sujet a definir"],
    "hypotheses": [],
    "manques": ["Sujet exact", "Duree cible"],
    "clarifications": ["Le ton satirique doit-il suivre un angle politique precis ?"],
    "niveau_cible": "n1",
    "notes": ""
  },
  "brief": {
    "objectif_principal": "",
    "objectifs_secondaires": [],
    "contraintes": [],
    "hypotheses": [],
    "niveau_cible": "",
    "priorites": []
  },
  "questions_en_suspens": []
}
```
