import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
AGENTIC_DIR = ROOT_DIR / "agentic"


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return value if value is not None else default


def get_openai_key() -> str:
    key = get_env("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required")
    return key


def get_openai_model() -> str:
    return get_env("OPENAI_CHAT_MODEL", "gpt-4o")


def get_r2r_base() -> str:
    return get_env("R2R_API_BASE", "http://localhost:7272")


def prompt_path(name: str) -> Path:
    return AGENTIC_DIR / name
