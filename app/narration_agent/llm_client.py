"""LLM client wrapper for narration agents.

This module centralizes model selection and request execution.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings


@dataclass
class LLMRequest:
    model: str
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    content: str
    raw: Optional[Dict[str, Any]] = None


class LLMClient:
    """Thin wrapper around the chosen LLM provider."""

    def __init__(self, default_model: str = "gpt-4o"):
        self.default_model = default_model

    def complete(self, request: LLMRequest) -> LLMResponse:
        """Execute a single LLM request."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for narration_agent")

        model = request.model or self.default_model
        if request.messages:
            messages = request.messages
        else:
            messages = []
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            if request.user_prompt:
                messages.append({"role": "user", "content": request.user_prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(headers=headers, timeout=90.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, raw=data)
