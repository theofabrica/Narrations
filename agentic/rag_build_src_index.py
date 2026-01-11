import json
import os
from pathlib import Path
from typing import Iterable, List, Dict, Any

import httpx

SRC_GLOB = "SRC_NARRATOLOGY__*.txt"
DEFAULT_EMBED_MODEL = "text-embedding-3-small"
DEFAULT_CHUNK_CHARS = 3600
DEFAULT_CHUNK_OVERLAP = 400


def chunk_text(text: str, chunk_size: int, overlap: int) -> Iterable[str]:
    if chunk_size <= 0:
        yield text
        return
    step = max(1, chunk_size - overlap)
    for start in range(0, len(text), step):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            yield chunk
        if end >= len(text):
            break


def embed_texts(client: httpx.Client, texts: List[str], model: str) -> List[List[float]]:
    resp = client.post(
        "https://api.openai.com/v1/embeddings",
        json={"model": model, "input": texts},
    )
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


def build_index(src_dir: Path, out_path: Path) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    model = os.environ.get("OPENAI_EMBED_MODEL", DEFAULT_EMBED_MODEL)
    chunk_size = int(os.environ.get("RAG_CHUNK_CHARS", DEFAULT_CHUNK_CHARS))
    overlap = int(os.environ.get("RAG_CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP))

    files = sorted(src_dir.glob(SRC_GLOB))
    if not files:
        raise RuntimeError(f"No files found for {SRC_GLOB} in {src_dir}")

    headers = {"Authorization": f"Bearer {api_key}"}
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(headers=headers, timeout=60.0) as client, out_path.open(
        "w", encoding="utf-8"
    ) as f:
        for file_path in files:
            text = file_path.read_text(encoding="utf-8")
            chunks = list(chunk_text(text, chunk_size, overlap))
            embeddings = embed_texts(client, chunks, model)
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                record = {
                    "id": f"{file_path.stem}::chunk_{idx:04d}",
                    "source_file": file_path.name,
                    "text": chunk,
                    "embedding": embedding,
                }
                f.write(json.dumps(record, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "chatGPT_project"
    out_path = Path(__file__).resolve().parent / "index" / "src_index.jsonl"
    build_index(src_dir, out_path)
