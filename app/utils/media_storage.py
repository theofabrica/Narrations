"""
Helper functions for downloading and storing media files in handlers.
"""
from typing import Dict, Any, Optional, List
from app.utils.storage import download_file, get_storage_path
from app.utils.ftp_storage import upload_to_ftp, is_ftp_enabled
from app.utils.logging import logger
from app.config.settings import settings
from app.mcp.schemas import AssetLink


def get_project_name(payload: Dict[str, Any], trace: Optional[Any] = None) -> str:
    """
    Extract project name from payload or trace.
    
    Args:
        payload: Request payload
        trace: Trace info from request
    
    Returns:
        Project name (default: "default")
    """
    # Try payload first
    project_name = payload.get("project_name") or payload.get("project")
    
    # Try trace
    if not project_name and trace:
        project_name = trace.project if hasattr(trace, 'project') else None
    
    # Default
    if not project_name:
        project_name = "default"
    
    return project_name


def download_and_store_asset(
    provider_url: str,
    project_name: str,
    asset_type: str,
    asset_id: str,
    created_at: str
) -> Optional[AssetLink]:
    """
    Download asset from provider URL and store it locally; optionally upload to SFTP.
    
    Returns:
        AssetLink with local or FTP URL, or None if download disabled/failed
    """
    if not settings.STORAGE_DOWNLOAD_ENABLED:
        logger.debug("Storage download disabled, skipping file download")
        return None
    
    if not provider_url or provider_url == "pending":
        logger.warning(f"Cannot download {asset_type}: invalid URL")
        return None
    
    try:
        # Download and store file locally
        storage_info = download_file(
            url=provider_url,
            project_name=project_name,
            asset_type=asset_type,
            asset_id=asset_id
        )
        
        # Default link: local storage
        link = AssetLink(
            url=storage_info["url"],
            asset_id=asset_id,
            asset_type=asset_type,
            provider="local",
            created_at=created_at
        )

        # Optional: upload to SFTP if enabled
        if is_ftp_enabled():
            ftp_info = upload_to_ftp(
                local_path=storage_info["local_path"],
                project_name=project_name,
                asset_type=asset_type,
                filename=storage_info["filename"]
            )
            if ftp_info and ftp_info.get("url"):
                link = AssetLink(
                    url=ftp_info["url"],
                    asset_id=asset_id,
                    asset_type=asset_type,
                    provider="ftp",
                    created_at=created_at
                )
        
        return link
    
    except Exception as e:
        logger.error(f"Failed to download/store {asset_type} from {provider_url}: {e}", exc_info=True)
        # Return None to fall back to provider URL
        return None


def process_asset_links(
    links: List[Any],
    project_name: str,
    asset_type: str,
    created_at: str
) -> List[Dict[str, Any]]:
    """
    Process asset links: download and store if enabled, or keep provider URLs.
    
    Args:
        links: List of AssetLink objects or dicts
        project_name: Project name
        asset_type: Type of asset
        created_at: Creation timestamp
    
    Returns:
        List of processed asset links (as dicts)
    """
    processed_links = []
    
    for link in links:
        # Convert to dict if needed
        if hasattr(link, 'model_dump'):
            link_dict = link.model_dump()
        elif hasattr(link, 'dict'):
            link_dict = link.dict()  # Fallback for Pydantic v1
        else:
            link_dict = link if isinstance(link, dict) else {}
        
        provider_url = link_dict.get("url", "")
        asset_id = link_dict.get("asset_id", "")
        
        # Try to download and store
        local_link = download_and_store_asset(
            provider_url=provider_url,
            project_name=project_name,
            asset_type=asset_type,
            asset_id=asset_id,
            created_at=created_at
        )
        
        if local_link:
            # Use local storage
            processed_links.append(
                local_link.model_dump() if hasattr(local_link, 'model_dump') else local_link.dict()
            )
        else:
            # Fall back to provider URL
            processed_links.append(link_dict)
    
    return processed_links
