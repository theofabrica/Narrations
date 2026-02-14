"""Flush R2R documents and optionally re-ingest narration library.

Usage examples:
  python -m app.narration_agent.tools.flush_r2r --prefix SRC_NARRATOLOGY__
  python -m app.narration_agent.tools.flush_r2r --prefix SRC_NARRATOLOGY__ --reingest
  python -m app.narration_agent.tools.flush_r2r --all --reingest
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, List, Tuple

from app.narration_agent.writer_agent.strategy_finder.library_rag import LibraryRAG


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _iter_documents(response: Any) -> Iterable[Any]:
    # SDK may return either a dict-like payload or an object with .results
    if isinstance(response, dict):
        for item in _as_list(response.get("results")):
            yield item
        return
    results = getattr(response, "results", None)
    if isinstance(results, list):
        for item in results:
            yield item


def _get_doc_id(doc: Any) -> str:
    if isinstance(doc, dict):
        return str(doc.get("id") or "").strip()
    return str(getattr(doc, "id", "") or "").strip()


def _get_metadata(doc: Any) -> dict:
    if isinstance(doc, dict):
        metadata = doc.get("metadata", {}) or {}
    else:
        metadata = getattr(doc, "metadata", {}) or {}
    return metadata if isinstance(metadata, dict) else {}


def _source_file_from_doc(doc: Any) -> str:
    metadata = _get_metadata(doc)
    return str(metadata.get("source_file") or "").strip()


def _matches_prefix(source_file: str, prefixes: List[str], all_docs: bool) -> bool:
    if all_docs:
        return True
    if not source_file:
        return False
    return any(source_file.startswith(prefix) for prefix in prefixes)


def _list_matching_docs(rag: LibraryRAG, prefixes: List[str], all_docs: bool) -> List[Tuple[str, str]]:
    response = rag._client.documents.list(limit=1000)
    selected: List[Tuple[str, str]] = []
    for doc in _iter_documents(response):
        doc_id = _get_doc_id(doc)
        source_file = _source_file_from_doc(doc)
        if not doc_id:
            continue
        if _matches_prefix(source_file, prefixes, all_docs):
            selected.append((doc_id, source_file))
    return selected


def _reset_bootstrap_state() -> str:
    path = Path("data/_system/rag_bootstrap_state.json")
    if not path.exists():
        return f"bootstrap_state_missing:{path}"
    path.unlink()
    return f"bootstrap_state_deleted:{path}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Flush R2R documents by source_file prefix.")
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="source_file prefix to delete (repeatable). Default: SRC_NARRATOLOGY__",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all R2R documents (dangerous).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show matched documents without deleting.",
    )
    parser.add_argument(
        "--reingest",
        action="store_true",
        help="Re-ingest library files after deletion.",
    )
    parser.add_argument(
        "--reset-bootstrap-state",
        action="store_true",
        help="Delete data/_system/rag_bootstrap_state.json so auto-ingest does not think library is up-to-date.",
    )
    args = parser.parse_args()

    prefixes = [str(p).strip() for p in args.prefix if str(p).strip()]
    if not prefixes and not args.all:
        prefixes = ["SRC_NARRATOLOGY__"]

    rag = LibraryRAG()
    if not getattr(rag, "_client", None):
        print("error: R2R client unavailable")
        return 2

    try:
        matches = _list_matching_docs(rag, prefixes, args.all)
    except Exception as exc:
        print(f"error: cannot list documents: {exc}")
        return 3

    print(
        json.dumps(
            {
                "mode": "dry_run" if args.dry_run else "apply",
                "all": bool(args.all),
                "prefixes": prefixes,
                "matched_count": len(matches),
                "matched_sample": [{"id": doc_id, "source_file": source_file} for doc_id, source_file in matches[:20]],
            },
            indent=2,
            ensure_ascii=True,
        )
    )

    if args.dry_run:
        return 0

    deleted = 0
    failures: List[dict] = []
    for doc_id, source_file in matches:
        try:
            rag._client.documents.delete(id=doc_id)
            deleted += 1
        except Exception as exc:
            failures.append({"id": doc_id, "source_file": source_file, "error": str(exc)})

    bootstrap_state_status = ""
    if args.reset_bootstrap_state:
        try:
            bootstrap_state_status = _reset_bootstrap_state()
        except Exception as exc:
            bootstrap_state_status = f"bootstrap_state_error:{exc}"

    reingest_count = 0
    if args.reingest:
        try:
            reingest_count = int(rag.ingest_all() or 0)
        except Exception as exc:
            failures.append({"step": "reingest", "error": str(exc)})

    print(
        json.dumps(
            {
                "deleted_count": deleted,
                "failed_count": len(failures),
                "failures": failures[:20],
                "reingest_requested": bool(args.reingest),
                "reingest_count": reingest_count,
                "bootstrap_state": bootstrap_state_status,
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

