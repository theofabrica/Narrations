from __future__ import annotations

from .base import BaseAgent, AgentResult


class EchoAgent(BaseAgent):
    name = "echo"
    description = "Retourne l'entrée telle quelle (sans LLM)."

    def run(self, prompt: str) -> AgentResult:
        return AgentResult(
            name=self.name,
            output=f"[echo] {prompt}",
            metadata={"mode": "deterministic"},
        )
