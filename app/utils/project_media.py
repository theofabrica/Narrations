"""
Helpers for storing project media files under project folders.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any, Optional

import httpx
from fastapi import UploadFile

from app.utils.storage import get_file_extension_from_url
from app.utils.project_storage import get_data_root


def _sanitize_project_id(project_id: str) -> str:
    safe_project_id = "".join(
        c for c in project_id if c.isalnum() or c in ("-", "_")
    ).strip()
    return safe_project_id or "default"


def get_project_media_dir(project_id: str, category: str) -> Path:
    safe_project_id = _sanitize_project_id(project_id)
    path = get_data_root() / safe_project_id / "Media" / category
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_n1_pix_dir(project_id: str) -> Path:
    return get_project_media_dir(project_id, "pix")


def get_project_n1_pix_path(project_id: str, filename: str) -> Path:
    directory = get_project_n1_pix_dir(project_id)
    safe_name = Path(filename).name
    return directory / safe_name


def ensure_project_media_folders(project_id: str) -> None:
    for category in ("pix", "video", "dialogue", "soundfx", "music"):
        get_project_media_dir(project_id, category)


def _next_media_index(directory: Path, prefix: str) -> int:
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)")
    max_index = 0
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        match = pattern.match(entry.name)
        if not match:
            continue
        try:
            max_index = max(max_index, int(match.group(1)))
        except ValueError:
            continue
    return max_index + 1


async def save_project_image_upload(
    project_id: str,
    file: UploadFile,
) -> Dict[str, Any]:
    directory = get_project_n1_pix_dir(project_id)
    prefix = f"{_sanitize_project_id(project_id)}_N0_image_"
    index = _next_media_index(directory, prefix)
    ext = Path(file.filename or "").suffix
    if not ext:
        ext = get_file_extension_from_url("", file.content_type or "") or ".bin"
    filename = f"{prefix}{index:02d}{ext}"
    destination = directory / filename
    content = await file.read()
    destination.write_bytes(content)
    return {"filename": filename, "local_path": str(destination)}


async def save_project_n1_character_image_upload(
    project_id: str,
    character_index: int,
    file: UploadFile,
) -> Dict[str, Any]:
    if character_index < 1:
        raise ValueError("character_index must be >= 1")
    directory = get_project_n1_pix_dir(project_id)
    prefix = f"N1_char_{character_index:02d}_image_"
    index = _next_media_index(directory, prefix)
    ext = Path(file.filename or "").suffix
    if not ext:
        ext = get_file_extension_from_url("", file.content_type or "") or ".bin"
    filename = f"{prefix}{index:02d}{ext}"
    destination = directory / filename
    content = await file.read()
    destination.write_bytes(content)
    return {"filename": filename, "local_path": str(destination)}


async def save_project_n1_costume_image_upload(
    project_id: str,
    character_index: int,
    costume_index: int,
    file: UploadFile,
) -> Dict[str, Any]:
    if character_index < 1:
        raise ValueError("character_index must be >= 1")
    if costume_index < 1:
        raise ValueError("costume_index must be >= 1")
    directory = get_project_n1_pix_dir(project_id)
    prefix = f"N1_cos_{costume_index:02d}_char_{character_index:02d}_image_"
    index = _next_media_index(directory, prefix)
    ext = Path(file.filename or "").suffix
    if not ext:
        ext = get_file_extension_from_url("", file.content_type or "") or ".bin"
    filename = f"{prefix}{index:02d}{ext}"
    destination = directory / filename
    content = await file.read()
    destination.write_bytes(content)
    return {"filename": filename, "local_path": str(destination)}


async def save_project_n1_motif_image_upload(
    project_id: str,
    motif_index: int,
    file: UploadFile,
) -> Dict[str, Any]:
    if motif_index < 1:
        raise ValueError("motif_index must be >= 1")
    directory = get_project_n1_pix_dir(project_id)
    prefix = f"N1_motif_{motif_index:02d}_image_"
    index = _next_media_index(directory, prefix)
    ext = Path(file.filename or "").suffix
    if not ext:
        ext = get_file_extension_from_url("", file.content_type or "") or ".bin"
    filename = f"{prefix}{index:02d}{ext}"
    destination = directory / filename
    content = await file.read()
    destination.write_bytes(content)
    return {"filename": filename, "local_path": str(destination)}


async def save_project_n1_motif_audio_upload(
    project_id: str,
    motif_index: int,
    file: UploadFile,
) -> Dict[str, Any]:
    if motif_index < 1:
        raise ValueError("motif_index must be >= 1")
    directory = get_project_n1_pix_dir(project_id)
    prefix = f"N1_motif_{motif_index:02d}_audio_"
    index = _next_media_index(directory, prefix)
    ext = Path(file.filename or "").suffix
    if not ext:
        ext = get_file_extension_from_url("", file.content_type or "") or ".bin"
    filename = f"{prefix}{index:02d}{ext}"
    destination = directory / filename
    content = await file.read()
    destination.write_bytes(content)
    return {"filename": filename, "local_path": str(destination)}


def save_project_image_url(project_id: str, url: str) -> Dict[str, Any]:
    directory = get_project_n1_pix_dir(project_id)
    prefix = f"{_sanitize_project_id(project_id)}_N0_image_"
    index = _next_media_index(directory, prefix)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        ext = get_file_extension_from_url(url, content_type)
        filename = f"{prefix}{index:02d}{ext}"
        destination = directory / filename
        destination.write_bytes(response.content)
    return {"filename": filename, "local_path": str(destination)}


def save_project_audio_url(project_id: str, url: str) -> Dict[str, Any]:
    directory = get_project_media_dir(project_id, "music")
    prefix = f"{_sanitize_project_id(project_id)}_N0_audio_"
    index = _next_media_index(directory, prefix)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        ext = get_file_extension_from_url(url, content_type)
        filename = f"{prefix}{index:02d}{ext}"
        destination = directory / filename
        destination.write_bytes(response.content)
    return {"filename": filename, "local_path": str(destination)}
