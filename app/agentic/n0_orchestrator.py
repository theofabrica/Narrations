import json
from pathlib import Path
from typing import Dict, Any

import httpx

from app.config.settings import settings


def _load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_n0_brief(n0_data: Dict[str, Any]) -> str:
    production = n0_data.get("production_summary", {}) or {}
    art_direction = n0_data.get("art_direction", {}) or {}
    sound_direction = n0_data.get("sound_direction", {}) or {}
    return (
        "Mission N0: enrichir le resume et ajuster l'esthetique et les directions artistiques.\n\n"
        "Contrainte: rester coherent avec les donnees N0 fournies.\n\n"
        f"Resume actuel:\n{production.get('summary', '')}\n\n"
        f"Type de production: {production.get('production_type', '')}\n"
        f"Duree cible: {production.get('target_duration', '')}\n"
        f"Ratio: {production.get('aspect_ratio', '')}\n"
        f"Style visuel actuel: {production.get('visual_style', '')}\n"
        f"Ton: {production.get('tone', '')}\n"
        f"Epoque: {production.get('era', '')}\n\n"
        f"Direction artistique image (actuelle):\n{art_direction.get('description', '')}\n\n"
        f"Direction artistique musique (actuelle):\n{sound_direction.get('description', '')}\n\n"
        "Sortie attendue (texte structure):\n"
        "1) Resume N0 ameliore (1-2 paragraphes)\n"
        "2) Esthetique (style visuel global)\n"
        "3) Direction artistique image\n"
        "4) Direction artistique musique\n"
    )


def _build_canonizer_input(narrative: str) -> str:
    template = {
        "summary": "",
        "esthetique": "",
        "art_direction_description": "",
        "sound_direction_description": "",
    }
    return (
        "Sortie narrative a canoniser:\n"
        f"{narrative}\n\n"
        "Modele JSON:\n"
        f"{json.dumps(template, ensure_ascii=True)}"
    )


def orchestrate_n0(n0_data: Dict[str, Any]) -> Dict[str, Any]:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required for N0 orchestration")

    root = _repo_root() / "agentic"
    narrative_prompt = _load_prompt(root / "system_prompt_narrative_global.md")
    canonizer_prompt = _load_prompt(root / "system_prompt_canonizer.md")

    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    model = "gpt-4o"

    brief = _build_n0_brief(n0_data)
    messages = [
        {"role": "system", "content": narrative_prompt},
        {"role": "user", "content": brief},
    ]

    with httpx.Client(headers=headers, timeout=90.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            json={"model": model, "messages": messages},
        )
        resp.raise_for_status()
        narrative = resp.json()["choices"][0]["message"]["content"]

        canonizer_messages = [
            {"role": "system", "content": canonizer_prompt},
            {"role": "user", "content": _build_canonizer_input(narrative)},
        ]
        canon_resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            json={"model": model, "messages": canonizer_messages},
        )
        canon_resp.raise_for_status()
        canon_text = canon_resp.json()["choices"][0]["message"]["content"]

    data = json.loads(canon_text)
    return {
        "summary": data.get("summary", ""),
        "esthetique": data.get("esthetique", ""),
        "art_direction_description": data.get("art_direction_description", ""),
        "sound_direction_description": data.get("sound_direction_description", ""),
        "narrative": narrative,
    }
