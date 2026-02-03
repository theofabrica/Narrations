"""Bootstrap R2R server and ingest narratology sources on startup."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.utils.ids import generate_timestamp
from app.utils.logging import setup_logger
from app.utils.project_storage import get_data_root
from app.narration_agent.writer_agent.strategy_finder.library_rag import LibraryRAG

logger = setup_logger("rag_bootstrap")

_R2R_PROCESS: Optional[subprocess.Popen] = None
_POSTGRES_STARTED = False


def ensure_rag_ready() -> None:
    """Ensure R2R is running and narratology sources are ingested."""
    started_at = time.monotonic()
    _ensure_r2r_env_defaults()
    log_payload: Dict[str, Any] = {
        "status": "",
        "rag_base": os.environ.get("R2R_API_BASE", "http://localhost:7272"),
        "auto_start": _env_flag("R2R_AUTO_START", default=True),
        "auto_ingest": _env_flag("R2R_AUTO_INGEST", default=True),
        "docker_auto_start": _env_flag("R2R_DOCKER_AUTO_START", default=True),
        "server_started": False,
        "server_ready": False,
        "server_ready_ms": 0,
        "ingest_items": 0,
        "ingest_ms": 0,
        "postgres_status": "",
        "postgres_ready": False,
        "postgres_ready_ms": 0,
        "docker_compose": "",
        "logged_at": generate_timestamp(),
    }
    if not _env_flag("R2R_AUTO_START", default=True):
        logger.info("R2R auto-start disabled")
        log_payload["status"] = "auto_start_disabled"
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)
        return

    base_url = log_payload["rag_base"]
    if not _is_local_base(base_url):
        logger.info("R2R base is remote; skipping auto-start")
        log_payload["status"] = "remote_base"
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)
        return

    postgres_info = _start_postgres_docker()
    log_payload.update(postgres_info)

    if _is_r2r_healthy(base_url):
        ingest_info = _auto_ingest()
        log_payload.update(ingest_info)
        log_payload["status"] = "already_running"
        log_payload["server_ready"] = True
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)
        return

    if not _is_r2r_installed():
        logger.warning("R2R package not available; cannot start server")
        log_payload["status"] = "r2r_not_installed"
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)
        return

    started = _start_r2r_server()
    if not started:
        logger.warning("Failed to start R2R server process")
        log_payload["status"] = "start_failed"
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)
        return
    log_payload["server_started"] = True

    timeout_s = int(os.environ.get("R2R_STARTUP_TIMEOUT", "20"))
    ready = _wait_for_r2r(base_url, timeout_s=timeout_s)
    if ready:
        log_payload["server_ready"] = True
        log_payload["server_ready_ms"] = _elapsed_ms(started_at)
        ingest_info = _auto_ingest()
        log_payload.update(ingest_info)
        log_payload["status"] = "ready"
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)
    else:
        logger.warning("R2R server did not become ready in time")
        log_payload["status"] = "start_timeout"
        log_payload["duration_ms"] = _elapsed_ms(started_at)
        _write_bootstrap_log(log_payload)


def _auto_ingest() -> Dict[str, Any]:
    started_at = time.monotonic()
    if not _env_flag("R2R_AUTO_INGEST", default=True):
        logger.info("R2R auto-ingest disabled")
        return {"ingest_items": 0, "ingest_ms": 0, "ingest_status": "disabled"}
    rag = LibraryRAG()
    if not getattr(rag, "_client", None):
        logger.warning("R2R client unavailable; skipping ingest")
        return {"ingest_items": 0, "ingest_ms": 0, "ingest_status": "client_unavailable"}
    count = rag.ingest_all()
    logger.info("R2R ingest requested for %s library items", count)
    return {
        "ingest_items": count,
        "ingest_ms": _elapsed_ms(started_at),
        "ingest_status": "requested",
    }


def _env_flag(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_r2r_installed() -> bool:
    _ensure_local_r2r_path()
    return importlib.util.find_spec("r2r") is not None


def _is_local_base(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    return host in {"localhost", "127.0.0.1", "0.0.0.0"}


def _is_r2r_healthy(base_url: str) -> bool:
    try:
        resp = httpx.get(f"{base_url}/docs", timeout=2.5)
        return resp.status_code < 500
    except Exception:
        return False


def _start_r2r_server() -> bool:
    global _R2R_PROCESS
    if _R2R_PROCESS and _R2R_PROCESS.poll() is None:
        return True
    command = [sys.executable, "-m", "r2r.serve"]
    host = os.environ.get("R2R_HOST")
    port = os.environ.get("R2R_PORT")
    config_name = os.environ.get("R2R_CONFIG_NAME")
    config_path = os.environ.get("R2R_CONFIG_PATH")
    if host:
        command += ["--host", host]
    if port:
        command += ["--port", port]
    if config_name:
        command += ["--config-name", config_name]
    if config_path:
        command += ["--config-path", config_path]
    env = os.environ.copy()
    local_path = _ensure_local_r2r_path()
    if local_path:
        existing = env.get("PYTHONPATH", "")
        if local_path not in existing.split(os.pathsep):
            env["PYTHONPATH"] = os.pathsep.join(
                [local_path] + ([existing] if existing else [])
            )
    try:
        _R2R_PROCESS = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=os.getcwd(),
            env=env,
        )
    except Exception as exc:
        logger.warning("Failed to spawn R2R server: %s", exc)
        return False
    return True


def _wait_for_r2r(base_url: str, timeout_s: int) -> bool:
    deadline = time.time() + max(1, timeout_s)
    while time.time() < deadline:
        if _is_r2r_healthy(base_url):
            return True
        time.sleep(0.5)
    return False


def _elapsed_ms(started_at: float) -> int:
    return int(max(0.0, time.monotonic() - started_at) * 1000)


def _write_bootstrap_log(payload: Dict[str, Any]) -> None:
    try:
        data_root = get_data_root()
        log_dir = data_root / "_system" / "rag_bootstrap_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{generate_timestamp()}_rag_bootstrap.json"
        path = log_dir / filename
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        return


def shutdown_rag_services() -> Dict[str, Any]:
    """Stop local R2R server and Postgres container if started."""
    result = {
        "r2r_stopped": False,
        "postgres_stopped": False,
        "errors": [],
    }
    if _stop_r2r_server():
        result["r2r_stopped"] = True
    if _env_flag("R2R_DOCKER_AUTO_STOP", default=True):
        postgres_stopped, error = _stop_postgres_docker()
        result["postgres_stopped"] = postgres_stopped
        if error:
            result["errors"].append(error)
    return result


def _ensure_local_r2r_path() -> str:
    candidates = [
        Path(__file__).resolve().parents[2] / "tools" / "r2r" / "py",
        Path(__file__).resolve().parents[4] / "agentic" / "r2r" / "R2R" / "py",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        path = str(candidate)
        if path not in sys.path:
            sys.path.append(path)
        return path
    return ""


def _ensure_r2r_env_defaults() -> None:
    defaults = {
        "R2R_POSTGRES_USER": "postgres",
        "R2R_POSTGRES_PASSWORD": "postgres",
        "R2R_POSTGRES_HOST": "localhost",
        "R2R_POSTGRES_PORT": "5432",
        "R2R_POSTGRES_DBNAME": "postgres",
        "R2R_PROJECT_NAME": "r2r_default",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def _start_postgres_docker() -> Dict[str, Any]:
    info = {
        "postgres_status": "skipped",
        "postgres_ready": False,
        "postgres_ready_ms": 0,
        "docker_compose": "",
        "compose_file": "",
    }
    if not _env_flag("R2R_DOCKER_AUTO_START", default=True):
        info["postgres_status"] = "auto_start_disabled"
        return info
    compose_cmd = _resolve_docker_compose_cmd()
    if not compose_cmd:
        info["postgres_status"] = "docker_unavailable"
        return info
    compose_file = _get_compose_file()
    if not compose_file.exists():
        info["postgres_status"] = "compose_missing"
        return info
    info["docker_compose"] = " ".join(compose_cmd)
    info["compose_file"] = str(compose_file)
    if _docker_compose_is_running(compose_cmd, compose_file, "postgres"):
        info["postgres_status"] = "already_running"
        info["postgres_ready"] = _wait_for_port("127.0.0.1", 5432, timeout_s=5)
        return info
    started_at = time.monotonic()
    profile = os.environ.get("R2R_DOCKER_PROFILE", "postgres")
    service = os.environ.get("R2R_DOCKER_SERVICE", "postgres")
    ok = _docker_compose_up(compose_cmd, compose_file, profile, service)
    global _POSTGRES_STARTED
    _POSTGRES_STARTED = bool(ok)
    if not ok:
        info["postgres_status"] = "start_failed"
        return info
    info["postgres_status"] = "started"
    ready = _wait_for_port("127.0.0.1", 5432, timeout_s=30)
    info["postgres_ready"] = ready
    info["postgres_ready_ms"] = _elapsed_ms(started_at)
    return info


def _stop_postgres_docker() -> Tuple[bool, str]:
    global _POSTGRES_STARTED
    if not _POSTGRES_STARTED:
        return False, ""
    compose_cmd = _resolve_docker_compose_cmd()
    if not compose_cmd:
        return False, "docker_unavailable"
    compose_file = _get_compose_file()
    if not compose_file.exists():
        return False, "compose_missing"
    profile = os.environ.get("R2R_DOCKER_PROFILE", "postgres")
    service = os.environ.get("R2R_DOCKER_SERVICE", "postgres")
    try:
        subprocess.run(
            compose_cmd
            + ["-f", str(compose_file), "--profile", profile, "stop", service],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return False, str(exc)
    _POSTGRES_STARTED = False
    return True, ""


def _stop_r2r_server() -> bool:
    global _R2R_PROCESS
    if not _R2R_PROCESS or _R2R_PROCESS.poll() is not None:
        return False
    try:
        _R2R_PROCESS.terminate()
        _R2R_PROCESS.wait(timeout=5)
        _R2R_PROCESS = None
        return True
    except Exception:
        try:
            _R2R_PROCESS.kill()
            _R2R_PROCESS = None
            return True
        except Exception:
            return False


def _resolve_docker_compose_cmd() -> List[str]:
    if shutil.which("docker"):
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return ["docker", "compose"]
        except Exception:
            pass
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    return []


def _get_compose_file() -> Path:
    override = os.environ.get("R2R_DOCKER_COMPOSE_FILE")
    if override:
        return Path(override)
    candidates = [
        Path(__file__).resolve().parents[2] / "tools" / "r2r" / "docker" / "compose.yaml",
        Path(__file__).resolve().parents[4] / "agentic" / "r2r" / "R2R" / "docker" / "compose.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _docker_compose_is_running(
    compose_cmd: List[str], compose_file: Path, service: str
) -> bool:
    try:
        proc = subprocess.run(
            compose_cmd
            + ["-f", str(compose_file), "ps", "--status", "running", "-q", service],
            check=False,
            capture_output=True,
            text=True,
        )
        return bool(proc.stdout.strip())
    except Exception:
        return False


def _docker_compose_up(
    compose_cmd: List[str], compose_file: Path, profile: str, service: str
) -> bool:
    try:
        subprocess.run(
            compose_cmd
            + ["-f", str(compose_file), "--profile", profile, "up", "-d", service],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _wait_for_port(host: str, port: int, timeout_s: int) -> bool:
    deadline = time.time() + max(1, timeout_s)
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except Exception:
            time.sleep(0.5)
    return False
