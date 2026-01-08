# N0_FRAME__production_context — Cadre de production du projet

## Statut du document
Ce document **décrit les paramètres concrets du projet en cours** (spécifications et contraintes de production).  
Il ne définit pas des lois : il fournit des **valeurs** (données) que les niveaux N1–N4 doivent respecter.

- **N0_META__*** = règles, gouvernance, protocole (stable)
- **N0_FRAME__production_context** = **données de production** (peuvent changer d’un projet à l’autre)

Autorité :
1) `N0_META__*` (règles / gouvernance / interaction)
2) `CORE_NARRATIONS__principles_and_patterns.md` (orchestration transversale)
3) `N0_FRAME__production_context.md` (ce document : données du projet)
4) `N1–N4` (exécution)
5) `PM_*` et `SRC_*` (guides & références)

---

## Meta (recommandé)
meta:
  niveau: 0
  document: N0_FRAME__production_context
  version: v0.1
  statut: brouillon | proposé | validé | gelé
  date: YYYY-MM-DD
  propriétaire: FXC
  projet: Narrations
  dépendances:
    - N0_META__role_mission_constraints
    - N0_META__interaction_protocol
    - N0_META__governance_and_versioning

---

## 1) Résumé de production (1 écran max)
Objectif :
Donner aux niveaux N1–N4 une lecture immédiate des contraintes “réelles”.

- Type de production : [film | série | animation | clip | BD | prototype | autre]
- Durée cible : [ex: 3–5 min | 12 min | 90 min | N/A]
- Format de sortie principal : [vidéo + stems audio | images + audio optionnel | storyboard | moodboard]
- Ratio / cadrage : [16:9 | 9:16 | 1:1 | 2.39:1 | À VALIDER]
- Réalisme / style global : [photoréaliste | stylisé | animation 2D | hybride | À VALIDER]
- Époque représentée (macro) : [À VALIDER]  
- Priorités : [cohérence visages | cohérence costumes | atmosphère sonore | vitesse | qualité | autre]

---

## 2) Livrables attendus
> Définir ce qui doit être “livré” en fin de chaîne, et dans quel niveau de finition.

### 2.1 Livrables visuels
- [ ] Images fixes (frames clés / storyboard)
  - quantité cible : [ex: 15–60]
  - usage : [moodboard | storyboard | frames finales | autre]
- [ ] Vidéos / clips
  - quantité cible : [ex: 5–30 plans animés]
  - durée totale vidéo : [ex: 60–180 s | À VALIDER]
  - niveau de finition : [prototype | final | test style]

### 2.2 Livrables audio (stems)
- [ ] DIALOGUE (voix) : [oui/non]  
- [ ] AMBIANCE (bed) : [oui/non]
- [ ] SFX (effets) : [oui/non]
- [ ] MUSIQUE (instrumental) : [oui/non]

Règle recommandée :
> Audio en **pistes séparées** (stems) pour permettre une synchro/mix final.

### 2.3 Finalisation (optionnelle dans le projet)
- Synchronisation audio/vidéo : [oui/non]
- Mixage final : [oui/non]
- Étalo / finition colorimétrique : [oui/non]

---

## 3) Spécifications techniques (À VALIDER si inconnu)

### 3.1 Vidéo
- Ratio : [16:9 | 9:16 | 2.39:1 | …]
- Résolution cible : [ex: 1920x1080 | 3840x2160 | À VALIDER]
- FPS cible : [ex: 24 | 25 | 30 | À VALIDER]
- Durée moyenne des plans (heuristique) : [2–6 s | À VALIDER]
- Style de mouvement : [stable | handheld | ciné | stylisé | À VALIDER]

### 3.2 Image (si image-first)
- Ratio : [idem vidéo ou différent]
- Taille / définition : [À VALIDER]
- Niveau de détail : [faible | moyen | élevé]

### 3.3 Audio
- Format d’export souhaité : [wav | mp3 | À VALIDER]
- Sample rate / bit depth : [À VALIDER]
- Contraintes de voix : [voix off | dialogues | minimal | aucun]
- Contraintes musique : [ponctuelle | continue | minimale | absente]

---

## 4) Contraintes de production (pragmatiques)
> Ces contraintes influencent directement N2/N3/N4 (planification, continuité, prompter).

- Nombre max de lieux distincts : [À VALIDER]
- Nombre max de personnages “actifs à l’écran” : [À VALIDER]
- Complexité décor : [faible | moyen | élevé]
- Variations de costumes : [faible | moyen | élevé]
- Effets (pluie, fumée, foule, véhicules, créatures…) : [liste + niveau]
- Interdits de prod (s’il y en a) : [ex: pas de foule / pas de nuit / pas d’enfants / etc.]

---

## 5) Direction artistique macro (sans prompts)
> Ici on pose des **lignes de production**, pas des détails narratifs.

- Type visuel : [photoréaliste / stylisé / animation / hybride]
- Grain / texture : [brut ↔ poli]
- Lumière : [douce ↔ tranchante]
- Palette (3–7 couleurs en mots) : [ex: ocre, bleu pétrole…]
- Densité de décor : [minimal ↔ baroque]
- Références d’atmosphère (sans artistes protégés) : [2–6 lignes max]

---

## 6) Direction sonore macro (sans timecodes)
> Le son ici est une “charte” : densité, rôle, signatures.

- Densité dialogues : [faible | moyenne | forte]
- Place musique : [absente | rare | ponctuelle | présente]
- Place ambiance : [faible | moyenne | forte]
- Signatures sonores souhaitées : [liste courte]
- Silence / respiration : [rare | stratégique | fréquent]

---

## 7) Pipeline outillage (standard du projet)
Ce pipeline guide N4. Il peut être ajusté, mais doit être **déclaré** ici.

### 7.1 Visuels — pipeline par défaut
1) **Midjourney** : images sources (frames clés / looks)
2) **Nano Banana** : corrections & cohérence (visages, mains, continuité)
3) Vidéo :
   - **Kling v2** : animation à partir d’images (image → vidéo)
   - **OU Kling O1** : vidéo à partir d’éléments descriptifs (si besoin)

Décision par défaut :
- Mode vidéo principal : [Kling v2 | Kling O1 | mix | À VALIDER]
- Règle de choix (recommandée) :
  - **Kling v2** si on veut préserver la continuité depuis une image source,
  - **Kling O1** si on veut plus de “génération” (mouvement/caméra) tout en restant canon.

### 7.2 Audio — stems séparés
- **ElevenLabs** :
  - Sound design : AMB + SFX
  - Music : MUSIQUE (instrumental recommandé)
  - Dialogues/voix : selon besoins du récit (texte canon si fourni en N3)

Règle projet :
> La musique est **instrumentale** sauf décision explicite contraire.

### 7.3 Synchronisation finale (option)
- Méthode : [notes de sync / tableau plan→stems / autre]
- Qui synchronise/mixe : [humain | workflow externe | À VALIDER]
- Niveau de précision : [macro (entrées/sorties) | micro (timecodes) | À VALIDER]

---

## 8) Conventions d’assets (naming & versioning)
Objectif :
Éviter les confusions et permettre l’itération locale (N4 corrige sans casser N3).

Recommandé :
- `IMG_P001_MJ_v01` (image Midjourney)
- `IMG_P001_NB_v01` (image corrigée Nanobanana)
- `VID_P001_KLV2_v01` (vidéo Kling v2)
- `VID_P001_KLO1_v01` (vidéo Kling O1)
- `AUD_P001_DIA_v01` (dialogue / voix)
- `AUD_P001_AMB_v01` (ambiance)
- `AUD_P001_SFX_v01` (SFX)
- `AUD_U003_MUS_v01` (musique plutôt par unité/séquence)

Règle :
- `v01, v02…` = itérations.
- Ne remplacer jamais silencieusement : conserver une trace (mini-changelog).

---

## 9) Hypothèses et champs à valider
> Tout ce qui est flou doit être visible, pas implicite.

- [À VALIDER] ratio : …
- [À VALIDER] fps : …
- [À VALIDER] résolution : …
- [À VALIDER] durée totale : …
- [À VALIDER] nombre de lieux max : …
- [À VALIDER] densité dialogues : …
- [À VALIDER] mode vidéo : Kling v2 / O1 / mix

---

## 10) Questions minimales (si ce cadre est incomplet)
> 6 questions max par tour, orientées choix.

1) Média / livrable principal : vidéo, images, ou mix ?
2) Ratio : 16:9 / 9:16 / 2.39:1 ?
3) FPS : 24 / 25 / 30 ?
4) Durée totale cible : … ?
5) Dialogue : faible / moyen / fort ?
6) Vidéo : pipeline Kling v2 (image→vidéo) / Kling O1 (desc→vidéo) / mix ?

---

## 11) Mini-changelog (optionnel)
- v0.2 : changement ratio
- v0.3 : passage vidéo-only → mix images+vidéo
- v0.4 : modification contraintes lieux/casting
