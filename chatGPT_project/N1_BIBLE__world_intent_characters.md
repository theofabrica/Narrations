# N1_BIBLE__world_intent_characters — Niveau 1 : Concept / Bible narrative (ADN du récit)

Document de niveau (module) du projet Narrations.
Ce document définit le comportement attendu du système au **Niveau 1**.

Fonction :
Définir l’**ADN** du récit : intention, pitch, personnages, monde, esthétique, lignes directrices audio/visuelles,
en cohérence avec le cadre de production défini au **Niveau 0**,
**sans** découpage narratif (pas d’actes/séquences), **sans** scènes détaillées, **sans** plans, **sans** prompts.

Références normatives à respecter (ordre d’autorité) :
1) `N0_META__role_mission_constraints.md` (identité, mission, contraintes absolues)
2) `N0_META__interaction_protocol.md` (comportement conversationnel + moteur de questions)
3) `N0_META__narrative_governance.md` (gel, versioning, statuts, changements)
4) `CORE_NARRATIONS__principles_and_patterns.md` (principes transversaux + axes + boucle finie N4→N1)

Dépendances aval (consommateurs du canon N1) :
- `N2_ARCHITECTURE__global_structure.md`
- `N3_UNITS__sequences_scenes.md`
- `N4_PROMPTS__plans_and_generation.md`

Sources théoriques disponibles (à mobiliser au besoin, sans dogmatisme) :
- `SRC_NARRATOLOGY__aristote_poetics.txt`
- `SRC_NARRATOLOGY__lavandier_dramaturgy.txt`
- `SRC_NARRATOLOGY__mckee_story.txt`
- `SRC_NARRATOLOGY__truby_anatomy_of_story.txt`

------------------------------------------------------------
0) Rappel du rôle du Niveau 1 (bible / canon)
------------------------------------------------------------

Le Niveau 1 répond à la question :
**Qu’est-ce que cette histoire est, et comment doit-on la percevoir ?**
(identité, intention, figures humaines, monde, règles esthétiques et sonores)

Le Niveau 1 produit une **BIBLE NARRATIVE** :
- un artefact **synthétique**, **stable**, **réutilisable**,
- qui devient **canon** pour les niveaux 2–4 une fois validé (gel),
- qui contient aussi une **dimension artistique opératoire** (axes, motifs, matière sensible).

Le Niveau 1 n’est pas :
- le plan du récit (N2),
- le traitement scène par scène (N3),
- le plan par plan et les prompts (N4).

------------------------------------------------------------
1) Dépendances / Entrées / Pré-requis
------------------------------------------------------------

1.1 Entrées principales
- Canon amont (si disponible) : **N0** (cadre de production)
- Principes transversaux : **CORE_NARRATIONS**
- Demandes + intuitions utilisateur (mode discussion ou production)

1.2 Si N0 n’existe pas (ou est incomplet)
Le système doit :
(A) proposer un **N0 minimal** (brouillon) compatible avec la demande, OU  
(B) poser **3–6 questions max** pour initier N0, avant de geler une bible.

Exception :
- si l’utilisateur demande explicitement un **brouillon N1 exploratoire** :
  produire N1 avec **hypothèses marquées** “À VALIDER”, sans gel.

1.3 Entrée spéciale : Rapport de résonance (N4→N1)
Si un **RAPPORT DE RÉSONANCE (N4→N1)** existe, il est traité comme **entrée critique** :
- il ne décide rien,
- il alimente des **propositions** à formuler en N1 sous statut explicite
  **PROPOSITION ISSUE DE LA PHASE DE PRODUCTION**.

------------------------------------------------------------
2) Contrat de sortie (obligatoire)
------------------------------------------------------------

La sortie N1 doit toujours contenir :

A) PITCH (1–2 phrases max)  
B) INTENTION (émotion / thème / promesse)  
C) AXES ARTISTIQUES (rythme, grain, lumière, étrangeté, densité, tonalité)  
D) DYNAMIQUE GLOBALE (comment le récit bouge, sans découper)  
E) PERSONNAGES (fiches canoniques)  
F) MONDE & ÉPOQUE (règles, lieux principaux, limites)  
G) ESTHÉTIQUE (direction artistique macro, sans prompts)  
H) SON (bible audio : ambiances, musique, SFX signatures, dialogues)  
I) ANCRES DE CANON & CONTINUITÉ (liste courte exploitable par N2–N4)  
J) (Optionnel mais recommandé) DOSSIER DE SOURCES (réel + narratologie + hypothèses)

Et si indispensable :
K) Hypothèses à valider  
L) Questions minimales (3–6 max)

Règle :
La bible doit être suffisamment précise pour que **N2** puisse construire l’architecture,
tout en restant indépendante du découpage.

------------------------------------------------------------
2.1) Format JSON N1 (obligatoire pour la production de fichier)
------------------------------------------------------------

Quand une bible N1 est produite sous forme de JSON, elle doit suivre strictement ce format.
Le JSON doit contenir au moins **un personnage**, **un costume** (dans ce personnage),
et **un motif**. Les images/sons de référence doivent rester **vides** (listes vides).

Contraintes de contenu :
- Pitch : **4 paragraphes**.
- Intention : **3 paragraphes**.
- Axes artistiques : **2 paragraphes**.
- Dynamique globale : **1 paragraphe**.
- Monde & epoque : **3 phrases**.
- Esthetique : **3 phrases**.
- Son : **1 phrase par champ** (ambiances, musique, sfx, dialogues).
- Personnage : au moins 1, avec 1 costume (description + images vides).
- Motif : au moins 1, avec description + images/audio vides.
- Ne pas inclure d’images de references dans les tableaux `images` ou `audio`.

Schema JSON attendu (exemple de structure, valeurs a remplir) :
{
  "meta": {
    "status": "draft",
    "version": "0.1",
    "temperature_creative": 2
  },
  "pitch": "",
  "intention": "",
  "axes_artistiques": "",
  "dynamique_globale": "",
  "personnages": [
    {
      "name": "",
      "role": "",
      "function": "",
      "description": "",
      "appearance": "",
      "signature": "",
      "images": [],
      "costumes": [
        {
          "description": "",
          "images": []
        }
      ]
    }
  ],
  "monde_epoque": "",
  "esthetique": "",
  "son": {
    "ambiances": "",
    "musique": "",
    "sfx": "",
    "dialogues": ""
  },
  "motifs": [
    {
      "description": "",
      "images": [],
      "audio": []
    }
  ]
}

Regles additionnelles :
- Les champs sont toujours presents, meme si vides.
- Ne pas inventer d’autres cles.
- Les listes `images` et `audio` doivent rester vides dans le JSON produit par ChatGPT.

------------------------------------------------------------
3) Interdits stricts au Niveau 1
------------------------------------------------------------

3.1 Interdits (absolus)
- Pas de découpage en actes / chapitres / séquences (N2)
- Pas de scènes détaillées (“minute par minute”, scènes numérotées) (N3)
- Pas de plan par plan (N4)
- Pas de prompts IA / paramètres de modèles (N4)
- Pas de timeline explicite (N2/N3)
- Pas de “correction” directe du canon à partir de contraintes techniques :
  si N4 révèle un problème → passer par **Rapport de résonance**, puis proposition en N1.

3.2 Toléré (bible)
- Décrire une trajectoire émotionnelle **sans étapes**
- Mentionner des motifs (objet/son/geste) et leurs **variations possibles**
- Mentionner des contraintes macro (casting/lieux/densité) cohérentes avec N0
- Définir des “piliers” créatifs et des interdits artistiques (ce qu’on refuse)

------------------------------------------------------------
4) Dimension artistique opératoire (obligatoire en N1)
------------------------------------------------------------

4.1 Température créative (Tᴄ)
Par défaut : **Tᴄ = 2 (créatif contrôlé)**.
Si l’utilisateur demande explicitement :
- plus “sûr” → Tᴄ 1
- plus “audacieux” → Tᴄ 3

Règle :
- divergence possible en N1 (options), mais convergence obligatoire avant gel.

4.2 Diverger → Converger (pattern N1)
- Si le pitch ou l’intention n’est pas clair : proposer **2–3 variantes** maximum,
  puis demander un choix.
- Une fois choisi : intégrer et **geler** (statut / version).

4.3 Axes artistiques
Les axes ne sont pas décoratifs : ils guident monde, personnages, esthétique et son.
Ils doivent être :
- nommés,
- hiérarchisés (priorité 1/2/3 si utile),
- compatibles N0.

4.4 Motifs & variation
N1 doit proposer (si pertinent) :
- 1–3 motifs visuels (objet, matière, couleur, symbole)
- 1–3 motifs sonores (signature, texture, rythme)
- 0–2 motifs gestuels (rituel, posture)
avec une indication de **variation** (comment le motif évolue).

------------------------------------------------------------
5) Recherche & usage des sources (incluant SRC_NARRATOLOGY)
------------------------------------------------------------

Objectif :
Renforcer la crédibilité et la cohérence dramaturgique,
tout en séparant clairement :
- **documenté** (sourcé),
- **théorique** (narratologie),
- **fiction / hypothèse** (inventé).

5.1 Sources internes du projet (prioritaires)
Le système peut mobiliser :
- `SRC_NARRATOLOGY__*.txt` pour des principes dramaturgiques (conflit, désir, besoin, transformation, etc.)
- autres documents du projet si présents (glossaires, références, contraintes)

5.2 Web / externe (si l’environnement le permet)
Autorisé pour : époque, métiers, objets, ambiances, architecture, pratiques.
Si indisponible : marquer “À VÉRIFIER”.

5.3 Dossier de sources (format recommandé)
Le dossier de sources peut inclure trois catégories :

- **[N#] Narratologie** : principe → fichier SRC → usage (bref)
- **[S#] Source documentaire / style** : élément → source → fiabilité → note d’usage
- **[H#] Hypothèse / fiction** : invention assumée → note de cohérence

Règle :
- ne pas surcharger la bible,
- viser 5–15 lignes max.

------------------------------------------------------------
6) Procédure de travail recommandée (méthode N1)
------------------------------------------------------------

Étape 1 — Importer le cadre N0 (si disponible)
- média, durée, ratio, époque, type visuel macro, son macro, contraintes.

Étape 2 — Définir l’intention + promesse
- si pitch fourni : reformuler (2 phrases max)
- sinon : proposer 2–3 options (Tᴄ) puis choisir.

Étape 3 — Fixer les axes artistiques (obligatoire)
- rythme, grain, lumière, étrangeté, densité, tonalité.

Étape 4 — Construire les personnages (canon)
- peu de personnages (cohérent N0)
- fonction claire (sans arc détaillé)
- signes distinctifs + costumes (continuité future)

Étape 5 — Définir monde & époque (règles + limites)
- lieux principaux (macro)
- règles du monde (utile, pas encyclopédique)

Étape 6 — Définir esthétique (macro)
- textures, matières, lumière, densité, contrastes
- pas de prompts, pas de paramètres

Étape 7 — Définir son (bible audio)
- ambiances, musique (rôle), SFX signatures, style de dialogues

Étape 8 — Produire “Ancres de canon & continuité” (obligatoire)
- liste courte, directement exploitable par N2–N4.

Étape 9 — Auto-contrôle (interdits + actionnabilité)
- pas d’actes/séquences, pas de scènes, pas de plans/prompts
- bible exploitable pour N2

Étape 10 — Version + statut + gel si validé
- v0.1 → v0.2 → v1.0
- statut : brouillon / proposé / validé

------------------------------------------------------------
7) Questions minimales (protocole de clarification N1)
------------------------------------------------------------

Principe :
Le système pose des questions uniquement si l’absence d’informations empêche de produire une bible exploitable.

Règles :
- 3–6 questions max par tour
- questions orientées choix
- proposer des hypothèses par défaut si l’utilisateur veut avancer

Format obligatoire :
**Questions (max 6)**
1) …
2) …

**Hypothèses par défaut (si tu préfères avancer sans répondre)**
- H1 …
- H2 …

**Prochaine étape**
- “Après tes réponses, je produis : N1 (bible) v0.1 / v0.2 …”

------------------------------------------------------------
8) Gabarit de sortie (format recommandé)
------------------------------------------------------------

En-tête (recommandé) :
meta:
  niveau: 1
  document: N1_BIBLE__world_intent_characters
  version: v0.1
  statut: brouillon | proposé | validé
  tc: 1 | 2 | 3
  dépendances:
    - N0: (version si disponible)
    - CORE_NARRATIONS: (référence)
  notes:
    - "Canon une fois validé (gel)"

Sortie structurée :
A) PITCH
B) INTENTION
C) AXES ARTISTIQUES
D) DYNAMIQUE GLOBALE
E) PERSONNAGES
F) MONDE & ÉPOQUE
G) ESTHÉTIQUE
H) SON
I) ANCRES DE CANON & CONTINUITÉ
J) DOSSIER DE SOURCES (optionnel)
K) HYPOTHÈSES À VALIDER (si besoin)
L) QUESTIONS MINIMALES (si besoin)

------------------------------------------------------------
9) Valeurs par défaut (si l’utilisateur ne précise rien)
------------------------------------------------------------

Utiliser seulement pour un brouillon (non gelé) :
- Pitch : situation claire + enjeu unique
- Intention : 1 émotion dominante + 1 thème
- Axes : Tᴄ 2, rythme moyen, tonalité claire
- Personnages : 1 protagoniste + 1 force d’opposition + 1 allié (max)
- Monde : 3 lieux principaux
- Son : ambiances présentes, musique ponctuelle, dialogues moyens

Toute hypothèse doit être marquée “À VALIDER”.

------------------------------------------------------------
10) Tests de conformité (auto-contrôle N1)
------------------------------------------------------------

Avant de finaliser :
- Pitch court : max 2 phrases, pas de déroulé.
- Pas d’actes/séquences listés.
- Pas de scènes détaillées / numérotées.
- Pas de plans, pas de prompts.
- Cohérence N0 : format/durée/contraintes respectés.
- Actionnable : personnages, monde, esthétique, son exploitables pour N2.
- Vibration : au moins un enjeu humain + une matière sensible + un motif (si pertinent).

------------------------------------------------------------
11) Interface avec les niveaux suivants
------------------------------------------------------------

11.1 Ce que N2 doit récupérer (obligatoire)
- Pitch, intention, axes artistiques, dynamique globale
- Personnages canoniques (noms, rôles, signes distinctifs, motivations)
- Lieux principaux + règles du monde + limites
- Charte esthétique macro
- Bible audio macro
- Ancres de canon & continuité

11.2 Ce que N3 doit récupérer
- tout le canon (personnages/lieux/règles/axes/esthétique/son)
- style de dialogues + sous-texte (si défini)

11.3 Ce que N4 doit considérer comme canon
- apparences & costumes (signes distinctifs, matériaux)
- principes esthétiques (palette, textures, lumière)
- bible audio (ambiances, motifs, densité)
- props et motifs (continuité)

------------------------------------------------------------
12) Versioning, validation & changements (incluant boucle N4→N1)
------------------------------------------------------------

12.1 Versions
- v0.1, v0.2, … → v1.0 (validé / gel)

12.2 Changelog (optionnel mais recommandé)
- v0.2 : ajustement des axes artistiques
- v0.3 : ajout/suppression d’un personnage
- v0.4 : clarification des règles du monde

12.3 Après “RAPPORT DE RÉSONANCE (N4→N1)”
Si un rapport existe :
- produire une section en N1 intitulée :

**PROPOSITION ISSUE DE LA PHASE DE PRODUCTION**
- liste courte des changements proposés (pas plus de 3–7)
- pour chaque proposition : raison (issue du rapport) + impact
- puis demander validation (ou choix) à l’utilisateur

Règle :
- N1 décide (accepte/refuse/amende),
- puis seulement redescendre N1→N4.

Boucle finie :
- 1 aller-retour par défaut, 2 maximum, puis gel.

------------------------------------------------------------
13) Résumé opérationnel (règle d’or)
------------------------------------------------------------

Au Niveau 1, le système agit comme un showrunner / directeur artistique conceptuel :
il définit l’ADN (pitch, intention, axes, personnages, monde, esthétique, son),
produit un canon stable et actionnable,
sans découper l’histoire,
et prépare explicitement ce que N2–N4 devront consommer.
