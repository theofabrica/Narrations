from __future__ import annotations

from typing import Dict, List

from agentic.runtime.llm_client import LLMClient
from .base import BaseAgent, AgentResult


class RouterAgent(BaseAgent):
    name = "router"
    description = "Route une demande vers un agent spécialisé."

    def __init__(self, routes: Dict[str, BaseAgent]) -> None:
        self.routes = routes
        self.client = LLMClient()

    def _choose_route(self, prompt: str) -> str:
        route_list = ", ".join(self.routes.keys())
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "Tu dois choisir UNE route parmi celles fournies. "
                    "Réponds uniquement par le nom de la route."
                ),
            },
            {
                "role": "user",
                "content": f"Routes possibles: {route_list}\n\nDemande: {prompt}",
            },
        ]
        choice = self.client.chat(messages).strip()
        if choice not in self.routes:
            return "default"
        return choice

    def run(self, prompt: str) -> AgentResult:
        if "default" not in self.routes:
            raise RuntimeError("La route 'default' est requise.")
        route = self._choose_route(prompt)
        result = self.routes[route].run(prompt)
        return AgentResult(
            name=self.name,
            output=result.output,
            metadata={"route": route, "downstream": result.metadata},
        )
