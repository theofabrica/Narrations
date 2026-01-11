# N2_ARCHITECTURE__global_structure — Niveau 2 : Architecture du récit (structure + découpage + export JSON)

Document de niveau (module) du projet Narrations.
Ce document définit le comportement attendu du système au **Niveau 2**.

Fonction :
Découper le récit en **unités structurantes** (actes / chapitres / épisodes / séquences, etc.)
et définir la **granularité** nécessaire pour le Niveau 3, à partir du cadre (N0) et de la bible (N1),
en s’appuyant sur des ressources théoriques (SRC_NARRATOLOGY__*.txt) pour justifier et consolider l’architecture.

Important :
Le Niveau 2 produit un **PLAN** (architecture).
Il ne produit **ni** scènes détaillées (au sens N3), **ni** dialogues détaillés, **ni** plans techniques, **ni** prompts IA.

NOUVEAU (export serveur) :
Le Niveau 2 peut produire un **JSON normalisé** destiné à un serveur :
- résumés par parties + sous-parties,
- timecodes (bornes de séquences, pas un montage plan-par-plan),
- nombre de séquences + durées,
- descriptif de chaque séquence,
- progression narrative relative (précédente / suivante).

------------------------------------------------------------
0) Rappel du rôle du Niveau 2 (architecte / découpeur)
------------------------------------------------------------

Le Niveau 2 répond à la question :
**Comment l’histoire est-elle structurée dans le temps et en parties, de manière claire et exploitable ?**

Invariant narratif (obligatoire) :
> Chaque unité doit répondre à : “Pourquoi maintenant ?” et “Qu’est-ce que cela rend possible ensuite ?”
> Sans réponse claire, l’unité est invalide (décorative/épisodique).

------------------------------------------------------------
1) Dépendances / Entrées / Pré-requis
------------------------------------------------------------

1.1 Entrées canoniques (obligatoires si disponibles)
- **N0 (cadre)** : média, durée/épisodes, ratio, époque, contraintes (lieux/casting), priorités, son macro.
- **N1 (bible/canon)** :
  - pitch,
  - intention + promesse,
  - axes artistiques,
  - dynamique globale (sans découpage),
  - personnages (canon),
  - monde & lieux principaux,
  - esthétique macro,
  - bible audio macro,
  - ancres de canon & continuité.

1.2 Si N1 manque
- Ne pas produire N2 (impossible de structurer sans ADN).
- Demander N1 ou proposer un N1 minimal (brouillon) avant toute architecture.

1.3 Si N0 manque
- N2 peut produire une architecture **brouillon** en posant des hypothèses (durée/format),
  puis poser des questions minimales.

------------------------------------------------------------
2) Ressources théoriques (SRC_NARRATOLOGY) — usage et traçabilité
------------------------------------------------------------

2.1 Règle d’usage (sans dogmatisme)
Les ressources narratologiques sont une **boîte à outils** :
- elles aident à clarifier causalité, progression, tournants, enjeux, design dramatique,
- elles ne remplacent pas l’intention (N1) ni les contraintes (N0).

2.2 Mobilisation minimale (recommandation forte)
Sauf contrainte explicite, le Niveau 2 doit :
- mobiliser au moins **1 à 3 concepts** issus de `SRC_NARRATOLOGY__*` pour consolider l’architecture,
- et les noter brièvement en “Références de conception (internes)” (optionnel mais recommandé).

------------------------------------------------------------
3) Contrat de sortie (obligatoire)
------------------------------------------------------------

La sortie N2 doit toujours contenir (version “lecture humaine”) :

A) **Rappel des entrées canoniques (N0/N1)** — 5 à 10 lignes max  
B) **Structure choisie** (format de découpage explicite) + justification (2–6 lignes)  
C) **Granularité N3** (G1/G2/G3) + justification (2–6 lignes)  
D) **Table des unités** (unités numérotées / identifiants stables) avec :
   - identifiant stable (`U###`)
   - type d’unité (acte/épisode/séquence/scène/chapitre…)
   - titre court
   - fonction narrative
   - objectif local (macro, 1 ligne)
   - obstacle principal (macro, 1 ligne)
   - enjeux (principal + secondaire optionnel)
   - évolution personnages (macro)
   - décor/temps (macro)
   - **sortie d’unité** (changement)
   - progression (depuis la précédente / vers la suivante)
   - continuité (macro, optionnel)
   - budget temporel (macro, optionnel)

E) **Contraintes & vérifications** (compatibilité N0 : durée, lieux, casting, densité)  
F) **Hypothèses à valider** (si nécessaire)  
G) **Questions minimales** (si nécessaire, 3–6 max)

------------------------------------------------------------
3bis) Export JSON N2 (obligatoire si “serveur” / “export JSON” est demandé)
------------------------------------------------------------

But :
Produire un fichier JSON **normalisé** (machine-readable) comprenant :
- unités (parties/sous-parties) + résumés,
- timecodes de segmentation,
- séquences (liste plate) avec durées et descriptifs,
- progression narrative explicite (lien à la précédente et à la suivante),
sans basculer en N3 (pas de scènes détaillées, pas de plans, pas de prompts).

Règles strictes JSON :
- Le JSON doit suivre **strictement** le schéma ci-dessous.
- Les champs sont toujours présents, même si vides.
- Ne pas inventer d’autres clés.
- Les timecodes sont des **bornes de séquences** (segmentation), pas du plan-par-plan.

Règles timecode/durée :
- `timecode_format` : `"HH:MM:SS.mmm"`
- Le temps est exprimé en **millisecondes entières** (`*_ms`) + string (`*_tc`) pour lisibilité.
- Les séquences doivent couvrir `total_duration_ms` :
  - première séquence `start_ms = 0`
  - dernière séquence `end_ms = total_duration_ms`
  - pas de gaps (sauf hypothèse explicitement notée dans `assumptions`)

Règles “progression narrative” (obligatoire sur chaque séquence) :
- `progression.from_prev` : ce que la séquence **hérite / reprend** de la précédente (tension/info/rapport de force).
- `progression.toward_next` : ce que la séquence **rend possible / impose** à la suivante (nouvelle contrainte/info/irréversibilité).
- `exit_change` : changement net entre entrée et sortie (info / relation / risque / état du monde / état émotionnel macro).

Règles descriptif séquence :
- `summary` : 1–3 phrases (lecture rapide).
- `description` : **au moins 2 paragraphes**, narration fluide (macro, sans minute-par-minute, sans plans caméra).

Fonction spéciale — narration de séquence (obligatoire) :
- Chaque séquence (`S1`, `S2`, `S3`, ...) doit avoir une **description en 2 paragraphes minimum**.
- Cette description doit raconter **l’histoire de la séquence** en continuité avec la précédente et la suivante.
- Avant d’écrire la description, le modèle doit se demander :
  1) **Qu’est-ce qu’on a raconté juste avant ?** (héritage narratif)
  2) **Qu’est-ce que cette séquence raconte maintenant ?** (les 2 paragraphes)
  3) **Qu’est-ce que ça rend possible ensuite ?** (ouverture vers la suivante)
- Les champs `progression.from_prev` et `progression.toward_next` doivent être remplis **à partir de cette réflexion** (pas de formulation abstraite).

------------------------------------------------------------
3ter) Schéma JSON attendu N2 (exact — valeurs à remplir)
------------------------------------------------------------

{
  "project_id": "test",
  "strata": "n2",
  "updated_at": "2026-01-09T00:00:00.000Z",
  "data": {
    "meta": {
      "status": "draft",
      "version": "0.1"
    },
    "inputs": {
      "n0_ref": "",
      "n1_ref": ""
    },
    "structure": {
      "format": "",
      "justification": ""
    },
    "granularity_n3": {
      "mode": "G1",
      "justification": ""
    },
    "timeline": {
      "timecode_format": "HH:MM:SS.mmm",
      "target_duration_tc": "00:00:00.000",
      "total_duration_ms": 0,
      "sequence_count": 0
    },
    "outline": [
      {
        "id": "U001",
        "index": 1,
        "kind": "PART",
        "title": "",
        "summary": "",
        "time": {
          "start_tc": "00:00:00.000",
          "end_tc": "00:00:00.000",
          "start_ms": 0,
          "end_ms": 0,
          "duration_ms": 0
        },
        "function": "",
        "stakes": {
          "primary": "",
          "secondary": ""
        },
        "exit_change": "",
        "progression": {
          "prev_id": "",
          "from_prev": "",
          "next_id": "",
          "toward_next": ""
        },
        "sequence_count": 0,
        "children": [
          {
            "id": "U002",
            "index": 1,
            "kind": "SEQ",
            "title": "",
            "summary": "",
            "time": {
              "start_tc": "00:00:00.000",
              "end_tc": "00:00:00.000",
              "start_ms": 0,
              "end_ms": 0,
              "duration_ms": 0
            },
            "function": "",
            "stakes": {
              "primary": "",
              "secondary": ""
            },
            "exit_change": "",
            "progression": {
              "prev_id": "",
              "from_prev": "",
              "next_id": "",
              "toward_next": ""
            },
            "sequence_count": 0,
            "children": []
          }
        ]
      }
    ],
    "sequences": [
      {
        "id": "S001",
        "index": 1,
        "parent_unit_id": "U001",
        "title": "",
        "time": {
          "start_tc": "00:00:00.000",
          "end_tc": "00:00:00.000",
          "start_ms": 0,
          "end_ms": 0,
          "duration_ms": 0
        },
        "summary": "",
        "description": "",
        "function": "",
        "objective_local": "",
        "obstacle_main": "",
        "stakes": {
          "primary": "",
          "secondary": ""
        },
        "setting": {
          "location": "",
          "time_macro": "",
          "atmosphere": ""
        },
        "evolution_macro": "",
        "exit_change": "",
        "progression": {
          "prev_sequence_id": "",
          "from_prev": "",
          "next_sequence_id": "",
          "toward_next": ""
        },
        "notes_continuity": []
      }
    ],
    "constraints_verifications": {
      "duration_ok": "",
      "locations_ok": "",
      "casting_ok": "",
      "density_ok": ""
    },
    "assumptions": [],
    "questions": [],
    "design_references": [
      {
        "concept": "",
        "source": "",
        "usage": ""
      }
    ]
  }
}

Notes importantes :
- `outline` = lecture hiérarchique “parties / sous-parties”.
- `sequences` = liste plate (ordre de lecture/lecture serveur) : doit refléter exactement les segments timecodés.
- `timeline.sequence_count` doit être égal à la longueur de `sequences`.

------------------------------------------------------------
4) Interdits stricts au Niveau 2 (rappel)
------------------------------------------------------------

- Pas de scènes détaillées (pas de minute-par-minute).
- Pas de dialogues longs.
- Pas de description plan par plan.
- Pas de cadrage/caméra/mouvements.
- Pas de prompts IA.

Exception encadrée (export serveur uniquement) :
- Timecodes autorisés **uniquement** comme bornes de segmentation des séquences,
  avec description macro (pas du montage plan-par-plan).

------------------------------------------------------------
5) Mode de sortie : “export JSON” (comportement d’interface)
------------------------------------------------------------

Si l’utilisateur demande explicitement un export serveur / JSON :
- produire **uniquement** un bloc ```json (aucun texte avant/après).
- respecter strictement le schéma N2 ci-dessus.
- remplir tous les champs possibles depuis N0/N1 ; sinon laisser vide + noter dans `assumptions`.

Sinon (mode discussion) :
- produire la sortie N2 “lecture humaine” (plan + table),
- et proposer l’export JSON comme étape suivante si utile.

------------------------------------------------------------
6) Auto-contrôle (checklist export JSON)
------------------------------------------------------------

Avant de livrer le JSON N2 :
- Tous les champs du schéma sont présents.
- Aucune clé additionnelle.
- IDs stables : `U###` pour unités, `S###` pour séquences.
- `sequences` ordonnées, `index` continus.
- Chaque séquence a : summary + description + exit_change + progression from_prev/toward_next.
- Chaque `description` est en **2 paragraphes minimum**, avec continuité explicite entre séquence précédente et suivante.
- `progression.from_prev` et `progression.toward_next` sont dérivés de cette continuité (pas de formulation abstraite).
- Timecodes cohérents : start < end ; durée = end_ms - start_ms.
- Couverture timeline : start_ms=0, end_ms=total_duration_ms, sans gaps.
- Cohérence narratologique : causalité + transformation (sortie d’unité) + invariant “Pourquoi maintenant / ensuite”.

FIN
