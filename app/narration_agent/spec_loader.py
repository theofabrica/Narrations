"""Load local specs (md/json) for narration_agent runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


_BASE_DIR = Path(__file__).resolve().parent


def load_text(relative_path: str) -> str:
    path = _BASE_DIR / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(relative_path: str) -> Dict[str, Any]:
    path = _BASE_DIR / relative_path
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text else {}
