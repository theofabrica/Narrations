# 1) Agent “Chat” (interface utilisateur)

## 1a — Dialogue (01a_chat.md)
- **Rôle** : parler avec l’utilisateur, clarifier la demande.
- **Contexte** : historique conversationnel (mémoire).
- **State** : initialise `state_01_abc.json` (section `core`) et ajoute `completed_steps=["1a"]`.

Propositions de FX  
# Première série d'appels au model avec son propre 01a_chat.md qui donne des instructions  
On peut imaginer des instructions de chat qui servent à garder la cohérence de la conversation.

**Entrée** : message utilisateur brut  
**Sortie** : `state_01_abc.json` (rempli partiellement)

## 1b — Thinker (01b_thinker.md)
- **Rôle** : reformuler + extraire objectifs/contraintes.
- **Contexte** : résumé 1a + objectifs globaux de l’app (`knowledge/app_scope.json`).
- **State** : remplit la section `thinker` et ajoute `completed_steps=["1a","1b"]`.

Propositions de FX  
# Deuxième série d'appels au model avec son propre 01b_thinker.md qui donne des instructions  
Un agent model qui repense la question de l'utilisateur dans la logique de l'application.
Ce thinker.md connait sommairement les buts et moyens de l'application et propose un cadrage clair (objectifs, contraintes, livrables).

**Entrée** : sortie 1a  
**Sortie** : `state_01_abc.json` (section `thinker` remplie)

## 1c — Translator (01c_orchestrator_translator.md)
- **Rôle** : transformer en brief d’orchestration structuré.
- **Contexte** : sortie 1b + format attendu par l’orchestrateur.
- **State** : remplit la section `brief` et ajoute `completed_steps=["1a","1b","1c"]`.

Propositions de FX  
# Troisième série d'appels au model avec son propre 01c_orchestrator_translator.md qui donne des instructions  
Un agent model qui transforme la demande en brief d'orchestration (format structuré).
Le brief contient objectifs, priorités, contraintes, et le niveau cible (N0/N1/N2/N3/N4).

**Entrée** : sortie 1b  
**Sortie** : `state_01_abc.json` (section `brief` remplie)

## 1d — Clarification (events_clarifier.md)
- **Rôle** : remonter des questions vers 1a pour clarification.
- **Déclencheurs** : `thinker.manques` ou `thinker.clarifications` non vides, ou besoin de la couche 2a.
  - Information obligatoire manquante (durée, format, niveau cible).
  - Ambiguïté bloquante (objectif trop vague, périmètre flou).
  - Contradiction entre éléments fournis.
- **Contexte** : sortie 1b/2a + historique du dialogue.

Propositions de FX  
# Série d'appels dédiée avec son propre events_clarifier.md qui donne des instructions  
Un agent model qui formule des questions ciblées pour compléter les informations manquantes.

**Entrée** : alerte + contexte  
**Sortie** : questions à poser à l’utilisateur via 1a

## State unique (couche 1)
- Schema commun : `state_structure_01_abc.json`.
- Fichier par session : `memory/sNNNN/state_01_abc.json`.
- Remplissage progressif : `core` → `thinker` → `brief`.

# Tableau de synthèse (couche 1)

| Bloc | Rôle | Entrée | Données | Sortie |
|---|---|---|---|---|
| 1a Dialogue | Clarifier la demande | Message utilisateur brut | Contexte du dialogue (historique) | `state_01_abc.json` (core) |
| 1b Thinker | Extraire objectifs/contraintes | `state_01_abc.json` | Contexte 1a + objectifs globaux | `state_01_abc.json` (thinker) |
| 1c Translator | Brief structuré | `state_01_abc.json` | Contexte 1b + format attendu | `state_01_abc.json` (brief) |
| 1d Clarifier | Remonter des questions | Alerte 1b/2a | Contexte 1b/2a + historique | Questions à poser via 1a |

# 2) Orchestrateur / Routeur

a. il prend la requete de 1c et orchestre la suite.
b. il séquence les appels si besoin.
c. il fusionne et valide les résultats.

# 3) Agents spécialisés

- Ils font une tâche précise (ex: progression, timecodes, dialogues…).
- Ils renvoient un sous‑bloc JSON.

En résumé :  
Utilisateur → Agent Chat → Orchestrateur → Agents spécialisés → Résultat final
