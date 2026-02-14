"""Bootstrap R2R server and ingest narratology sources on startup."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import signal
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
from app.utils.project_storage import get_data_root, get_project_root
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
        "flush_conversations_on_start": _env_flag("R2R_FLUSH_CONVERSATIONS_ON_START", default=True),
        "flush_conversations_deleted_count": 0,
        "flush_conversations_failed_count": 0,
        "rag_meta_files_cleared_count": 0,
        "flush_all_on_start": _env_flag("R2R_FLUSH_ALL_ON_START", default=False),
        "flush_deleted_count": 0,
        "flush_failed_count": 0,
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


def purge_rag_conversations_now(project_id: str = "") -> Dict[str, Any]:
    """Purge all R2R conversations immediately and clear local RAG meta files."""
    rag = LibraryRAG()
    client = getattr(rag, "_client", None)
    if not client:
        return {
            "status": "client_unavailable",
            "deleted_count": 0,
            "failed_count": 0,
            "rag_meta_files_cleared_count": 0,
        }
    deleted, failed = _flush_all_r2r_conversations(rag)
    if isinstance(project_id, str) and project_id.strip():
        cleared = 1 if _clear_project_rag_meta_file(project_id) else 0
    else:
        cleared = _clear_all_rag_meta_files()
    return {
        "status": "ok",
        "deleted_count": int(deleted),
        "failed_count": int(failed),
        "rag_meta_files_cleared_count": int(cleared),
    }


def _auto_ingest() -> Dict[str, Any]:
    started_at = time.monotonic()
    if not _env_flag("R2R_AUTO_INGEST", default=True):
        logger.info("R2R auto-ingest disabled")
        return {"ingest_items": 0, "ingest_ms": 0, "ingest_status": "disabled"}
    flush_all_on_start = _env_flag("R2R_FLUSH_ALL_ON_START", default=False)
    flush_once_on_start = _env_flag("R2R_FLUSH_ALL_ON_START_ONCE", default=False)
    fingerprint = _compute_ingest_fingerprint()
    state = _read_bootstrap_state()
    flush_once_done = bool(state.get("flush_all_on_start_once_done")) if isinstance(state, dict) else False
    effective_flush_on_start = bool(
        flush_all_on_start or (flush_once_on_start and not flush_once_done)
    )
    rag = LibraryRAG()
    if not getattr(rag, "_client", None):
        logger.warning("R2R client unavailable; skipping ingest")
        return {"ingest_items": 0, "ingest_ms": 0, "ingest_status": "client_unavailable"}
    flush_conversations_on_start = _env_flag("R2R_FLUSH_CONVERSATIONS_ON_START", default=True)
    flush_conversations_deleted_count = 0
    flush_conversations_failed_count = 0
    rag_meta_files_cleared_count = 0
    if flush_conversations_on_start:
        flush_conversations_deleted_count, flush_conversations_failed_count = (
            _flush_all_r2r_conversations(rag)
        )
        rag_meta_files_cleared_count = _clear_all_rag_meta_files()
        logger.info(
            "R2R conversation flush on start: deleted=%s, failed=%s, meta_cleared=%s",
            flush_conversations_deleted_count,
            flush_conversations_failed_count,
            rag_meta_files_cleared_count,
        )
    if (
        not effective_flush_on_start
        and isinstance(fingerprint, str)
        and fingerprint
        and isinstance(state, dict)
        and state.get("library_fingerprint") == fingerprint
    ):
        return {
            "ingest_items": int(state.get("ingest_items", 0) or 0),
            "ingest_ms": 0,
            "ingest_status": "up_to_date",
            "library_fingerprint": fingerprint,
            "flush_conversations_on_start": bool(flush_conversations_on_start),
            "flush_conversations_deleted_count": int(flush_conversations_deleted_count),
            "flush_conversations_failed_count": int(flush_conversations_failed_count),
            "rag_meta_files_cleared_count": int(rag_meta_files_cleared_count),
            "flush_all_on_start": bool(flush_all_on_start),
            "flush_all_on_start_once": bool(flush_once_on_start),
            "flush_all_on_start_once_done": bool(flush_once_done),
            "flush_deleted_count": 0,
            "flush_failed_count": 0,
        }
    flush_deleted_count = 0
    flush_failed_count = 0
    if effective_flush_on_start:
        flush_deleted_count, flush_failed_count = _flush_all_r2r_documents(rag)
        logger.info(
            "R2R flush-all on start: deleted=%s, failed=%s",
            flush_deleted_count,
            flush_failed_count,
        )
    count = rag.ingest_all()
    logger.info("R2R ingest requested for %s library items", count)
    next_flush_once_done = bool(flush_once_done or (flush_once_on_start and effective_flush_on_start))
    state_payload = {
        "ingest_items": count,
        "ingested_at": generate_timestamp(),
        "flush_all_on_start_once_done": next_flush_once_done,
    }
    if isinstance(fingerprint, str) and fingerprint:
        state_payload["library_fingerprint"] = fingerprint
    _write_bootstrap_state(state_payload)
    return {
        "ingest_items": count,
        "ingest_ms": _elapsed_ms(started_at),
        "ingest_status": "requested",
        "library_fingerprint": fingerprint,
        "flush_conversations_on_start": bool(flush_conversations_on_start),
        "flush_conversations_deleted_count": int(flush_conversations_deleted_count),
        "flush_conversations_failed_count": int(flush_conversations_failed_count),
        "rag_meta_files_cleared_count": int(rag_meta_files_cleared_count),
        "flush_all_on_start": bool(flush_all_on_start),
        "flush_all_on_start_once": bool(flush_once_on_start),
        "flush_all_on_start_once_done": bool(next_flush_once_done),
        "flush_deleted_count": int(flush_deleted_count),
        "flush_failed_count": int(flush_failed_count),
    }


def _iter_r2r_documents(response: Any) -> List[Any]:
    if isinstance(response, dict):
        results = response.get("results", [])
        return results if isinstance(results, list) else []
    results = getattr(response, "results", None)
    return results if isinstance(results, list) else []


def _doc_id(document: Any) -> str:
    if isinstance(document, dict):
        return str(document.get("id", "") or "").strip()
    return str(getattr(document, "id", "") or "").strip()


def _iter_r2r_conversations(response: Any) -> List[Any]:
    if isinstance(response, dict):
        results = response.get("results", [])
        return results if isinstance(results, list) else []
    results = getattr(response, "results", None)
    return results if isinstance(results, list) else []


def _conversation_id(conversation: Any) -> str:
    if isinstance(conversation, dict):
        return str(conversation.get("id", "") or "").strip()
    return str(getattr(conversation, "id", "") or "").strip()


def _flush_all_r2r_documents(rag: LibraryRAG) -> Tuple[int, int]:
    client = getattr(rag, "_client", None)
    if not client:
        return 0, 0
    deleted = 0
    failed = 0
    seen: set[str] = set()
    while True:
        try:
            response = client.documents.list(limit=1000)
        except Exception:
            break
        docs = _iter_r2r_documents(response)
        if not docs:
            break
        progressed = False
        for doc in docs:
            doc_id = _doc_id(doc)
            if not doc_id or doc_id in seen:
                continue
            seen.add(doc_id)
            progressed = True
            try:
                client.documents.delete(id=doc_id)
                deleted += 1
            except Exception:
                failed += 1
        if not progressed:
            break
    return deleted, failed


def _flush_all_r2r_conversations(rag: LibraryRAG) -> Tuple[int, int]:
    client = getattr(rag, "_client", None)
    if not client:
        return 0, 0
    deleted = 0
    failed = 0
    seen: set[str] = set()
    while True:
        try:
            response = client.conversations.list(limit=100)
        except Exception:
            break
        conversations = _iter_r2r_conversations(response)
        if not conversations:
            break
        progressed = False
        for conversation in conversations:
            conversation_id = _conversation_id(conversation)
            if not conversation_id or conversation_id in seen:
                continue
            seen.add(conversation_id)
            progressed = True
            try:
                client.conversations.delete(id=conversation_id)
                deleted += 1
            except Exception:
                failed += 1
        if not progressed:
            break
    return deleted, failed


def _clear_all_rag_meta_files() -> int:
    cleared = 0
    try:
        data_root = get_data_root()
    except Exception:
        return 0
    try:
        for path in data_root.glob("*/metadata/*_RAG_META.json"):
            try:
                path.unlink(missing_ok=True)
                cleared += 1
            except Exception:
                continue
    except Exception:
        return cleared
    return cleared


def _clear_project_rag_meta_file(project_id: str) -> bool:
    try:
        root = get_project_root(project_id)
        safe_project = "".join(c for c in project_id if c.isalnum() or c in ("-", "_")).strip()
        if not safe_project:
            safe_project = "default"
        path = root / "metadata" / f"{safe_project}_RAG_META.json"
        if path.exists():
            path.unlink(missing_ok=True)
            return True
        return False
    except Exception:
        return False


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


def _bootstrap_state_path() -> Path:
    return get_data_root() / "_system" / "rag_bootstrap_state.json"


def _read_bootstrap_state() -> Dict[str, Any]:
    try:
        path = _bootstrap_state_path()
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return {}
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _write_bootstrap_state(payload: Dict[str, Any]) -> None:
    try:
        path = _bootstrap_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    except Exception:
        return


def _compute_ingest_fingerprint() -> str:
    try:
        index_path = (
            Path(__file__).resolve().parent / "library" / "index.json"
        )
        if not index_path.exists():
            return ""
        index_text = index_path.read_text(encoding="utf-8")
        return hashlib.sha256(index_text.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def shutdown_rag_services() -> Dict[str, Any]:
    """Stop local R2R server and Postgres container if started."""
    result = {
        "r2r_stopped": False,
        "r2r_pidfile_stopped": False,
        "postgres_stopped": False,
        "errors": [],
    }
    if _stop_r2r_server():
        result["r2r_stopped"] = True
    pidfile_stopped, pidfile_error = _stop_r2r_server_from_pidfile()
    result["r2r_pidfile_stopped"] = pidfile_stopped
    if pidfile_error:
        result["errors"].append(pidfile_error)
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


def _r2r_pid_file_path() -> Path:
    custom = os.environ.get("R2R_PID_FILE", "").strip()
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parents[4] / "status" / "r2r.pid"


def _is_expected_r2r_process(pid: int) -> bool:
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_text(
            encoding="utf-8", errors="ignore"
        )
    except Exception:
        return False
    text = cmdline.replace("\x00", " ").lower()
    return "r2r.serve" in text or " -m r2r" in text


def _wait_for_process_exit(pid: int, timeout_s: float = 6.0) -> bool:
    deadline = time.monotonic() + max(0.5, timeout_s)
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
            time.sleep(0.2)
        except ProcessLookupError:
            return True
        except Exception:
            return False
    return False


def _stop_r2r_server_from_pidfile() -> Tuple[bool, str]:
    pid_file = _r2r_pid_file_path()
    if not pid_file.exists():
        return False, ""
    try:
        raw = pid_file.read_text(encoding="utf-8").strip()
        pid = int(raw)
    except Exception:
        return False, f"invalid_r2r_pid_file:{pid_file}"
    if pid <= 1:
        return False, f"invalid_r2r_pid:{pid}"
    if not _is_expected_r2r_process(pid):
        return False, f"refused_to_stop_unexpected_process:{pid}"
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pid_file.unlink(missing_ok=True)
        return True, ""
    except Exception as exc:
        return False, f"failed_sigterm_r2r:{exc}"
    if _wait_for_process_exit(pid, timeout_s=6.0):
        pid_file.unlink(missing_ok=True)
        return True, ""
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception as exc:
        return False, f"failed_sigkill_r2r:{exc}"
    if _wait_for_process_exit(pid, timeout_s=2.0):
        pid_file.unlink(missing_ok=True)
        return True, ""
    return False, f"r2r_process_still_running:{pid}"


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
