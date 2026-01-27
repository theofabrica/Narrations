# 01c_orchestrator_translator.md — Agent translator (couche 1c)

## Role
- Transformer la sortie de 1b en brief d'orchestration structuré.
- Normaliser la demande pour l'orchestrateur.

## Contexte disponible
- `objectifs`, `contraintes`, `hypotheses`, `manques`, `clarifications` (depuis 1b)
- `format_attendu_orchestrateur` (schema ou contrat interne)

## Entree attendue
- `sortie_1b` (structure 1b complete)

## Sortie attendue (structure)
Le schema JSON est externe et versionne :
- `state_structure_01_abc.json`

1c doit finaliser `state_01_abc.json` conforme a ce schema.

```json
{
  "state_id": "",
  "state_version": "1abc_v1",
  "completed_steps": ["1a", "1b", "1c"],
  "core": {},
  "thinker": {},
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

## Regles
- Ne pas inventer d'informations.
- Si `manques` ou `clarifications` existent, les propager dans `questions_en_suspens`.
- Rester concis et factuel.

## Exemple
**Entree** : sortie_1b

**Sortie** :
```json
{
  "state_id": "s0001",
  "state_version": "1abc_v1",
  "completed_steps": ["1a", "1b", "1c"],
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
    "objectif_principal": "Produire une narration courte au ton satirique",
    "objectifs_secondaires": [],
    "contraintes": ["Duree a definir", "Sujet a definir"],
    "hypotheses": [],
    "niveau_cible": "n1",
    "priorites": ["Clarifier sujet et duree"]
  },
  "questions_en_suspens": ["Sujet exact", "Duree cible"]
}
```
