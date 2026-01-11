"""
Normalize raw ChatGPT JSON into canonical MCP request payloads.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.tools.registry import list_actions
from app.utils.errors import ValidationError
from app.utils.ids import generate_request_id


_ACTION_ALIASES = {
    "image.generate": "higgsfield_image",
    "image": "higgsfield_image",
    "video.generate": "higgsfield_video",
    "video": "higgsfield_video",
    "pipeline.image_to_video": "pipeline_image_to_video",
    "image_to_video": "pipeline_image_to_video",
    "pipeline.audio_stack": "pipeline_audio_stack",
    "audio_stack": "pipeline_audio_stack",
    "voice.generate": "elevenlabs_voice",
    "tts.generate": "elevenlabs_voice",
    "voice": "elevenlabs_voice",
    "music.generate": "elevenlabs_music",
    "music": "elevenlabs_music",
    "soundfx.generate": "elevenlabs_soundfx",
    "sfx.generate": "elevenlabs_soundfx",
    "soundfx": "elevenlabs_soundfx",
    "sfx": "elevenlabs_soundfx",
}


def _parse_resolution(value: str) -> Optional[Dict[str, int]]:
    if not isinstance(value, str) or "x" not in value:
        return None
    parts = value.lower().split("x")
    if len(parts) != 2:
        return None
    try:
        width = int(parts[0].strip())
        height = int(parts[1].strip())
    except ValueError:
        return None
    return {"width": width, "height": height}


def _infer_action(raw_action: Optional[str], engine: Optional[str]) -> str:
    if raw_action:
        raw_action = raw_action.strip()
        if raw_action in list_actions():
            return raw_action
        if raw_action in _ACTION_ALIASES:
            return _ACTION_ALIASES[raw_action]
        lowered = raw_action.lower()
    else:
        lowered = ""

    if "image" in lowered and "video" not in lowered:
        return "higgsfield_image"
    if "video" in lowered:
        return "higgsfield_video"
    if "audio_stack" in lowered:
        return "pipeline_audio_stack"
    if "image_to_video" in lowered:
        return "pipeline_image_to_video"
    if "voice" in lowered or "tts" in lowered:
        return "elevenlabs_voice"
    if "music" in lowered:
        return "elevenlabs_music"
    if "sound" in lowered or "sfx" in lowered:
        return "elevenlabs_soundfx"

    if engine:
        engine = engine.lower()
        if "eleven" in engine:
            return "elevenlabs_voice"
        if "higgs" in engine or "kling" in engine:
            return "higgsfield_image"

    raise ValidationError("Unable to infer action for normalization")


def normalize_request(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw JSON into canonical MCP request fields.

    Returns:
        Dict with action, payload, request_id, and optional trace.
    """
    raw_action = raw.get("action")
    engine = raw.get("engine")
    action = _infer_action(raw_action, engine)

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    inputs = raw.get("inputs")
    if isinstance(inputs, dict) and not payload:
        payload = dict(inputs)
        aspect_ratio = payload.get("aspect_ratio")
        if aspect_ratio == "16:9":
            payload["aspect_ratio"] = "3:2"

    if not payload:
        for key in ("prompt", "image_url", "text"):
            if key in raw:
                payload[key] = raw[key]

    output = raw.get("output")
    if isinstance(output, dict):
        resolution = output.get("resolution")
        parsed = _parse_resolution(resolution) if resolution else None
        if parsed:
            payload.setdefault("width", parsed["width"])
            payload.setdefault("height", parsed["height"])
        if "count" in output and "num_images" not in payload:
            payload["num_images"] = output["count"]
        if "format" in output and "output_format" not in payload:
            payload["output_format"] = output["format"]

    if "wait_for_completion" in raw:
        payload.setdefault("wait_for_completion", raw["wait_for_completion"])
    if engine and "model" not in payload:
        payload["model"] = engine

    request_id = raw.get("request_id") or raw.get("id") or generate_request_id()

    trace = raw.get("trace")
    if not isinstance(trace, dict):
        trace = {}
    meta = raw.get("meta")
    if isinstance(meta, dict) and meta.get("project"):
        trace.setdefault("project", meta.get("project"))

    normalized = {
        "action": action,
        "payload": payload,
        "request_id": request_id,
    }
    if trace:
        normalized["trace"] = trace

    return normalized
