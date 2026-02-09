"""Context builder to assemble context packs for writers."""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union

from app.narration_agent.spec_loader import load_json
from app.utils.project_storage import get_strata_path, read_strata

PathSegment = Union[str, int]


@dataclass
class ContextPack:
    target_path: str
    payload: Dict[str, Any]


class ContextBuilder:
    """Build context packs from project states, schemas, and brief."""

    def build(
        self, project_id: str, source_state: Dict[str, Any], target_path: str
    ) -> ContextPack:
        if not project_id:
            raise ValueError("project_id is required")
        if not target_path:
            raise ValueError("target_path is required")

        strata, segments = _parse_target_path(target_path)
        target_state = read_strata(project_id, strata)
        target_data = (
            target_state.get("data") if isinstance(target_state, dict) else {}
        )
        if not isinstance(target_data, dict):
            target_data = {}

        schema = load_json(f"narration/specs/state_structure_{strata}.json") or {}
        schema_data = schema.get("data") if isinstance(schema, dict) else {}
        if not isinstance(schema_data, dict):
            schema_data = {}

        target_current = _get_path_value(target_data, segments) if segments else target_data
        target_schema = _get_schema_value(schema_data, segments) if segments else schema_data

        dependencies = _load_neighbor_dependencies(project_id, strata)
        # Sparse view for prompting: include only non-empty fields as (path, name, value).
        target_strata_non_empty = _collect_non_empty_fields(
            target_data, base_path=strata
        )
        dependencies_non_empty = _collect_non_empty_fields(
            dependencies, base_path="dependencies"
        )

        core = source_state.get("core", {}) if isinstance(source_state, dict) else {}
        thinker = source_state.get("thinker", {}) if isinstance(source_state, dict) else {}
        brief = source_state.get("brief", {}) if isinstance(source_state, dict) else {}
        brief_duration_s = (
            brief.get("target_duration_s") if isinstance(brief, dict) else None
        )
        if brief_duration_s in (None, "", 0):
            brief_duration_s = source_state.get("target_duration_s") if isinstance(source_state, dict) else None
        duration_s = _coerce_duration_seconds(brief_duration_s)

        if strata == "n1":
            n0_state = dependencies.get("n0") if isinstance(dependencies, dict) else {}
            n0_data = n0_state.get("data") if isinstance(n0_state, dict) else {}
            if isinstance(n0_data, dict):
                prod = n0_data.get("production_summary", {})
                if isinstance(prod, dict):
                    if not isinstance(core, dict) or not core.get("summary"):
                        core = {"summary": prod.get("summary", "")} if isinstance(prod.get("summary", ""), str) else core
                    if isinstance(brief, dict) and not brief.get("video_type"):
                        brief = {**brief, "video_type": prod.get("production_type", "")}
                    if duration_s in (None, 0):
                        duration_s = _coerce_duration_seconds(prod.get("target_duration", ""))

        payload = {
            "target_path": target_path,
            "target_section_name": segments[0] if segments else "",
            "writing_typology": _infer_writing_typology(target_path),
            "strategy_question": "",
            "target_current": target_current or {},
            "target_strata_data": target_data or {},
            "target_strata_non_empty": target_strata_non_empty,
            "target_schema": target_schema or {},
            "source_state_id": source_state.get("state_id", ""),
            "project_id": project_id,
            "core_summary": core.get("summary", "") or source_state.get("summary", ""),
            "thinker_constraints": thinker.get("constraints", []),
            "brief_constraints": brief.get("constraints", []),
            "brief_primary_objective": brief.get("primary_objective", ""),
            "brief_project_title": brief.get("project_title", ""),
            "brief_video_type": brief.get("video_type", "") or source_state.get("video_type", ""),
            "brief_target_duration_s": duration_s,
            "brief_secondary_objectives": brief.get("secondary_objectives", []),
            "brief_priorities": brief.get("priorities", []),
            "missing": source_state.get("missing", []),
            "pending_questions": source_state.get("pending_questions", []),
            "dependencies": dependencies,
            "dependencies_non_empty": dependencies_non_empty,
            "style_constraints": {"language": "en", "tone": "", "format": ""},
            "strategy_card": {},
            "redaction_constraints": {"min_chars": 0, "max_chars": 0},
            "rules": {
                "strategy_role": "",
                "strategy_hints": [],
                "redaction_rules": [],
                "quality_criteria": [],
                "extra_rule": "",
            },
            "do_not_invent": True,
        }

        return ContextPack(target_path=target_path, payload=payload)


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _coerce_duration_seconds(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit():
            return max(0, int(trimmed))
    return 0




def _collect_non_empty_fields(data: Any, base_path: str = "") -> List[Dict[str, Any]]:
    """
    Collect only non-empty leaf fields from a nested structure.
    Returns items like: { "path": "n1.data.pitch", "name": "pitch", "value": "..." }.
    """
    out: List[Dict[str, Any]] = []

    def walk(obj: Any, path: str) -> None:
        if _is_empty_value(obj):
            return
        if isinstance(obj, dict):
            for key, val in obj.items():
                key_str = str(key)
                next_path = f"{path}.{key_str}" if path else key_str
                walk(val, next_path)
            return
        if isinstance(obj, list):
            for idx, val in enumerate(obj):
                next_path = f"{path}[{idx}]" if path else f"[{idx}]"
                walk(val, next_path)
            return
        # Leaf value
        name = path.split(".")[-1] if path else ""
        out.append({"path": path, "name": name, "value": obj})

    walk(data, base_path.strip("."))
    return out


def _parse_target_path(target_path: str) -> Tuple[str, List[PathSegment]]:
    parts = target_path.split(".")
    if not parts:
        return "", []
    strata = parts[0].strip().lower()
    segments: List[PathSegment] = []
    for part in parts[1:]:
        segments.extend(_parse_part(part))
    return strata, segments


def _parse_part(part: str) -> List[PathSegment]:
    segments: List[PathSegment] = []
    remaining = part
    while remaining:
        if "[" in remaining:
            before, rest = remaining.split("[", 1)
            if before:
                segments.append(before)
            if "]" not in rest:
                if rest:
                    segments.append(rest)
                break
            index_str, remaining = rest.split("]", 1)
            if index_str.isdigit():
                segments.append(int(index_str))
            elif index_str:
                segments.append(index_str)
        else:
            segments.append(remaining)
            break
    return segments


def _get_path_value(data: Any, segments: List[PathSegment]) -> Any:
    current = data
    for segment in segments:
        if isinstance(segment, int):
            if isinstance(current, list) and len(current) > segment:
                current = current[segment]
            else:
                return {}
        else:
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                return {}
    return current


def _get_schema_value(data: Any, segments: List[PathSegment]) -> Any:
    current = data
    for segment in segments:
        if isinstance(segment, int):
            if isinstance(current, list) and current:
                current = current[0]
            else:
                return {}
        else:
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                return {}
    return current


def _load_neighbor_dependencies(project_id: str, strata: str) -> Dict[str, Any]:
    neighbors = {
        "n0": ["n1"],
        "n1": ["n0", "n2"],
        "n2": ["n1", "n3"],
        "n3": ["n2", "n4"],
        "n4": ["n3", "n5"],
        "n5": ["n4"],
    }
    result: Dict[str, Any] = {
        "n0_ref": "",
        "n0": {},
        "n1_ref": "",
        "n1": {},
        "n2_ref": "",
        "n2": {},
        "n3_ref": "",
        "n3": {},
        "n4_ref": "",
        "n4": {},
        "n5_ref": "",
        "n5": {},
    }
    for neighbor in neighbors.get(strata, []):
        path = get_strata_path(project_id, neighbor)
        if path.exists():
            result[f"{neighbor}_ref"] = str(path)
            try:
                result[neighbor] = read_strata(project_id, neighbor)
            except FileNotFoundError:
                result[neighbor] = {}
    return result


def _infer_writing_typology(target_path: str) -> str:
    mapping = load_json("narration/specs/writing_typology_map.json") or {}
    defaults = mapping.get("defaults", {}) if isinstance(mapping, dict) else {}
    sections_map = mapping.get("sections", {}) if isinstance(mapping, dict) else {}

    strata, segments = _parse_target_path(target_path)
    section = segments[0] if segments and isinstance(segments[0], str) else ""
    if strata and section:
        strata_sections = sections_map.get(strata, {})
        if isinstance(strata_sections, dict) and section in strata_sections:
            return strata_sections[section]
    if strata and strata in defaults:
        return defaults[strata]

    path = target_path.lower()
    if "production_summary" in path or ".summary" in path:
        return "summary"
    if ".pitch" in path or ".intention" in path:
        return "pitch"
    if "characters" in path or "personnages" in path or ".cast" in path:
        return "character"
    if ".structure" in path or ".timeline" in path or ".units" in path:
        return "structure"
    if "sound" in path or "audio" in path or "art_direction" in path:
        return "style"
    if "prompts" in path or "render_specs" in path or "stack" in path:
        return "prompting"
    return "structure"
