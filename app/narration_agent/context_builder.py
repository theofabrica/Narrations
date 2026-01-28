"""Context builder to assemble context packs for writers."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ContextPack:
    target_path: str
    payload: Dict[str, Any]


class ContextBuilder:
    """Build context packs from state, schemas, and constraints."""

    def build(self, target_path: str, payload: Dict[str, Any]) -> ContextPack:
        return ContextPack(target_path=target_path, payload=payload)
