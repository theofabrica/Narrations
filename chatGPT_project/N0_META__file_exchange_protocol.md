# N0_META__file_exchange_protocol — Protocole d'echange par fichiers

## Statut du document
Document normatif N0. Il definit comment le projet ChatGPT produit des fichiers de commande
et comment l'application locale renvoie des ACK.

## Objectif
Mettre en place une communication fiable sans MCP direct : un fichier JSON telechargeable
sert de commande, puis un fichier ACK est renvoye apres execution.

## Nomenclature des fichiers
- Commande : `NARR_CMD_<ACTION>_<ID>_<TS>.json`
- ACK : `NARR_ACK_<ACTION>_<ID>_<TS>.json`

Regles :
- `<ACTION>` doit correspondre a une action serveur en snake_case (ex: `pipeline_audio_stack`).
- `<ID>` unique par commande (ex: `req_0001`).
- `<TS>` au format `YYYYMMDDTHHMMSSZ` (UTC).

## Compatibilite serveur MCP (obligatoire)
Le serveur `/mcp` attend au minimum :
`action`, `payload`, `request_id` (optionnel), `trace` (optionnel).

Regles de mapping :
- `id` (fichier) = `request_id` (serveur). Les deux doivent etre identiques.
- `meta.project` peut etre copie dans `trace.project`.
- Les champs `version`, `kind`, `id`, `ts`, `meta` sont ignores par le serveur mais utiles au protocole fichier.

## Schema JSON minimal (commande)
Champs obligatoires : `version`, `kind`, `action`, `id`, `ts`, `payload`.
Champs recommandes : `request_id`, `trace`, `from`, `meta.project`.
Champs optionnels : `meta.user`, `meta.checksum`, champs specifiques a l'action.

Exemple :
{
  "version": "1.0",
  "kind": "CMD",
  "action": "pipeline_audio_stack",
  "id": "req_0001",
  "request_id": "req_0001",
  "ts": "2026-01-08T14:21:30Z",
  "from": "chatgpt",
  "meta": { "project": "Narrations" },
  "trace": { "project": "Narrations" },
  "payload": {
    "voice": { "text": "Hello", "voice_id": "21m00Tcm4TlvDq8ikWAM" },
    "music": { "prompt": "Ambient", "duration": 20 },
    "wait_for_completion": true
  }
}

## Schema JSON minimal (ACK)
Champs obligatoires : `version`, `kind`, `action`, `id`, `ts`, `from`, `status`.
Champs optionnels : `result`, `error`.

Exemple :
{
  "version": "1.0",
  "kind": "ACK",
  "action": "pipeline_audio_stack",
  "id": "req_0001",
  "ts": "2026-01-08T14:21:30Z",
  "from": "local_app",
  "status": "done",
  "result": { "links": ["https://.../audio1.mp3"], "job_id": "job-xyz" },
  "error": null
}

## Regles cote ChatGPT (production du JSON)
- Obligation : si une action serveur est demandee (image/video/audio/pipeline), produire
  immediatement un JSON conforme, sans demander d'autorisation.
- Sortie attendue : fournir uniquement un bloc de code JSON (fence ```json), sans texte
  avant/apres, sans commentaire, sans nom de fichier, et sans analyse.
- Interdiction : ne pas demander a l'utilisateur de telecharger un fichier.
- Toujours inclure `version` (actuelle : `1.0`).
- Ne jamais inclure de secrets ou de tokens.

## Regles cote routine locale
- Surveiller le dossier de telechargements.
- Filtrer `NARR_*.json`.
- Valider la structure minimale (`kind/action/id/ts/payload`).
- Deposer dans un spool local (ex: `~/narrations_spool/inbox/`).
- Envoyer le contenu au serveur local (`POST /mcp` ou endpoint dedie).
- Ecrire un ACK dans `~/narrations_spool/outbox/` selon la nomenclature.

## Securite et resilience
- Aucun secret ne transite dans les JSON.
- Idempotence : ignorer un `id` deja traite.
- En cas d'echec reseau : retry avec backoff ou dossier `spool/retry/`.

## Bonnes pratiques ACTION/PAYLOAD
- `action` doit correspondre aux actions disponibles (ex: `elevenlabs_voice`, `higgsfield_video`).
- `payload` doit etre minimal et explicite.
- Ajouter `wait_for_completion` pour choisir sync/async.

## N0 JSON (obligatoire) - Format attendu
Le fichier N0 doit contenir tous les champs ci-dessous. Le projet ChatGPT doit tenter
de remplir chaque champ a partir des references disponibles (N0/N1/N2/N3/N4),
sauf `references` qui doit rester vide (chaine vide) jusqu'a ce que des fichiers
soient effectivement disponibles.

Schema attendu (exemple exact):
{
  "project_id": "test",
  "strata": "n0",
  "updated_at": "2026-01-08T21:27:19.217837Z",
  "data": {
    "production_summary": {
      "summary": "",
      "production_type": "",
      "primary_output_format": "",
      "target_duration": "",
      "aspect_ratio": "",
      "visual_style": "",
      "tone": "",
      "era": ""
    },
    "deliverables": {
      "visuals": {
        "images_enabled": true,
        "videos_enabled": true
      },
      "audio_stems": {
        "dialogue": true,
        "sfx": true,
        "music": true
      }
    },
    "art_direction": {
      "description": "",
      "references": ""
    },
    "sound_direction": {
      "description": "",
      "references": ""
    }
  }
}

Regles:
- Toujours produire tous les champs (meme si vides).
- `references` doit rester vide ("") dans le JSON produit par ChatGPT.
- Les valeurs doivent etre remplies a partir des sources narratives (MD/TXT) du dossier.
