"""LLM client wrapper for narration agents.

This module centralizes model selection and request execution.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import random
import re
import time

from app.config.settings import settings
from app.utils.logging import setup_logger


logger = setup_logger("mcp_narrations")


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

    def __init__(self, default_model: str = "gpt-4o", max_retries: int = 3):
        self.default_model = default_model
        self.max_retries = max(0, int(max_retries))

    @staticmethod
    def _safe_error_code(response: Optional[httpx.Response]) -> str:
        if response is None:
            return ""
        try:
            data = response.json()
        except Exception:
            return ""
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                return str(error.get("code") or "").strip()
        return ""

    @staticmethod
    def _parse_reset_seconds(value: str) -> float:
        text = (value or "").strip().lower()
        if not text:
            return 0.0
        if text.isdigit():
            return float(text)
        total = 0.0
        for amount, unit in re.findall(r"(\d+)(ms|s|m|h)", text):
            n = float(amount)
            if unit == "ms":
                total += n / 1000.0
            elif unit == "s":
                total += n
            elif unit == "m":
                total += n * 60.0
            elif unit == "h":
                total += n * 3600.0
        return total

    def _retry_delay_seconds(self, attempt: int, response: Optional[httpx.Response]) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After", "")
            if retry_after:
                try:
                    return max(0.0, float(retry_after))
                except ValueError:
                    pass
            reset_requests = self._parse_reset_seconds(
                response.headers.get("x-ratelimit-reset-requests", "")
            )
            if reset_requests > 0:
                return min(30.0, reset_requests + random.uniform(0.05, 0.5))
        base = min(30.0, 2 ** max(0, attempt - 1))
        jitter = random.uniform(0.05, 0.5 * max(1.0, base))
        return min(30.0, base + jitter)

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
        retryable_statuses = {500, 502, 503, 504}
        with httpx.Client(headers=headers, timeout=90.0) as client:
            last_http_error: Optional[httpx.HTTPStatusError] = None
            for attempt in range(1, self.max_retries + 2):
                try:
                    resp = client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except httpx.HTTPStatusError as exc:
                    last_http_error = exc
                    status_code = exc.response.status_code if exc.response is not None else 0
                    error_code = self._safe_error_code(exc.response)
                    if status_code == 429:
                        logger.warning(
                            "LLM request blocked by OpenAI status=%s error_code=%s (no retry)",
                            status_code,
                            error_code,
                        )
                        raise
                    can_retry = (
                        status_code in retryable_statuses and attempt <= self.max_retries
                    )
                    if not can_retry:
                        raise
                    delay = self._retry_delay_seconds(attempt=attempt, response=exc.response)
                    logger.warning(
                        "LLM request retry attempt=%s/%s status=%s error_code=%s wait=%.2fs",
                        attempt,
                        self.max_retries,
                        status_code,
                        error_code,
                        delay,
                    )
                    time.sleep(delay)
            else:
                if last_http_error is not None:
                    raise last_http_error
                raise RuntimeError("LLM request failed without response")

        content = data["choices"][0]["message"]["content"]
        return LLMResponse(content=content, raw=data)
