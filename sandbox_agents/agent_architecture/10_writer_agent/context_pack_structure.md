# context_pack_structure.md — Clarification des champs

Le fichier `context_pack_structure.json` est un conteneur de contexte, sans ajout de
nouvelles informations. Chaque champ provient du state ou des sources de connaissance.

## Champs
- `target_path` : chemin du champ cible a rediger (ex: `core.resume`).
- `source_state_id` : identifiant du state source (ex: `s0001`).
- `core_resume` : resume court du state (si disponible).
- `core_resume_detaille` : resume detaille du state (si disponible).
- `intentions` : liste de tags courts pour guider la redaction.
- `thinker_contraintes` : contraintes issues de la section `thinker`.
- `brief_contraintes` : contraintes issues de la section `brief`.
- `manques` : liste des elements manquants detectes.
- `questions_en_suspens` : questions a reposer a l'utilisateur.
- `redaction_constraints` : bornes de longueur pour le champ cible.
- `do_not_invent` : booleen de securite (true = ne pas inventer).

## Regles
- Aucun champ ne doit contenir d'information nouvelle.
- Le pack ne sert qu'a structurer ce qui est deja connu.
