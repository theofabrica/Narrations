# Higgsfield — Nano Banana (API)

## Auth
- Base URL: `https://platform.higgsfield.ai`
- Headers:
  - `hf-api-key: <HIGGSFIELD_API_KEY_ID>` (UUID)
  - `hf-secret: <HIGGSFIELD_API_KEY_SECRET>` (secret)
  - `Content-Type: application/json`
- Variables déjà utilisées dans l’app (`.env`):
  - `HIGGSFIELD_API_KEY_ID`
  - `HIGGSFIELD_API_KEY_SECRET`

## Endpoints
- Génération image (Nano Banana):
  - `POST https://platform.higgsfield.ai/nano-banana`
  - (alias doc: `POST https://platform.higgsfield.ai/v1/text2image/nano-banana`)
- Statut:
  - `GET https://platform.higgsfield.ai/requests/{request_id}/status`
- Cancel:
  - `POST https://platform.higgsfield.ai/requests/{request_id}/cancel`

## Payload (génération)
```json
{
  "prompt": "Your prompt",
  "num_images": 1,
  "aspect_ratio": "4:3",
  "input_images": [],
  "output_format": "png"
}
```
- `aspect_ratio` autorisés: `auto`, `1:1`, `4:3`, `3:4`, `3:2`
- `output_format`: `png` (defaut) ou `jpeg`
- `num_images`: 1–4

## Exemple cURL
```bash
curl -X POST "https://platform.higgsfield.ai/nano-banana" \
  -H "Content-Type: application/json" \
  -H "hf-api-key: $HIGGSFIELD_API_KEY_ID" \
  -H "hf-secret: $HIGGSFIELD_API_KEY_SECRET" \
  -d '{
    "prompt": "A cinematic portrait in soft light, 4k detail",
    "num_images": 1,
    "aspect_ratio": "4:3",
    "input_images": [],
    "output_format": "png"
  }'
```

## Réponse (queued)
```json
{
  "id": "...",
  "type": "nano_banana",
  "created_at": "...",
  "jobs": [
    { "id": "...", "job_set_type": "nano_banana", "status": "queued", "results": null }
  ],
  "input_params": { ... }
}
```
Puis via `status_url`: `status` ∈ `queued | in_progress | nsfw | failed | completed | canceled`.

## Schéma status (GET /requests/{request_id}/status)
```json
{
  "status": "queued | in_progress | nsfw | failed | completed | canceled",
  "request_id": "uuid",
  "status_url": "uri",
  "cancel_url": "uri"
}
```

## Exemple GET status

### cURL
```bash
curl https://platform.higgsfield.ai/requests/{request_id}/status
```

## Exemple POST cancel

## Exemple POST génération (v1/text2image/nano-banana)

### cURL
```bash
curl https://platform.higgsfield.ai/v1/text2image/nano-banana \
  --request POST \
  --header "hf-api-key: $HIGGSFIELD_API_KEY_ID" \
  --header "hf-secret: $HIGGSFIELD_API_KEY_SECRET" \
  --header "Content-Type: application/json" \
  --data '{
    "params": {
      "prompt": "",
      "num_images": 1,
      "aspect_ratio": "1:1",
      "input_images": [],
      "output_format": "png"
    }
  }'
```

## Exemple POST génération ( /nano-banana ) avec image_url

### cURL
```bash
curl https://platform.higgsfield.ai/nano-banana \
  --request POST \
  --header "Content-Type: application/json" \
  --header "hf-api-key: $HIGGSFIELD_API_KEY_ID" \
  --header "hf-secret: $HIGGSFIELD_API_KEY_SECRET" \
  --data '{
    "prompt": "",
    "num_images": 1,
    "aspect_ratio": "4:3",
    "input_images": [
      {
        "type": "image_url",
        "image_url": ""
      }
    ],
    "output_format": "png"
  }'
```

### Python (http.client)
```python
import http.client

conn = http.client.HTTPSConnection("platform.higgsfield.ai")

payload = '{"prompt":"","num_images":1,"aspect_ratio":"4:3","input_images":[{"type":"image_url","image_url":""}],"output_format":"png"}'

headers = {
    "Content-Type": "application/json",
    "hf-api-key": "",
    "hf-secret": ""
}

conn.request("POST", "/nano-banana", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```
### Python (http.client)
```python
import http.client

conn = http.client.HTTPSConnection("platform.higgsfield.ai")

payload = '{"params":{"prompt":"","num_images":1,"aspect_ratio":"1:1","input_images":[],"output_format":"png"}}'

headers = {
    'hf-api-key': "",
    'hf-secret': "",
    'Content-Type': "application/json"
}

conn.request("POST", "/v1/text2image/nano-banana", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```
### cURL
```bash
curl https://platform.higgsfield.ai/requests/{request_id}/cancel \
  --request POST
```

### Python (http.client)
```python
import http.client

conn = http.client.HTTPSConnection("platform.higgsfield.ai")
conn.request("POST", "/requests/{request_id}/cancel")
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```
### Python (http.client)
```python
import http.client

conn = http.client.HTTPSConnection("platform.higgsfield.ai")
conn.request("GET", "/requests/{request_id}/status")
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```

## Nano Banana Pro — TextToImage (`/nano-banana-pro`)

### Payload
```json
{
  "prompt": "Your prompt",
  "num_images": 1,
  "resolution": "1k",        // valeur vue dans l’UI (autres valeurs non documentées ici)
  "aspect_ratio": "4:3",
  "output_format": "png"
}
```

### cURL
```bash
curl https://platform.higgsfield.ai/nano-banana-pro \
  --request POST \
  --header "Content-Type: application/json" \
  --header "hf-api-key: $HIGGSFIELD_API_KEY_ID" \
  --header "hf-secret: $HIGGSFIELD_API_KEY_SECRET" \
  --data '{
    "prompt": "",
    "num_images": 1,
    "resolution": "1k",
    "aspect_ratio": "4:3",
    "output_format": "png"
  }'
```

### Python (http.client)
```python
import http.client

conn = http.client.HTTPSConnection("platform.higgsfield.ai")

payload = '{"prompt":"","num_images":1,"resolution":"1k","aspect_ratio":"4:3","output_format":"png"}'

headers = {
    "Content-Type": "application/json",
    "hf-api-key": "",
    "hf-secret": ""
}

conn.request("POST", "/nano-banana-pro", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))
```
