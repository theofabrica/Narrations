# context_pack_structure.md — Clarification des champs

Le fichier `context_pack_structure.json` est un conteneur de contexte, sans ajout de
nouvelles informations. Chaque champ provient du state, des schemas N, ou des sources
de connaissance (strategie).

## Champs
- `target_path` : chemin du champ cible a rediger (ex: `data.production_summary`).
- `target_section_name` : nom court de la section (ex: `production_summary`).
- `target_current` : contenu actuel de la section cible.
- `target_schema` : extrait du schema de la section cible.
- `source_state_id` : identifiant du state source (ex: `s0001`).
- `project_id` : identifiant du projet (si connu).
- `core_resume` : resume court du state (si disponible).
- `core_resume_detaille` : resume detaille du state (si disponible).
- `intentions` : liste de tags courts pour guider la redaction.
- `thinker_contraintes` : contraintes issues de la section `thinker`.
- `brief_contraintes` : contraintes issues de la section `brief`.
- `brief_objectif_principal` : objectif principal (brief).
- `brief_objectifs_secondaires` : objectifs secondaires (brief).
- `brief_priorites` : priorites (brief).
- `manques` : liste des elements manquants detectes.
- `questions_en_suspens` : questions a reposer a l'utilisateur.
- `dependencies` : references aux states N0-N5 si disponibles.
- `style_constraints` : langue, ton, format.
- `strategy_card` : carte de strategie fournie par le Strategy Finder.
- `redaction_constraints` : bornes de longueur pour le champ cible.
- `do_not_invent` : booleen de securite (true = ne pas inventer).

## Regles
- Aucun champ ne doit contenir d'information nouvelle.
- Le pack ne sert qu'a structurer ce qui est deja connu.
- Le writer ne doit produire que `target_path`.
