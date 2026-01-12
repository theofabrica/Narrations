🚦 Statut : Normatif (Niveau 5 — Prompts & Plans)

# N5_PROMPTS — Plans & Génération (à partir de la Timeline N4)

## 0) Fonction du Niveau 5
N5 traduit la **Timeline N4** (pistes V1/A1/A2/A3) et les unités N3 en **plans promp-tables** (image/vidéo/audio) conformes aux guides `PM_*`, sans modifier la narration.

Interdit cardinal :  
> N5 ne modifie jamais l’histoire. Il traduit et prépare la production.

## 1) Autorité (ordre)
1) N0_META__* (gouvernance / protocole)
2) CORE_NARRATIONS__principles_and_patterns.md
3) N1–N4 (cadre, bible, architecture, timeline)
4) PM_* (guides techniques) + SRC_* (références)

## 2) Dépendances
- **N0** : format, ratio, fps, durée, contraintes.
- **N1** : canon (personnages, monde, esthétique, audio macro).
- **N2** : ordre/fonction des unités.
- **N3** : scènes, beats, moments incontournables, continuité.
- **N4 Timeline** : pistes V1/A1/A2/A3, timecodes, source_ref.

## 3) Guides de prompting (obligatoires)
Uniquement les paramètres des fichiers :
- `PM_MIDJOURNEY__image_generation.txt`
- `PM_NANOBANANA__image_model.txt`
- `PM_KLING__v2_video_generation.txt`
- `PM_KLING__o1_video_generation.txt`
- `PM_ELEVENLABS__sound_design.txt`
- `PM_ELEVENLABS__music_generation.txt`

Règle :  
- Ne jamais inventer un paramètre.  
- Si absent du guide → laisser vide / marquer **[À VALIDER]**.  
- 1 prompt = 1 modèle = 1 guide (pas de mélange).

## 4) Workflow recommandé (hérite de N4 Timeline)
1) Image clé (Midjourney) → correction (Nanobanana)  
2) Vidéo (Kling v2 ou O1) à partir des frames/description de plan  
3) Audio : SFX/Ambiances (ElevenLabs sound design), Musique (ElevenLabs music), Voix (texte N3 exact, sinon **DIALOGUE À FOURNIR**)  
4) Sync : lier aux timecodes N4 (entrées/sorties, intensité) sans imposer de DAW.

## 5) Grammaire du plan (fiche plan)
Chaque plan `P###` contient :
- Réf unité : `U###` (+ beat `B#` si utile) et `source_ref` N4 quand présent
- Intention / Action
- Composition (sujets, décor clé)
- Mouvement (si vidéo, descriptif)
- Continuité : costumes/props/état + météo/heure
- Audio (4 couches) : ambiance, voix, SFX, musique

## 6) Heuristiques
- 1 beat ≈ 1–3 plans (adapter au rythme N0).
- Chaque “moment incontournable” N3 doit être couvert au moins une fois.
- S’appuyer sur les timecodes/segments N4 ; si un segment est vide, marquer **[INCOMPLET]**.

## 7) Gestion des manques
- Questions courtes (3 max) si info critique absente.  
- Sinon produire et marquer **[INCOMPLET]** ou **[À VALIDER]** sur l’hypothèse.
- Ne jamais ajouter d’événement pour combler un trou.

## 8) Prompts (par média)
- Image (Midjourney) : prompt, paramètres, négatifs, variantes (1–3).  
- Correction (Nanobanana) : instruction, paramètres, variantes (1–2).  
- Vidéo (Kling v2/O1) : prompt, paramètres (durée, ratio…), continuité.  
- SFX/Ambiances (ElevenLabs sound design) : prompt précis (source/texture/distance).  
- Musique (ElevenLabs music) : prompt + durée ; préciser “instrumental only” si aucune voix.  
- Voix : texte N3 sinon **DIALOGUE À FOURNIR**.

## 9) Sortie attendue (gabarit)
meta:
  niveau: 5
  document: N5_PROMPTS__plans_and_generation
  version: v0.1
  statut: propose | valide
  dependances:
    - N0:vX.Y
    - N1:vX.Y
    - N2:vX.Y
    - N3:vX.Y
    - N4:vX.Y

A) Résumé de production (ratio/fps/résolution, modèles utilisés)  
B) Index des plans : `P001 → U### (B#) / source_ref`  
C) Plans détaillés (fiche plan + prompts par média)  
D) (Optionnel) Rapport de résonance vers N1 (borné, sans appliquer)

## 10) Auto-contrôle N5
- Fidélité : aucun fait narratif modifié.  
- Couverture : moments incontournables N3 couverts ; segments N4 exploités.  
- Continuité : costumes/props/états cohérents.  
- Conformité : prompts conformes aux PM_*.  
- Producibilité : un opérateur peut exécuter sans deviner.
