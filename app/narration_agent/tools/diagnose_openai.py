"""Diagnose OpenAI API access and quota/rate-limit state.

Usage:
  python -m app.narration_agent.tools.diagnose_openai
  python -m app.narration_agent.tools.diagnose_openai --model gpt-4o --max-tokens 16
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict

import httpx

from app.config.settings import settings


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
OPENAI_USAGE_COMPLETIONS_URL = "https://api.openai.com/v1/organization/usage/completions"


def _mask_key(api_key: str) -> str:
    text = api_key.strip()
    if len(text) <= 12:
        return "*" * len(text)
    return f"{text[:7]}...{text[-4:]}"


def _headers_snapshot(response: httpx.Response) -> Dict[str, str]:
    wanted = [
        "x-request-id",
        "x-ratelimit-limit-requests",
        "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-requests",
        "x-ratelimit-reset-tokens",
        "retry-after",
    ]
    out: Dict[str, str] = {}
    for key in wanted:
        value = response.headers.get(key)
        if value is not None:
            out[key] = value
    return out


def _error_fields(payload: Dict[str, Any]) -> Dict[str, str]:
    err = payload.get("error")
    if not isinstance(err, dict):
        return {"type": "", "code": "", "message": ""}
    return {
        "type": str(err.get("type") or ""),
        "code": str(err.get("code") or ""),
        "message": str(err.get("message") or ""),
    }


def _diagnosis_from_response(status_code: int, error_type: str, error_code: str) -> str:
    code = (error_code or "").strip().lower()
    etype = (error_type or "").strip().lower()
    if status_code == 200:
        return "ok_openai_access"
    if status_code == 429 and (code == "insufficient_quota" or etype == "insufficient_quota"):
        return "blocked_insufficient_quota"
    if status_code == 429:
        return "blocked_rate_limit"
    if status_code == 401:
        return "blocked_authentication"
    if status_code == 403:
        return "blocked_permission_or_region"
    if 500 <= status_code < 600:
        return "openai_server_side_error"
    return "blocked_other_error"


def _short_body(response: httpx.Response, max_len: int = 600) -> str:
    text = response.text or ""
    text = text.strip()
    return text[:max_len]


def run_diagnosis(model: str, timeout_s: float, max_tokens: int) -> Dict[str, Any]:
    api_key = (settings.OPENAI_API_KEY or "").strip()
    base_report: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "endpoint": OPENAI_CHAT_COMPLETIONS_URL,
        "model": model,
        "timeout_s": timeout_s,
        "max_tokens": max_tokens,
        "openai_api_key_present": bool(api_key),
        "openai_api_key_masked": _mask_key(api_key) if api_key else "",
    }
    if not api_key:
        base_report.update(
            {
                "ok": False,
                "diagnosis": "missing_openai_api_key",
                "details": "OPENAI_API_KEY absent de l'environnement/.env",
            }
        )
        return base_report

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "diagnostic ping"}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }

    try:
        with httpx.Client(headers=headers, timeout=timeout_s) as client:
            response = client.post(OPENAI_CHAT_COMPLETIONS_URL, json=payload)
    except Exception as exc:
        base_report.update(
            {
                "ok": False,
                "diagnosis": "network_or_transport_error",
                "details": str(exc),
            }
        )
        return base_report

    headers_info = _headers_snapshot(response)
    status_code = int(response.status_code)
    secondary_checks: Dict[str, Any] = {}
    try:
        with httpx.Client(headers=headers, timeout=timeout_s) as client:
            models_resp = client.get(OPENAI_MODELS_URL)
        secondary_checks["models_api"] = {
            "http_status": int(models_resp.status_code),
            "ok": int(models_resp.status_code) == 200,
            "body_preview": _short_body(models_resp),
        }
    except Exception as exc:
        secondary_checks["models_api"] = {
            "http_status": 0,
            "ok": False,
            "body_preview": str(exc),
        }

    # Usage API often requires elevated/admin scopes. This helps explain why
    # we cannot always auto-diagnose daily/monthly budget from app keys.
    start_time = int(time.time()) - 86400
    usage_url = (
        f"{OPENAI_USAGE_COMPLETIONS_URL}?start_time={start_time}&bucket_width=1d&limit=1"
    )
    try:
        with httpx.Client(headers=headers, timeout=timeout_s) as client:
            usage_resp = client.get(usage_url)
        secondary_checks["usage_api"] = {
            "http_status": int(usage_resp.status_code),
            "ok": int(usage_resp.status_code) == 200,
            "body_preview": _short_body(usage_resp),
            "note": "Needs api.usage.read scope or admin key in many org setups.",
        }
    except Exception as exc:
        secondary_checks["usage_api"] = {
            "http_status": 0,
            "ok": False,
            "body_preview": str(exc),
            "note": "Usage API call failed at transport level.",
        }

    report: Dict[str, Any] = {
        **base_report,
        "http_status": status_code,
        "response_headers": headers_info,
        "secondary_checks": secondary_checks,
    }

    if status_code == 200:
        report.update(
            {
                "ok": True,
                "diagnosis": "ok_openai_access",
                "details": "Appel OpenAI reussi",
            }
        )
        return report

    try:
        data = response.json()
    except Exception:
        data = {}
    err = _error_fields(data if isinstance(data, dict) else {})
    diagnosis = _diagnosis_from_response(
        status_code=status_code, error_type=err["type"], error_code=err["code"]
    )
    report.update(
        {
            "ok": False,
            "diagnosis": diagnosis,
            "error": err,
            "raw_error_payload": data if isinstance(data, dict) else {},
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose OpenAI API errors (quota/rate/auth).")
    parser.add_argument("--model", default="gpt-4o", help="Model used for the diagnostic ping.")
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=8,
        help="Small response budget for cheap diagnostic call.",
    )
    args = parser.parse_args()

    report = run_diagnosis(
        model=str(args.model).strip() or "gpt-4o",
        timeout_s=max(1.0, float(args.timeout_s)),
        max_tokens=max(1, int(args.max_tokens)),
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
