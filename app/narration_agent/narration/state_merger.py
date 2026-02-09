"""Utilities to merge writer patches into project states."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, List, Tuple, Union

from app.utils.project_storage import read_strata, write_strata

PathSegment = Union[str, int]


def merge_target_patch(project_id: str, target_path: str, target_patch: Any) -> dict:
    if not project_id:
        raise ValueError("project_id is required")
    if not target_path:
        raise ValueError("target_path is required")

    strata, segments = _parse_target_path(target_path)
    if not strata:
        raise ValueError(f"Invalid target_path: {target_path}")

    current_state = read_strata(project_id, strata)
    data = current_state.get("data") if isinstance(current_state, dict) else None
    if not isinstance(data, dict):
        data = {}

    updated_data = _apply_patch(deepcopy(data), segments, target_patch)
    return write_strata(project_id, strata, updated_data)


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


def _apply_patch(data: dict, path: List[PathSegment], patch: Any) -> dict:
    if not path:
        if isinstance(data, dict) and isinstance(patch, dict):
            return _deep_merge(data, patch)
        return patch if isinstance(patch, dict) else data

    current: Any = data
    parent: Any = None
    parent_key: PathSegment | None = None

    for idx, segment in enumerate(path[:-1]):
        next_segment = path[idx + 1]
        if isinstance(segment, str):
            if not isinstance(current, dict):
                current = _replace_container(parent, parent_key, {})
            if segment not in current or current[segment] is None:
                current[segment] = [] if isinstance(next_segment, int) else {}
            parent, parent_key = current, segment
            current = current[segment]
        else:
            if not isinstance(current, list):
                current = _replace_container(parent, parent_key, [])
            while len(current) <= segment:
                current.append({} if isinstance(next_segment, str) else [])
            parent, parent_key = current, segment
            current = current[segment]

    last = path[-1]
    if isinstance(last, str):
        if not isinstance(current, dict):
            current = _replace_container(parent, parent_key, {})
        if isinstance(patch, dict) and len(patch) == 1 and last in patch:
            current[last] = _merge_value(current.get(last), patch.get(last))
        else:
            current[last] = _merge_value(current.get(last), patch)
    else:
        if not isinstance(current, list):
            current = _replace_container(parent, parent_key, [])
        while len(current) <= last:
            current.append(None)
        current[last] = _merge_value(current[last], patch)

    return data


def _replace_container(parent: Any, key: PathSegment | None, container: Any) -> Any:
    if parent is None:
        return container
    if isinstance(parent, dict):
        parent[key] = container
    else:
        parent[key] = container
    return container


def _merge_value(existing: Any, patch: Any) -> Any:
    if isinstance(existing, dict) and isinstance(patch, dict):
        return _deep_merge(existing, patch)
    return patch


def _deep_merge(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
