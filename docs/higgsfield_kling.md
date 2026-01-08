# Higgsfield — Kling (API notes)

## Auth (à confirmer selon Nano Banana)
- Généralement : `hf-api-key` (UUID) et `hf-secret` (clé secrète), plus `Content-Type: application/json`.
- Base URL : `https://platform.higgsfield.ai`

## Status / Cancel (communs)
- GET `/requests/{request_id}/status`
- POST `/requests/{request_id}/cancel`
- Réponse status :
  - `status` ∈ `queued | in_progress | nsfw | failed | completed | canceled`
  - `request_id`, `status_url`, `cancel_url`

## Kling 2.6 — Image to Video (pro)
- Endpoint : `POST /kling-video/v2.6/pro/image-to-video`
- Payload (exemple UI) :
```json
{
  "sound": "on",
  "prompt": "",
  "duration": 5,
  "cfg_scale": 0.5,
  "image_url": "",
  "aspect_ratio": "16:9"
}
```
- Headers :
  - `Content-Type: application/json`
  - (probablement) `hf-api-key`, `hf-secret`

### cURL (copié de l’UI)
```bash
curl https://platform.higgsfield.ai/kling-video/v2.6/pro/image-to-video \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "sound": "on",
    "prompt": "",
    "duration": 5,
    "cfg_scale": 0.5,
    "image_url": "",
    "aspect_ratio": "16:9"
  }'
```

## Kling 2.6 — Text to Video (pro)
- Endpoint : `POST /kling-video/v2.6/pro/text-to-video`
- Payload (exemple UI) :
```json
{
  "sound": "on",
  "prompt": "",
  "duration": 5,
  "cfg_scale": 0.5,
  "aspect_ratio": "16:9"
}
```
- Headers :
  - `Content-Type: application/json`
  - (probablement) `hf-api-key`, `hf-secret`

### cURL (copié de l’UI)
```bash
curl https://platform.higgsfield.ai/kling-video/v2.6/pro/text-to-video \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "sound": "on",
    "prompt": "",
    "duration": 5,
    "cfg_scale": 0.5,
    "aspect_ratio": "16:9"
  }'
```

## Kling Omni — First/Last Frame (kling01)
- Endpoint : `POST /kling-video/omni/first-last-frame`
- Payload (exemple UI) :
```json
{
  "mode": "pro",          // std | pro
  "prompt": "",
  "duration": 5,          // 5 ou 10
  "aspect_ratio": "16:9", // 16:9 | 9:16 | 1:1
  "last_frame_url": "",
  "first_frame_url": ""
}
```
- Headers :
  - `Content-Type: application/json`
  - (probablement) `hf-api-key`, `hf-secret`

### cURL (copié de l’UI)
```bash
curl https://platform.higgsfield.ai/kling-video/omni/first-last-frame \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "mode": "pro",
    "prompt": "",
    "duration": 5,
    "aspect_ratio": "16:9",
    "last_frame_url": "",
    "first_frame_url": ""
  }'
```

## Kling Omni — Image Reference (Image→Video conditionné)
- Endpoint : `POST /kling-video/omni/image-reference`
- Payload (exemple UI) :
```json
{
  "mode": "pro",          // std | pro
  "prompt": "",
  "duration": 5,          // min 3, max 10 (default 5)
  "elements": [""],       // array string, ...x7
  "image_urls": [""],     // array Image URL, ...x7
  "aspect_ratio": "16:9"  // 16:9 | 9:16 | 1:1
}
```
- Headers :
  - `Content-Type: application/json`
  - (probablement) `hf-api-key`, `hf-secret`

### cURL (copié de l’UI)
```bash
curl https://platform.higgsfield.ai/kling-video/omni/image-reference \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{
    "mode": "pro",
    "prompt": "",
    "duration": 5,
    "elements": [
      ""
    ],
    "image_urls": [
      ""
    ],
    "aspect_ratio": "16:9"
  }'
```

## TODO
- Kling Omni — Image to Video (non fourni)
- Kling Omni — image_edit (non utilisé ici)
