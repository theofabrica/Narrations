from __future__ import annotations

from typing import List, Dict

from agentic.runtime.llm_client import LLMClient
from .base import BaseAgent, AgentResult


class SimpleLLMAgent(BaseAgent):
    name = "simple_llm"
    description = "Agent one-shot utilisant un prompt système court."

    def __init__(self, system_prompt: str) -> None:
        self.system_prompt = system_prompt
        self.client = LLMClient()

    def run(self, prompt: str) -> AgentResult:
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt},
        ]
        answer = self.client.chat(messages)
        return AgentResult(
            name=self.name,
            output=answer.strip(),
            metadata={"mode": "one_shot"},
        )
