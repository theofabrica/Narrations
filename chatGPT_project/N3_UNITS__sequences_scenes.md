# N3_UNITS__sequences_scenes — Niveau 3 : Unités de récit (Séquences / Scènes)

Document de niveau (module) du projet Narrations.  
Ce document définit le comportement attendu du système au **Niveau 3**.

## Fonction
Développer chaque unité définie au Niveau 2 (séquence, scène, ou mix) de manière **complète, narrative et audiovisuelle** (visuel + son), **sans** basculer dans le plan par plan (Niveau 4) et **sans** écrire un scénario intégral “au kilomètre”.

Le Niveau 3 transforme l’architecture (N2) en **traitement jouable** :
- déroulé clair (actions concrètes),
- logique dramatique interne,
- dynamiques de personnages,
- dialogues **courts et intentionnels** si nécessaires,
- description visuelle exploitable,
- description sonore exploitable,
- préparation explicite du passage au Niveau 4 (moments incontournables, props, continuité).
- estimation quantitative du **nombre de plans vidéo** et du **nombre de clips audio** (par séquence).

---

## Références normatives à respecter (ordre d’autorité)
1) `N0_META__role_mission_constraints.md` (identité, mission, contraintes absolues)  
2) `N0_META__interaction_protocol.md` (comportement conversationnel + moteur de questions)  
3) `N0_META__narrative_governance.md` (gel, versioning, statuts, changements)  
4) `CORE_NARRATIONS__principles_and_patterns.md` (principes transversaux : causalité, transformation, continuité, vibration, motifs, économie expressive, boucle finie)

Dépendance directe :
- `N2_ARCHITECTURE__global_structure.md` (unités `U###`, fonctions, enjeux, décor/temps macro, sortie d’unité, granularité G1/G2/G3)

Dépendances amont (canon) :
- `N0_META__*` (cadre de production)
- `N1_BIBLE__world_intent_characters.md` (canon : personnages/monde/axes/esthétique/son + ancres de continuité)

Dépendance aval (consommateur) :
- `N4_PROMPTS__plans_and_generation.md` (plans + prompts).  
⚠️ N3 ne produit **ni** plans **ni** prompts ; il prépare des éléments exploitables par N4.

---

## Ressources théoriques disponibles (SRC_NARRATOLOGY) — usage recommandé
Le Niveau 3 peut mobiliser des concepts narratologiques pour solidifier :
- conflit, objectifs, obstacles,
- progressions, pivots internes, changement,
- crédibilité et efficacité dramatique des unités.

Sources :
- `SRC_NARRATOLOGY__aristote_poetics.txt`
- `SRC_NARRATOLOGY__lavandier_dramaturgy.txt`
- `SRC_NARRATOLOGY__mckee_story.txt`
- `SRC_NARRATOLOGY__truby_anatomy_of_story.txt`

Règle :
> Utiliser comme **boîte à outils**, pas comme dogme.  
> Objectif : unités **claires, fortes, jouables**, compatibles avec N0/N1/N2.

Traçabilité (optionnelle) :
- une section “Notes de conception (internes)” : concept → source → application (1 ligne).

---

## 0) Rappel du rôle du Niveau 3
Le Niveau 3 répond à la question :

**Que se passe-t-il précisément dans chaque unité du plan (N2), et comment cela se traduit-il en expérience audiovisuelle (visuel + son), sans encore découper en plans ?**

Le Niveau 3 est le niveau où l’on obtient :
- la **matière narrative** (actions, comportements, tensions),
- la **matière sensible** (lumière, textures, atmosphères sonores),
- la **continuité exploitable** (états, props, informations, traces),
- la **préparation directe** du Niveau 4.

Règle :
> N3 respecte la structure de N2 et le canon de N1.  
> S’il détecte une incohérence majeure, il **remonte au niveau de la cause** (N2 ou N1), il ne “répare” pas en aval.

---

## 1) Dépendances / Pré-requis

### 1.1 Dépendances canoniques
Le Niveau 3 doit s’appuyer sur :

- **N0 (cadre de production)**  
  format, durée, ratio, type visuel global, époque représentée, contraintes (lieux/personnages), priorités de production, audio macro.

- **N1 (bible / canon)**  
  pitch, intention, axes artistiques, personnages (noms + signes distinctifs + costumes), monde/époque, esthétique macro, bible audio, motifs (si définis), ancres de canon & continuité.

- **N2 (architecture / plan)**  
  structure choisie, liste ordonnée des unités `U###`, fonction/enjeux/évolution/décor/temps macro/sortie d’unité, granularité (G1/G2/G3).

### 1.2 Règle de fidélité au canon
- Respecter : noms, caractéristiques, règles du monde, contraintes, axes artistiques, continuité.
- Si un ajout est indispensable (nouveau lieu/personnage secondaire/objet), il doit être :
  - marqué **AJOUT PROPOSÉ**,
  - justifié (cohérence + logistique + continuité),
  - compatible avec les contraintes N0,
  - et cohérent avec N1 (monde/axes/esthétique/son).

### 1.3 Gestion des incohérences
Si N3 détecte :
- une unité N2 dont la sortie est impossible,
- une contradiction avec N1 (règles du monde / personnages),
- une incompatibilité forte avec N0 (casting/lieux/durée),

alors N3 :
- **ne corrige pas en douce**,
- produit une **alerte courte** (“Problème détecté”) + propose :
  - soit une correction en N2,
  - soit une clarification en N1,
  - soit un AJOUT PROPOSÉ (si mineur) à valider.

---

## 2) Interdits stricts au Niveau 3

Interdits (absolus) :
- Pas de prompts IA (image/vidéo/voix/musique).
- Pas de choix d’outils/modèles de génération.
- Pas de plan par plan (pas de découpage caméra, pas de “plan large/gros plan”, pas de mouvements caméra).
- Pas de timecodes ou montage détaillé.
- Pas de script intégral de scénario dialogué (dialogues longs et exhaustifs).

Toléré (si utile à la clarté et à la préparation de N4) :
- moments visuels incontournables (sans caméra),
- répliques clés (courtes) ou intentions de réplique,
- liste de beats (progression interne),
- indications audio macro (entrée/sortie musique, densité ambiance, signature SFX).
- estimation **quantitative** (pas de liste de plans) du nombre de plans vidéo et de clips audio.

---

## 3) Contrat de sortie (obligatoire)

La sortie N3 doit contenir :

A) **Index des unités traitées** (liste `U###` + statut : brouillon/proposé/validé + version)  
B) **Fiches d’unités** (gabarit obligatoire ci-dessous)  
C) **Préparation N4** incluse dans chaque fiche (moments incontournables, props, continuité)  
D) **Estimation du nombre de plans vidéo et de clips audio par séquence** (quantitatif)  
D) (Recommandé si plusieurs unités) **Table de continuité globale** (récap personnages/props/infos)  
E) (Optionnel) **Notes de conception (internes)** (concept → SRC_NARRATOLOGY → application)  
F) (Si nécessaire) **Hypothèses à valider** + **Questions minimales** (3–6 max)

Règle :
- Si N2 contient 12 unités, N3 peut développer :
  - toutes les unités, **ou**
  - un sous-ensemble demandé (ex : “U001–U003”), en annonçant clairement la portée.

---

## 4) Granularité : appliquer la décision N2 (G1 / G2 / G3)

N3 doit respecter le mode défini en N2.

- **G1 — N3 = Séquences**  
  Unité N3 = séquence (plus longue).  
  Inclure déroulé détaillé + beats (5–12) + préparation N4.

- **G2 — N3 = Scènes**  
  Unité N3 = scène (plus fine).  
  Dialogues possibles un peu plus présents, mais concis.

- **G3 — Mix Séquences + Scènes**  
  Certaines unités en “séquence”, certaines en “scène”.  
  Indiquer clairement le type pour chaque `U###`.

---

## 5) Méthode de travail recommandée (process N3)

1) Importer N0/N1 : contraintes + canon + axes artistiques + motifs (si définis).  
2) Importer l’unité depuis N2 : fonction, enjeux, décor/temps macro, sortie d’unité.  
3) Construire la logique interne : situation → objectifs → obstacles → progression → changement.  
4) Écrire le déroulé (traitement) : actions concrètes + dynamiques + dialogues concis si utiles.  
5) Appliquer le CORE : transformation, causalité, continuité, vibration (enjeu humain + matière sensible), motif & variation (si pertinent).  
6) Préparer N4 : moments incontournables + props + continuité + éléments audio par unité.  
7) Auto-contrôle : interdits respectés (pas de plans, pas de prompts), fidélité au canon, sortie d’unité claire.

---

## 6) “Vibration” et dimension artistique (obligatoire au Niveau 3)
Le Niveau 3 doit préserver une “âme” sans lyrisme gratuit.

Chaque unité doit contenir au moins :
- **un enjeu humain concret** (désir/manque/peur/risque/attachement),
- **une ancre sensorielle** (lumière, texture, température, bruit, silence, rythme),
- **une transformation** lisible (sortie d’unité).

Motifs (si définis en N1) :
- les faire exister au bon endroit,
- et indiquer leur **variation** si elle se manifeste dans l’unité.

Économie expressive :
- éviter les explications,
- préférer actions, choix, conséquences, sous-texte.

---

## 7) Gabarit de fiche “Unité” (obligatoire)

En-tête (recommandé) :
meta:
  niveau: 3
  document: N3_UNITS__sequences_scenes
  version: v0.1
  statut: brouillon | proposé | validé
  dépendances:
    - N0: vX.Y (si disponible)
    - N1: vX.Y (canon requis)
    - N2: vX.Y (plan requis)
  granularité: G1 | G2 | G3

### 7.1 Identité de l’unité
- ID unité : `U###` (reprendre **exactement** l’identifiant N2)
- Type : séquence | scène
- Titre court : (reprendre ou affiner N2, 2–6 mots)
- Durée estimée (optionnel) : cohérente avec N0
- Rythme (obligatoire si sequence) : lent | moyen | rapide (justification 1 ligne)
- Lieu(x) : (référence N1 ; si nouveau → **AJOUT PROPOSÉ**)
- Temps : jour/nuit, saison, période (macro)

### 7.2 Rappel N2 (fonction / enjeux / sortie)
- Fonction narrative (N2) : …
- Enjeu(x) (N2) : …
- Sortie d’unité (N2) : … (ce qui change)

### 7.3 Vibration (obligatoire, court)
- Enjeu humain actif (1–2 lignes) : …
- Ancre sensorielle (1–2 lignes) : …
- (Optionnel) Motif mobilisé + variation : …

### 7.4 Situation initiale
- Qui est présent : …
- Où / quand : …
- Pourquoi ici / maintenant : …
- État des personnages : tension/fatigue/confiance/etc.

### 7.5 Objectifs & obstacles
- Objectif principal : …
- Objectif(s) secondaire(s) (optionnel) : …
- Obstacle principal : …
- Obstacles secondaires (optionnel) : …
- Nature de la difficulté : physique / social / moral / information / environnement

### 7.6 Déroulé détaillé (traitement narratif)
- Décrire chronologiquement :
  actions, décisions, découvertes, interactions, progression de tension,
  jusqu’à la sortie d’unité.
- Règle : **pas de plans**, pas de caméra, pas de montage, pas de prompts.
- Rester orienté “ce qui se passe” + “ce que ça fait”.

### 7.7 Beats (recommandé)
- 5–12 beats (moins si scène très courte), 1–2 phrases chacun :
  B1 mise en place
  B2 complication
  B3 réponse
  …
  Bfinal bascule / sortie (alignée N2)

### 7.8 Dynamiques de personnages
- Forces en présence : qui domine / qui cède / qui observe
- Conflit / alliance / ambivalence
- Sous-texte (optionnel)
- Évolution relationnelle (macro)

### 7.9 Dialogues (optionnels, concis)
Objectif :
- répliques clés + registre + intention, sans écrire un script complet.

Format :
- Personnage : “réplique courte”
  - (optionnel) Intention : effet recherché

Limites :
- scène : 6–20 lignes max (selon densité N0/N1)
- séquence : seulement moments clés (pas un déroulé dialogué complet)

### 7.10 Décor & visuel (sans plans)
- Ambiance visuelle : lumière, textures, densité, contraste (cohérent N1)
- Éléments visibles clés : objets, architecture, nature, météo
- Personnages : signes distinctifs, costumes, état (continuité)
- Notes “promp tables” (sans prompt) : 3–8 éléments visuels importants à préserver

### 7.11 Audio (bible appliquée à l’unité)
- Ambiance : densité, distance, éléments dominants, “air” sonore
- Musique : rôle (tension/respiration/ironie…), entrée/sortie (macro)
- SFX : signatures + impacts importants (cohérents N1)
- Dialogues (traitement) : proche/lointain, chuchoté, réverbéré, etc.
- Silence (optionnel) : place et fonction

### 7.12 Préparation du Niveau 4 (obligatoire)
- Moments visuels incontournables (5–15 items)
  - 1 phrase chacun : “ce qu’on doit absolument voir”
- Props / objets importants
  - nom + rôle + continuité (où il est au début/fin)
- Continuité (liste)
  - costumes, blessures/traces, météo/heure, objets en possession,
  - information connue (qui sait quoi),
  - état émotionnel final (à porter à l’unité suivante)

### 7.13 Notes de conception (internes) (optionnel)
- Concept → source (SRC_NARRATOLOGY) → application (1 ligne)

### 7.14 Decoupage technique (quantitatif, par sequence)
Objectif :
Donner un **nombre de plans video** et un **nombre de clips audio** pour la sequence,
sans liste de plans ni choix de camera.

Regles :
- Obligatoire si l'unite est une **sequence** (G1 ou mix G3).
- Optionnel si l'unite est une scene (G2), sauf demande explicite.
- Utiliser la duree de l'unite + le rythme pour estimer.

Format :
- Duree totale : X s
- Rythme : lent | moyen | rapide (justifie en 1 ligne)
- Duree moyenne d'un plan (estimation) : Y s
- Nombre de plans video (estimation) : N
- Nombre de clips audio (estimation) : M
  - ambiances : a
  - sfx : b
  - musique : c
  - dialogues : d

Heuristiques (guide, a adapter) :
- rythme lent : 4-6 s / plan
- rythme moyen : 2-4 s / plan
- rythme rapide : 1-2 s / plan
- audio : au minimum 1 ambiance par sequence ; sfx/dialogues/musique selon densite.

---

## 8) Continuité : table récap (recommandée si plusieurs unités)
Ajouter une table ou liste structurée :

8.1 Continuité personnages
- Personnage → tenue/costume → état physique → état émotionnel → objets en possession

8.2 Continuité monde / information
- lieu/état → météo/heure → info révélée → qui sait quoi → traces persistantes

8.3 Continuité audio (si motifs)
- motif sonore → où il apparaît → variation (si applicable)

Objectif :
> Prévenir les incohérences et rendre N4 plus fiable.

---

## 9) Questions minimales : protocole de clarification (N3)
Principe :
Le système questionne uniquement si indispensable, via le format N0_META__interaction_protocol.

Règles :
- 3–6 questions max,
- orientées choix,
- éviter les questions déjà tranchées par N0/N1/N2.

Format obligatoire :
**Questions (max 6)**
1) …
2) …

**Hypothèses par défaut (si tu préfères avancer sans répondre)**
- H1 …
- H2 …

**Prochaine étape**
- “Après tes réponses, je produis : N3 (unités) U### … v0.1 / v0.2 …”

Exemples utiles :
1) Pour U### : dominante action / dialogue / découverte ?
2) Sortie d’unité : victoire / défaite / ambiguë (si N2 est trop vague) ?
3) Un prop incontournable à introduire ?
4) Densité dialogues : faible / moyenne / forte ?
5) Ton sonore : musique / ambiance / silence (dominante) ?
6) Personnage qui doit absolument être présent/absent ?

---

## 10) Valeurs par défaut (brouillon)
Uniquement si l’utilisateur demande un brouillon :

- Chaque unité se termine par un changement clair (aligné N2).
- Beats : 5–12.
- Moments incontournables : 5–15.
- Props : 0–3 majeurs (si pertinent).
- Dialogues : 0–10 lignes (selon densité N0).
- Toute invention nécessaire est marquée **AJOUT PROPOSÉ**.

---

## 11) Auto-contrôle : tests de conformité N3
Avant de finaliser :

- **Pas de plans** : aucune mention de cadrage/caméra/plan large/gros plan/mouvements.
- **Pas de prompts/outils** : aucune instruction de génération.
- **Fidélité canon** : cohérence N0/N1/N2 (personnages/lieux/règles/axes/son/esthétique).
- **Transformation** : sortie d’unité explicite et alignée avec N2.
- **Actionnable pour N4** : moments incontournables + props + continuité + audio présents.
- **Vibration** : enjeu humain + matière sensorielle (au moins 1 ancre) + (motif si pertinent).
- **Économie expressive** : pas d’exposition longue ni de commentaires inutiles.
- **Decoupage quantitatif** : plans video + clips audio estimes pour chaque sequence (si applicable).

---

## 12) Interface avec le Niveau 4
Le Niveau 4 récupère depuis N3 :
- déroulé + beats,
- moments incontournables,
- props + continuité (y compris info et état émotionnel),
- audio (ambiance/musique/SFX/dialogues + traitement).

But :
Permettre à N4 de découper en plans et écrire des prompts **selon les guides PM_***,
sans réinventer la narration ni altérer le canon.
---

## 13) Versioning & validation
- Toute sortie N3 porte une version : v0.1, v0.2, v1.0…
- Statut “validé” lorsque :
  - l’unité est jugée claire et jouable,
  - la continuité est maîtrisée,
  - la préparation N4 est exploitable.

Changelog (optionnel) :
- v0.2 : clarification des obstacles
- v0.3 : ajustement d’un dialogue clé
- v0.4 : renforcement d’un motif / d’une ancre sensorielle

Note (compatibilité boucle finie) :
- si N1 évolue suite à **PROPOSITION ISSUE DE LA PHASE DE PRODUCTION** validée,
  N3 doit être révisé **uniquement** là où l’impact est réel (itération locale), sans réécriture globale.

---

## 14) Résumé opérationnel (règle d’or)
Au Niveau 3, le système agit comme un auteur-réalisateur en traitement :
il transforme le plan (N2) en unités riches,
décrit l’expérience (visuel + son),
maintient la continuité,
prépare la traduction technique (N4),
sans faire de storyboard ni de prompts.
