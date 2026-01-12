
# MCP Narrations Server

# Ecriture win - git - kubuntu : 01 from win
# Ecriture win - git - kubuntu : 01 from win
# Ecriture ub -git -win :01

Serveur MCP (FastAPI) pour orchestrer la génération de médias via Higgsfield et ElevenLabs.

## 🎯 Objectif

Construire un serveur MCP qui expose un endpoint `/mcp` acceptant des commandes JSON ("actions") pour orchestrer :

- **Higgsfield** : génération d'images et vidéos
- **ElevenLabs** : voix (TTS), sound design (SFX), musique
- **Pipelines** : orchestration de workflows complexes (image→video, audio_stack)

## 📋 État d'avancement

### ✅ Phase 1 - MVP MCP stable (TERMINÉE)

Infrastructure de base complète :

- ✅ Configuration (`app/config/settings.py`) avec Pydantic Settings
- ✅ Schémas (`app/mcp/schemas.py`) pour Request/Response normalisés
- ✅ Gestion d'erreurs (`app/utils/errors.py`) avec exceptions normalisées
- ✅ Générateurs d'IDs (`app/utils/ids.py`) pour request_id, job_id, asset_id
- ✅ Logging structuré (`app/utils/logging.py`)
- ✅ Registry d'actions (`app/tools/registry.py`) pour dispatch
- ✅ Handler MCP (`app/mcp/server.py`) avec validation et gestion d'erreurs
- ✅ Application FastAPI (`app/main.py`) avec endpoints `/health` et `/mcp`
- ✅ Tests (`tests/test_mcp.py`) : ping, list_tools, action inconnue

**Actions disponibles** :
- `ping` : test de connectivité
- `list_tools` : liste toutes les actions disponibles
- `elevenlabs_voice` : génération de voix (TTS) depuis un texte
- `elevenlabs_music` : génération de musique depuis un prompt
- `elevenlabs_soundfx` : génération d'effets sonores depuis un prompt
- `higgsfield_image` : génération d'images depuis un prompt
- `higgsfield_video` : génération de vidéos depuis un prompt ou une image
- `check_job_status` : vérifier le statut d'un job (elevenlabs ou higgsfield)
- `pipeline_image_to_video` : pipeline qui génère une image puis une vidéo
- `pipeline_audio_stack` : pipeline qui combine voice, sfx et music

### ✅ Phase 2 - Providers (TERMINÉE)

Intégration complète des providers :

- ✅ Client HTTP ElevenLabs (`app/tools/elevenlabs/client.py`) avec authentification et retry logic
- ✅ Client HTTP Higgsfield (`app/tools/higgsfield/client.py`) avec authentification et polling
- ✅ Handlers ElevenLabs :
  - ✅ `elevenlabs_voice` : génération de voix (TTS)
  - ✅ `elevenlabs_music` : génération de musique
  - ✅ `elevenlabs_soundfx` : génération d'effets sonores
- ✅ Handlers Higgsfield :
  - ✅ `higgsfield_image` : génération d'images
  - ✅ `higgsfield_video` : génération de vidéos
- ✅ Gestion de statut de jobs avec polling (`poll_job()` dans les clients)
- ✅ Action `check_job_status` pour vérifier le statut d'un job
- ✅ Tests complets (`tests/test_elevenlabs.py` et `tests/test_higgsfield.py`)

### ✅ Phase 3 - Pipelines (TERMINÉE)

Orchestration de workflows complexes :

- ✅ Pipeline `pipeline_image_to_video` : génère une image puis une vidéo à partir de cette image
  - Support des paramètres séparés pour image et video
  - Gestion des jobs asynchrones avec polling optionnel
  - Retourne les liens vers l'image et la vidéo générées
- ✅ Pipeline `pipeline_audio_stack` : combine voice, sfx et music
  - Génération parallèle ou séquentielle des différents types d'audio
  - Au moins un type d'audio requis (voice, music, ou soundfx)
  - Retourne tous les liens audio générés
- ✅ Tests complets (`tests/test_pipelines.py`)

## 🚀 Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Copier et configurer les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API
```

## 🏃 Démarrage

```bash
# Mode développement (avec reload automatique)
python -m uvicorn app.main:app --host 0.0.0.0 --port 3333 --reload

# Ou utiliser le script (API seule)
./scripts/run_dev.sh

# API + interface (et tunnel Cloudflare si ENABLE_CLOUDFLARE_TUNNEL=1)
./scripts/dev_all.sh
```

Le serveur sera accessible sur `http://0.0.0.0:3333`

L'interface Vite est disponible sur `http://localhost:5173`.

## 📡 Utilisation

### Health Check

```bash
curl http://localhost:3333/health
```

### Endpoint MCP

```bash
# Ping
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "ping",
    "payload": {}
  }'

# Lister les outils disponibles
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "list_tools",
    "payload": {}
  }'

# Générer une voix (ElevenLabs)
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "elevenlabs_voice",
    "payload": {
      "text": "Hello, this is a test",
      "voice_id": "21m00Tcm4TlvDq8ikWAM",
      "model_id": "eleven_multilingual_v2"
    }
  }'

# Générer une image (Higgsfield)
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "higgsfield_image",
    "payload": {
      "prompt": "A beautiful sunset over the ocean",
      "width": 1024,
      "height": 1024,
      "wait_for_completion": false
    }
  }'

# Générer une vidéo (Higgsfield)
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "higgsfield_video",
    "payload": {
      "prompt": "A cat dancing",
      "duration": 5.0,
      "fps": 24,
      "wait_for_completion": true
    }
  }'

# Vérifier le statut d'un job
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "check_job_status",
    "payload": {
      "job_id": "higgsfield_job_abc123",
      "provider": "higgsfield"
    }
  }'

# Pipeline image_to_video
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "pipeline_image_to_video",
    "payload": {
      "prompt": "A beautiful sunset over the ocean",
      "image_params": {
        "width": 1024,
        "height": 1024
      },
      "video_params": {
        "duration": 5.0,
        "fps": 24
      },
      "wait_for_completion": true
    }
  }'

# Pipeline audio_stack
curl -X POST http://localhost:3333/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "action": "pipeline_audio_stack",
    "payload": {
      "voice": {
        "text": "Welcome to our presentation",
        "voice_id": "21m00Tcm4TlvDq8ikWAM"
      },
      "music": {
        "prompt": "Upbeat background music",
        "duration": 30
      },
      "soundfx": {
        "prompt": "Applause sound",
        "duration": 3
      },
      "wait_for_completion": true
    }
  }'
```

### Format de requête

```json
{
  "action": "nom_de_l_action",
  "payload": {
    "param1": "value1",
    "param2": "value2"
  },
  "request_id": "req_123456",  // optionnel
  "trace": {                    // optionnel
    "project": "project_name",
    "user": "user_id",
    "session": "session_id"
  }
}
```

### Format de réponse

```json
{
  "status": "ok",  // ou "error"
  "action": "nom_de_l_action",
  "request_id": "req_123456",
  "data": {
    // données de réponse
  },
  "error": null,  // ou { "code": "...", "message": "...", "retryable": false }
  "received_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:01Z"
}
```

## 🧪 Tests

```bash
# Lancer tous les tests
pytest

# Tests avec détails
pytest -v

# Tests spécifiques
pytest tests/test_mcp.py -v
```

## 📁 Structure du projet

```
MCP_Narrations/
├── app/
│   ├── config/
│   │   └── settings.py          # Configuration (Pydantic Settings)
│   ├── mcp/
│   │   ├── schemas.py           # Schémas Request/Response
│   │   └── server.py            # Handler MCP principal
│   ├── tools/
│   │   ├── registry.py          # Registry d'actions
│   │   ├── higgsfield/          # (Phase 2)
│   │   └── elevenlabs/          # (Phase 2)
│   ├── pipelines/               # (Phase 3)
│   ├── utils/
│   │   ├── errors.py            # Gestion d'erreurs
│   │   ├── ids.py               # Générateurs d'IDs
│   │   └── logging.py           # Logging structuré
│   └── main.py                  # Application FastAPI
├── tests/
│   ├── test_mcp.py              # Tests Phase 1
│   ├── test_higgsfield.py       # (Phase 2)
│   └── test_elevenlabs.py       # (Phase 2)
├── requirements.txt
├── .env.example
└── README.md
```

## 💾 Stockage des médias

Les fichiers générés (images, vidéos, audio) sont automatiquement téléchargés et stockés localement dans le dossier `Media/` organisé par projet :

```
Media/
├── {project_name}/
│   ├── image/
│   │   └── {asset_id}.png
│   ├── video/
│   │   └── {asset_id}.mp4
│   └── audio/
│       └── {asset_id}.mp3
```

**Configuration :**
- Le nom du projet est extrait depuis `payload.project_name` ou `trace.project`
- Si aucun projet n'est spécifié, les fichiers sont stockés dans `Media/default/`
- Les URLs retournées pointent vers `/assets/{project_name}/{type}/{filename}`
- Le téléchargement peut être désactivé via `STORAGE_DOWNLOAD_ENABLED=false` dans `.env`
- Upload SFTP optionnel : `STORAGE_FTP_ENABLED=true` + `FTP_HOST`, `FTP_PORT`, `FTP_USER`, `FTP_PASSWORD`, `FTP_BASE_DIR`, `FTP_PUBLIC_BASE_URL`

**Endpoint de service :**
- `GET /assets/{project_name}/{type}/{filename}` : sert les fichiers stockés

## 🔒 Sécurité

- Les clés API sont chargées uniquement via variables d'environnement (`.env`)
- Jamais de clés hardcodées dans le code
- Validation stricte des requêtes avec Pydantic
- Les fichiers servis via `/assets/` sont validés pour éviter l'accès hors du dossier Media/

## 📝 Contraintes de qualité

- ✅ **Traçabilité** : tout résultat contient job_id, asset_id, provider, model, params, created_at, status, links[]
- ✅ **Erreurs propres** : erreurs normalisées (code, message, details, retryable)
- ✅ **Sécurité** : clés API uniquement via .env
- ✅ **Extensibilité** : ajout de providers via `tools/registry.py` sans casser les pipelines

## 🔗 Intégration avec ChatGPT

Le serveur doit être joignable en HTTPS pour ChatGPT. Options :

- **Cloudflare Tunnel (recommandé, domaine Cloudflare)**  
  1) `cloudflared login` (sélectionne ton domaine Cloudflare)  
  2) `cloudflared tunnel create mcp-narrations`  
  3) `cloudflared tunnel route dns mcp-narrations mcp.numeniagen76.com`  
  4) Lancer le tunnel :  
     ```bash
     chmod +x scripts/expose_cloudflare.sh
     TUNNEL_HOSTNAME=mcp.numeniagen76.com \
     TUNNEL_NAME=mcp-narrations \
     TARGET_URL=http://localhost:3333 \
     ./scripts/expose_cloudflare.sh
     ```
  Dans ChatGPT, utiliser `https://mcp.numeniagen76.com/mcp` comme URL MCP.

- **Cloudflare Tunnel “quick” (sans domaine, éphémère)**  
  ```bash
  cloudflared tunnel --url http://localhost:3333
  # récupère l’URL *.trycloudflare.com affichée, et mets-la dans ChatGPT : https://…/mcp
  ```
  À relancer à chaque redémarrage (URL change).

- **Reverse proxy (nginx + TLS) ou VPS public**

## 📚 Documentation API

Une fois le serveur démarré, la documentation Swagger est disponible sur :
- `http://localhost:3333/docs`
- `http://localhost:3333/redoc`
