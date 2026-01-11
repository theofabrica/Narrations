"""
Storage utilities for downloading and organizing media files.
"""
import os
import httpx
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from app.config.settings import settings
from app.utils.errors import InternalError
from app.utils.logging import logger
from app.utils.ids import generate_asset_id


# Default storage path
STORAGE_ROOT = Path(__file__).parent.parent.parent / "Media"


def get_storage_path() -> Path:
    """Get the root storage path."""
    storage_path = getattr(settings, "STORAGE_PATH", None)
    if storage_path:
        return Path(storage_path)
    return STORAGE_ROOT


def ensure_project_directory(project_name: str, asset_type: str) -> Path:
    """
    Ensure project directory exists and return the path.
    
    Args:
        project_name: Project name (used as directory name)
        asset_type: Type of asset (image, video, audio)
    
    Returns:
        Path to the project's asset type directory
    """
    if not project_name:
        raise ValueError("project_name is required")
    
    # Sanitize project name (remove invalid characters)
    safe_project_name = "".join(c for c in project_name if c.isalnum() or c in ('-', '_', ' ')).strip()
    safe_project_name = safe_project_name.replace(' ', '_')
    
    if not safe_project_name:
        safe_project_name = "default"
    
    storage_root = get_storage_path()
    project_path = storage_root / safe_project_name / "Media" / asset_type
    
    # Create directory if it doesn't exist
    project_path.mkdir(parents=True, exist_ok=True)
    
    return project_path


def get_file_extension_from_url(url: str, content_type: Optional[str] = None) -> str:
    """
    Determine file extension from URL or content type.
    
    Args:
        url: File URL
        content_type: HTTP Content-Type header (optional)
    
    Returns:
        File extension (with dot, e.g., '.mp4')
    """
    # Try to get extension from URL
    parsed = urlparse(url)
    path = parsed.path
    if path:
        ext = os.path.splitext(path)[1]
        if ext:
            return ext.lower()
    
    # Try to get from content type
    if content_type:
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/mpeg': '.mp4',
            'video/quicktime': '.mov',
            'video/x-msvideo': '.avi',
            'audio/mpeg': '.mp3',
            'audio/mp3': '.mp3',
            'audio/wav': '.wav',
            'audio/wave': '.wav',
            'audio/ogg': '.ogg',
            'audio/webm': '.webm',
        }
        ext = content_type_map.get(content_type.lower())
        if ext:
            return ext
    
    # Default extensions by asset type (fallback)
    if 'image' in url.lower() or 'image' in (content_type or '').lower():
        return '.png'
    elif 'video' in url.lower() or 'video' in (content_type or '').lower():
        return '.mp4'
    elif 'audio' in url.lower() or 'audio' in (content_type or '').lower():
        return '.mp3'
    
    return '.bin'  # Generic binary


def download_file(
    url: str,
    project_name: str,
    asset_type: str,
    asset_id: Optional[str] = None,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    Download a file from URL and save it to project directory.
    
    Args:
        url: URL of the file to download
        project_name: Project name (used for directory structure)
        asset_type: Type of asset (image, video, audio)
        asset_id: Optional asset ID (used in filename if provided)
        filename: Optional custom filename (without extension)
    
    Returns:
        Dict with:
            - local_path: Path to the saved file
            - url: Local URL path (relative to storage root)
            - filename: Name of the saved file
            - size: File size in bytes
    """
    if not url or url == "pending":
        raise ValueError("Invalid URL provided")
    
    logger.info(f"Downloading {asset_type} from {url} for project '{project_name}'")
    
    try:
        # Ensure project directory exists
        project_dir = ensure_project_directory(project_name, asset_type)
        
        # Download file
        with httpx.Client(timeout=300, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            
            # Get content type
            content_type = response.headers.get("content-type", "")
            
            # Determine filename
            if filename:
                file_ext = get_file_extension_from_url(url, content_type)
                file_name = f"{filename}{file_ext}"
            elif asset_id:
                file_ext = get_file_extension_from_url(url, content_type)
                file_name = f"{asset_id}{file_ext}"
            else:
                # Generate filename from URL hash
                url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                file_ext = get_file_extension_from_url(url, content_type)
                file_name = f"{url_hash}{file_ext}"
            
            # Ensure unique filename
            local_path = project_dir / file_name
            counter = 1
            while local_path.exists():
                name_part = file_name.rsplit('.', 1)[0]
                ext_part = file_name.rsplit('.', 1)[1] if '.' in file_name else ''
                file_name = f"{name_part}_{counter}.{ext_part}" if ext_part else f"{name_part}_{counter}"
                local_path = project_dir / file_name
                counter += 1
            
            # Save file
            local_path.write_bytes(response.content)
            file_size = local_path.stat().st_size
            
            # Generate relative URL path
            storage_root = get_storage_path()
            relative_path = local_path.relative_to(storage_root)
            url_path = f"/assets/{relative_path.as_posix()}"
            
            logger.info(f"Downloaded {asset_type} to {local_path} ({file_size} bytes)")
            
            return {
                "local_path": str(local_path),
                "url": url_path,
                "filename": file_name,
                "size": file_size,
                "content_type": content_type
            }
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error downloading {url}: {e}")
        raise InternalError(f"Failed to download file: {str(e)}")
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}", exc_info=True)
        raise InternalError(f"Failed to download file: {str(e)}")


def get_asset_url(project_name: str, asset_type: str, filename: str) -> str:
    """
    Generate URL path for a stored asset.
    
    Args:
        project_name: Project name
        asset_type: Type of asset
        filename: Filename
    
    Returns:
        URL path relative to storage root
    """
    safe_project_name = "".join(c for c in project_name if c.isalnum() or c in ('-', '_', ' ')).strip()
    safe_project_name = safe_project_name.replace(' ', '_')
    if not safe_project_name:
        safe_project_name = "default"
    
    relative_path = f"{safe_project_name}/Media/{asset_type}/{filename}"
    return f"/assets/{relative_path}"
