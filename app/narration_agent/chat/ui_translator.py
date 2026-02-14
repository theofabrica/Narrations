"""UI translation agent for project strata."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List

from app.narration_agent.llm_client import LLMClient, LLMRequest
from app.utils.logging import setup_logger
from app.utils.project_storage import read_strata, write_strata, write_ui_strata

UI_TRANSLATE_FIELDS = {
    "n0": [
        "narrative_presentation.summary",
        "narrative_presentation.production_type",
        "production_summary.summary",
        "production_summary.production_type",
        "art_direction.description",
        "sound_direction.description",
    ],
    "n1": [
        "characters.main_characters.characters",
        "characters.secondary_characters.characters",
        "characters.background_characters.characters",
    ],
}

UI_PASSTHROUGH_FIELDS = {
    "n0": [
        "narrative_presentation.target_duration",
        "narrative_presentation.aspect_ratio",
        "production_summary.target_duration",
        "production_summary.aspect_ratio",
    ],
    "n1": [
        "characters.main_characters.number",
        "characters.main_characters.names",
        "characters.secondary_characters.number",
        "characters.secondary_characters.names",
        "characters.background_characters.number",
        "characters.background_characters.names",
    ],
}

CHAT_TRANSLATE_FIELDS = [
    "core.summary",
    "core.open_questions",
    "core.notes",
    "thinker.objectives",
    "thinker.constraints",
    "thinker.hypotheses",
    "thinker.missing",
    "thinker.clarifications",
    "thinker.notes",
    "brief.primary_objective",
    "brief.project_title",
    "brief.video_type",
    "brief.secondary_objectives",
    "brief.constraints",
    "brief.hypotheses",
    "brief.priorities",
    "missing",
    "pending_questions",
]


class UITranslator:
    """Translate strata content for UI display."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.logger = setup_logger("ui_translator")

    def update_ui_translation(
        self, project_id: str, strata: str, language: str = "fr"
    ) -> Dict[str, Any] | None:
        try:
            source_state = read_strata(project_id, strata)
        except FileNotFoundError:
            return None
        data = source_state.get("data") if isinstance(source_state, dict) else None
        if not isinstance(data, dict):
            return None
        translate_paths = UI_TRANSLATE_FIELDS.get(strata, [])
        if strata == "n1":
            translate_fields = self._select_fields(data, translate_paths)
            translated = self._translate_n1_payload_leafwise(
                translate_fields,
                source_language="en",
                target_language=language,
            )
        else:
            translate_fields = self._select_fields(data, translate_paths)
            translated = self._translate_payload(
                translate_fields, source_language="en", target_language=language
            )
        passthrough = self._select_fields(data, UI_PASSTHROUGH_FIELDS.get(strata, []))
        ui_payload = _deep_merge(translated, passthrough)
        source_updated_at = (
            source_state.get("updated_at", "") if isinstance(source_state, dict) else ""
        )
        return write_ui_strata(
            project_id, strata, ui_payload, source_updated_at=source_updated_at
        )

    def update_source_from_ui(
        self,
        project_id: str,
        strata: str,
        ui_payload: Dict[str, Any],
        source_language: str = "fr",
    ) -> Dict[str, Any] | None:
        try:
            source_state = read_strata(project_id, strata)
        except FileNotFoundError:
            return None
        data = source_state.get("data") if isinstance(source_state, dict) else None
        if not isinstance(data, dict):
            return None
        ui_data = ui_payload.get("data") if isinstance(ui_payload, dict) else None
        if not isinstance(ui_data, dict):
            ui_data = ui_payload if isinstance(ui_payload, dict) else {}
        translate_paths = UI_TRANSLATE_FIELDS.get(strata, [])
        if strata == "n1":
            translate_fields = self._select_fields(ui_data, translate_paths)
            translated = self._translate_n1_payload_leafwise(
                translate_fields,
                source_language=source_language,
                target_language="en",
            )
        else:
            translate_fields = self._select_fields(ui_data, translate_paths)
            translated = self._translate_payload(
                translate_fields, source_language=source_language, target_language="en"
            )
        passthrough = self._select_fields(ui_data, UI_PASSTHROUGH_FIELDS.get(strata, []))
        merged_fields = _deep_merge(translated, passthrough)
        updated = write_strata(project_id, strata, _deep_merge(deepcopy(data), merged_fields))
        self.update_ui_translation(project_id, strata, language=source_language)
        return updated

    def translate_chat_patch(
        self,
        patch: Dict[str, Any],
        source_language: str = "auto",
        target_language: str = "en",
    ) -> Dict[str, Any]:
        if not isinstance(patch, dict):
            return patch
        translate_fields = self._select_fields(patch, CHAT_TRANSLATE_FIELDS)
        translated = self._translate_payload(
            translate_fields, source_language=source_language, target_language=target_language
        )
        return _deep_merge(patch, translated)

    def _translate_payload(
        self, payload: Dict[str, Any], source_language: str, target_language: str
    ) -> Dict[str, Any]:
        if not payload:
            return payload
        system_prompt = (
            "You translate JSON values for UI display.\n"
            f"Source language: {source_language}.\n"
            f"Target language: {target_language}.\n"
            "- Keep keys unchanged.\n"
            "- Preserve JSON structure.\n"
            "- Translate only string values.\n"
            "- Never translate person names in `name` fields.\n"
            "- Never translate file paths in `image_path` fields.\n"
            "- Keep numbers, URLs, codes, and short tokens unchanged.\n"
            "- Return ONLY valid JSON."
        )
        user_prompt = json.dumps(payload, ensure_ascii=True, indent=2)
        response = self.llm_client.complete(
            LLMRequest(
                model=self.llm_client.default_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=1800,
            )
        )
        raw = response.content.strip()
        parsed = self._parse_json(raw)
        if isinstance(parsed, dict):
            return parsed
        self.logger.warning("ui_translation_failed")
        return payload

    def _translate_fields_incremental(
        self,
        payload: Dict[str, Any],
        fields: List[str],
        source_language: str,
        target_language: str,
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict) or not fields:
            return {}
        merged: Dict[str, Any] = {}
        for field_path in fields:
            value = _get_path_value(payload, field_path)
            if value is None:
                continue
            chunk: Dict[str, Any] = {}
            _set_path_value(chunk, field_path, value)
            translated_chunk = self._translate_payload(
                chunk,
                source_language=source_language,
                target_language=target_language,
            )
            merged = _deep_merge(merged, translated_chunk)
        return merged

    def _translate_n1_payload_leafwise(
        self,
        payload: Dict[str, Any],
        source_language: str,
        target_language: str,
    ) -> Dict[str, Any]:
        def walk(value: Any, key_name: str = "", parent_key: str = "") -> Any:
            if isinstance(value, dict):
                out: Dict[str, Any] = {}
                for k, v in value.items():
                    out[k] = walk(v, key_name=str(k), parent_key=key_name)
                return out
            if isinstance(value, list):
                # Keep explicit name lists unchanged.
                if key_name == "names":
                    return value
                return [walk(item, key_name=key_name, parent_key=parent_key) for item in value]
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return value
                # Keep entity names and media paths untouched.
                if key_name in {"name", "image_path"} or parent_key == "names":
                    return value
                translated = self._translate_payload(
                    {"value": value},
                    source_language=source_language,
                    target_language=target_language,
                )
                candidate = translated.get("value") if isinstance(translated, dict) else None
                return candidate if isinstance(candidate, str) and candidate.strip() else value
            return value

        if not isinstance(payload, dict):
            return {}
        translated_payload = walk(payload)
        return translated_payload if isinstance(translated_payload, dict) else {}

    def _select_fields(self, payload: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
        if not fields:
            return payload
        selected: Dict[str, Any] = {}
        for field_path in fields:
            value = _get_path_value(payload, field_path)
            if value is not None:
                _set_path_value(selected, field_path, value)
        return selected

    def _parse_json(self, content: str) -> Dict[str, Any] | None:
        if not content:
            return None
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(content[start : end + 1])
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return None
        return None


def _get_path_value(payload: Dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_path_value(target: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current: Dict[str, Any] = target
    for part in parts[:-1]:
        if part not in current or not isinstance(current.get(part), dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged.get(key, {}), value)
        else:
            merged[key] = value
    return merged
