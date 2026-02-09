"""Persistent chat memory storage for narration_agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.utils.ids import generate_timestamp
from app.utils.project_storage import get_project_root


def _safe_session_id(session_id: str) -> str:
    safe = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")).strip()
    return safe or "session"


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    return json.loads(text) if text else {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")


class ChatMemoryStore:
    """Store chat sessions on disk under each project."""

    def _legacy_session_path(self, project_id: str, session_id: str) -> Path:
        root = get_project_root(project_id)
        safe_session = _safe_session_id(session_id)
        return root / "chat_memory" / f"{safe_session}.json"

    def get_session_path(self, project_id: str, session_id: str) -> Path:
        root = get_project_root(project_id)
        safe_session = _safe_session_id(session_id)
        return root / "chat_states" / f"{safe_session}.json"

    def get_state_path(self, project_id: str, session_id: str) -> Path:
        root = get_project_root(project_id)
        safe_session = _safe_session_id(session_id)
        return root / "chat_states" / f"{safe_session}_state.json"

    def get_output_state_path(self, project_id: str, session_id: str) -> Path:
        root = get_project_root(project_id)
        safe_session = _safe_session_id(session_id)
        return root / "chat_states" / f"output_{safe_session}_state.json"

    def get_edit_session_path(self, project_id: str, edit_session_id: str) -> Path:
        root = get_project_root(project_id)
        safe_session = _safe_session_id(edit_session_id)
        return root / "chat_states" / f"edit_{safe_session}.json"

    def load_messages(self, project_id: str, session_id: str) -> List[Dict[str, str]]:
        current_path = self.get_session_path(project_id, session_id)
        payload = _read_json(current_path)
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            return [m for m in messages if isinstance(m, dict)]

        legacy_path = self._legacy_session_path(project_id, session_id)
        legacy_payload = _read_json(legacy_path)
        legacy_messages = legacy_payload.get("messages")
        if isinstance(legacy_messages, list) and legacy_messages:
            self.save_messages(project_id, session_id, legacy_messages)
            try:
                legacy_path.unlink()
            except OSError:
                pass
            return [m for m in legacy_messages if isinstance(m, dict)]
        return []

    def save_messages(
        self, project_id: str, session_id: str, messages: List[Dict[str, str]]
    ) -> None:
        existing = _read_json(self.get_session_path(project_id, session_id))
        payload = {
            "project_id": project_id,
            "session_id": session_id,
            "updated_at": generate_timestamp(),
            "messages": messages,
            "meta": existing.get("meta", {}) if isinstance(existing, dict) else {},
        }
        _write_json(self.get_session_path(project_id, session_id), payload)

    def save_state_snapshot(
        self, project_id: str, session_id: str, state_snapshot: Dict[str, Any]
    ) -> None:
        payload = {
            "project_id": project_id,
            "session_id": session_id,
            "updated_at": generate_timestamp(),
            "state_snapshot": state_snapshot,
        }
        _write_json(self.get_state_path(project_id, session_id), payload)

    def save_output_state_snapshot(
        self, project_id: str, session_id: str, state_snapshot: Dict[str, Any]
    ) -> None:
        payload = {
            "project_id": project_id,
            "session_id": session_id,
            "updated_at": generate_timestamp(),
            "state_snapshot": state_snapshot,
        }
        _write_json(self.get_output_state_path(project_id, session_id), payload)

    def load_edit_messages(self, project_id: str, edit_session_id: str) -> List[Dict[str, str]]:
        payload = _read_json(self.get_edit_session_path(project_id, edit_session_id))
        messages = payload.get("messages")
        if isinstance(messages, list) and messages:
            return [m for m in messages if isinstance(m, dict)]
        return []

    def save_edit_messages(
        self,
        project_id: str,
        edit_session_id: str,
        messages: List[Dict[str, str]],
        meta: Dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "project_id": project_id,
            "edit_session_id": edit_session_id,
            "updated_at": generate_timestamp(),
            "messages": messages,
            "meta": meta or {},
        }
        _write_json(self.get_edit_session_path(project_id, edit_session_id), payload)

    def load_state_snapshot(self, project_id: str, session_id: str) -> Dict[str, Any]:
        payload = _read_json(self.get_state_path(project_id, session_id))
        snapshot = payload.get("state_snapshot") if isinstance(payload, dict) else None
        return snapshot if isinstance(snapshot, dict) else {}

    def load_meta(self, project_id: str, session_id: str) -> Dict[str, Any]:
        payload = _read_json(self.get_session_path(project_id, session_id))
        meta = payload.get("meta") if isinstance(payload, dict) else None
        return meta if isinstance(meta, dict) else {}

    def save_meta(self, project_id: str, session_id: str, meta: Dict[str, Any]) -> None:
        existing = _read_json(self.get_session_path(project_id, session_id))
        payload = {
            "project_id": project_id,
            "session_id": session_id,
            "updated_at": generate_timestamp(),
            "messages": existing.get("messages", []) if isinstance(existing, dict) else [],
            "meta": meta,
        }
        _write_json(self.get_session_path(project_id, session_id), payload)
