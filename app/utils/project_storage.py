"""
Storage helpers for project strata JSON files.
"""
from pathlib import Path
from typing import Any, Dict, List

import shutil

from app.config.settings import settings
from app.utils.ids import generate_timestamp


STRATA_FILES = {
    "n0": "project_id_N0.json",
    "n1": "project_id_N1.json",
    "n2": "project_id_N2.json",
    "n3": "project_id_N3.json",
    "n4": "project_id_N4.json",
    "n5": "project_id_N5.json",
}


def _safe_project_id(project_id: str) -> str:
    safe_project_id = "".join(
        c for c in project_id if c.isalnum() or c in ("-", "_")
    ).strip()
    return safe_project_id or "default"


def get_data_root() -> Path:
    data_path = settings.DATA_PATH
    if data_path:
        return Path(data_path)
    return Path(__file__).resolve().parent.parent.parent / "data"


def get_project_dir(project_id: str) -> Path:
    if not project_id:
        raise ValueError("project_id is required")
    safe_project_id = _safe_project_id(project_id)
    return get_data_root() / safe_project_id / "metadata"


def get_project_root(project_id: str) -> Path:
    if not project_id:
        raise ValueError("project_id is required")
    safe_project_id = _safe_project_id(project_id)
    return get_data_root() / safe_project_id


def list_projects() -> List[Dict[str, Any]]:
    data_root = get_data_root()
    if not data_root.exists():
        return []
    projects = []
    for entry in data_root.iterdir():
        if not entry.is_dir():
            continue
        metadata_dir = entry / "metadata"
        media_dir = entry / "Media"
        if metadata_dir.exists() or media_dir.exists():
            projects.append(
                {
                    "project_id": entry.name,
                    "has_metadata": metadata_dir.exists(),
                    "has_media": media_dir.exists(),
                }
            )
    return sorted(projects, key=lambda item: item["project_id"])


def delete_project(project_id: str) -> None:
    project_root = get_project_root(project_id)
    if not project_root.exists():
        raise FileNotFoundError(str(project_root))
    shutil.rmtree(project_root)


def get_strata_path(project_id: str, strata: str) -> Path:
    if strata not in STRATA_FILES:
        raise ValueError(f"Unknown strata: {strata}")
    safe_project_id = _safe_project_id(project_id)
    new_path = get_project_dir(project_id) / f"{safe_project_id}_{strata.upper()}.json"
    if new_path.exists():
        return new_path
    legacy_map = {
        "n2": "n2_architecture.json",
        "n3": "n3_sequences.json",
        "n4": "n4_timeline.json",
        "n5": "n5_media.json",
    }
    legacy_name = legacy_map.get(strata)
    if legacy_name:
        legacy_path = get_project_dir(project_id) / legacy_name
        if legacy_path.exists():
            return legacy_path
    if strata == "n5":
        legacy_media = get_project_dir(project_id) / "n4_media.json"
        if legacy_media.exists():
            return legacy_media
    return new_path


def _load_state_template(strata: str) -> Dict[str, Any]:
    template_root = (
        Path(__file__).resolve().parent.parent
        / "narration_agent"
        / "narration"
        / "specs"
    )
    template_path = template_root / f"state_structure_{strata}.json"
    if not template_path.exists():
        return {}
    template = _read_json(template_path)
    if isinstance(template, dict) and isinstance(template.get("data"), dict):
        return template["data"]
    return {}


def read_strata(project_id: str, strata: str) -> Dict[str, Any]:
    path = get_strata_path(project_id, strata)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return _read_json(path)


def write_strata(project_id: str, strata: str, data: Dict[str, Any]) -> Dict[str, Any]:
    path = get_strata_path(project_id, strata)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": project_id,
        "strata": strata,
        "updated_at": generate_timestamp(),
        "data": data,
    }
    _write_json(path, payload)
    return payload


def get_ui_strata_path(project_id: str, strata: str) -> Path:
    safe_project_id = _safe_project_id(project_id)
    return get_project_dir(project_id) / f"{safe_project_id}_{strata.upper()}_UI.json"


def read_ui_strata(project_id: str, strata: str) -> Dict[str, Any]:
    path = get_ui_strata_path(project_id, strata)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return _read_json(path)


def write_ui_strata(
    project_id: str,
    strata: str,
    data: Dict[str, Any],
    source_updated_at: str = "",
) -> Dict[str, Any]:
    path = get_ui_strata_path(project_id, strata)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": project_id,
        "strata": f"{strata}_ui",
        "updated_at": generate_timestamp(),
        "source_updated_at": source_updated_at,
        "data": data,
    }
    _write_json(path, payload)
    return payload


def create_project(project_id: str) -> None:
    project_dir = get_project_dir(project_id)
    if project_dir.exists() and any(project_dir.iterdir()):
        raise ValueError("Project already exists")
    project_dir.mkdir(parents=True, exist_ok=True)
    for strata in STRATA_FILES:
        payload = _load_state_template(strata)
        write_strata(project_id, strata, payload)


def reset_strata(project_id: str, strata: str) -> Dict[str, Any]:
    if strata not in STRATA_FILES:
        raise ValueError(f"Unknown strata: {strata}")
    payload = _load_state_template(strata)
    return write_strata(project_id, strata, payload)


def _read_json(path: Path) -> Dict[str, Any]:
    import json

    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text else {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    import json

    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
