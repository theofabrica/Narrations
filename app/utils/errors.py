"""
Normalized error handling for MCP server.
"""
from typing import Optional, Dict, Any
from app.mcp.schemas import MCPError


class MCPException(Exception):
    """Base exception for MCP errors."""
    
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(self.message)


class ValidationError(MCPException):
    """Request validation error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details=details,
            retryable=False
        )


class ActionNotFoundError(MCPException):
    """Action not found in registry."""
    
    def __init__(self, action: str):
        super().__init__(
            code="ACTION_NOT_FOUND",
            message=f"Unknown action: {action}",
            details={"action": action},
            retryable=False
        )


class ProviderError(MCPException):
    """Error from external provider (Higgsfield/ElevenLabs)."""
    
    def __init__(
        self,
        provider: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = True
    ):
        super().__init__(
            code=f"{provider.upper()}_ERROR",
            message=message,
            details=details or {},
            retryable=retryable
        )


class InternalError(MCPException):
    """Internal server error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="INTERNAL_ERROR",
            message=message,
            details=details or {},
            retryable=True
        )


def to_mcp_error(exception: Exception) -> MCPError:
    """
    Convert an exception to a normalized MCPError.
    
    Args:
        exception: Exception to convert
    
    Returns:
        MCPError schema instance
    """
    if isinstance(exception, MCPException):
        return MCPError(
            code=exception.code,
            message=exception.message,
            details=exception.details if exception.details else None,
            retryable=exception.retryable
        )
    
    # Unknown exception - convert to internal error
    return MCPError(
        code="INTERNAL_ERROR",
        message=str(exception) or "An unexpected error occurred",
        details={"exception_type": type(exception).__name__},
        retryable=True
    )
