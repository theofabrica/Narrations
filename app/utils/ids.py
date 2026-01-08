"""
ID generators for request_id, job_id, asset_id.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"req_{uuid.uuid4().hex[:16]}"


def generate_job_id(provider: Optional[str] = None) -> str:
    """Generate a unique job ID, optionally prefixed with provider."""
    job_uuid = uuid.uuid4().hex[:16]
    if provider:
        return f"{provider}_job_{job_uuid}"
    return f"job_{job_uuid}"


def generate_asset_id(provider: Optional[str] = None, asset_type: Optional[str] = None) -> str:
    """Generate a unique asset ID, optionally prefixed with provider and type."""
    asset_uuid = uuid.uuid4().hex[:16]
    parts = []
    if provider:
        parts.append(provider)
    if asset_type:
        parts.append(asset_type)
    parts.append("asset")
    parts.append(asset_uuid)
    return "_".join(parts)


def generate_timestamp() -> str:
    """Generate ISO 8601 timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
