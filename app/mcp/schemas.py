"""
Pydantic schemas for MCP requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class TraceInfo(BaseModel):
    """Trace information for request tracking."""
    project: Optional[str] = None
    user: Optional[str] = None
    session: Optional[str] = None


class MCPRequest(BaseModel):
    """MCP request schema."""
    action: str = Field(..., description="Action to execute")
    payload: Optional[Dict[str, Any]] = Field(None, description="Action payload")
    request_id: Optional[str] = Field(None, description="Client-provided request ID")
    trace: Optional[TraceInfo] = Field(None, description="Trace information")


class MCPError(BaseModel):
    """Normalized error schema."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retryable: bool = Field(False, description="Whether the error is retryable")


class MCPResponse(BaseModel):
    """MCP response schema."""
    status: str = Field(..., description="Status: 'received', 'ok', or 'error'")
    action: str = Field(..., description="Action that was executed")
    request_id: Optional[str] = Field(None, description="Request ID")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[MCPError] = Field(None, description="Error information if status is 'error'")
    received_at: str = Field(..., description="ISO timestamp when request was received")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when request was completed")


class AssetLink(BaseModel):
    """Asset link with metadata."""
    url: str
    asset_id: str
    asset_type: str
    provider: str
    created_at: str


class JobStatus(BaseModel):
    """Job status information."""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    provider: str
    model: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    created_at: str
    completed_at: Optional[str] = None
    links: List[AssetLink] = Field(default_factory=list)
    error: Optional[MCPError] = None
