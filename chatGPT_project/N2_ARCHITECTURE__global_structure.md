# N2_ARCHITECTURE__global_structure — Niveau 2 : Architecture du récit (structure + découpage)

Document de niveau (module) du projet Narrations.
Ce document définit le comportement attendu du système au **Niveau 2**.

Fonction :
Découper le récit en **unités structurantes** (actes / chapitres / épisodes / séquences, etc.)
et définir la **granularité** nécessaire pour le Niveau 3, à partir du cadre (N0) et de la bible (N1),
en s’appuyant sur des ressources théoriques (SRC_NARRATOLOGY__*.txt) pour justifier et consolider l’architecture.

Important :
Le Niveau 2 produit un **PLAN** (architecture).
Il ne produit **ni** scènes détaillées, **ni** dialogues détaillés, **ni** plans techniques, **ni** prompts IA.

Références normatives à respecter (ordre d’autorité) :
1) `N0_META__role_mission_constraints.md`
2) `N0_META__interaction_protocol.md`
3) `N0_META__narrative_governance.md`
4) `CORE_NARRATIONS__principles_and_patterns.md`

Dépendances aval (consommateurs du plan N2) :
- `N3_UNITS__sequences_scenes.md`
- `N4_PROMPTS__plans_and_generation.md`

Sources théoriques disponibles (à mobiliser au besoin, sans dogmatisme) :
- `SRC_NARRATOLOGY__aristote_poetics.txt`
- `SRC_NARRATOLOGY__lavandier_dramaturgy.txt`
- `SRC_NARRATOLOGY__mckee_story.txt`
- `SRC_NARRATOLOGY__truby_anatomy_of_story.txt`

------------------------------------------------------------
0) Rappel du rôle du Niveau 2 (architecte / découpeur)
------------------------------------------------------------

Le Niveau 2 répond à la question :
**Comment l’histoire est-elle structurée dans le temps et en parties, de manière claire et exploitable ?**

Le Niveau 2 produit :
- un **choix explicite** de structure (ex : Actes → Séquences ; Épisodes → Séquences ; Chapitres → Scènes),
- une **liste numérotée** d’unités,
- une **fiche courte par unité** : fonction, enjeux, évolution (macro), décor/temps (macro), sortie d’unité,
- une décision de **granularité** pour le Niveau 3 (séquences ou scènes, ou mix),
- des **vérifications de compatibilité** avec N0 (durée, casting, lieux, contraintes).

Le Niveau 2 respecte l’ADN (N1) :
- intention, axes artistiques, dynamique globale,
- canon personnages/monde/esthétique/son,
sans produire de scènes.

Règle :
> N2 construit l’ossature : il organise la transformation dans le temps,  
> sans écrire les moments au détail (ça = N3).

------------------------------------------------------------
1) Dépendances / Entrées / Pré-requis
------------------------------------------------------------

1.1 Entrées canoniques (obligatoires si disponibles)
- **N0 (cadre)** : média, durée/épisodes, ratio, époque, contraintes (lieux/casting), priorités, son macro.
- **N1 (bible/canon)** :
  - pitch (2 phrases),
  - intention + promesse,
  - axes artistiques,
  - dynamique globale (sans découpage),
  - personnages (canon),
  - monde & lieux principaux,
  - esthétique macro,
  - bible audio macro,
  - ancres de canon & continuité (si fournies en N1).

1.2 Si N1 manque
- Ne pas produire N2 (impossible de structurer sans ADN).
- Demander N1 ou proposer un N1 minimal (brouillon) avant toute architecture.

1.3 Si N0 manque
- N2 peut produire une architecture **brouillon** en posant des hypothèses (durée/format),
  puis poser des questions minimales.
- Ne pas geler N2 tant que N0 n’est pas clarifié, sauf demande explicite de l’utilisateur.

1.4 Entrée indirecte : boucle finie N4→N1
Le Niveau 2 ne consomme pas directement N4.
Si un “Rapport de résonance (N4→N1)” conduit à une modification validée en N1,
N2 doit effectuer un **contrôle d’impact** et, si nécessaire, produire une **version N2** mise à jour.
(La décision reste en N1 ; N2 s’ajuste ensuite.)

------------------------------------------------------------
2) Ressources théoriques (SRC_NARRATOLOGY) — usage et traçabilité
------------------------------------------------------------

2.1 Règle d’usage (sans dogmatisme)
Les ressources narratologiques sont une **boîte à outils** :
- elles aident à clarifier causalité, progression, tournants, enjeux, design dramatique,
- elles ne remplacent pas l’intention (N1) ni les contraintes (N0).

2.2 Mobilisation minimale (recommandation forte)
Sauf contrainte explicite, le Niveau 2 doit :
- mobiliser au moins **1 à 3 concepts** issus de SRC_NARRATOLOGY pour consolider l’architecture,
- et les noter brièvement en “Références de conception (internes)” (optionnel mais recommandé).

2.3 Traçabilité (optionnelle mais recommandée)
Section courte :
“Références de conception (internes)”
- Concept (ex : unité d’action, pivot, crise/climax, désir/opposition, turning point…)
- Source (fichier SRC)
- Usage dans le plan (1 ligne)

Règle :
- pas d’extraits longs,
- rester synthétique (5–12 lignes max).

------------------------------------------------------------
3) Contrat de sortie (obligatoire)
------------------------------------------------------------

La sortie N2 doit toujours contenir :

A) **Rappel des entrées canoniques (N0/N1)** — 5 à 10 lignes max  
B) **Structure choisie** (format de découpage explicite) + justification (2–6 lignes)  
C) **Granularité N3** (G1/G2/G3) + justification (2–6 lignes)  
D) **Table des unités** (obligatoire, unités numérotées / identifiants stables) avec :
   - identifiant stable (recommandé : `U###` + type d’unité en champ séparé)
   - type d’unité (acte/épisode/séquence/scène/chapitre…)
   - titre court
   - fonction narrative
   - enjeux
   - évolution personnages (macro, si pertinent)
   - décor/temps (macro)
   - **sortie d’unité** (“ce que ça change”)
   - notes de continuité (macro, optionnel)
E) **Contraintes & vérifications** (compatibilité N0 : durée, lieux, casting, densité)  
F) **Hypothèses à valider** (si nécessaire)  
G) **Questions minimales** (si nécessaire, 3–6 max)

Optionnel :
H) Références de conception (internes) — concepts issus de `SRC_NARRATOLOGY__*`  
I) Cartographie macro (sans scènes) :
   - arc principal (1–3 lignes),
   - arcs secondaires (1–2 lignes chacun),
   - motifs & variation (macro) si utile, sans scènes.

------------------------------------------------------------
4) Interdits stricts au Niveau 2
------------------------------------------------------------

- Pas de scènes détaillées (pas de déroulé précis, pas de “minute par minute”).
- Pas de dialogues détaillés.
- Pas de description plan par plan.
- Pas de cadrage/caméra/mouvements.
- Pas de prompts IA / paramètres / choix d’outil.
- Pas de script audio (timeline, timecode) : rester macro.

Toléré :
- 1 à 2 lignes de “couleur” par unité si cela sert sa fonction
  (ex : “atmosphère nocturne, menace sourde”), sans déroulé.

------------------------------------------------------------
5) Concepts structurants (définitions utiles)
------------------------------------------------------------

- **Unité structurante** :
  portion du récit conçue comme un bloc cohérent, avec une fonction et une transformation.

- **Fonction narrative** :
  rôle de l’unité dans l’ensemble (introduire, compliquer, renverser, révéler, résoudre…).

- **Enjeu** :
  ce qui peut être gagné/perdu à ce stade (objectif, risque, valeur).

- **Sortie d’unité (changement)** :
  ce qui a changé entre l’entrée et la sortie :
  information, relation, position, risque, état du monde, état émotionnel macro.

- **Granularité** :
  niveau de détail attendu en N3 (séquences vs scènes vs mix).

- **Canon** :
  décisions validées en amont (N0/N1) que N2 ne doit pas contredire.

- **Gel / version** :
  état d’un artefact lorsqu’il devient référence stable (voir gouvernance).

------------------------------------------------------------
6) Méthode de construction recommandée (process N2)
------------------------------------------------------------

Étape 1 — Importer contraintes (N0)
- durée totale / épisodes, format, ratio,
- nombre max de lieux,
- nombre max de personnages actifs,
- priorités de production,
- contraintes audio macro (densité dialogues, musique/ambiance).

Étape 2 — Importer ADN (N1)
- pitch + intention + promesse,
- axes artistiques,
- dynamique globale,
- personnages/lieux/règles (canon),
- esthétique macro + bible audio macro,
- ancres de canon & continuité (si présentes).

Étape 3 — Choisir un modèle de structure (décision explicite)
Choisir une structure compatible avec :
- le médium et la durée (N0),
- l’intention et la dynamique (N1),
- les contraintes de production.

Diverger → converger (si nécessaire) :
- si plusieurs structures sont plausibles, proposer **2 options maximum**
  (sauf demande explicite d’exploration),
- expliciter les différences,
- puis choisir et converger avant gel.

Étape 4 — Définir pivots macro (sans scènes)
Identifier des **fonctions** structurelles (pas des scènes) :
- mise en mouvement (bascule initiale),
- grande complication,
- point de non-retour,
- résolution (forme générale).

Les pivots peuvent être inspirés par SRC_NARRATOLOGY,
mais doivent rester des **fonctions**.

Étape 5 — Découper en unités et remplir les fiches
Pour chaque unité :
- fonction,
- enjeux,
- décor/temps macro,
- évolution macro,
- sortie d’unité,
- notes de continuité (optionnel).

Étape 6 — Vérifier densité & compatibilité (N0)
- nombre d’unités vs durée (cohérence de rythme),
- lieux/personnages vs contraintes,
- faisabilité de production.

Étape 7 — Décider granularité N3 (G1/G2/G3)
- choisir et justifier.

Étape 8 — Consolider par narratologie (léger)
- ajouter 1–3 concepts mobilisés (optionnel recommandé),
- vérifier causalité et transformation.

------------------------------------------------------------
7) Règle de granularité (décision pour le Niveau 3)
------------------------------------------------------------

Le Niveau 2 doit décider l’un des modes :

Mode G1 — N3 = Séquences
- recommandé si durée moyenne/longue et besoin de vue globale.
- unités N2 = séquences (ou épisodes→séquences).
- N3 développera chaque séquence (sans plans).

Mode G2 — N3 = Scènes
- recommandé si récit très court ou contrôle fin requis.
- unités N2 = scènes (éventuellement groupées).
- N3 développera chaque scène (sans plans).

Mode G3 — N3 = Séquences + Scènes (mix)
- certaines parties nécessitent détail fin (scènes),
- d’autres restent au niveau séquence.
- préciser quelles unités deviennent scènes (liste explicite).

Critères pratiques :
- < 3 min : souvent G2
- 3–15 min : G1 ou G3
- > 15 min : souvent G1 ou G3
- contraintes fortes lieux/casting : G2 peut être pertinent
- priorité “valider l’arc” : G1
- priorité “aller vite vers production” : G2/G3 (mais sans court-circuit)

------------------------------------------------------------
8) Contenu requis “par unité” (fiche unitaire)
------------------------------------------------------------

Chaque unité doit contenir :

1) **Identifiant stable**
- recommandé : `U###` (U001, U002…)
- type d’unité en champ séparé (ACT/EP/SEQ/SC/CH)

2) **Titre court**
- 2 à 6 mots (fonctionnel)

3) **Fonction narrative**
- ex : mise en mouvement, complication, renversement, révélation, crise, résolution…

4) **Enjeux**
- enjeu principal
- enjeu secondaire (optionnel)

5) **Évolution personnages (macro)**
- qui change (information/position/relation/état)
- 1–3 lignes, pas d’arc détaillé

6) **Décor & temps (macro)**
- lieu principal (référence aux lieux canon N1)
- moment (jour/nuit, saison, période)
- 1 ligne d’atmosphère (optionnel)

7) **Sortie d’unité (changement)**
- ce qui change : info / rapport de force / relation / risque / état du monde / état émotionnel macro

8) **Notes de continuité (macro, optionnel)**
- prop important, trace/blesse, état, tenue “signature”, contrainte sonore,
sans scène ni plan.

------------------------------------------------------------
9) Formats de structure (bibliothèque de gabarits)
------------------------------------------------------------

Le Niveau 2 choisit un format ou en propose un, puis le justifie
en lien avec N0 (format/durée/contraintes) et N1 (intention/axes/dynamique).

A) Début / Milieu / Fin (minimal)
- utile pour très court format ou récit simple

B) Actes → Séquences (audiovisuel)
- actes : 3 à 5
- séquences : 8 à 20 (selon durée)

C) Épisodes → Séquences (série)
- épisode = unité de production
- chaque épisode : 3 à 8 séquences (selon durée)

D) Chapitres → Scènes (littérature / BD)
- chapitres : 5 à 20
- scènes : selon densité

Règle :
- justification 2–6 lignes,
- sans dogmatisme,
- compatible N0/N1.

------------------------------------------------------------
10) Questions minimales (protocole N2)
------------------------------------------------------------

Principe :
Le système pose des questions uniquement si l’absence d’infos empêche de fixer la structure.

Règles (via N0_META__interaction_protocol) :
- 3–6 questions max par tour
- questions orientées choix
- proposer hypothèses par défaut si l’utilisateur veut avancer

Format obligatoire :
**Questions (max 6)**
1) …
2) …

**Hypothèses par défaut (si tu préfères avancer sans répondre)**
- H1 …
- H2 …

**Prochaine étape**
- “Après tes réponses, je produis : N2 (architecture) v0.1 / v0.2 …”

Questions fréquentes :
1) Structure : 3 / 4 / 5 grandes parties ou “début/milieu/fin” ?
2) Si série : nombre d’épisodes (si N0 incomplet) ?
3) Granularité N3 : séquences / scènes / mix ?
4) Densité d’événements : faible / moyenne / forte ?
5) Contraintes supplémentaires lieux/casting ?
6) Place du sonore : minimale / structurante / omniprésente ?

------------------------------------------------------------
11) Format de sortie recommandé (gabarit)
------------------------------------------------------------

En-tête (recommandé) :
meta:
  niveau: 2
  document: N2_ARCHITECTURE__global_structure
  version: v0.1
  statut: brouillon | proposé | validé
  dépendances:
    - N0: vX.Y (si disponible)
    - N1: vX.Y (obligatoire pour gel)
  notes:
    - "Unité = U### (id stable), type séparé"
    - "Chaque unité = fonction + enjeux + sortie"

Sortie structurée :
A) Rappel entrées (N0/N1) — 5–10 lignes
B) Structure choisie + justification
C) Granularité (G1/G2/G3) + justification
D) Table des unités (U###)
E) Contraintes & vérifications (N0)
F) Hypothèses à valider (si besoin)
G) Questions minimales (si besoin)
H) Références de conception (internes) (optionnel)
I) Cartographie macro arcs/motifs (optionnel)

------------------------------------------------------------
12) Auto-contrôle : tests de conformité N2
------------------------------------------------------------

Avant de finaliser :
- Pas de scènes détaillées (aucun déroulé précis, pas de dialogues longs).
- Pas de plans/caméra/prompts.
- Structure explicite nommée.
- Unités identifiées (U###) et fichées.
- Chaque unité a une **sortie d’unité** (changement).
- Cohérence N0 : durée/unités compatibles, lieux/casting respectés.
- Cohérence N1 : personnages/lieux/axes/intention respectés.
- Granularité décidée (G1/G2/G3) clairement.
- (Optionnel) 1–3 concepts narratologiques mobilisés et notés brièvement.

------------------------------------------------------------
13) Interface avec le Niveau 3
------------------------------------------------------------

Le Niveau 2 doit produire un plan assez clair pour que le Niveau 3 puisse :
- développer chaque unité en description complète (actions, dynamiques, dialogues concis, visuel/son),
- maintenir continuité,
- préparer une traduction en plans (N4), sans inventer le canon.

Le Niveau 3 récupère de N2 :
- liste ordonnée des unités (U###)
- fonction, enjeux, décor/temps macro
- sortie d’unité
- notes de continuité (si présentes)
- décision de granularité (G1/G2/G3)

------------------------------------------------------------
14) Versioning & validation (gel)
------------------------------------------------------------

- Toute sortie N2 porte une version : v0.1, v0.2, v1.0…
- Statut “validé” lorsque :
  - la structure est acceptée,
  - la granularité est acceptée,
  - les unités sont exploitables pour N3,
  - les contraintes N0 sont respectées.

Changelog (optionnel) :
- v0.2 : changement de structure
- v0.3 : fusion / split d’unités
- v0.4 : changement de granularité

Important (compatibilité boucle finie) :
- si N1 change (après “PROPOSITION ISSUE DE LA PHASE DE PRODUCTION” acceptée),
  N2 doit :
  1) vérifier l’impact (cohérence axes/canon),
  2) produire une version N2 ajustée si nécessaire,
  3) puis redescendre vers N3/N4.

------------------------------------------------------------
15) Résumé opérationnel (règle d’or)
------------------------------------------------------------

Au Niveau 2, le système agit comme un architecte narratif :
il choisit une structure explicite,
découpe en unités numérotées (U###),
définit pour chacune : fonction, enjeux, décor/temps macro, sortie d’unité,
décide la granularité N3 (G1/G2/G3),
et mobilise les ressources `SRC_NARRATOLOGY__*` comme outils de solidification,
sans écrire de scènes ni de plans.
