"""
Poller minimal pour le bus GitHub "boîte aux lettres".

Principe :
- Lit les commandes dans `commands/*.json` (status=new).
- Marque la prise via un fichier `status/<id>.in_progress`.
- Produit une réponse dans `responses/<id>.json` avec status=done|error.
- git pull/commit/push pour synchroniser.

Ce script est volontairement simple et sans dépendance externe.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parent.parent
CMD_DIR = REPO / "commands"
RESP_DIR = REPO / "responses"
STATUS_DIR = REPO / "status"
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "15"))


def sh(*args: str) -> str:
    """Exécute une commande shell dans le repo et retourne stdout."""
    return subprocess.run(
        args, cwd=REPO, check=True, capture_output=True, text=True
    ).stdout


def pull() -> None:
    try:
        sh("git", "pull", "--rebase")
    except subprocess.CalledProcessError as exc:
        print("Pull failed:", exc.stdout, exc.stderr)


def push() -> None:
    try:
        sh("git", "add", ".")
        sh("git", "commit", "-m", "process mailbox commands")
        sh("git", "push")
    except subprocess.CalledProcessError as exc:
        # Rien de grave si aucun changement ou conflit léger
        print("Push failed:", exc.stdout, exc.stderr)


def mark_in_progress(cmd_id: str) -> None:
    STATUS_DIR.mkdir(exist_ok=True)
    (STATUS_DIR / f"{cmd_id}.in_progress").write_text("")


def already_processed(cmd_id: str) -> bool:
    if (RESP_DIR / f"{cmd_id}.json").exists():
        return True
    if (STATUS_DIR / f"{cmd_id}.done").exists():
        return True
    return False


def process_command(cmd_path: Path) -> None:
    try:
        data: Dict[str, Any] = json.loads(cmd_path.read_text())
    except Exception as exc:  # noqa: BLE001
        print(f"Invalid JSON in {cmd_path.name}: {exc}")
        return

    cmd_id = data.get("id") or cmd_path.stem
    status = data.get("status", "new")
    if status != "new":
        return
    if already_processed(cmd_id):
        return

    # Marquer la prise
    mark_in_progress(cmd_id)

    # Traitement factice : on se contente d'échoer le payload
    result = {"echo": data.get("payload"), "action": data.get("action")}

    response = {
        "id": cmd_id,
        "status": "done",
        "result": result,
        "from": "local_app",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    RESP_DIR.mkdir(exist_ok=True)
    (RESP_DIR / f"{cmd_id}.json").write_text(json.dumps(response, indent=2))
    (STATUS_DIR / f"{cmd_id}.done").write_text("")


def main() -> None:
    CMD_DIR.mkdir(exist_ok=True)
    RESP_DIR.mkdir(exist_ok=True)
    STATUS_DIR.mkdir(exist_ok=True)

    while True:
        pull()
        for cmd_file in CMD_DIR.glob("*.json"):
            process_command(cmd_file)
        push()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
