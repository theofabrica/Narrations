"""
FastAPI application entry point.
"""
from fastapi import FastAPI, HTTPException, Response, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.utils.logging import setup_logger
from app.utils.storage import get_storage_path
from app.utils.project_storage import (
    read_strata,
    write_strata,
    list_projects,
    delete_project,
    STRATA_FILES,
    create_project,
)
from app.utils.project_media import (
    save_project_audio_url,
    save_project_image_upload,
    save_project_image_url,
    save_project_n1_character_image_upload,
    save_project_n1_costume_image_upload,
    save_project_n1_motif_image_upload,
    save_project_n1_motif_audio_upload,
    ensure_project_media_folders,
    get_project_n1_pix_path,
)
from app.mcp.schemas import MCPRequest, MCPResponse
from app.mcp.server import handle_mcp_request
from app.utils.errors import to_mcp_error, ProviderError
from app.utils.normalize import normalize_request
from app.tools.registry import list_actions
from app.tools.higgsfield.client import get_client as get_higgsfield_client
from app.agentic.n0_orchestrator import orchestrate_n0
from datetime import datetime, timezone
import asyncio
import json
import uuid
from typing import Dict, Any
from pydantic import BaseModel

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def _extract_higgsfield_result_url(status: Dict[str, Any]) -> str:
    if not isinstance(status, dict):
        return ""
    for key in ("result_url", "url", "image_url", "video_url"):
        value = status.get(key)
        if value:
            return value
    result = status.get("result")
    if isinstance(result, dict):
        for key in ("result_url", "url", "image_url", "video_url"):
            value = result.get(key)
            if value:
                return value
    results = status.get("results")
    if isinstance(results, list) and results:
        entry = results[0]
        if isinstance(entry, dict):
            for key in ("result_url", "url", "image_url", "video_url"):
                value = entry.get(key)
                if value:
                    return value
    images = status.get("images")
    if isinstance(images, list) and images:
        entry = images[0]
        if isinstance(entry, dict):
            value = entry.get("url")
            if value:
                return value
    videos = status.get("videos")
    if isinstance(videos, list) and videos:
        entry = videos[0]
        if isinstance(entry, dict):
            value = entry.get("url")
            if value:
                return value
    jobs = status.get("jobs")
    if isinstance(jobs, list) and jobs:
        job = jobs[0]
        if isinstance(job, dict):
            for key in ("result_url", "url", "image_url", "video_url"):
                value = job.get(key)
                if value:
                    return value
            job_results = job.get("results")
            if isinstance(job_results, list) and job_results:
                entry = job_results[0]
                if isinstance(entry, dict):
                    for key in ("result_url", "url", "image_url", "video_url"):
                        value = entry.get(key)
                        if value:
                            return value
    return ""


@app.middleware("http")
async def log_request_routes(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if (
        path.endswith("/normalize")
        or path.endswith("/mcp")
        or response.status_code == 404
    ):
        logger.info(
            "HTTP %s %s?%s root_path=%s status=%s",
            request.method,
            path,
            request.url.query,
            request.scope.get("root_path", ""),
            response.status_code
        )
    return response

# Optional: serve the web console if built
INTERFACE_DIST = Path(__file__).resolve().parent.parent / "interface" / "dist"
if INTERFACE_DIST.exists():
    app.mount("/console", StaticFiles(directory=INTERFACE_DIST, html=True), name="console")
    logger.info("Console UI mounted at /console")


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
# Project strata endpoints
# -------------------------------------------------

@app.get("/projects/{project_id}/{strata}")
def get_project_strata(project_id: str, strata: str) -> Dict[str, Any]:
    if strata not in STRATA_FILES:
        raise HTTPException(status_code=400, detail="Unknown strata")
    try:
        return read_strata(project_id, strata)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Strata not found")
    except Exception as e:
        logger.error(
            "Error reading strata project=%s strata=%s: %s",
            project_id,
            strata,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/{strata}")
def post_project_strata(
    project_id: str,
    strata: str,
    body: Dict[str, Any],
) -> Dict[str, Any]:
    if strata not in STRATA_FILES:
        raise HTTPException(status_code=400, detail="Unknown strata")
    try:
        return write_strata(project_id, strata, body)
    except Exception as e:
        logger.error(
            "Error writing strata project=%s strata=%s: %s",
            project_id,
            strata,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/n0/orchestrate")
def post_project_n0_orchestrate(
    project_id: str,
    body: Dict[str, Any],
) -> Dict[str, Any]:
    n0_data = body.get("n0")
    if not isinstance(n0_data, dict):
        raise HTTPException(status_code=400, detail="Missing n0 payload")
    try:
        result = orchestrate_n0(n0_data)
        return {"project_id": project_id, "data": result}
    except Exception as e:
        logger.error(
            "Error orchestrating N0 project=%s: %s",
            project_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


class MediaUrlRequest(BaseModel):
    url: str


class ProjectCreateRequest(BaseModel):
    project_id: str


@app.post("/projects/{project_id}/media/pix/upload")
async def upload_project_pix(project_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        result = await save_project_image_upload(project_id, file)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error("Error saving image upload project=%s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/n1/characters/{character_index}/images")
async def upload_n1_character_image(
    project_id: str,
    character_index: int,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    if not file:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        result = await save_project_n1_character_image_upload(
            project_id,
            character_index,
            file
        )
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error saving N1 character image project=%s index=%s: %s",
            project_id,
            character_index,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/n1/characters/{character_index}/costumes/{costume_index}/images")
async def upload_n1_costume_image(
    project_id: str,
    character_index: int,
    costume_index: int,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    if not file:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        result = await save_project_n1_costume_image_upload(
            project_id,
            character_index,
            costume_index,
            file
        )
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error saving N1 costume image project=%s char=%s costume=%s: %s",
            project_id,
            character_index,
            costume_index,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/n1/motifs/{motif_index}/images")
async def upload_n1_motif_image(
    project_id: str,
    motif_index: int,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    if not file:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        result = await save_project_n1_motif_image_upload(
            project_id,
            motif_index,
            file
        )
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error saving N1 motif image project=%s index=%s: %s",
            project_id,
            motif_index,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/n1/motifs/{motif_index}/audio")
async def upload_n1_motif_audio(
    project_id: str,
    motif_index: int,
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    if not file:
        raise HTTPException(status_code=400, detail="File is required")
    try:
        result = await save_project_n1_motif_audio_upload(
            project_id,
            motif_index,
            file
        )
        return {"status": "ok", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error saving N1 motif audio project=%s index=%s: %s",
            project_id,
            motif_index,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/projects/{project_id}/mediapix/{filename}")
def get_n1_character_image(project_id: str, filename: str) -> Response:
    try:
        file_path = get_project_n1_pix_path(project_id, filename)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            path=str(file_path),
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error serving N1 image project=%s file=%s: %s",
            project_id,
            filename,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/projects/{project_id}/n1/characters/{character_index}/images/{filename}")
def delete_n1_character_image(
    project_id: str,
    character_index: int,
    filename: str
) -> Dict[str, Any]:
    if character_index < 1:
        raise HTTPException(status_code=400, detail="character_index must be >= 1")
    safe_filename = Path(filename).name
    expected_prefix = f"N1_char_{character_index:02d}_image_"
    if not safe_filename.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="Invalid filename prefix")
    try:
        file_path = get_project_n1_pix_path(project_id, safe_filename)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        file_path.unlink()
        return {"status": "ok", "filename": safe_filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting N1 image project=%s file=%s: %s",
            project_id,
            safe_filename,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/projects/{project_id}/n1/characters/{character_index}/costumes/{costume_index}/images/{filename}")
def delete_n1_costume_image(
    project_id: str,
    character_index: int,
    costume_index: int,
    filename: str
) -> Dict[str, Any]:
    if character_index < 1:
        raise HTTPException(status_code=400, detail="character_index must be >= 1")
    if costume_index < 1:
        raise HTTPException(status_code=400, detail="costume_index must be >= 1")
    safe_filename = Path(filename).name
    expected_prefix = f"N1_cos_{costume_index:02d}_char_{character_index:02d}_image_"
    if not safe_filename.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="Invalid filename prefix")
    try:
        file_path = get_project_n1_pix_path(project_id, safe_filename)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        file_path.unlink()
        return {"status": "ok", "filename": safe_filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting N1 costume image project=%s file=%s: %s",
            project_id,
            safe_filename,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/projects/{project_id}/n1/motifs/{motif_index}/images/{filename}")
def delete_n1_motif_image(
    project_id: str,
    motif_index: int,
    filename: str
) -> Dict[str, Any]:
    if motif_index < 1:
        raise HTTPException(status_code=400, detail="motif_index must be >= 1")
    safe_filename = Path(filename).name
    expected_prefix = f"N1_motif_{motif_index:02d}_image_"
    if not safe_filename.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="Invalid filename prefix")
    try:
        file_path = get_project_n1_pix_path(project_id, safe_filename)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        file_path.unlink()
        return {"status": "ok", "filename": safe_filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting N1 motif image project=%s file=%s: %s",
            project_id,
            safe_filename,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/projects/{project_id}/n1/motifs/{motif_index}/audio/{filename}")
def delete_n1_motif_audio(
    project_id: str,
    motif_index: int,
    filename: str
) -> Dict[str, Any]:
    if motif_index < 1:
        raise HTTPException(status_code=400, detail="motif_index must be >= 1")
    safe_filename = Path(filename).name
    expected_prefix = f"N1_motif_{motif_index:02d}_audio_"
    if not safe_filename.startswith(expected_prefix):
        raise HTTPException(status_code=400, detail="Invalid filename prefix")
    try:
        file_path = get_project_n1_pix_path(project_id, safe_filename)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        file_path.unlink()
        return {"status": "ok", "filename": safe_filename}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error deleting N1 motif audio project=%s file=%s: %s",
            project_id,
            safe_filename,
            e,
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/media/pix/url")
def upload_project_pix_url(project_id: str, body: MediaUrlRequest) -> Dict[str, Any]:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    try:
        result = save_project_image_url(project_id, url)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error("Error saving image url project=%s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/projects/{project_id}/media/audio/url")
def upload_project_audio_url(project_id: str, body: MediaUrlRequest) -> Dict[str, Any]:
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    try:
        result = save_project_audio_url(project_id, url)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error("Error saving audio url project=%s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# -------------------------------------------------
# Project management pages
# -------------------------------------------------

@app.get("/projects")
def list_projects_endpoint() -> Dict[str, Any]:
    projects = list_projects()
    return {"projects": projects, "count": len(projects)}


@app.post("/projects")
def create_project_endpoint(body: ProjectCreateRequest) -> Dict[str, Any]:
    project_id = body.project_id.strip()
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    try:
        create_project(project_id)
        ensure_project_media_folders(project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating project %s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"status": "ok", "project_id": project_id}


@app.delete("/projects/{project_id}")
def delete_project_endpoint(project_id: str) -> Dict[str, Any]:
    try:
        delete_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    except Exception as e:
        logger.error("Error deleting project %s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"status": "ok", "project_id": project_id}


def _render_project_list(projects: list[Dict[str, Any]]) -> str:
    items = []
    for project in projects:
        project_id = project["project_id"]
        items.append(
            f"<li><a href=\"/projects/ui/{project_id}\">{project_id}</a></li>"
        )
    if not items:
        items.append("<li><em>Aucun projet trouve.</em></li>")
    items_html = "\n".join(items)
    return f"""
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <title>Projets Narrations</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; color: #1f2937; }}
      h1 {{ margin-bottom: 8px; }}
      ul {{ padding-left: 18px; }}
      a {{ color: #1d4ed8; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
    </style>
  </head>
  <body>
    <h1>Projets</h1>
    <p>Total: {len(projects)}</p>
    <ul>{items_html}</ul>
  </body>
</html>
"""


def _render_project_detail(project_id: str) -> str:
    links = []
    for strata in STRATA_FILES:
        links.append(
            f"<li><a href=\"/projects/{project_id}/{strata}\">{strata.upper()}</a></li>"
        )
    links_html = "\n".join(links)
    return f"""
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <title>Projet {project_id}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; color: #1f2937; }}
      a {{ color: #1d4ed8; text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      ul {{ padding-left: 18px; }}
      .danger {{ margin-top: 24px; }}
      .danger button {{ background: #dc2626; color: #fff; border: 0; padding: 8px 14px; cursor: pointer; }}
    </style>
  </head>
  <body>
    <h1>Projet {project_id}</h1>
    <p><a href="/projects/ui">Retour aux projets</a></p>
    <h2>Metadonnees</h2>
    <ul>{links_html}</ul>
    <form class="danger" method="post" action="/projects/ui/{project_id}/delete">
      <input type="hidden" name="confirm" value="yes">
      <button type="submit">Supprimer le projet</button>
    </form>
  </body>
</html>
"""


@app.get("/projects/ui", response_class=HTMLResponse)
def projects_ui() -> HTMLResponse:
    projects = list_projects()
    return HTMLResponse(_render_project_list(projects))


@app.get("/projects/ui/{project_id}", response_class=HTMLResponse)
def project_ui_detail(project_id: str) -> HTMLResponse:
    return HTMLResponse(_render_project_detail(project_id))


@app.post("/projects/ui/{project_id}/delete")
async def project_ui_delete(project_id: str, request: Request) -> Response:
    # Basic guard: require form confirmation.
    try:
        form = await request.form()
    except Exception:
        form = {}
    confirm = form.get("confirm") if form else None
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Confirmation requise")
    try:
        delete_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Projet introuvable")
    except Exception as e:
        logger.error("Error deleting project %s: %s", project_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    return Response(status_code=303, headers={"Location": "/projects/ui"})


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
        session_id = f"sse_{uuid.uuid4().hex}"
        queue = asyncio.Queue()
        SESSION_QUEUES[session_id] = queue

        async def event_stream():
            try:
                yield ": connected\n\n"
                yield f"data: {json.dumps(ready)}\n\n"
                while True:
                    try:
                        msg = await asyncio.wait_for(queue.get(), timeout=10)
                        yield f"data: {json.dumps(msg)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                if SESSION_QUEUES.get(session_id) is queue:
                    del SESSION_QUEUES[session_id]

        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "mcp-session-id": session_id,
        }
        return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)

    # POST branch
    session_id = (
        request.headers.get("mcp-session-id")
        or request.query_params.get("mcp-session-id")
        or DEFAULT_SESSION_ID
    )
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


@app.post("/normalize")
def normalize_endpoint(
    request: Request,
    body: Dict[str, Any],
    dispatch: bool = True
) -> Dict[str, Any]:
    """
    Normalize raw ChatGPT JSON into canonical MCP request.
    If dispatch is true, also execute the request and return the response.
    """
    logger.info(
        "Normalize payload keys=%s dispatch=%s path=%s",
        list(body.keys()),
        dispatch,
        request.url.path
    )
    normalized = normalize_request(body)
    result: Dict[str, Any] = {"normalized": normalized}

    if dispatch:
        request = MCPRequest(**normalized)
        response = handle_mcp_request(request)
        result["response"] = response.model_dump()

    return result


@app.get("/higgsfield/status/{job_id}")
def higgsfield_status(
    job_id: str,
    status_url: str | None = None
) -> Dict[str, Any]:
    client = get_higgsfield_client()
    try:
        if status_url:
            status = client.get_status_by_url(status_url)
        else:
            status = client.get_request_status(job_id)
    except ProviderError as e:
        details = e.details or {}
        if details.get("status_code") == 404:
            try:
                status = client.get_job_status(job_id)
            except ProviderError as fallback_error:
                return {
                    "status": "error",
                    "error": {
                        "code": fallback_error.code,
                        "message": fallback_error.message,
                        "details": fallback_error.details,
                        "retryable": fallback_error.retryable
                    }
                }
        else:
            return {
                "status": "error",
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "details": e.details,
                    "retryable": e.retryable
                }
            }
    result_url = _extract_higgsfield_result_url(status)
    return {
        "status": status.get("status"),
        "result_url": result_url,
        "raw": status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.APP_ENV == "development"
    )
