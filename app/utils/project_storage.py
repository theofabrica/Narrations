"""
Storage helpers for project strata JSON files.
"""
from pathlib import Path
from typing import Any, Dict, List

import shutil

from app.config.settings import settings
from app.utils.ids import generate_timestamp


STRATA_FILES = {
    "n0": "dynamic",
    "n1": "dynamic",
    "n2": "n2_architecture.json",
    "n3": "n3_sequences.json",
    "n4": "n4_timeline.json",
    "n5": "n5_media.json",
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
    if strata == "n0":
        safe_project_id = _safe_project_id(project_id)
        return get_project_dir(project_id) / f"{safe_project_id}_N0.json"
    if strata == "n1":
        safe_project_id = _safe_project_id(project_id)
        return get_project_dir(project_id) / f"{safe_project_id}_N1.json"
    if strata in ("n2", "n3", "n4", "n5"):
        safe_project_id = _safe_project_id(project_id)
        legacy_path = get_project_dir(project_id) / f"{safe_project_id}_{strata.upper()}.json"
        if legacy_path.exists():
            return legacy_path
    if strata == "n5":
        legacy_media = get_project_dir(project_id) / "n4_media.json"
        if legacy_media.exists():
            return legacy_media
    if strata not in STRATA_FILES:
        raise ValueError(f"Unknown strata: {strata}")
    return get_project_dir(project_id) / STRATA_FILES[strata]


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


def create_project(project_id: str) -> None:
    project_dir = get_project_dir(project_id)
    if project_dir.exists() and any(project_dir.iterdir()):
        raise ValueError("Project already exists")
    project_dir.mkdir(parents=True, exist_ok=True)
    n0_payload = {
        "production_summary": {
            "summary": "",
            "production_type": "",
            "primary_output_format": "",
            "target_duration": "",
            "aspect_ratio": "",
            "visual_style": "",
            "tone": "",
            "era": "",
        },
        "balises": [],
        "deliverables": {
            "visuals": {
                "images_enabled": True,
                "videos_enabled": True,
            },
            "audio_stems": {
                "dialogue": True,
                "sfx": True,
                "music": True,
            },
        },
        "art_direction": {
            "description": "",
            "references": "",
        },
        "sound_direction": {
            "description": "",
            "references": "",
        },
    }
    write_strata(project_id, "n0", n0_payload)
    n1_payload = {
        "meta": {
            "status": "draft",
            "version": "0.1",
            "temperature_creative": 2,
        },
        "balises": [],
        "pitch": "",
        "intention": "",
        "axes_artistiques": "",
        "dynamique_globale": "",
        "personnages": [],
        "monde_epoque": "",
        "esthetique": "",
        "son": {
            "ambiances": "",
            "musique": "",
            "sfx": "",
            "dialogues": "",
        },
        "motifs": [],
        "ancres_canon_continuite": [],
        "sources": "",
        "hypotheses": "",
        "questions": "",
    }
    write_strata(project_id, "n1", n1_payload)
    n2_payload = {
        "meta": {
            "status": "draft",
            "version": "0.1",
            "dependencies": {
                "n0": "",
                "n1": "",
            },
        },
        "balises": [],
        "rappel_entrees": "",
        "structure": {
            "format": "",
            "justification": "",
        },
        "granularite": {
            "niveau": "",
            "justification": "",
        },
        "units": [],
        "contraintes_verifications": "",
        "hypotheses": "",
        "questions": "",
        "references": [],
        "cartographie_macro": {
            "arc_principal": "",
            "arcs_secondaires": [],
            "motifs_variation": "",
        },
    }
    write_strata(project_id, "n2", n2_payload)
    timeline_payload = {
        "meta": {
            "status": "draft",
            "version": "0.1",
            "dependencies": {
                "n2": "",
                "n3": "",
            },
        },
        "tracks": [
            {"id": "V1", "type": "video", "label": "Video 1", "segments": []},
            {"id": "A1", "type": "audio", "label": "Audio 1", "segments": []},
            {"id": "A2", "type": "audio", "label": "Audio 2", "segments": []},
            {"id": "A3", "type": "audio", "label": "Audio 3", "segments": []},
        ],
        "notes": "",
    }
    write_strata(project_id, "n4", timeline_payload)
    write_strata(project_id, "n5", {})


def _read_json(path: Path) -> Dict[str, Any]:
    import json

    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text else {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    import json

    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
