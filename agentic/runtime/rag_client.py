from typing import List, Dict, Any

from .config import get_r2r_base


class R2RSearchError(RuntimeError):
    pass


class R2RClientWrapper:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or get_r2r_base()
        try:
            from r2r import R2RClient
        except Exception as exc:  # pragma: no cover - optional dependency
            raise R2RSearchError("r2r package is not available") from exc
        self._client = R2RClient(self.base_url)

    def search_src(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        search_settings = {
            "use_semantic_search": True,
            "limit": top_k,
            "filters": {"metadata.doc_type": {"$eq": "SRC"}},
        }
        results = self._client.retrieval.search(
            query=query,
            search_mode="custom",
            search_settings=search_settings,
        ).results
        chunk_results = getattr(results, "chunk_search_results", []) or []
        passages = []
        for chunk in chunk_results:
            metadata = getattr(chunk, "metadata", {}) or {}
            passages.append(
                {
                    "source_file": metadata.get("source_file", "unknown"),
                    "text": getattr(chunk, "text", "") or "",
                }
            )
        return passages
