"""
Client de bureau (polling) pour traiter les fichiers d'ordre JSON générés par
le projet ChatGPT (cf. N0_META__file_exchange_protocol.md).

Fonctionnement :
- Surveille le dossier de téléchargements (ou DOWNLOAD_DIR env).
- Détecte les fichiers NARR_*.json, les valide, puis les déplace en spool.
- Transmet leur contenu au serveur (HTTP) et écrit un ACK dans la spool/outbox.

Usage :
  python -m app.client_app.watcher

Variables d'environnement utiles :
- DOWNLOAD_DIR : dossier à surveiller (défaut = ~/Downloads ou équivalent OS)
- NARRATIONS_SPOOL_DIR : dossier racine spool (défaut = ~/.narrations_spool)
- SERVER_ENDPOINT : URL HTTP pour envoyer la commande (défaut http://localhost:3333/mcp)
- POLL_INTERVAL : intervalle de polling en secondes (défaut 10)
- REQUEST_TIMEOUT : timeout HTTP en secondes (défaut 30)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

# Patterns et defaults
FILENAME_RE = re.compile(r"^NARR_([A-Z]+)_(.+)_(.+)_([0-9]{8}T[0-9]{6}Z)\.json$")
DEFAULT_ENDPOINT = "http://localhost:3333/mcp"
DEFAULT_POLL_INTERVAL = 10.0
DEFAULT_TIMEOUT = 30.0


@dataclass
class Settings:
    download_dir: Path
    spool_root: Path
    endpoint: str
    poll_interval: float
    request_timeout: float

    @property
    def inbox(self) -> Path:
        return self.spool_root / "inbox"

    @property
    def outbox(self) -> Path:
        return self.spool_root / "outbox"

    @property
    def rejected(self) -> Path:
        return self.spool_root / "rejected"


def detect_download_dir() -> Path:
    env_dir = os.getenv("DOWNLOAD_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    home = Path.home()
    # Mac / Linux standard
    guess = home / "Downloads"
    if guess.exists():
        return guess
    return home


def load_settings() -> Settings:
    download_dir = detect_download_dir()
    spool_root = Path(os.getenv("NARRATIONS_SPOOL_DIR", "~/.narrations_spool")).expanduser()
    endpoint = os.getenv("SERVER_ENDPOINT", DEFAULT_ENDPOINT)
    poll_interval = float(os.getenv("POLL_INTERVAL", DEFAULT_POLL_INTERVAL))
    request_timeout = float(os.getenv("REQUEST_TIMEOUT", DEFAULT_TIMEOUT))
    return Settings(
        download_dir=download_dir,
        spool_root=spool_root,
        endpoint=endpoint,
        poll_interval=poll_interval,
        request_timeout=request_timeout,
    )


def ensure_dirs(cfg: Settings) -> None:
    cfg.spool_root.mkdir(parents=True, exist_ok=True)
    cfg.inbox.mkdir(parents=True, exist_ok=True)
    cfg.outbox.mkdir(parents=True, exist_ok=True)
    cfg.rejected.mkdir(parents=True, exist_ok=True)


def is_narr_file(path: Path) -> bool:
    return path.is_file() and FILENAME_RE.match(path.name) is not None


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_payload(data: Dict[str, Any]) -> Optional[str]:
    required_fields = ["version", "kind", "action", "id", "ts", "payload"]
    for field in required_fields:
        if field not in data:
            return f"missing field {field}"
    if data.get("kind") not in {"CMD", "CFG", "DATA"}:
        return f"unsupported kind {data.get('kind')}"
    return None


def move_to_spool(src: Path, dest_dir: Path) -> Path:
    dest = dest_dir / src.name
    dest.write_bytes(src.read_bytes())
    src.unlink(missing_ok=True)
    return dest


def http_send(endpoint: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(endpoint, json=payload)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}") from exc
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Invalid JSON response: {resp.text}") from exc


def build_ack(data: Dict[str, Any], status: str, result: Optional[Dict[str, Any]], error: Optional[str]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "version": data.get("version", "1.0"),
        "kind": "ACK",
        "action": data.get("action"),
        "id": data.get("id"),
        "ts": now,
        "from": "local_app",
        "status": status,
        "result": result,
        "error": None if error is None else {"code": "client_error", "message": error, "retryable": False},
    }


def ack_filename(action: str, req_id: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_action = re.sub(r"[^A-Za-z0-9_-]", "-", action or "action")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "-", req_id or "id")
    return f"NARR_ACK_{safe_action}_{safe_id}_{ts}.json"


def process_file(path: Path, cfg: Settings) -> None:
    data: Dict[str, Any]
    try:
        data = read_json(path)
    except Exception as exc:  # noqa: BLE001
        move_to_spool(path, cfg.rejected)
        print(f"[reject] {path.name}: invalid JSON ({exc})")
        return

    error = validate_payload(data)
    if error:
        move_to_spool(path, cfg.rejected)
        print(f"[reject] {path.name}: {error}")
        return

    inbox_path = move_to_spool(path, cfg.inbox)
    print(f"[info] reçu {inbox_path.name}, envoi à {cfg.endpoint}")

    result: Optional[Dict[str, Any]] = None
    ack_error: Optional[str] = None
    status = "done"
    try:
        result = http_send(cfg.endpoint, data, cfg.request_timeout)
    except Exception as exc:  # noqa: BLE001
        status = "error"
        ack_error = str(exc)
        print(f"[error] envoi échoué: {exc}")

    ack = build_ack(data, status, result, ack_error)
    ack_path = cfg.outbox / ack_filename(data.get("action", ""), data.get("id", ""))
    ack_path.write_text(json.dumps(ack, indent=2), encoding="utf-8")
    print(f"[info] ACK écrit: {ack_path.name}")


def loop(cfg: Settings) -> None:
    ensure_dirs(cfg)
    print(f"[start] Surveillance de {cfg.download_dir} → endpoint {cfg.endpoint}")
    while True:
        try:
            for path in cfg.download_dir.glob("NARR_*.json"):
                if is_narr_file(path):
                    process_file(path, cfg)
        except KeyboardInterrupt:
            print("\n[stop] Arrêt demandé par l'utilisateur.")
            sys.exit(0)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] boucle: {exc}")
        time.sleep(cfg.poll_interval)


def main() -> None:
    cfg = load_settings()
    loop(cfg)


if __name__ == "__main__":
    main()
