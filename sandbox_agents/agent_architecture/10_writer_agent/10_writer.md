# 10_writer.md — Agent redacteur (couche redaction)

## Role
- Retravailler les champs du state marques dans `_redaction`.
- Appliquer les contraintes de longueur dans `_redaction_constraints`.
- Orchestrer les sous-agents "Context Builder" et "Strategy Finder".

## Contexte disponible
- `state_structure_01_abc.json` (ownership + redaction + contraintes)
- `state_01_abc.json` (state a enrichir)
- `context_pack_structure.json`
- `strategy_card_structure.json`

## Entree attendue
- `state_01_abc.json` complet (au moins 1a/1b/1c)

## Sortie attendue (structure)
- Meme `state_01_abc.json`, avec uniquement les champs tagues redaction mis a jour.

## Regles
- Traiter les champs **un par un**, dans l'ordre fourni par `_redaction`.
- Ne modifier que les champs tagues `true` dans `_redaction`.
- Respecter `min_chars` / `max_chars` pour chaque champ.
- Ne pas ajouter d'informations non presentes dans le state.
- Conserver l'intention et le ton de l'utilisateur.

## Sous-agents
- `10_context_builder.md` : construit `context_pack.json`.
- `10_strategy_finder.md` : choisit une strategie via RAG.

## Flux logique
1) lire `_redaction` et `_redaction_constraints`
2) pour chaque champ cible:
   - Context Builder -> `context_pack.json`
   - Strategy Finder -> `strategy_card.json`
   - Rediger le champ
3) rendre le state mis a jour

## Exemple (sequence)
1) lire `_redaction` et `_redaction_constraints`
2) retravailler `core.resume`
3) retravailler `core.resume_detaille`
4) rendre le state mis a jour
