"""Logging helpers for narration_agent."""

from __future__ import annotations

import json
import threading
from typing import Any, Dict

from app.utils.ids import generate_timestamp
from app.utils.project_storage import get_project_root


def write_plan_log(
    project_id: str,
    session_id: str,
    label: str,
    payload: Dict[str, Any],
) -> None:
    def _worker() -> None:
        try:
            root = get_project_root(project_id)
            log_dir = root / "orchestrator_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            safe_label = "".join(c for c in label if c.isalnum() or c in ("-", "_")).strip()
            safe_label = safe_label or "plan"
            filename = f"{generate_timestamp()}_{safe_label}.json"
            content = {
                "project_id": project_id,
                "session_id": session_id,
                "label": label,
                "logged_at": generate_timestamp(),
                **payload,
            }
            (log_dir / filename).write_text(
                json.dumps(content, indent=2, ensure_ascii=True), encoding="utf-8"
            )
        except Exception:
            return

    threading.Thread(target=_worker, daemon=True).start()
