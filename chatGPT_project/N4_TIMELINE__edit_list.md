🚦 Statut : Normatif (Niveau 4 — Timeline)

# N4_TIMELINE — Edit list structurée (V1/A1/A2/A3)

## 0) Fonction
Le N4 “Timeline” construit une **edit list temporelle** à partir de N2 (architecture) et N3 (scènes), sans réécrire l’histoire. Il produit des **pistes** (V1, A1, A2, A3) composées de **segments timecodés** pour préparer la génération et l’assemblage des médias.  
N4 Timeline est l’entrée obligatoire du N5 Prompts (ex-N4).

## 1) Dépendances
- **N0** : format, ratio, fps, durée cible, contraintes de média.
- **N1** : canon (personnages, monde, esthétique, audio macro).
- **N2** : ordre, durées, fonctions, sorties d’unités (actes/séquences).
- **N3** : scènes, beats, moments incontournables, continuité (visuel/audio).

## 2) Pistes et segments
- Pistes obligatoires :
  - `V1` (vidéo)
  - `A1` (dialogue/voix)
  - `A2` (SFX/ambiances)
  - `A3` (musique)
- Chaque piste contient des **segments** `{id, label, start_tc, end_tc, duration_ms, source_ref, notes}`.
- `source_ref` pointe vers un `U###` (acte/séquence/scene) ou `B#` (beat) quand utile.
- Règle de timecode : `HH:MM:SS.mmm`; le premier segment commence à `00:00:00.000`.
- Pas de gaps : les segments d’une même piste se succèdent ou se chevauchent explicitement selon le besoin (crossfade audio possible).

## 3) Alignement temporel
- La somme des segments vidéo doit couvrir la durée cible (N0/N2).  
- Les segments audio peuvent chevaucher (A1/A2/A3) mais doivent rester calés sur la timeline globale.  
- Si N2/N3 donnent des durées différentes, documenter l’hypothèse et marquer **[À VALIDER]**.

## 4) Couverture narrative
- Chaque séquence/scène N3 marquée “incontournable” doit avoir au moins un segment vidéo associé.  
- Les beats critiques (N3) se reflètent par un segment (ou un marqueur) sur V1 et, si pertinent, sur A1/A2/A3.
- N4 Timeline **ne crée pas de nouveaux événements** : il ne fait que minuter l’existant.

## 5) Notes audio
- `A1` : dialogues/voix (utiliser le texte N3 tel quel, sinon **DIALOGUE À FOURNIR**).  
- `A2` : ambiances + SFX (liées aux lieux/actions).  
- `A3` : musique (intention, montée/descente, entrées/sorties).

## 6) Export JSON attendu (gabarit)
```json
{
  "project_id": "demo",
  "strata": "n4",
  "updated_at": "2026-01-12T00:00:00.000Z",
  "data": {
    "meta": {
      "status": "draft",
      "version": "0.1",
      "dependencies": { "n2": "v1.0", "n3": "v0.1" }
    },
    "tracks": [
      {
        "id": "V1",
        "type": "video",
        "label": "Video 1",
        "segments": [
          {
            "id": "SEG001",
            "label": "Arrivée mascotte",
            "start_tc": "00:00:09.000",
            "end_tc": "00:00:18.000",
            "duration_ms": 9000,
            "source_ref": "U006",
            "notes": "Inclure sticker claim + geste de propriété"
          }
        ]
      },
      {
        "id": "A1",
        "type": "audio",
        "label": "Voix/Dialogues",
        "segments": []
      },
      {
        "id": "A2",
        "type": "audio",
        "label": "Ambiance/SFX",
        "segments": []
      },
      {
        "id": "A3",
        "type": "audio",
        "label": "Musique",
        "segments": []
      }
    ],
    "notes": ""
  }
}
```

## 7) Auto-contrôles N4 Timeline
- Continuité : aucun conflit de timecodes, pas de trous involontaires.
- Couverture : actes/séquences/scènes clés sont présents sur V1.
- Alignement : durée totale ≈ durée cible N0/N2.
- Traçabilité : chaque segment a un `source_ref` quand applicable.
- Neutralité narrative : aucun ajout d’événement ni de dialogue inventé.
