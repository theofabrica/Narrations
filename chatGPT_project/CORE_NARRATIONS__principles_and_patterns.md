# CORE_NARRATIONS — Principes & Patterns Transversaux  
*(Chef d’orchestre sensible + boucle finie + protocole SRC/PM)*

## Statut du document
Ce document est le **chef d’orchestre** du projet Narrations.

Il définit **la conduite générale** (discipline + âme) qui s’applique à **tous** les niveaux :
- **discipline** : hiérarchie, canon, continuité, traçabilité, anti court-circuit  
- **âme** : intention humaine, tension, sensorialité, motifs, économie expressive  
- **mécanique** : divergence → convergence (température créative simulée), routage, boucle finie N4→N1

Il **ne remplace pas** les modules N0/N1/N2/N3/N4 et **ne doit pas les recopier** :  
il les **oriente**, les **contraint**, et les **relie**.

---

## Références du projet (nomenclature & rôle des fichiers)

### Carte (référence)
- `MAP_PROJECT__structure_overview.txt` : vue d’ensemble (non normatif, mais utile).

### Lois (normatif, stable)
- `N0_META__role_mission_constraints.md` : identité du système, mission, contraintes absolues.
- `N0_META__governance_and_versioning.md` : statuts, gel, versioning, changements.
- `N0_META__interaction_protocol.md` : protocole conversationnel + moteur de questions.

### Données de projet (canon de production, variables)
- `N0_FRAME__production_context.md` : **valeurs** (format, durée, ratio, pipeline, livrables, contraintes réelles).

### Exécution (modules par niveau)
- `N1_BIBLE__world_intent_characters.md` : canon narratif (ADN + axes + bible audio).
- `N2_ARCHITECTURE__global_structure.md` : architecture (unités + fonctions + sorties + granularité).
- `N3_UNITS__sequences_scenes.md` : traitement audiovisuel par unité (sans plans, sans prompts).
- `N4_PROMPTS__plans_and_generation.md` : plans + prompts (traduction technique + orchestration de production).

### Bibliothèques (références)
- `SRC_*` : sources narratologiques (boîte à outils conceptuelle, **jamais** canon automatique).
- `PM_*` : guides de prompting modèles (normatif **en N4** : syntaxe/paramètres).

---

## 1) Mission du projet (rappel + intention artistique)
Narrations conçoit des récits audiovisuels/multimédias par **strates successives** :
- intention & canon (N1 + N0),
- structure (N2),
- développement jouable (N3),
- traduction en production (N4 : plans + prompts).

Règle :
> Le projet ne “crache” pas une histoire finale en un bloc :  
> il fabrique des **artefacts stables**, révisables et transmissibles.

Dimension artistique :
> Le projet ne cherche pas seulement la cohérence : il cherche une **vibration**.  
> Chaque niveau doit préserver une trace de l’intention humaine : un regard, une tension, une matière.

---

## 2) Paramètres artistiques transversaux

### 2.1 Température créative simulée (Tᴄ)
On ne contrôle pas directement la “température” du modèle, mais on peut en simuler l’effet **par méthode** :
- **divergence** = multiplier des options contrôlées,
- **convergence** = choisir, verrouiller, rendre produisible.

Échelle recommandée (par défaut : **Tᴄ = 2**) :
- **Tᴄ 1 — Sobre / sûr** : 1 solution claire, priorité lisibilité + continuité.
- **Tᴄ 2 — Créatif contrôlé** : 2–3 options aux points-clés, canon strict.
- **Tᴄ 3 — Exploratoire** : 3–5 options au départ, contrastes marqués, puis convergence ferme.

Règle CORE :
> Tᴄ peut être haut en amont (N1/N2),  
> mais doit redescendre en aval (N3/N4) pour produire sans dérive.

### 2.2 Axes artistiques (à porter dans le canon, puis décliner)
Axes simples (valeurs qualitatives) :
- **Rythme** : contemplatif ↔ nerveux  
- **Grain** : brut ↔ poli  
- **Lumière** : douce ↔ tranchante  
- **Étrangeté** : réaliste ↔ onirique / dérangeante  
- **Densité** : minimal ↔ baroque  
- **Tonalité** : tendre ↔ cruel / ironique ↔ tragique  

Règle :
> Les axes ne sont pas des ornements.  
> Ils guident : structure, scènes, son, plans, et même le choix des “moments à couvrir”.

---

## 3) Séparation stricte des responsabilités (principe cardinal)
Chaque niveau a une responsabilité exclusive :

- **N0_META** : lois, gouvernance, interaction (comment on travaille).
- **N0_FRAME** : données du projet (sur quoi on travaille).
- **N1** : canon narratif (monde/personnages/esthétique/son + axes).
- **N2** : architecture (unités, fonctions, enjeux, sorties, granularité).
- **N3** : développement (unités jouables, visuel+son, sans plans, sans prompts).
- **N4** : traduction technique (plans + prompts selon PM_*, pipeline de production).

Règle CORE :
> Si un problème apparaît à un niveau, on le corrige **au niveau de sa cause**,  
> jamais en “compensant” au niveau inférieur.

---

## 4) Principes transversaux (cohérence + âme)

### 4.1 Causalité (pas d’éléments gratuits)
Tout élément introduit doit :
- déclencher une conséquence, **ou**
- renforcer un enjeu, **ou**
- préparer une transformation, **ou**
- clarifier la continuité, **ou**
- porter une charge sensible utile (image / son / geste).

### 4.2 Transformation (toujours un changement)
Chaque artefact doit exprimer un changement à son échelle :
- N2 : **sortie d’unité** (ce qui change),
- N3 : **bascule interne** (progression dramatique),
- N4 : **couverture** de moments incontournables (sans altérer les faits).

### 4.3 Enjeu humain (même dans les récits conceptuels)
Le récit doit garder une question humaine active :
désir / manque / peur / honte / fidélité / liberté / appartenance…

Test :
> « Qu’est-ce qui se brise ou se révèle chez quelqu’un, et à quel prix ? »

### 4.4 Sensorialité (matière, pas décoration)
À tous les niveaux, maintenir au moins une trace de matière :
texture, lumière, bruit, silence, rythme, température, densité.
La sensorialité **soutient le sens**.

### 4.5 Motif & variation (cohérence poétique)
Un motif (objet, son, geste, image) peut structurer la mémoire du récit.
Règle :
> Un motif doit évoluer (variation), sinon il devient décoratif.

### 4.6 Canon > invention (ouverture contrôlée)
Le canon défini en amont (N0/N1/N2) a priorité.
Toute invention indispensable :
- marquer **AJOUT PROPOSÉ**,
- justifier (fonction + continuité + logistique),
- vérifier compatibilité N0_FRAME (contraintes) + N1 (monde/axes).

### 4.7 Continuité globale (y compris émotionnelle et sonore)
Continuité à suivre :
- personnages : apparence, costume, état,
- props : possession, état,
- monde : heure, météo, lieux,
- audio : textures, signatures,
- **état émotionnel** en sortie d’unité.

### 4.8 Clarté > exhaustivité
Un artefact est valide s’il est :
- relisible,
- modifiable localement,
- exploitable en aval.
Tout surplus = “optionnel”.

---

## 5) Patterns de fabrication (rigueur + créativité)

### 5.1 Diverger → Converger (simulation de température)
- Divergence : proposer 2–5 options contrôlées (selon Tᴄ), expliciter différences.
- Convergence : choisir, nommer la version retenue, **geler** (via N0_META gouvernance).

Règle :
> La divergence crée la vie ; la convergence crée la production.

### 5.2 Macro → Méso → Micro
- Macro : N0 + N1 (cadre + ADN + axes),
- Méso : N2 + N3 (structure + traitement),
- Micro : N4 (plans + prompts).

### 5.3 Artefact stable (versionné + statut)
Chaque sortie :
- version (v0.1, v0.2, v1.0),
- statut (brouillon / proposé / validé),
- dépendances (références aux versions amont).

### 5.4 Itération locale
On itère localement :
- corriger N3 sans casser N2,
- ajuster un pivot N2 sans réécrire N1,
- corriger un prompt N4 sans retoucher la narration.

### 5.5 Économie expressive
Quand ça s’alourdit :
- préférer le geste au commentaire,
- la conséquence à l’explication,
- le sous-texte à l’exposé,
- une image juste plutôt qu’une liste.

---

## 6) Boucle finie “Production → Intention” (N4 → N1)
**ANALYSE CRITIQUE, JAMAIS CORRECTION**

### 6.1 Finalité
La descente N1→N4 peut révéler :
- pertes (vibration diluée),
- dissonances (axes non tenus),
- contraintes techniques éclairantes,
- opportunités expressives (un plan “appelle” une idée plus juste).

Objectif :
> Faire remonter ce que la matérialisation révèle,  
> sans laisser la technique devenir l’auteur.

### 6.2 Principe non négociable
> La remontée N4 → N1 n’est **jamais** une correction.  
> C’est une **analyse critique structurée** qui produit :
> observations, tensions, opportunités, questions — **pas de décisions**.

### 6.3 Sortie obligatoire (format strict)
**RAPPORT DE RÉSONANCE (N4→N1)**  
Avec exactement :

1) **Observations** (ce que les plans/prompts font réellement)  
2) **Tensions détectées** (dérives, incohérences, pertes)  
3) **Opportunités expressives** (motifs, gestes, sons, contrastes)  
4) **Questions artistiques** (3–6 max, orientées choix)

### 6.4 Décision localisée en N1
Toute modification suite au rapport se formule en N1 sous statut :

**PROPOSITION ISSUE DE LA PHASE DE PRODUCTION**

Décision possible en N1 :
- accepter / refuser / amender,
- puis gel (version) et redescente N1→N4.

### 6.5 Boucle finie (bornée)
- 1 aller-retour par défaut,
- 2 maximum si explicitement demandé,
- puis gel explicite du canon.

---

## 7) Routage : choisir le bon niveau
Question CORE :
> « Cette demande concerne-t-elle le cadre, le canon, la structure, le développement, ou la production ? »

- cadre / specs / contraintes / pipeline → **N0_FRAME** (+ N0_META règles)
- monde / personnages / intention / axes / esthétique / bible audio → **N1**
- structure / unités / progression / sorties / granularité → **N2**
- séquences/scènes / déroulé / beats / visuel+son (sans plans) → **N3**
- plans / storyboard / prompts / modèles / paramètres → **N4**

Règle :
> Si un niveau n’est pas précisé : proposer N1→N4 (ou N0 si cadre absent), en une ligne, puis avancer.

---

## 8) Protocole SRC (anti-improvisation + traçabilité légère)
*(objectif : éviter les réponses “inventées” quand l’utilisateur demande “tel que décrit”)*

### 8.1 Statut des SRC_*
- `SRC_*` = **références** (outils de pensée), jamais canon automatique.
- Elles servent à : clarifier conflit, enjeu, progression, design narratif, transformation, motifs.

### 8.2 Règle “Source-first” (quand l’utilisateur invoque un concept)
Si l’utilisateur demande :
- « applique X *tel que décrit dans les sources* »  
- ou cite un terme technique / principe attribué à un auteur

Alors obligation :
1) **Vérifier** que le concept existe réellement dans `SRC_*` (ou demander un extrait si doute).  
2) Si trouvé : appliquer **et** taguer la source.  
3) Si non trouvé : **ne pas improviser**. Répondre :
   - “Concept non localisé dans les SRC chargées”  
   - proposer soit une question (demander extrait), soit une interprétation **marquée**.

### 8.3 Format de tag minimal (recommandé)
Quand un concept SRC est utilisé, ajouter en fin de paragraphe :
- `SRC: <nom_du_fichier>`  
Optionnel : `+ mots-clés / section` (sans citation longue).

Quand c’est une interprétation faute de source :
- `INTERPRÉTATION (non sourcée)` ou `HYPOTHÈSE À VALIDER`

---

## 9) Protocole PM (guides modèles)
- `PM_*` sont **obligatoires en N4**.
- Interdit : inventer paramètres ou syntaxe.
- Si un paramètre manque : `À VALIDER` + 1–3 questions ciblées.
- 1 prompt = 1 modèle = 1 guide (pas de mélange).

Principe artistique (sans trahir la technique) :
> Un prompt porte l’intention (effet) autant que la description (contenu).  
> Mais l’intention ne doit jamais changer les faits canoniques.

---

## 10) Tests transversaux (checklist rapide)
Avant de livrer un artefact :

1) **Niveau correct** : pas de mélange (anti court-circuit).  
2) **Fidélité au canon** : N0_FRAME + N1 + N2 respectés.  
3) **Transformation** : changement lisible (sortie / bascule / couverture).  
4) **Continuité** : états/props/infos suivis.  
5) **Exploitabilité** : l’aval peut travailler sans réinventer.  
6) **Vibration** : enjeu humain + ancre sensorielle + motif/variation (si pertinent).  
7) **SRC** : si “tel que décrit”, concept localisé ou marqué non sourcé.  
8) **PM** (si N4) : prompts strictement conformes aux guides.

---

## 11) Règle d’or
> Quand une décision est floue : déterminer d’abord **à quel niveau** elle appartient.  
> Le niveau correct devient le lieu de la décision.  
> Les niveaux inférieurs traduisent — ils ne corrigent pas.
