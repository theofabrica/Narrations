"""
SFTP storage utilities for uploading media files.
"""
import os
import posixpath
from pathlib import Path
from typing import Optional, Dict, Any
import paramiko
from app.config.settings import settings
from app.utils.logging import logger


def _sanitize_project_name(project_name: str) -> str:
    """Sanitize project name to be filesystem-safe."""
    safe_project_name = "".join(
        c for c in project_name if c.isalnum() or c in ("-", "_", " ")
    ).strip()
    safe_project_name = safe_project_name.replace(" ", "_")
    return safe_project_name or "default"


def is_ftp_enabled() -> bool:
    """Check if SFTP upload is enabled and configured."""
    return bool(
        getattr(settings, "STORAGE_FTP_ENABLED", False)
        and settings.FTP_HOST
        and settings.FTP_USER
        and settings.FTP_PASSWORD
    )


def upload_to_ftp(
    local_path: str,
    project_name: str,
    asset_type: str,
    filename: str
) -> Optional[Dict[str, Any]]:
    """
    Upload a local file to SFTP storage.

    Args:
        local_path: Path to local file
        project_name: Project name for directory structure
        asset_type: Type of asset (image, video, audio)
        filename: Filename to use on remote

    Returns:
        Dict with remote_path and public_url (if configured), or None on failure
    """
    if not is_ftp_enabled():
        return None

    if not os.path.isfile(local_path):
        logger.warning(f"SFTP upload skipped: file not found {local_path}")
        return None

    safe_project = _sanitize_project_name(project_name)
    remote_base = settings.FTP_BASE_DIR.rstrip("/") if settings.FTP_BASE_DIR else ""
    remote_dir = posixpath.join(remote_base, safe_project, asset_type)
    remote_path = posixpath.join(remote_dir, filename)

    try:
        transport = paramiko.Transport((settings.FTP_HOST, settings.FTP_PORT or 22))
        transport.connect(
            username=settings.FTP_USER,
            password=settings.FTP_PASSWORD,
        )
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Ensure remote directories exist
        path_parts = remote_dir.strip("/").split("/")
        current = ""
        for part in path_parts:
            current = posixpath.join(current, part)
            try:
                sftp.stat("/" + current)
            except IOError:
                sftp.mkdir("/" + current)

        # Upload file
        sftp.put(local_path, "/" + remote_path)
        sftp.close()
        transport.close()

        public_url = None
        if settings.FTP_PUBLIC_BASE_URL:
            public_url = f"{settings.FTP_PUBLIC_BASE_URL.rstrip('/')}/{safe_project}/{asset_type}/{filename}"

        logger.info(f"SFTP upload successful: {remote_path}")

        return {
            "remote_path": remote_path,
            "url": public_url or remote_path
        }

    except Exception as e:
        logger.error(f"SFTP upload failed for {local_path}: {e}", exc_info=True)
        return None
