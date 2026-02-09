"""Agentic RAG helper for writer library retrieval."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.narration_agent.spec_loader import load_json, load_text

DEFAULT_R2R_BASE = "http://localhost:7272"
DEFAULT_RAG_MODEL = os.environ.get("R2R_RAG_MODEL", "openai/gpt-4o-mini")
DEFAULT_RESEARCH_MODEL = os.environ.get("R2R_RESEARCH_MODEL", "openai/gpt-4o-mini")
DEFAULT_MODE = os.environ.get("R2R_AGENT_MODE", "research")
LOCAL_R2R_PATHS = [
    Path(__file__).resolve().parents[2] / "tools" / "r2r" / "py",
    Path(__file__).resolve().parents[4] / "agentic" / "r2r" / "R2R" / "py",
]


def _ensure_local_r2r_path() -> str:
    for candidate in LOCAL_R2R_PATHS:
        if not candidate.exists():
            continue
        path = str(candidate)
        if path not in sys.path:
            sys.path.append(path)
        return path
    return ""


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class LibraryHit:
    item_id: str
    title: str
    author: str
    source_path: str
    writing_typologies: List[str]
    language: str
    excerpt: str
    summary: str
    key_concepts: List[str]
    score: float


class LibraryRAG:
    """Retrieve relevant library snippets using R2R agentic RAG."""

    def __init__(self) -> None:
        _ensure_local_r2r_path()
        self._library_index = load_json("writer_agent/strategy_finder/library/index.json") or {}
        self._text_cache: Dict[str, str] = {}
        self._client = None
        self._base_url = os.environ.get("R2R_API_BASE", DEFAULT_R2R_BASE)
        self._ingested_source_files: set[str] = set()
        self._ingested_loaded = False
        self.last_mode = "fallback"
        self.last_hit_count = 0
        try:
            from r2r import R2RClient
        except Exception:
            self._client = None
        else:
            self._client = R2RClient(self._base_url)
        self._filename_map = _build_filename_map(self._library_index)
        self._base_dir = Path(__file__).resolve().parents[2]

    def retrieve(self, context_pack: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        if not isinstance(context_pack, dict):
            return []
        if not self._client:
            hits = self._fallback_local(context_pack, limit)
            self.last_mode = "fallback"
            self.last_hit_count = len(hits)
            return hits
        try:
            self.last_mode = ""
            hits = self._retrieve_agentic(context_pack, limit)
        except Exception:
            hits = self._fallback_local(context_pack, limit)
            self.last_mode = "fallback_error"
            self.last_hit_count = len(hits)
            return hits
        else:
            if not self.last_mode:
                self.last_mode = "agentic"
            self.last_hit_count = len(hits)
            return hits

    def ingest_all(self) -> int:
        items = self._library_index.get("items", [])
        if not isinstance(items, list):
            return 0
        self._ensure_ingested(items)
        return len(items)

    def _retrieve_agentic(self, context_pack: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        query_text = _build_query_text(context_pack)
        writing_typology = context_pack.get("writing_typology", "") or ""
        language = (
            context_pack.get("style_constraints", {}).get("language", "") or ""
            if isinstance(context_pack.get("style_constraints"), dict)
            else ""
        )
        filename_prefixes = context_pack.get("library_filename_prefixes", [])
        if not isinstance(filename_prefixes, list):
            filename_prefixes = []
        filename_prefixes = [
            str(prefix).strip() for prefix in filename_prefixes if str(prefix).strip()
        ]

        library_typologies = _infer_library_typologies(context_pack, self._library_index)
        ingest_items = _select_ingest_items(
            self._library_index, library_typologies, writing_typology, language
        )
        if filename_prefixes:
            ingest_items = _select_items_by_filename_prefixes(self._library_index, filename_prefixes)
        self._ensure_ingested(ingest_items)
        allowed_filenames = _select_filenames(
            self._library_index, writing_typology, language, library_typologies
        )
        if filename_prefixes:
            allowed_filenames = [
                item.get("filename")
                for item in ingest_items
                if isinstance(item, dict) and item.get("filename")
            ]
        search_settings = _build_search_settings(allowed_filenames, limit=12)
        use_system_context = _env_bool("R2R_USE_SYSTEM_CONTEXT", True)
        task_prompt = None if use_system_context else _build_task_prompt(context_pack, limit)
        conversation_id = context_pack.get("source_state_id") or None

        mode = DEFAULT_MODE if DEFAULT_MODE in ("rag", "research") else "research"
        response = self._client.retrieval.agent(
            message={"role": "user", "content": query_text},
            task_prompt=task_prompt,
            search_mode="custom",
            search_settings=search_settings,
            use_system_context=use_system_context,
            rag_tools=["search_file_knowledge", "search_file_descriptions", "get_file_content"],
            research_tools=["rag", "reasoning", "critique"],
            mode=mode,
            rag_generation_config={
                "model": DEFAULT_RAG_MODEL,
                "temperature": 0.3,
                "max_tokens_to_sample": 1200,
                "stream": False,
            },
            research_generation_config={
                "model": DEFAULT_RESEARCH_MODEL,
                "temperature": 0.2,
                "max_tokens_to_sample": 2000,
                "stream": False,
            },
            conversation_id=conversation_id,
        )

        agent_items = _extract_agent_items(response)
        citation_hits = _extract_citation_hits(response)
        combined = _merge_agent_items_with_citations(
            agent_items, citation_hits, self._filename_map
        )
        combined.sort(key=lambda entry: entry.score, reverse=True)
        selected = combined[: max(1, limit)]
        if not selected:
            search_hits = self._search_hits(query_text, search_settings, limit)
            if search_hits:
                self.last_mode = "agentic_search"
                return search_hits
        return [
            {
                "id": hit.item_id,
                "title": hit.title,
                "author": hit.author,
                "source_path": hit.source_path,
                "writing_typologies": hit.writing_typologies,
                "language": hit.language,
                "excerpt": hit.excerpt,
                "summary": hit.summary,
                "key_concepts": hit.key_concepts,
                "score": round(hit.score, 2),
            }
            for hit in selected
        ]

    def _search_hits(
        self, query_text: str, search_settings: Dict[str, Any], limit: int
    ) -> List[Dict[str, Any]]:
        if not self._client:
            return []
        try:
            response = self._client.retrieval.search(
                query=query_text, search_mode="custom", search_settings=search_settings
            )
        except Exception:
            return []
        results = getattr(response, "results", None)
        chunk_results = getattr(results, "chunk_search_results", None)
        if not isinstance(chunk_results, list):
            return []
        hits: List[LibraryHit] = []
        for chunk in chunk_results[: max(1, limit)]:
            meta = getattr(chunk, "metadata", {}) or {}
            if not isinstance(meta, dict):
                meta = {}
            source_file = meta.get("source_file", "") or ""
            if not source_file:
                continue
            file_meta = self._filename_map.get(source_file, {})
            excerpt = _trim_excerpt(str(getattr(chunk, "text", "") or ""))
            hits.append(
                LibraryHit(
                    item_id=file_meta.get("id", source_file),
                    title=file_meta.get("title", source_file),
                    author=file_meta.get("author", ""),
                    source_path=file_meta.get("source_path", ""),
                    writing_typologies=file_meta.get("writing_typologies", []) or [],
                    language=file_meta.get("language", ""),
                    excerpt=excerpt,
                    summary="",
                    key_concepts=[],
                    score=float(getattr(chunk, "score", 0) or 0),
                )
            )
        hits.sort(key=lambda entry: entry.score, reverse=True)
        return [
            {
                "id": hit.item_id,
                "title": hit.title,
                "author": hit.author,
                "source_path": hit.source_path,
                "writing_typologies": hit.writing_typologies,
                "language": hit.language,
                "excerpt": hit.excerpt,
                "summary": hit.summary,
                "key_concepts": hit.key_concepts,
                "score": round(hit.score, 2),
            }
            for hit in hits[: max(1, limit)]
        ]

    def _ensure_ingested(self, items: List[Dict[str, Any]]) -> None:
        if not self._client or not items:
            return
        if not self._ingested_loaded:
            self._load_ingested_source_files()
        for item in items:
            filename = item.get("filename")
            if not filename or filename in self._ingested_source_files:
                continue
            source_path = item.get("source_path")
            if not source_path:
                continue
            file_path = self._base_dir / source_path
            if not file_path.exists():
                continue
            metadata = {
                "doc_type": "SRC",
                "source_file": filename,
                "library_typology": item.get("typology", ""),
                "writing_typologies": item.get("writing_typologies", []),
                "language": item.get("language", ""),
            }
            try:
                self._client.documents.create(file_path=str(file_path), metadata=metadata)
                self._ingested_source_files.add(filename)
            except Exception:
                continue

    def _load_ingested_source_files(self) -> None:
        if not self._client:
            return
        try:
            response = self._client.documents.list(limit=1000)
        except Exception:
            self._ingested_loaded = True
            return
        results = getattr(response, "results", None)
        documents = results if isinstance(results, list) else None
        if documents is None and isinstance(response, dict):
            candidate = response.get("results")
            documents = candidate if isinstance(candidate, list) else None
        if not isinstance(documents, list):
            self._ingested_loaded = True
            return
        for doc in documents:
            metadata = (
                doc.get("metadata", {}) if isinstance(doc, dict) else getattr(doc, "metadata", {})
            )
            if not isinstance(metadata, dict):
                continue
            source_file = metadata.get("source_file")
            if source_file:
                self._ingested_source_files.add(source_file)
        self._ingested_loaded = True

    def _fallback_local(self, context_pack: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        writing_typology = context_pack.get("writing_typology", "") or ""
        language = (
            context_pack.get("style_constraints", {}).get("language", "") or ""
            if isinstance(context_pack.get("style_constraints"), dict)
            else ""
        )
        filename_prefixes = context_pack.get("library_filename_prefixes", [])
        if not isinstance(filename_prefixes, list):
            filename_prefixes = []
        filename_prefixes = [
            str(prefix).strip() for prefix in filename_prefixes if str(prefix).strip()
        ]
        query_terms = _build_query_terms(context_pack)
        items = self._library_index.get("items", [])
        if not isinstance(items, list):
            return []

        def collect_hits(filter_typology: str, filter_language: str) -> List[Dict[str, Any]]:
            hits: List[LibraryHit] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename", "") or ""
                if filename_prefixes and not any(filename.startswith(p) for p in filename_prefixes):
                    continue
                item_id = item.get("id", "")
                source_path = item.get("source_path", "")
                title = item.get("title", "")
                author = item.get("author", "")
                typologies = item.get("writing_typologies", [])
                item_language = item.get("language", "")
                if filter_typology and filter_typology not in (typologies or []):
                    continue
                if filter_language and item_language != filter_language:
                    continue
                score = 0.0
                meta_text = f"{title} {author} {' '.join(typologies or [])}".lower()
                score += _count_term_hits(meta_text, query_terms) * 0.5
                text = self._load_text(source_path)
                excerpt, text_score = _find_excerpt(text, query_terms)
                score += text_score
                hits.append(
                    LibraryHit(
                        item_id=item_id,
                        title=title,
                        author=author,
                        source_path=source_path,
                        writing_typologies=typologies if isinstance(typologies, list) else [],
                        language=item_language,
                        excerpt=excerpt,
                        summary="",
                        key_concepts=[],
                        score=score,
                    )
                )
            hits.sort(key=lambda entry: entry.score, reverse=True)
            selected = hits[: max(1, limit)] if hits else []
            return [
                {
                    "id": hit.item_id,
                    "title": hit.title,
                    "author": hit.author,
                    "source_path": hit.source_path,
                    "writing_typologies": hit.writing_typologies,
                    "language": hit.language,
                    "excerpt": hit.excerpt,
                    "summary": hit.summary,
                    "key_concepts": hit.key_concepts,
                    "score": round(hit.score, 2),
                }
                for hit in selected
            ]

        hits = collect_hits(writing_typology, language)
        if hits:
            return hits
        if writing_typology or language:
            return collect_hits("", "")
        return hits

    def _load_text(self, source_path: str) -> str:
        if not source_path:
            return ""
        if source_path not in self._text_cache:
            self._text_cache[source_path] = load_text(source_path) or ""
        return self._text_cache[source_path]


def _build_filename_map(index: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    items = index.get("items", []) if isinstance(index, dict) else []
    filename_map: Dict[str, Dict[str, Any]] = {}
    if not isinstance(items, list):
        return filename_map
    for item in items:
        if isinstance(item, dict) and item.get("filename"):
            filename_map[item["filename"]] = item
    return filename_map


def _select_filenames(
    index: Dict[str, Any],
    writing_typology: str,
    language: str,
    library_typologies: List[str],
) -> List[str]:
    items = index.get("items", []) if isinstance(index, dict) else []
    filenames = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        if library_typologies:
            typology = item.get("typology")
            if typology not in library_typologies:
                continue
        if writing_typology:
            if writing_typology not in (item.get("writing_typologies") or []):
                continue
        if language and item.get("language") != language:
            continue
        filename = item.get("filename")
        if filename:
            filenames.append(filename)
    return filenames


def _build_search_settings(filenames: List[str], limit: int = 12) -> Dict[str, Any]:
    base_filter: Dict[str, Any] = {"metadata.doc_type": {"$eq": "SRC"}}
    if filenames:
        base_filter = {
            "$and": [
                {"metadata.doc_type": {"$eq": "SRC"}},
                {"metadata.source_file": {"$in": filenames}},
            ]
        }
    search_strategy = os.environ.get("R2R_SEARCH_STRATEGY", "rag_fusion").strip().lower()
    if search_strategy not in {"vanilla", "hyde", "rag_fusion"}:
        search_strategy = "vanilla"
    num_sub_queries = _env_int("R2R_NUM_SUB_QUERIES", 3)
    include_scores = _env_bool("R2R_INCLUDE_SCORES", True)
    include_metadatas = _env_bool("R2R_INCLUDE_METADATA", True)
    return {
        "use_semantic_search": True,
        "use_fulltext_search": True,
        "use_hybrid_search": True,
        "include_scores": include_scores,
        "include_metadatas": include_metadatas,
        "search_strategy": search_strategy,
        "num_sub_queries": num_sub_queries,
        "hybrid_settings": {
            "full_text_weight": 1.0,
            "semantic_weight": 4.0,
            "full_text_limit": 200,
            "rrf_k": 50,
        },
        "filters": base_filter,
        "limit": limit,
    }


def _build_task_prompt(context_pack: Dict[str, Any], limit: int) -> str:
    target_path = context_pack.get("target_path", "")
    writing_typology = context_pack.get("writing_typology", "")
    return (
        "You are a research agent. Search the library to extract concepts and passages "
        f"relevant to {writing_typology or 'writing'} for target '{target_path}'. "
        "Return ONLY valid JSON with this schema:\n"
        '{ "items": [ { "source_file": "", "summary": "", "key_concepts": [], '
        '"excerpt": "" } ] }\n'
        f"- Provide at most {limit} items.\n"
        "- Excerpts must be verbatim from sources and under 400 characters.\n"
        "- Summaries must be concise (1-3 sentences).\n"
        "- If unsure, return an empty items list."
    )


def _build_query_text(context_pack: Dict[str, Any]) -> str:
    parts: List[str] = []
    strategy_question = context_pack.get("strategy_question")
    if isinstance(strategy_question, str) and strategy_question.strip():
        parts.append(strategy_question.strip())
    for key in (
        "writing_typology",
        "target_path",
        "target_section_name",
        "core_summary",
        "brief_primary_objective",
        "brief_project_title",
        "brief_video_type",
    ):
        value = context_pack.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    duration_s = context_pack.get("brief_target_duration_s")
    if isinstance(duration_s, (int, float)) and duration_s:
        parts.append(f"duration_seconds={int(duration_s)}")
    for list_key in (
        "brief_secondary_objectives",
        "brief_priorities",
        "thinker_constraints",
        "brief_constraints",
    ):
        values = context_pack.get(list_key, [])
        if isinstance(values, list):
            parts.extend([str(item) for item in values if str(item).strip()])
    parts.extend(_extract_sparse_context(context_pack.get("target_strata_non_empty")))
    parts.extend(_extract_sparse_context(context_pack.get("dependencies_non_empty")))
    return " | ".join(parts) if parts else "Narrative writing guidance."


def _extract_sparse_context(items: Any, limit: int = 18) -> List[str]:
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for entry in items:
        if len(out) >= limit:
            break
        if not isinstance(entry, dict):
            continue
        value = entry.get("value")
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        path = str(entry.get("path", "")).strip()
        snippet = " ".join(text.split())
        if len(snippet) > 80:
            snippet = snippet[:80].rsplit(" ", 1)[0].strip() + "..."
        out.append(f"{path}: {snippet}" if path else snippet)
    return out


def _build_query_terms(context_pack: Dict[str, Any]) -> List[str]:
    text = _build_query_text(context_pack)
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return list(dict.fromkeys(tokens))


def _infer_library_typologies(context_pack: Dict[str, Any], index: Dict[str, Any]) -> List[str]:
    target_path = context_pack.get("target_path", "")
    if isinstance(target_path, str) and target_path.startswith("n0"):
        return ["narratology"]
    typologies = index.get("typologies") if isinstance(index, dict) else []
    return typologies if isinstance(typologies, list) else []


def _select_items_by_filename_prefixes(
    index: Dict[str, Any], prefixes: List[str]
) -> List[Dict[str, Any]]:
    items = index.get("items", []) if isinstance(index, dict) else []
    if not isinstance(items, list) or not prefixes:
        return []
    selected: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        filename = item.get("filename", "") or ""
        if filename and any(filename.startswith(prefix) for prefix in prefixes):
            selected.append(item)
    return selected


def _select_ingest_items(
    index: Dict[str, Any],
    library_typologies: List[str],
    writing_typology: str,
    language: str,
) -> List[Dict[str, Any]]:
    items = index.get("items", []) if isinstance(index, dict) else []
    selected = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        if library_typologies:
            typology = item.get("typology")
            if typology not in library_typologies:
                continue
        if writing_typology:
            if writing_typology not in (item.get("writing_typologies") or []):
                continue
        if language and item.get("language") != language:
            continue
        selected.append(item)
    return selected


def _extract_agent_items(response: Any) -> List[Dict[str, Any]]:
    message_text = _get_latest_message_text(response)
    if not message_text:
        return []
    json_block = _extract_json_block(message_text)
    if not json_block:
        return []
    try:
        parsed = json.loads(json_block)
    except json.JSONDecodeError:
        return []
    items = parsed.get("items", []) if isinstance(parsed, dict) else []
    return items if isinstance(items, list) else []


def _extract_citation_hits(response: Any) -> List[Dict[str, Any]]:
    citations = _get_latest_citations(response)
    hits = []
    for citation in citations:
        if not isinstance(citation, dict):
            continue
        meta = citation.get("metadata", {}) or {}
        source_file = meta.get("source_file") or meta.get("title") or ""
        text = citation.get("text", "") or ""
        hits.append(
            {
                "source_file": source_file,
                "excerpt": _trim_excerpt(text),
                "score": float(citation.get("score") or 0),
            }
        )
    return hits


def _merge_agent_items_with_citations(
    agent_items: List[Dict[str, Any]],
    citation_hits: List[Dict[str, Any]],
    filename_map: Dict[str, Dict[str, Any]],
) -> List[LibraryHit]:
    merged: Dict[str, LibraryHit] = {}
    for item in agent_items:
        if not isinstance(item, dict):
            continue
        source_file = item.get("source_file", "") or ""
        meta = filename_map.get(source_file, {})
        merged[source_file] = LibraryHit(
            item_id=meta.get("id", source_file),
            title=meta.get("title", source_file),
            author=meta.get("author", ""),
            source_path=meta.get("source_path", ""),
            writing_typologies=meta.get("writing_typologies", []) or [],
            language=meta.get("language", ""),
            excerpt=_trim_excerpt(item.get("excerpt", "") or ""),
            summary=(item.get("summary", "") or "").strip(),
            key_concepts=item.get("key_concepts", []) if isinstance(item.get("key_concepts"), list) else [],
            score=1.0,
        )
    for hit in citation_hits:
        source_file = hit.get("source_file", "") or ""
        if not source_file:
            continue
        meta = filename_map.get(source_file, {})
        if source_file in merged:
            existing = merged[source_file]
            if hit.get("excerpt") and not existing.excerpt:
                existing.excerpt = hit.get("excerpt", "")
            existing.score = max(existing.score, hit.get("score", 0))
        else:
            merged[source_file] = LibraryHit(
                item_id=meta.get("id", source_file),
                title=meta.get("title", source_file),
                author=meta.get("author", ""),
                source_path=meta.get("source_path", ""),
                writing_typologies=meta.get("writing_typologies", []) or [],
                language=meta.get("language", ""),
                excerpt=hit.get("excerpt", ""),
                summary="",
                key_concepts=[],
                score=hit.get("score", 0),
            )
    return list(merged.values())


def _get_latest_message_text(response: Any) -> str:
    messages = _get_messages(response)
    for message in reversed(messages):
        if isinstance(message, dict):
            content = message.get("content")
        else:
            content = getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def _get_latest_citations(response: Any) -> List[Dict[str, Any]]:
    messages = _get_messages(response)
    for message in reversed(messages):
        metadata = message.get("metadata") if isinstance(message, dict) else getattr(message, "metadata", None)
        if isinstance(metadata, dict):
            citations = metadata.get("citations")
            if isinstance(citations, list):
                return citations
    return []


def _get_messages(response: Any) -> List[Any]:
    results = getattr(response, "results", None)
    if results is not None:
        messages = getattr(results, "messages", None)
        if isinstance(messages, list):
            return messages
    if isinstance(response, dict):
        messages = response.get("results", {}).get("messages", [])
        if isinstance(messages, list):
            return messages
    return []


def _extract_json_block(content: str) -> str:
    if "```json" not in content:
        return ""
    _, _, rest = content.partition("```json")
    json_block = rest
    if "```" in rest:
        json_block, _, _ = rest.partition("```")
    return json_block.strip()


def _count_term_hits(text: str, terms: List[str]) -> int:
    if not text or not terms:
        return 0
    return sum(1 for term in terms if term in text)


def _find_excerpt(text: str, terms: List[str]) -> Tuple[str, float]:
    if not text:
        return "", 0.0
    lowered = text.lower()
    best_index: Optional[int] = None
    for term in terms:
        idx = lowered.find(term)
        if idx != -1 and (best_index is None or idx < best_index):
            best_index = idx
    if best_index is None:
        return _trim_excerpt(text[:320]), 0.1
    start = max(0, best_index - 160)
    end = min(len(text), best_index + 220)
    excerpt = _trim_excerpt(text[start:end])
    return excerpt, 1.0 + (0.1 * len(terms))


def _trim_excerpt(text: str) -> str:
    cleaned = " ".join(str(text).split())
    return cleaned[:360]
