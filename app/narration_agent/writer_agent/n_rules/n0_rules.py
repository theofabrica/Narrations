"""Deterministic rules and heuristics for N0 writing."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.utils.project_storage import read_strata


def infer_n0_production_summary(
    source_state: Dict[str, Any],
    target_current: Dict[str, Any],
    llm_client: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    combined_text = collect_brief_text(source_state)
    production_type = pick_from_keywords(
        combined_text,
        [
            (["clip", "music video"], "clip"),
            (["advertisement", "ad", "commercial", "pub"], "advertisement"),
            (["documentary", "docu"], "documentary"),
            (["short film", "court-metrage", "short"], "short film"),
            (["feature film", "long metrage", "feature"], "feature film"),
            (["series", "serie"], "series"),
        ],
    )
    target_duration = extract_duration(combined_text, llm_client=llm_client)
    aspect_ratio = extract_aspect_ratio(combined_text)
    if not aspect_ratio:
        aspect_ratio = "16:9"

    patch: Dict[str, Any] = {}
    patch.update(apply_if_empty(target_current, "production_type", production_type))
    patch.update(apply_if_empty(target_current, "target_duration", target_duration))
    patch.update(
        apply_if_empty(
            target_current,
            "target_duration_text",
            duration_to_text(target_duration),
        )
    )
    patch.update(apply_if_empty(target_current, "aspect_ratio", aspect_ratio))
    return patch


def infer_n0_visual_style_tone(project_id: str, source_state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        n0_state = read_strata(project_id, "n0")
    except Exception:
        n0_state = {}
    n0_data = n0_state.get("data") if isinstance(n0_state, dict) else {}
    if not isinstance(n0_data, dict):
        n0_data = {}
    narrative_presentation = n0_data.get("narrative_presentation")
    if not isinstance(narrative_presentation, dict):
        narrative_presentation = n0_data.get("production_summary", {})
    art_desc = (n0_data.get("art_direction", {}) or {}).get("description", "")
    sound_desc = (n0_data.get("sound_direction", {}) or {}).get("description", "")
    combined_text = " | ".join(
        [
            collect_brief_text(source_state),
            narrative_presentation.get("summary", "")
            if isinstance(narrative_presentation, dict)
            else "",
            art_desc if isinstance(art_desc, str) else "",
            sound_desc if isinstance(sound_desc, str) else "",
        ]
    )
    visual_style = pick_from_keywords(
        combined_text,
        [
            (["futuristic", "futuriste", "cyberpunk"], "futuristic"),
            (["retro", "vintage"], "retro"),
            (["noir", "film noir"], "noir"),
            (["surreal", "surréaliste", "surrealiste"], "surreal"),
            (["minimal", "minimalist", "minimaliste"], "minimal"),
            (["neon", "néon", "neon-lit"], "neon"),
            (["classical", "classique"], "classical"),
            (["documentary", "docu", "documentaire"], "documentary"),
        ],
    )
    tone = pick_from_keywords(
        combined_text,
        [
            (["dramatic", "dramatique"], "dramatic"),
            (["epic", "epique", "épique"], "epic"),
            (["poetic", "poetique", "poétique"], "poetic"),
            (["dark", "sombre"], "dark"),
            (["melancholic", "melancolique", "mélancolique"], "melancholic"),
            (["romantic", "romantique"], "romantic"),
            (["comedic", "comedy", "comedie", "comédie"], "comedic"),
            (["satirical", "satire", "satirique"], "satirical"),
        ],
    )
    patch: Dict[str, Any] = {}
    if isinstance(narrative_presentation, dict):
        patch.update(apply_if_empty(narrative_presentation, "visual_style", visual_style))
        patch.update(apply_if_empty(narrative_presentation, "tone", tone))
    return patch


def infer_n0_deliverables(
    source_state: Dict[str, Any], target_current: Dict[str, Any]
) -> Dict[str, Any]:
    combined_text = collect_brief_text(source_state)
    defaults = {
        "visuals": {"images_enabled": True, "videos_enabled": True},
        "audio_stems": {"dialogue": True, "sfx": True, "music": True},
    }
    current_visuals = target_current.get("visuals") if isinstance(target_current, dict) else {}
    current_audio = target_current.get("audio_stems") if isinstance(target_current, dict) else {}
    visuals = {**defaults["visuals"], **(current_visuals or {})}
    audio = {**defaults["audio_stems"], **(current_audio or {})}

    if has_negative(combined_text, ["no video", "sans video", "pas de video"]):
        visuals["videos_enabled"] = False
    if has_negative(combined_text, ["no image", "no images", "sans image", "sans images"]):
        visuals["images_enabled"] = False
    if has_negative(combined_text, ["no audio", "sans audio"]):
        audio["dialogue"] = False
        audio["sfx"] = False
        audio["music"] = False
    if has_negative(combined_text, ["no dialogue", "sans dialogue", "no voice", "sans voix"]):
        audio["dialogue"] = False
    if has_negative(combined_text, ["no music", "sans musique"]):
        audio["music"] = False
    if has_negative(combined_text, ["no sfx", "sans sfx", "sans bruitage"]):
        audio["sfx"] = False

    if has_positive(combined_text, ["image", "photo", "illustration", "affiche"]):
        visuals["images_enabled"] = True
    if has_positive(combined_text, ["video", "clip", "film", "animation"]):
        visuals["videos_enabled"] = True
    if has_positive(combined_text, ["dialogue", "voice", "voix", "narration"]):
        audio["dialogue"] = True
    if has_positive(combined_text, ["music", "musique", "soundtrack"]):
        audio["music"] = True
    if has_positive(combined_text, ["sfx", "bruitage", "sound design"]):
        audio["sfx"] = True

    return {"visuals": visuals, "audio_stems": audio}


def collect_brief_text(source_state: Dict[str, Any]) -> str:
    parts: List[str] = []
    parts.append(get_str(source_state, ["core", "summary"]))
    if not parts[-1]:
        parts.append(get_str(source_state, ["summary"]))
    parts.append(get_str(source_state, ["brief", "primary_objective"]))
    parts.extend(get_list(source_state, ["brief", "secondary_objectives"]))
    parts.extend(get_list(source_state, ["brief", "constraints"]))
    parts.extend(get_list(source_state, ["thinker", "constraints"]))
    parts.extend(get_list(source_state, ["thinker", "hypotheses"]))
    return " | ".join([part for part in parts if part])


def pick_from_keywords(
    text: str,
    mapping: List[tuple[list[str], str]],
) -> str:
    haystack = text.lower()
    for keywords, value in mapping:
        for keyword in keywords:
            if keyword in haystack:
                return value
    return ""


def extract_tagged_value(text: str, tags: List[str]) -> str:
    if not text:
        return ""
    for tag in tags:
        pattern = re.compile(rf"{re.escape(tag)}\s*[:=-]\s*([^\n|]+)", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return ""


def extract_duration(text: str, llm_client: Optional[LLMClient] = None) -> str:
    if not text:
        return ""
    tagged = extract_tagged_value(text, ["duration", "durée", "duree", "temps", "time"])
    candidate = tagged or text
    duration = extract_duration_heuristic(candidate)
    if duration:
        return duration
    if llm_client is None:
        return ""
    return extract_duration_llm(text, llm_client)


def extract_duration_heuristic(text: str) -> str:
    if not text:
        return ""
    timecode_match = re.search(r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b", text)
    if timecode_match:
        hours = 0
        minutes = int(timecode_match.group(1))
        seconds = int(timecode_match.group(2))
        if timecode_match.group(3) is not None:
            hours = minutes
            minutes = seconds
            seconds = int(timecode_match.group(3))
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return format_duration_seconds(total_seconds)

    match = re.search(r"\b(\d{1,2})\s*h\s*(\d{1,2})\b", text, re.IGNORECASE)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        return format_duration_seconds(hours * 3600 + minutes * 60)

    match = re.search(r"\b(\d{1,2})\s*m(?:in)?\s*(\d{1,2})\s*s?\b", text, re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return format_duration_seconds(minutes * 60 + seconds)

    total_seconds = 0.0
    pattern = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(h|hr|hour|hours|heure|heures|m|min|minute|minutes|s|sec|secs|second|seconds|seconde|secondes)",
        re.IGNORECASE,
    )
    for value_str, unit in pattern.findall(text):
        value = float(value_str.replace(",", "."))
        unit = unit.lower()
        if unit.startswith("h") or "heure" in unit:
            total_seconds += value * 3600
        elif unit.startswith("m"):
            total_seconds += value * 60
        else:
            total_seconds += value

    if total_seconds > 0:
        return format_duration_seconds(int(round(total_seconds)))

    return ""


def extract_duration_llm(text: str, llm_client: LLMClient) -> str:
    if not text:
        return ""
    system_prompt = (
        "Extract a target duration from the text. "
        "Return ONLY JSON: {\"duration\": \"HH:MM:SS\"} or {\"duration\": \"\"}. "
        "If missing or ambiguous, return empty."
    )
    llm_response = llm_client.complete(
        LLMRequest(
            model=llm_client.default_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
    )
    raw_content = llm_response.content.strip()
    json_block = extract_json_block(raw_content) or raw_content
    parsed = parse_json_payload(json_block, raw_content)
    if not isinstance(parsed, dict):
        return ""
    duration = parsed.get("duration", "")
    if not isinstance(duration, str):
        return ""
    return extract_duration_heuristic(duration)


def format_duration_seconds(total_seconds: int) -> str:
    if total_seconds <= 0:
        return ""
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def duration_to_text(value: str) -> str:
    seconds = _duration_to_seconds(value)
    if seconds <= 0:
        return ""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts: List[str] = []
    if hours:
        parts.append(f"{_to_english(hours)} hour{'s' if hours > 1 else ''}")
    if minutes:
        parts.append(f"{_to_english(minutes)} minute{'s' if minutes > 1 else ''}")
    if secs and not hours:
        parts.append(f"{_to_english(secs)} second{'s' if secs > 1 else ''}")
    return " ".join(parts).strip()


def _duration_to_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str):
        return 0
    text = value.strip().lower()
    if not text:
        return 0
    if text.isdigit():
        return max(0, int(text))
    match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
    if match:
        hours = 0
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        if match.group(3) is not None:
            hours = minutes
            minutes = seconds
            seconds = int(match.group(3))
        return max(0, hours * 3600 + minutes * 60 + seconds)
    return 0


def _to_english(value: int) -> str:
    if value < 0:
        return str(value)
    if value == 0:
        return "zero"
    ones = [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "eleven",
        "twelve",
        "thirteen",
        "fourteen",
        "fifteen",
        "sixteen",
        "seventeen",
        "eighteen",
        "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty"]
    if value < 20:
        return ones[value]
    if value < 60:
        ten = value // 10
        rest = value % 10
        if rest == 0:
            return tens[ten]
        return f"{tens[ten]} {ones[rest]}"
    return str(value)


def extract_aspect_ratio(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"\b(\d{1,2})\s*:\s*(\d{1,2})\b", text)
    if match:
        return f"{match.group(1)}:{match.group(2)}"
    if "vertical" in text.lower() or "portrait" in text.lower():
        return "9:16"
    if "square" in text.lower() or "carré" in text.lower():
        return "1:1"
    return ""


def apply_if_empty(current: Dict[str, Any], field: str, value: str) -> Dict[str, Any]:
    if not value:
        return {}
    existing = current.get(field)
    if isinstance(existing, str) and existing.strip():
        return {}
    if existing not in (None, "", 0):
        return {}
    return {field: value}


def has_negative(text: str, patterns: List[str]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def has_positive(text: str, patterns: List[str]) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def get_str(source_state: Dict[str, Any], path: List[str]) -> str:
    current: Any = source_state
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current.strip() if isinstance(current, str) else ""


def get_list(source_state: Dict[str, Any], path: List[str]) -> List[str]:
    current: Any = source_state
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if isinstance(current, list):
        return [str(item).strip() for item in current if str(item).strip()]
    return []


def extract_json_block(content: str) -> str:
    if "```json" not in content:
        return ""
    _, _, rest = content.partition("```json")
    json_block = rest
    if "```" in rest:
        json_block, _, _ = rest.partition("```")
    return json_block.strip()


def parse_json_payload(payload: str, fallback: str) -> Optional[Dict[str, Any]]:
    if payload:
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    trimmed = fallback.strip()
    if not trimmed:
        return None
    start = trimmed.find("{")
    end = trimmed.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(trimmed[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None
