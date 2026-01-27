from __future__ import annotations

from typing import List, Dict

from agentic.runtime.llm_client import LLMClient
from .base import BaseAgent, AgentResult


class PlannerExecutorAgent(BaseAgent):
    name = "planner_executor"
    description = "Agent en 2 étapes: planification puis exécution."

    def __init__(self) -> None:
        self.client = LLMClient()

    def _plan(self, prompt: str) -> str:
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Tu es un agent qui planifie en 3-6 étapes courtes. "
                    "Retourne une liste numérotée uniquement."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        return self.client.chat(messages).strip()

    def _execute(self, prompt: str, plan: str) -> str:
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Tu exécutes un plan de manière concise. "
                    "Respecte le plan, réponds en français."
                ),
            },
            {
                "role": "user",
                "content": f"Demande: {prompt}\n\nPlan:\n{plan}\n\nRéponse:",
            },
        ]
        return self.client.chat(messages).strip()

    def run(self, prompt: str) -> AgentResult:
        plan = self._plan(prompt)
        output = self._execute(prompt, plan)
        return AgentResult(
            name=self.name,
            output=output,
            metadata={"plan": plan},
        )
