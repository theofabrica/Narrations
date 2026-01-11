from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

from .config import prompt_path
from .llm_client import LLMClient
from .rag_client import R2RClientWrapper


@dataclass
class AgentSpec:
    name: str
    system_prompt: Path


class BaseAgent:
    def __init__(self, spec: AgentSpec, llm: LLMClient) -> None:
        self.spec = spec
        self.llm = llm

    def _load_prompt(self) -> str:
        return self.spec.system_prompt.read_text(encoding="utf-8")

    def run(self, user_content: str) -> str:
        messages = [
            {"role": "system", "content": self._load_prompt()},
            {"role": "user", "content": user_content},
        ]
        return self.llm.chat(messages)


class NarrativeAgent(BaseAgent):
    def __init__(self, llm: LLMClient, rag: R2RClientWrapper | None = None) -> None:
        spec = AgentSpec(
            name="narrative",
            system_prompt=prompt_path("system_prompt_narrative_global.md"),
        )
        super().__init__(spec, llm)
        self.rag = rag

    def run_with_rag(self, user_content: str, query: str, top_k: int = 5) -> str:
        if not self.rag:
            return self.run(user_content)
        passages = self.rag.search_src(query, top_k=top_k)
        if passages:
            context = "\n\n".join(
                [f"SOURCE: {p['source_file']}\n{p['text']}" for p in passages]
            )
            user_content = f"{user_content}\n\nExtraits RAG (SRC_NARRATOLOGY):\n{context}"
        return self.run(user_content)


class CanonizerAgent(BaseAgent):
    def __init__(self, llm: LLMClient) -> None:
        spec = AgentSpec(
            name="canonizer",
            system_prompt=prompt_path("system_prompt_canonizer.md"),
        )
        super().__init__(spec, llm)
