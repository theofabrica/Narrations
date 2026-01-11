import os
from pathlib import Path
from typing import List, Dict, Any

import httpx
from r2r import R2RClient

DEFAULT_CHAT_MODEL = "gpt-4o"
DEFAULT_TOP_K = 5
DEFAULT_R2R_BASE = "http://localhost:7272"


def retrieve_passages(query: str, top_k: int) -> List[Dict[str, Any]]:
    r2r_base = os.environ.get("R2R_API_BASE", DEFAULT_R2R_BASE)
    client = R2RClient(r2r_base)
    search_settings = {
        "use_semantic_search": True,
        "limit": top_k,
        "filters": {"metadata.doc_type": {"$eq": "SRC"}},
    }
    results = client.retrieval.search(
        query=query,
        search_mode="custom",
        search_settings=search_settings,
    ).results
    passages = []
    chunk_results = getattr(results, "chunk_search_results", []) or []
    for chunk in chunk_results:
        metadata = getattr(chunk, "metadata", {}) or {}
        passages.append(
            {
                "source_file": metadata.get("source_file", "unknown"),
                "text": getattr(chunk, "text", "") or "",
            }
        )
    return passages


def build_prompt(system_prompt: str, user_request: str, passages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    context = []
    for item in passages:
        context.append(f"SOURCE: {item['source_file']}\n{item['text']}")
    context_block = "\n\n".join(context)
    user_content = (
        f"Demande utilisateur:\n{user_request}\n\n"
        f"Extraits RAG (SRC_NARRATOLOGY):\n{context_block}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def run_n0_node(user_request: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    chat_model = os.environ.get("OPENAI_CHAT_MODEL", DEFAULT_CHAT_MODEL)
    top_k = int(os.environ.get("RAG_TOP_K", DEFAULT_TOP_K))

    repo_root = Path(__file__).resolve().parents[1]
    prompt_path = repo_root / "agentic" / "system_prompt_narrative_global.md"

    system_prompt = prompt_path.read_text(encoding="utf-8")
    passages = retrieve_passages(user_request, top_k)
    messages = build_prompt(system_prompt, user_request, passages)

    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(headers=headers, timeout=60.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            json={"model": chat_model, "messages": messages},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


if __name__ == "__main__":
    request = os.environ.get("N0_USER_REQUEST", "Definir le cadre de production du projet.")
    output = run_n0_node(request)
    print(output)
