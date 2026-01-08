# ElevenLabs API — Notes rapides

Source : [https://elevenlabs.io/docs/api-reference/introduction](https://elevenlabs.io/docs/api-reference/introduction)

## Installation
- Python : `pip install elevenlabs`
- Node.js : `npm install @elevenlabs/elevenlabs-js`

## Clients officiels (extraits)
### Python
```python
from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="your_api_key")

# Exemple d'appel TTS avec accès aux headers (coûts, request-id)
response = client.text_to_speech.with_raw_response.convert(
    text="Hello, world!",
    voice_id="voice_id"
)
char_cost = response.headers.get("x-character-count")
request_id = response.headers.get("request-id")
audio_data = response.data
```

### JavaScript / TypeScript
```typescript
import { ElevenLabsClient } from '@elevenlabs/elevenlabs-js';

const client = new ElevenLabsClient({ apiKey: 'your_api_key' });

const { data, rawResponse } = await client.textToSpeech
  .convert('voice_id', {
    text: 'Hello, world!',
    modelId: 'eleven_multilingual_v2',
  })
  .withRawResponse();

const charCost = rawResponse.headers.get('x-character-count');
const requestId = rawResponse.headers.get('request-id');
const audioData = data;
```

## Métadonnées de facturation
- Les en-têtes de réponse exposent les coûts de génération (caractères) et `request-id` :
  - `x-character-count`
  - `request-id`

## Remarque
Le serveur MCP utilise `ELEVENLABS_API_KEY` (env) et envoie `xi-api-key` côté HTTP. Ajouter la clé dans `.env` :
```
ELEVENLABS_API_KEY=...
```

## Usages / Endpoints (catalogue)
- **Text to Speech** : génération TTS
- **Speech to Speech** : conversion voix→voix
- **Speech to Text** : transcription
- **Sound Effects** : génération SFX
- **Audio Isolation** : séparation de sources
- **Music Generation** : génération musicale
- **Voice Generation** : (selon offre) génération de voix
- **Dubbing** : doublage
- **ElevenLabs Agents / Projects** : gestion d’agents/projets (selon offre)
- **Audio Native** : fonctionnalités natives audio
- **Voices** : gestion des voix (list, add, edit)
- **Forced Alignment** : alignement forcé
- **History / Models / Pronunciation Dictionaries / User** : gestion des historiques, modèles, dictionnaires, infos utilisateur

## Musique (API “music”)
- Composer (prompt simple) : `POST /v1/music`
  - `prompt` ou `composition_plan`
  - `music_length_ms` (3000–600000), `model_id` (ex. `music_v1`)
  - Options : `force_instrumental`, `respect_sections_durations`, `store_for_inpainting`, `sign_with_c2pa`
  - `xi-api-key` en header, réponse binaire (audio)
- Composer (detailed) : `POST /v1/music/detailed`
  - Même champs, réponse détaillée
- Créer un composition plan : `POST /v1/music/composition-plan` (plan structuré : sections, styles)
- Séparer les stems : `POST /v1/music/separate-stems` (envoi d’un audio, extraction de stems)

## Sound Effects
- `POST /v1/text-to-sound-effects/convert`
  - `text`/`prompt` pour générer un SFX, `duration_ms` optionnel

## Dialogue (TTS étendu)
- `POST /v1/text-to-dialogue/convert`
- `POST /v1/text-to-dialogue/convert-with-timestamps`
- `POST /v1/text-to-dialogue/stream-with-timestamps`
  - Entrée : `text`, `voice_id`, options de modèle ; variantes avec timestamps ou streaming

## TTS WebSocket (streaming partiel)
Endpoint : `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input`
- Headers : `xi-api-key`
- Query/options (WS bindings) : `model_id`, `language_code`, `output_format` (mp3_22050_32, mp3_44100_32/64/96/128/192, pcm_8000/16000/22050/24000/32000/44100/48000, ulaw_8000, alaw_8000, opus_48000_32/64/96/128/192), `enable_logging`, `enable_ssml_parsing`, `inactivity_timeout`, `sync_alignment`, `auto_mode`, `apply_text_normalization`, `seed`.
- Messages :
  - Init : `text: " "` + `voice_settings` (stability, similarity_boost, style, use_speaker_boost, speed) + `generation_config` (chunk_length_schedule).
  - Send text : `text` (terminé par un espace), `try_trigger_generation`, `flush` (force la génération), optionnellement `voice_settings`/`generator_config` si déjà envoyés et non changés.
  - Close : `text: ""` pour terminer le stream.
- Sortie : chunks audio (base64 selon `output_format`) + alignments (charStartTimesMs/charDurationsMs), puis message final `isFinal=true`.
