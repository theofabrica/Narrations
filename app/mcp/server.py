"""
MCP server handler - validates requests, dispatches actions, handles errors.
"""
import time
from typing import Dict, Any
from app.mcp.schemas import MCPRequest, MCPResponse, MCPError
from app.tools.registry import dispatch_action, list_actions
from app.utils.errors import to_mcp_error, ValidationError, ActionNotFoundError
from app.utils.ids import generate_request_id, generate_timestamp
from app.utils.logging import logger


def handle_mcp_request(request: MCPRequest) -> MCPResponse:
    """
    Handle an MCP request: validate, dispatch, and return response.
    
    Args:
        request: MCP request
    
    Returns:
        MCP response
    """
    received_at = generate_timestamp()
    request_id = request.request_id or generate_request_id()
    
    # Log request
    logger.info(
        f"Received MCP request: action={request.action}, "
        f"request_id={request_id}"
    )
    
    if request.trace:
        logger.debug(
            f"Trace info: project={request.trace.project}, "
            f"user={request.trace.user}, session={request.trace.session}"
        )
    
    start_time = time.time()
    
    try:
        # Validate request
        if not request.action:
            raise ValidationError("Action is required")
        
        # Dispatch action (pass trace in payload for handlers to access)
        try:
            payload_with_trace = request.payload or {}
            if request.trace:
                payload_with_trace["_trace"] = request.trace
            data = dispatch_action(request.action, payload_with_trace)
            completed_at = generate_timestamp()
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Action completed: action={request.action}, "
                f"request_id={request_id}, latency_ms={latency_ms}"
            )
            
            return MCPResponse(
                status="ok",
                action=request.action,
                request_id=request_id,
                data=data,
                error=None,
                received_at=received_at,
                completed_at=completed_at
            )
        
        except ActionNotFoundError as e:
            # Action not found - return error response
            error = to_mcp_error(e)
            completed_at = generate_timestamp()
            
            logger.warning(
                f"Action not found: action={request.action}, "
                f"request_id={request_id}"
            )
            
            return MCPResponse(
                status="error",
                action=request.action,
                request_id=request_id,
                data=None,
                error=error,
                received_at=received_at,
                completed_at=completed_at
            )
    
    except Exception as e:
        # Unexpected error - convert to MCP error
        error = to_mcp_error(e)
        completed_at = generate_timestamp()
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.error(
            f"Error processing request: action={request.action}, "
            f"request_id={request_id}, error={error.code}, "
            f"latency_ms={latency_ms}",
            exc_info=True
        )
        
        return MCPResponse(
            status="error",
            action=request.action,
            request_id=request_id,
            data=None,
            error=error,
            received_at=received_at,
            completed_at=completed_at
        )
