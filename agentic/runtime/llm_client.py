from typing import List, Dict

import httpx

from .config import get_openai_key, get_openai_model


class LLMClient:
    def __init__(self, model: str | None = None, timeout: float = 60.0) -> None:
        self.model = model or get_openai_model()
        self.timeout = timeout
        self._headers = {"Authorization": f"Bearer {get_openai_key()}"}

    def chat(self, messages: List[Dict[str, str]], model: str | None = None) -> str:
        payload = {
            "model": model or self.model,
            "messages": messages,
        }
        with httpx.Client(headers=self._headers, timeout=self.timeout) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
