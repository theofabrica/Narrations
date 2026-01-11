import os
from pathlib import Path

from r2r import R2RClient

SRC_GLOB = "SRC_NARRATOLOGY__*.txt"
DEFAULT_R2R_BASE = "http://localhost:7272"


def ingest_src_files() -> None:
    r2r_base = os.environ.get("R2R_API_BASE", DEFAULT_R2R_BASE)
    client = R2RClient(r2r_base)

    repo_root = Path(__file__).resolve().parents[1]
    src_dir = repo_root / "chatGPT_project"
    files = sorted(src_dir.glob(SRC_GLOB))
    if not files:
        raise RuntimeError(f"No files found for {SRC_GLOB} in {src_dir}")

    for file_path in files:
        metadata = {
            "doc_type": "SRC",
            "source_file": file_path.name,
        }
        client.documents.create(file_path=str(file_path), metadata=metadata)
        print(f"Ingested {file_path.name}")


if __name__ == "__main__":
    ingest_src_files()
