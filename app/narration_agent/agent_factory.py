"""Agent factory to build prompts and requests by role."""

from dataclasses import dataclass
from typing import Dict

from .llm_client import LLMRequest


@dataclass
class AgentSpec:
    name: str
    model: str
    system_prompt: str


class AgentFactory:
    """Resolve agent specs and build LLM requests."""

    def __init__(self, default_model: str = "gpt-4o"):
        self.default_model = default_model
        self._specs: Dict[str, AgentSpec] = {}

    def register(self, name: str, system_prompt: str, model: str | None = None) -> None:
        self._specs[name] = AgentSpec(
            name=name,
            model=model or self.default_model,
            system_prompt=system_prompt,
        )

    def build_request(self, name: str, user_prompt: str) -> LLMRequest:
        if name not in self._specs:
            raise KeyError(f"Unknown agent: {name}")
        spec = self._specs[name]
        return LLMRequest(
            model=spec.model,
            system_prompt=spec.system_prompt,
            user_prompt=user_prompt,
        )
