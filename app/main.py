"""
FastAPI application entry point.
"""
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.utils.logging import setup_logger
from app.utils.storage import get_storage_path
from app.mcp.schemas import MCPRequest, MCPResponse
from app.mcp.server import handle_mcp_request
from app.utils.errors import to_mcp_error
from app.tools.registry import list_actions
from datetime import datetime, timezone
import asyncio
import json
import uuid
from typing import Dict

# Setup logger
logger = setup_logger("mcp_narrations")

# Session store for SSE streams
SESSION_QUEUES: Dict[str, asyncio.Queue] = {}
DEFAULT_SESSION_ID = "default"


# -------------------------------------------------
# Lifespan event handlers
# -------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info(f"Starting MCP Narrations Server (env={settings.APP_ENV})")
    logger.info(f"Log level: {settings.LOG_LEVEL}")
    logger.info(f"Registered actions: {len(list_actions())}")
    yield
    # Shutdown (if needed in the future)
    logger.info("Shutting down MCP Narrations Server")


# Initialize FastAPI app
app = FastAPI(
    title="MCP Narrations Server",
    description="MCP server for orchestrating Higgsfield and ElevenLabs media generation",
    version="0.1.0",
    lifespan=lifespan
)


# -------------------------------------------------
# Health check endpoint
# -------------------------------------------------

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "MCP Narrations",
        "version": "0.1.0",
        "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }


# -------------------------------------------------
# MCP main endpoint
# -------------------------------------------------

# -------------------------------------------------
# Assets endpoint - serve stored media files
# -------------------------------------------------

@app.get("/assets/{file_path:path}")
def serve_asset(file_path: str):
    """
    Serve stored media files from Media/ directory.
    
    Path format: {project_name}/{asset_type}/{filename}
    Example: /assets/my_project/image/abc123.png
    """
    try:
        storage_root = get_storage_path()
        file_full_path = storage_root / file_path
        
        # Security: ensure file is within storage root
        try:
            file_full_path.resolve().relative_to(storage_root.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not file_full_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_full_path.is_file():
            raise HTTPException(status_code=404, detail="Not a file")
        
        return FileResponse(
            path=str(file_full_path),
            media_type="application/octet-stream"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving asset {file_path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------------------------------
# MCP main endpoint
# -------------------------------------------------

@app.get("/")
def root():
    """Root endpoint to signal service presence."""
    return {
        "service": "MCP Narrations",
        "version": "0.1.0",
        "status": "ok",
        "endpoints": {
            "sse": "/sse",
            "mcp": "/mcp",
            "health": "/health",
            "assets": "/assets/{path}"
        },
        "auth": "none"
    }


@app.get("/mcp")
def mcp_info():
    """
    Lightweight GET endpoint for MCP connector discovery (no OAuth).
    Returns available actions and a hint that POST is required for execution.
    """
    return {
        "service": "MCP Narrations",
        "version": "0.1.0",
        "auth": "none",
        "endpoint": "/mcp",
        "method": "POST",
        "actions": list_actions(),
    }

@app.api_route("/sse", methods=["GET", "POST"])
async def mcp_sse(request: Request):
    """
    Streamable HTTP transport: GET opens SSE stream, POST sends JSON-RPC.
    We associate a session_id to each GET, and POST must include mcp-session-id.
    """
    ready = {
        "type": "server_ready",
        "service": "MCP Narrations",
        "version": "0.1.0",
        "auth": "none",
        "endpoint": "/mcp",
        "method": "POST",
        "actions": list_actions(),
    }

    if request.method == "GET":
        session_id = DEFAULT_SESSION_ID
        queue = SESSION_QUEUES.get(session_id)
        if queue is None:
            queue = asyncio.Queue()
            SESSION_QUEUES[session_id] = queue

        async def event_stream():
            yield ": connected\n\n"
            yield f"data: {json.dumps(ready)}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=10)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"

        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "mcp-session-id": session_id,
        }
        return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)

    # POST branch
    session_id = DEFAULT_SESSION_ID
    queue = SESSION_QUEUES.get(session_id)
    if queue is None:
        queue = asyncio.Queue()
        SESSION_QUEUES[session_id] = queue
    try:
        body = await request.json()
    except Exception:
        body = None

    logger.info("POST /sse session=%s body=%s", session_id, body)

    response_msg = None
    if isinstance(body, dict) and body.get("method") == "initialize":
        protocol_version = (
            body.get("params", {}).get("protocolVersion")
            or "2025-11-25"
        )
        response_msg = {
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {
                "protocolVersion": protocol_version,
                "serverInfo": {
                    "name": "MCP Narrations",
                    "version": "0.1.0",
                },
                "capabilities": {
                    "experimental": {
                        "openai/visibility": {"enabled": True}
                    }
                },
            },
        }
    elif isinstance(body, dict):
        response_msg = {"jsonrpc": "2.0", "id": body.get("id"), "result": {"ok": True}}

    if queue and response_msg:
        try:
            queue.put_nowait(response_msg)
        except Exception as e:
            logger.error("Failed to enqueue SSE response: %s", e, exc_info=True)

    # Also return the JSON-RPC response in HTTP body as fallback
    if response_msg:
        return JSONResponse(content=response_msg)

    return {"status": "ok", "session": session_id}


@app.head("/sse")
def mcp_sse_head():
    """HEAD endpoint to satisfy clients probing SSE."""
    return Response(
        status_code=200,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Content-Type": "text/event-stream",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/sse/log")
async def mcp_sse_log(request: Request):
    """
    Debug: log headers and body received on POST /sse.
    Not used by clients; for troubleshooting only.
    """
    body = await request.body()
    logger.info(
        "POST /sse/log headers=%s body=%s",
        dict(request.headers),
        body.decode(errors="ignore"),
    )
    return {"status": "ok"}


@app.post("/mcp", response_model=MCPResponse)
def mcp_endpoint(request: MCPRequest) -> MCPResponse:
    """
    Main MCP endpoint for handling actions.
    
    Accepts JSON requests with:
    - action: string (required)
    - payload: dict (optional)
    - request_id: string (optional)
    - trace: dict (optional)
    
    Returns normalized MCPResponse with status, data, or error.
    """
    try:
        response = handle_mcp_request(request)
        return response
    except Exception as e:
        # Fallback error handling (should not happen if handle_mcp_request works correctly)
        logger.error(f"Unexpected error in mcp_endpoint: {e}", exc_info=True)
        error = to_mcp_error(e)
        return MCPResponse(
            status="error",
            action=request.action if request else "unknown",
            request_id=None,
            data=None,
            error=error,
            received_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            completed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development"
    )
