from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentResult:
    name: str
    output: str
    metadata: Dict[str, Any]


class BaseAgent:
    name: str = "base"
    description: str = "Agent de base"

    def run(self, prompt: str) -> AgentResult:
        raise NotImplementedError
