"""Redactor sub-agent: performs the LLM writing step."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.narration_agent.llm_client import LLMClient, LLMRequest


@dataclass
class RedactionOutput:
    raw_output: str
    parsed: Optional[Dict[str, Any]]


class Redactor:
    """Execute a writing request and parse JSON output."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def redact(self, system_prompt: str, user_prompt: str) -> RedactionOutput:
        llm_response = self.llm_client.complete(
            LLMRequest(
                model=self.llm_client.default_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
            )
        )
        raw_content = llm_response.content.strip()
        json_block = extract_json_block(raw_content) or raw_content
        parsed = parse_json_payload(json_block, raw_content)
        return RedactionOutput(raw_output=raw_content, parsed=parsed)


def extract_json_block(content: str) -> str:
    if "```json" not in content:
        return ""
    _, _, rest = content.partition("```json")
    json_block = rest
    if "```" in rest:
        json_block, _, _ = rest.partition("```")
    return json_block.strip()


def parse_json_payload(payload: str, fallback: str) -> Optional[Dict[str, Any]]:
    if payload:
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
    trimmed = fallback.strip()
    if not trimmed:
        return None
    start = trimmed.find("{")
    end = trimmed.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(trimmed[start : end + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None
