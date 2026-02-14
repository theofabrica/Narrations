"""Agentic RAG helper for writer library retrieval."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from difflib import SequenceMatcher
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import settings
from app.narration_agent.spec_loader import load_json, load_text
from app.narration_agent.writer_agent.prompt_compiler import RedactorPromptCompiler

DEFAULT_R2R_BASE = "http://localhost:7272"
DEFAULT_RAG_MODEL = os.environ.get("R2R_RAG_MODEL", "openai/gpt-4o-mini")
DEFAULT_RESEARCH_MODEL = os.environ.get("R2R_RESEARCH_MODEL", "openai/gpt-4o-mini")
DEFAULT_MODE = os.environ.get("R2R_AGENT_MODE", "research")
DEFAULT_DISABLE_WEB_AGENTIC = os.environ.get("R2R_DISABLE_WEB_AGENTIC", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_EXCERPT_MAX_CHARS = max(
    240, int(os.environ.get("R2R_EXCERPT_MAX_CHARS", "1400") or "1400")
)
DEFAULT_POSTPARSE_SCORE_BONUS = float(
    os.environ.get("R2R_POSTPARSE_SCORE_BONUS", "0.35") or 0.35
)
DEFAULT_SRC_SEGMENT_MIN_CHARS = max(
    500, int(os.environ.get("R2R_SRC_SEGMENT_MIN_CHARS", "5000") or "5000")
)
DEFAULT_SRC_SEGMENT_CONTEXT_CHARS = max(
    500, int(os.environ.get("R2R_SRC_SEGMENT_CONTEXT_CHARS", "5000") or "5000")
)
DEFAULT_SEGMENT_TAG_SIMILARITY_MIN = min(
    0.99,
    max(0.0, float(os.environ.get("R2R_SEGMENT_TAG_SIMILARITY_MIN", "0.50") or 0.50)),
)
DEFAULT_DEEP_AGENTIC = os.environ.get("R2R_DEEP_AGENTIC", "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DEFAULT_ENABLE_AGENTIC_GET_FILE_CONTENT = os.environ.get(
    "R2R_ENABLE_AGENTIC_GET_FILE_CONTENT", "0"
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LOCAL_R2R_PATHS = [
    Path(__file__).resolve().parents[2] / "tools" / "r2r" / "py",
    Path(__file__).resolve().parents[4] / "agentic" / "r2r" / "R2R" / "py",
]
_NARRATION_BASE_DIR = Path(__file__).resolve().parents[2]
_SEGMENT_TAG_RE = re.compile(r"###([A-Za-z0-9_-]+)###")


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


def _env_float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
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
    source_file: str = ""


class LibraryRAG:
    """Retrieve relevant library snippets using R2R agentic RAG."""

    def __init__(self) -> None:
        _ensure_local_r2r_path()
        self._library_index = load_json("writer_agent/strategy_finder/library/index.json") or {}
        self._text_cache: Dict[str, str] = {}
        self._segment_map_cache: Dict[str, Dict[str, str]] = {}
        self._client = None
        self._base_url = os.environ.get("R2R_API_BASE", DEFAULT_R2R_BASE)
        self._default_base_url = self._base_url
        configured_timeout = getattr(settings, "R2R_CLIENT_TIMEOUT_S", None)
        if isinstance(configured_timeout, (int, float)) and configured_timeout > 0:
            self._client_timeout_s = max(5.0, float(configured_timeout))
        else:
            self._client_timeout_s = max(5.0, _env_float("R2R_CLIENT_TIMEOUT_S", 90.0))
        self._ingested_source_files: set[str] = set()
        self._ingested_loaded = False
        self.last_mode = "fallback"
        self.last_hit_count = 0
        self.last_error = ""
        self.last_reason = ""
        self.last_policy_path: List[str] = []
        self.last_retry = ""
        self.last_request_payload: Dict[str, Any] = {}
        self.last_response_debug: Dict[str, Any] = {}
        self.last_src_expand_debug: Dict[str, Any] = {}
        self._r2r_client_cls = None
        self._clients_by_base: Dict[str, Any] = {}
        self._ingested_source_files_by_base: Dict[str, set[str]] = {}
        self._ingested_loaded_by_base: Dict[str, bool] = {}
        try:
            from r2r import R2RClient
        except Exception:
            self._client = None
        else:
            self._r2r_client_cls = R2RClient
            self._client = R2RClient(self._base_url, timeout=self._client_timeout_s)
            self._clients_by_base[self._base_url] = self._client
            self._ingested_source_files_by_base[self._base_url] = set()
            self._ingested_loaded_by_base[self._base_url] = False
        self._filename_map = _build_filename_map(self._library_index)
        self._base_dir = _NARRATION_BASE_DIR

    def retrieve(self, context_pack: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        if not isinstance(context_pack, dict):
            return []
        self._activate_client_for_target(str(context_pack.get("target_path", "") or ""))
        self.last_error = ""
        self.last_reason = ""
        self.last_policy_path = []
        self.last_retry = ""
        self.last_request_payload = {
            "limit": limit,
            "path": "agentic",
            "client_timeout_s": self._client_timeout_s,
            "r2r_base_url": self._base_url,
        }
        self.last_response_debug = {}
        self.last_src_expand_debug = {}
        if not self._client:
            hits = self._fallback_local(context_pack, limit)
            hits = self._expand_hits_from_src_segments(hits)
            if self.last_src_expand_debug:
                self.last_response_debug["src_expand"] = _to_jsonable(self.last_src_expand_debug)
            self.last_mode = "fallback_local"
            self.last_hit_count = len(hits)
            self.last_error = "R2R client unavailable"
            self.last_reason = "client_unavailable"
            self.last_policy_path = ["agentic", "local"]
            self.last_request_payload["path"] = "local"
            return hits
        try:
            self.last_mode = ""
            hits = self._retrieve_agentic(context_pack, limit)
        except Exception as exc:
            pre_fallback_payload = (
                dict(self.last_request_payload)
                if isinstance(self.last_request_payload, dict)
                else {}
            )
            pre_fallback_debug = (
                dict(self.last_response_debug)
                if isinstance(self.last_response_debug, dict)
                else {}
            )
            hits = self._fallback_local(context_pack, limit)
            hits = self._expand_hits_from_src_segments(hits)
            if self.last_src_expand_debug:
                self.last_response_debug["src_expand"] = _to_jsonable(self.last_src_expand_debug)
            self.last_mode = "fallback_error"
            self.last_hit_count = len(hits)
            self.last_error = f"{exc.__class__.__name__}: {str(exc)}"
            self.last_reason = f"agentic_exception:{exc.__class__.__name__}"
            self.last_policy_path = ["agentic", "local"]
            if not isinstance(self.last_request_payload, dict):
                self.last_request_payload = {}
            self.last_request_payload["fallback_origin"] = "agentic_exception"
            self.last_request_payload["fallback_exception_class"] = exc.__class__.__name__
            self.last_request_payload["fallback_exception"] = str(exc)
            if pre_fallback_payload:
                self.last_request_payload["fallback_from_request_payload"] = _to_jsonable(
                    pre_fallback_payload
                )
            if pre_fallback_debug:
                self.last_request_payload["fallback_from_response_debug"] = _to_jsonable(
                    pre_fallback_debug
                )
            if not isinstance(self.last_response_debug, dict):
                self.last_response_debug = {}
            self.last_response_debug["fallback_origin"] = "agentic_exception"
            self.last_response_debug["fallback_exception_class"] = exc.__class__.__name__
            self.last_response_debug["fallback_exception"] = str(exc)
            return hits
        else:
            if not self.last_mode:
                self.last_mode = "agentic"
            if not self.last_reason:
                if self.last_mode == "agentic_search":
                    self.last_reason = "agentic_empty_then_search"
                    self.last_policy_path = ["agentic", "search"]
                else:
                    self.last_reason = "agentic_success"
                    self.last_policy_path = ["agentic"]
            self.last_hit_count = len(hits)
            self.last_error = ""
            hits = self._expand_hits_from_src_segments(hits)
            if self.last_src_expand_debug:
                self.last_response_debug["src_expand"] = _to_jsonable(self.last_src_expand_debug)
            return hits

    def ingest_all(self) -> int:
        items = self._library_index.get("items", [])
        if not isinstance(items, list):
            return 0
        self._activate_client_for_target("")
        self._ensure_ingested(items)
        return len(items)

    def conversation_exists(self, conversation_id: str, target_path: str = "") -> bool:
        self._activate_client_for_target(target_path)
        if not self._client:
            return False
        cid = _as_uuid_or_none(conversation_id)
        if not cid:
            return False
        try:
            self._client.conversations.retrieve(id=cid)
            return True
        except Exception:
            return False

    def create_conversation(self, name: str = "", target_path: str = "") -> str:
        self._activate_client_for_target(target_path)
        if not self._client:
            return ""
        try:
            response = self._client.conversations.create(name=name or None)
        except Exception:
            return ""
        return _extract_conversation_id(response)

    def _retrieve_agentic(self, context_pack: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        self._activate_client_for_target(str(context_pack.get("target_path", "") or ""))
        query_bundle = _build_query_bundle(context_pack)
        query_text = query_bundle.get("architecture_query", "") or _build_query_text(
            context_pack
        )
        context_object = query_bundle.get("context_object", "")
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
        task_prompt = (
            None
            if use_system_context
            else _build_task_prompt(context_pack, limit, context_object=context_object)
        )
        # IMPORTANT: only use an actual R2R conversation id.
        # source_state_id is app-level state tracking and must never be used as R2R conversation_id.
        conversation_id = _as_uuid_or_none(context_pack.get("rag_conversation_id"))
        deep_agentic = _is_deep_agentic_enabled(context_pack)
        if deep_agentic:
            return self._retrieve_agentic_deep(
                context_pack=context_pack,
                query_text=query_text,
                context_object=context_object,
                search_settings=search_settings,
                allowed_filenames=allowed_filenames,
                conversation_id=conversation_id,
                limit=limit,
            )

        tools_cfg = _agentic_tools_config()
        mode = tools_cfg["mode"]
        self.last_request_payload = {
            "limit": limit,
            "path": "agentic",
            "query_text": query_text,
            "query_text_architecture": query_text,
            "query_context_object": context_object,
            "writing_typology": writing_typology,
            "language": language,
            "filename_prefixes": filename_prefixes,
            "library_typologies": library_typologies,
            "allowed_filenames": allowed_filenames,
            "search_settings": _to_jsonable(search_settings),
            "use_system_context": use_system_context,
            "task_prompt": task_prompt or "",
            "conversation_id": conversation_id or "",
            "mode": mode,
            "rag_tools": tools_cfg["rag_tools"],
            "disable_web_agentic": tools_cfg["disable_web_agentic"],
        }
        if tools_cfg["research_tools"]:
            self.last_request_payload["research_tools"] = tools_cfg["research_tools"]
        request_kwargs = {
            "message": {"role": "user", "content": query_text},
            "task_prompt": task_prompt,
            "search_mode": "custom",
            "search_settings": search_settings,
            "use_system_context": use_system_context,
            "rag_tools": tools_cfg["rag_tools"],
            "mode": mode,
            "rag_generation_config": {
                "model": DEFAULT_RAG_MODEL,
                "temperature": 0.3,
                "max_tokens_to_sample": 1200,
                "stream": False,
            },
            "research_generation_config": {
                "model": DEFAULT_RESEARCH_MODEL,
                "temperature": 0.2,
                "max_tokens_to_sample": 2000,
                "stream": False,
            },
        }
        if tools_cfg["research_tools"]:
            request_kwargs["research_tools"] = tools_cfg["research_tools"]

        try:
            response = self._client.retrieval.agent(
                **request_kwargs,
                conversation_id=conversation_id,
            )
        except Exception as first_exc:
            conversation_not_found = _is_conversation_not_found_error(first_exc)
            if conversation_not_found:
                if not isinstance(self.last_response_debug, dict):
                    self.last_response_debug = {}
                self.last_response_debug["conversation_not_found"] = True
            if conversation_id:
                try:
                    response = self._client.retrieval.agent(
                        **request_kwargs,
                        conversation_id=None,
                    )
                    self.last_request_payload["path"] = "agentic_retry_without_conversation"
                    self.last_retry = "agentic_retry_without_conversation_success"
                    self.last_reason = (
                        "agentic_retry_without_conversation_after_not_found"
                        if conversation_not_found
                        else "agentic_retry_without_conversation_success"
                    )
                    self.last_policy_path = [
                        "agentic_with_conversation",
                        "agentic_without_conversation",
                    ]
                except Exception as second_exc:
                    raise RuntimeError(
                        f"agent_with_conversation_failed={first_exc};"
                        f" agent_without_conversation_failed={second_exc}"
                    ) from second_exc
            else:
                raise

        agent_items = _extract_agent_items(response)
        citation_hits = _extract_citation_hits(response)
        message_text = _get_latest_message_text(response)
        search_seed_hits: List[Dict[str, Any]] = []
        if not citation_hits:
            search_seed_hits = self._search_hits(query_text, search_settings, max(3, limit))
        if not agent_items and message_text:
            source_candidates = _collect_candidate_source_files(
                citation_hits=citation_hits,
                search_hits=search_seed_hits,
                allowed_sources=set(allowed_filenames),
            )
            agent_items = _coerce_freeform_agent_items(
                message_text=message_text,
                source_candidates=source_candidates,
                max_items=max(2, limit),
            )
        agent_items, non_verbatim_items = self._filter_non_verbatim_agent_items(agent_items)
        combined = _merge_agent_items_with_citations(
            agent_items,
            citation_hits,
            self._filename_map,
            allowed_sources=set(allowed_filenames),
        )
        self.last_response_debug = {
            "raw_agent_message": _compact_debug_text(message_text, 2400),
            "raw_citations_count": len(citation_hits),
            "parsed_agent_items_count": len(agent_items),
            "merged_hits_count": len(combined),
            "non_verbatim_excerpt_items_count": non_verbatim_items,
            "coerced_freeform_items_count": len(agent_items) if message_text and not _extract_agent_items(response) else 0,
        }
        combined.sort(key=lambda entry: entry.score, reverse=True)
        selected = combined[: max(1, limit)]
        if not selected:
            search_hits = search_seed_hits or self._search_hits(query_text, search_settings, limit)
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

    def _retrieve_agentic_deep(
        self,
        *,
        context_pack: Dict[str, Any],
        query_text: str,
        context_object: str,
        search_settings: Dict[str, Any],
        allowed_filenames: List[str],
        conversation_id: str | None,
        limit: int,
    ) -> List[Dict[str, Any]]:
        tools_cfg = _agentic_tools_config()
        mode = tools_cfg["mode"]
        deep_pass_count = _target_deep_pass_count(str(context_pack.get("target_path", "") or ""))
        focused_limit = max(8, limit * 3)
        exploratory_limit = max(10, limit * 4)
        focused_settings = _build_deep_search_settings(
            filenames=allowed_filenames, limit=focused_limit, profile="focused"
        )
        exploratory_settings = _build_deep_search_settings(
            filenames=allowed_filenames, limit=exploratory_limit, profile="exploratory"
        )
        focused_prompt = _build_task_prompt(
            context_pack,
            focused_limit,
            pass_name="focused",
            deep_mode=True,
            allowed_filenames=allowed_filenames,
            context_object=context_object,
        )
        exploratory_prompt = _build_task_prompt(
            context_pack,
            exploratory_limit,
            pass_name="exploratory",
            deep_mode=True,
            allowed_filenames=allowed_filenames,
            context_object=context_object,
        )
        exploratory_query = _build_exploratory_query(
            query_text, context_pack, context_object=context_object
        )
        use_system_context = False

        self.last_request_payload = {
            "limit": limit,
            "path": "agentic_deep",
            "query_text": query_text,
            "query_text_architecture": query_text,
            "query_context_object": context_object,
            "writing_typology": str(context_pack.get("writing_typology", "") or ""),
            "language": str(
                (
                    context_pack.get("style_constraints", {}).get("language", "")
                    if isinstance(context_pack.get("style_constraints"), dict)
                    else ""
                )
                or ""
            ),
            "allowed_filenames": allowed_filenames,
            "base_search_settings": _to_jsonable(search_settings),
            "deep_agentic": {
                "enabled": True,
                "pass_count": int(deep_pass_count),
                "use_system_context": use_system_context,
                "passes": [
                    {
                        "name": "focused",
                        "query_text": query_text,
                        "task_prompt": focused_prompt,
                        "search_settings": _to_jsonable(focused_settings),
                    },
                    {
                        "name": "exploratory",
                        "query_text": exploratory_query,
                        "task_prompt": exploratory_prompt,
                        "search_settings": _to_jsonable(exploratory_settings),
                    },
                ],
            },
            "conversation_id": conversation_id or "",
            "mode": mode,
            "rag_tools": tools_cfg["rag_tools"],
            "disable_web_agentic": tools_cfg["disable_web_agentic"],
        }
        if tools_cfg["research_tools"]:
            self.last_request_payload["research_tools"] = tools_cfg["research_tools"]

        def run_pass(
            *, pass_name: str, pass_query: str, pass_prompt: str, pass_settings: Dict[str, Any]
        ) -> tuple[List[Dict[str, Any]], bool]:
            request_kwargs = {
                "message": {"role": "user", "content": pass_query},
                "task_prompt": pass_prompt,
                "search_mode": "custom",
                "search_settings": pass_settings,
                "use_system_context": use_system_context,
                "rag_tools": tools_cfg["rag_tools"],
                "mode": mode,
                "rag_generation_config": {
                    "model": DEFAULT_RAG_MODEL,
                    "temperature": 0.2,
                    "max_tokens_to_sample": 1400,
                    "stream": False,
                },
                "research_generation_config": {
                    "model": DEFAULT_RESEARCH_MODEL,
                    "temperature": 0.15,
                    "max_tokens_to_sample": 2400,
                    "stream": False,
                },
            }
            if tools_cfg["research_tools"]:
                request_kwargs["research_tools"] = tools_cfg["research_tools"]
            retried_without_conversation = False
            try:
                response = self._client.retrieval.agent(
                    **request_kwargs,
                    conversation_id=conversation_id,
                )
            except Exception as first_exc:
                conversation_not_found = _is_conversation_not_found_error(first_exc)
                if conversation_not_found:
                    if not isinstance(self.last_response_debug, dict):
                        self.last_response_debug = {}
                    self.last_response_debug["conversation_not_found"] = True
                if conversation_id:
                    try:
                        response = self._client.retrieval.agent(
                            **request_kwargs,
                            conversation_id=None,
                        )
                        retried_without_conversation = True
                    except Exception as second_exc:
                        raise RuntimeError(
                            f"{pass_name}_with_conversation_failed={first_exc};"
                            f" {pass_name}_without_conversation_failed={second_exc}"
                        ) from second_exc
                else:
                    raise

            agent_items = _extract_agent_items(response)
            citation_hits = _extract_citation_hits(response)
            message_text = _get_latest_message_text(response)
            search_seed_hits: List[Dict[str, Any]] = []
            if not citation_hits:
                search_seed_hits = self._search_hits(pass_query, pass_settings, max(4, limit * 2))
            if not agent_items and message_text:
                source_candidates = _collect_candidate_source_files(
                    citation_hits=citation_hits,
                    search_hits=search_seed_hits,
                    allowed_sources=set(allowed_filenames),
                )
                agent_items = _coerce_freeform_agent_items(
                    message_text=message_text,
                    source_candidates=source_candidates,
                    max_items=max(3, limit),
                )
            agent_items, non_verbatim_items = self._filter_non_verbatim_agent_items(agent_items)
            merged_hits = _merge_agent_items_with_citations(
                agent_items,
                citation_hits,
                self._filename_map,
                allowed_sources=set(allowed_filenames),
            )
            invalid_source_file_items = max(0, len(agent_items) - len(merged_hits))
            pass_debug = {
                "pass_name": pass_name,
                "raw_agent_message": _compact_debug_text(message_text, 1600),
                "raw_citations_count": len(citation_hits),
                "parsed_agent_items_count": len(agent_items),
                "merged_hits_count": len(merged_hits),
                "invalid_source_file_items_count": invalid_source_file_items,
                "non_verbatim_excerpt_items_count": non_verbatim_items,
                "coerced_freeform_items_count": len(agent_items)
                if message_text and not _extract_agent_items(response)
                else 0,
            }
            if not isinstance(self.last_response_debug, dict):
                self.last_response_debug = {}
            passes = self.last_response_debug.get("passes", [])
            if not isinstance(passes, list):
                passes = []
            passes.append(pass_debug)
            self.last_response_debug["passes"] = passes
            merged_hits.sort(key=lambda entry: entry.score, reverse=True)
            if merged_hits:
                return (
                    [
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
                            "score": round(hit.score, 3),
                        }
                        for hit in merged_hits[: max(6, limit * 3)]
                    ],
                    retried_without_conversation,
                )
            search_hits = search_seed_hits or self._search_hits(pass_query, pass_settings, max(4, limit * 2))
            return search_hits, retried_without_conversation

        focused_hits, focused_retried = run_pass(
            pass_name="focused",
            pass_query=query_text,
            pass_prompt=focused_prompt,
            pass_settings=focused_settings,
        )
        exploratory_hits: List[Dict[str, Any]] = []
        exploratory_retried = False
        exploratory_error = ""
        if deep_pass_count >= 2:
            try:
                exploratory_hits, exploratory_retried = run_pass(
                    pass_name="exploratory",
                    pass_query=exploratory_query,
                    pass_prompt=exploratory_prompt,
                    pass_settings=exploratory_settings,
                )
            except Exception as exc:
                exploratory_error = f"{exc.__class__.__name__}: {str(exc)}"
                if not isinstance(self.last_response_debug, dict):
                    self.last_response_debug = {}
                passes = self.last_response_debug.get("passes", [])
                if not isinstance(passes, list):
                    passes = []
                passes.append(
                    {
                        "pass_name": "exploratory",
                        "error": exploratory_error,
                        "raw_agent_message": "",
                        "raw_citations_count": 0,
                        "parsed_agent_items_count": 0,
                        "merged_hits_count": 0,
                        "invalid_source_file_items_count": 0,
                        "coerced_freeform_items_count": 0,
                    }
                )
                self.last_response_debug["passes"] = passes

        if focused_retried or exploratory_retried:
            self.last_retry = "agentic_retry_without_conversation_success"
            self.last_reason = "agentic_retry_without_conversation_success"
            self.last_policy_path = [
                "agentic_with_conversation",
                "agentic_without_conversation",
                "deep_two_pass",
            ]
        if exploratory_error and focused_hits:
            self.last_reason = "deep_exploratory_failed_kept_focused"
            self.last_policy_path = [
                "deep_two_pass",
                "focused_ok",
                "exploratory_failed",
                "keep_focused",
            ]

        combined = _fuse_deep_hits(
            focused_hits=focused_hits,
            exploratory_hits=exploratory_hits,
            final_limit=max(6, limit * 3),
        )
        passes = self.last_response_debug.get("passes", []) if isinstance(self.last_response_debug, dict) else []
        if not isinstance(passes, list):
            passes = []
        self.last_response_debug = {
            "raw_agent_message": "\n\n---\n\n".join(
                [
                    str(entry.get("raw_agent_message", "")).strip()
                    for entry in passes
                    if isinstance(entry, dict) and str(entry.get("raw_agent_message", "")).strip()
                ]
            )[:3200],
            "raw_citations_count": sum(
                int(entry.get("raw_citations_count", 0) or 0)
                for entry in passes
                if isinstance(entry, dict)
            ),
            "parsed_agent_items_count": sum(
                int(entry.get("parsed_agent_items_count", 0) or 0)
                for entry in passes
                if isinstance(entry, dict)
            ),
            "merged_hits_count": sum(
                int(entry.get("merged_hits_count", 0) or 0)
                for entry in passes
                if isinstance(entry, dict)
            ),
            "invalid_source_file_items_count": sum(
                int(entry.get("invalid_source_file_items_count", 0) or 0)
                for entry in passes
                if isinstance(entry, dict)
            ),
            "coerced_freeform_items_count": sum(
                int(entry.get("coerced_freeform_items_count", 0) or 0)
                for entry in passes
                if isinstance(entry, dict)
            ),
            "fused_hits_count": len(combined),
            "exploratory_error": exploratory_error,
            "passes": passes,
        }
        parsed_total = int(self.last_response_debug.get("parsed_agent_items_count", 0) or 0)
        merged_total = int(self.last_response_debug.get("merged_hits_count", 0) or 0)
        if parsed_total > 0 and merged_total == 0:
            if self.last_reason:
                self.last_reason = f"{self.last_reason}_agent_items_invalid_source_file"
            else:
                self.last_reason = "agent_items_invalid_source_file"
        if combined:
            self.last_mode = "agentic_deep"
            return combined[: max(1, limit * 3)]

        # Last fallback in deep mode: keep standard search behavior.
        fallback_hits = self._search_hits(query_text, search_settings, limit)
        if fallback_hits:
            self.last_mode = "agentic_search"
            return fallback_hits
        return []

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
                    source_file=source_file,
                )
            )
        hits.sort(key=lambda entry: entry.score, reverse=True)
        return [
            {
                "id": hit.item_id,
                "title": hit.title,
                "author": hit.author,
                "source_path": hit.source_path,
                "source_file": hit.source_file,
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
        self._ingested_source_files_by_base[self._base_url] = set(self._ingested_source_files)

    def _load_ingested_source_files(self) -> None:
        if not self._client:
            return
        try:
            response = self._client.documents.list(limit=1000)
        except Exception:
            self._ingested_loaded = True
            self._ingested_loaded_by_base[self._base_url] = True
            return
        results = getattr(response, "results", None)
        documents = results if isinstance(results, list) else None
        if documents is None and isinstance(response, dict):
            candidate = response.get("results")
            documents = candidate if isinstance(candidate, list) else None
        if not isinstance(documents, list):
            self._ingested_loaded = True
            self._ingested_loaded_by_base[self._base_url] = True
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
        self._ingested_source_files_by_base[self._base_url] = set(self._ingested_source_files)
        self._ingested_loaded_by_base[self._base_url] = True

    def _activate_client_for_target(self, target_path: str) -> None:
        base_url = self._resolve_r2r_base_url(target_path)
        self._base_url = base_url
        self._client = self._get_or_create_client(base_url)
        self._ingested_source_files = self._ingested_source_files_by_base.setdefault(base_url, set())
        self._ingested_loaded = bool(self._ingested_loaded_by_base.get(base_url, False))

    def _get_or_create_client(self, base_url: str):
        existing = self._clients_by_base.get(base_url)
        if existing is not None:
            return existing
        if self._r2r_client_cls is None:
            return None
        try:
            created = self._r2r_client_cls(base_url, timeout=self._client_timeout_s)
        except Exception:
            return None
        self._clients_by_base[base_url] = created
        self._ingested_source_files_by_base.setdefault(base_url, set())
        self._ingested_loaded_by_base.setdefault(base_url, False)
        return created

    def _resolve_r2r_base_url(self, target_path: str) -> str:
        value = str(target_path or "").strip()
        if value.startswith("n0.art_direction"):
            return (
                os.environ.get("R2R_API_BASE_ART", "").strip()
                or os.environ.get("R2R_API_BASE_ART_DIRECTION", "").strip()
                or self._default_base_url
            )
        if value.startswith("n0.sound_direction"):
            return (
                os.environ.get("R2R_API_BASE_SOUND", "").strip()
                or os.environ.get("R2R_API_BASE_SOUND_DIRECTION", "").strip()
                or self._default_base_url
            )
        if value.startswith("n0.narrative_presentation") or value.startswith("n0.production_summary"):
            return (
                os.environ.get("R2R_API_BASE_NARRATIVE", "").strip()
                or self._default_base_url
            )
        return self._default_base_url

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
        self.last_request_payload = {
            "limit": limit,
            "path": "local",
            "query_terms": query_terms,
            "writing_typology": writing_typology,
            "language": language,
            "filename_prefixes": filename_prefixes,
        }
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
                        source_file=filename,
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
                    "source_file": hit.source_file,
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

    def _expand_hits_from_src_segments(self, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(hits, list) or not hits:
            self.last_src_expand_debug = {
                "input_count": 0,
                "switched_to_src_count": 0,
                "expanded_segment_count": 0,
                "missing_src_count": 0,
                "missing_tag_or_segment_count": 0,
                "tag_from_embedded_count": 0,
                "tag_from_20_excerpt_count": 0,
                "tag_from_similarity_count": 0,
                "tag_total_resolved_count": 0,
            }
            return []
        out: List[Dict[str, Any]] = []
        switched_to_src = 0
        expanded_segment = 0
        missing_src = 0
        missing_tag_or_segment = 0
        tag_from_embedded = 0
        tag_from_20_excerpt = 0
        tag_from_similarity = 0
        tag_total_resolved = 0
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            updated = self._expand_single_hit_from_src(hit)
            tag_source = str(updated.pop("__segment_tag_source", "") or "").strip()
            if tag_source == "embedded":
                tag_from_embedded += 1
                tag_total_resolved += 1
            elif tag_source == "inferred_from_20_excerpt":
                tag_from_20_excerpt += 1
                tag_total_resolved += 1
            elif tag_source == "inferred_by_similarity":
                tag_from_similarity += 1
                tag_total_resolved += 1
            old_source_file = str(hit.get("source_file", "") or "").strip()
            old_source_path = str(hit.get("source_path", "") or "").strip()
            is_twenty_variant = old_source_file.endswith(".20.txt") or old_source_path.endswith(".20.txt")
            if is_twenty_variant:
                old_variant_ref = old_source_file or old_source_path
                new_source_file = str(updated.get("source_file", "") or "").strip()
                new_source_path = str(updated.get("source_path", "") or "").strip()
                new_variant_ref = new_source_file or new_source_path
                if new_source_file.endswith(".src.txt") or new_source_path.endswith(".src.txt"):
                    switched_to_src += 1
                else:
                    missing_src += 1
                if old_variant_ref != new_variant_ref and str(updated.get("excerpt", "") or "") != str(hit.get("excerpt", "") or ""):
                    expanded_segment += 1
                elif old_variant_ref != new_variant_ref:
                    missing_tag_or_segment += 1
            out.append(updated)
        self.last_src_expand_debug = {
            "input_count": len(hits),
            "switched_to_src_count": switched_to_src,
            "expanded_segment_count": expanded_segment,
            "missing_src_count": missing_src,
            "missing_tag_or_segment_count": missing_tag_or_segment,
            "tag_from_embedded_count": tag_from_embedded,
            "tag_from_20_excerpt_count": tag_from_20_excerpt,
            "tag_from_similarity_count": tag_from_similarity,
            "tag_total_resolved_count": tag_total_resolved,
        }
        return out

    def _expand_single_hit_from_src(self, hit: Dict[str, Any]) -> Dict[str, Any]:
        source_file = str(hit.get("source_file", "") or "").strip()
        source_path = str(hit.get("source_path", "") or "").strip()
        source_ref = source_file or (Path(source_path).name if source_path else "")
        if not source_ref.endswith(".20.txt"):
            return hit
        src_file = f"{source_ref[:-7]}.src.txt"
        src_path = self._resolve_src_path_from_hit(hit, src_file)
        if not src_path:
            return hit
        # Always canonicalize to .src when available, even if no segment tag is found.
        updated = dict(hit)
        updated["source_file"] = src_file
        updated["source_path"] = src_path
        tag_source = ""
        tag = self._extract_segment_tag(hit)
        if tag:
            tag_source = "embedded"
        else:
            twenty_path = self._resolve_twenty_path_from_hit(hit, source_ref)
            tag = self._infer_segment_tag_from_twenty_excerpt(twenty_path, hit)
            if tag:
                tag_source = "inferred_from_20_excerpt"
            elif twenty_path:
                fuzzy_tag = self._infer_segment_tag_by_similarity(
                    twenty_path=twenty_path,
                    excerpt=str(hit.get("excerpt", "") or ""),
                    min_similarity=DEFAULT_SEGMENT_TAG_SIMILARITY_MIN,
                )
                if fuzzy_tag:
                    tag = fuzzy_tag
                    tag_source = "inferred_by_similarity"
        if not tag:
            return updated
        src_segment = self._get_segment_text(src_path, tag)
        if not src_segment:
            return updated
        expanded_segment = self._expand_src_segment_with_context(
            source_path=src_path,
            segment_tag=tag,
            src_segment=src_segment,
            min_chars=DEFAULT_SRC_SEGMENT_MIN_CHARS,
            context_chars=DEFAULT_SRC_SEGMENT_CONTEXT_CHARS,
        )
        updated["excerpt"] = _trim_excerpt(expanded_segment)
        summary = str(updated.get("summary", "") or "").strip()
        if not summary or len(summary) < 40:
            updated["summary"] = self._segment_summary(expanded_segment, max_chars=420)
        if tag_source:
            updated["__segment_tag_source"] = tag_source
        return updated

    def _resolve_src_path_from_hit(self, hit: Dict[str, Any], src_file: str) -> str:
        meta = self._filename_map.get(src_file, {})
        if isinstance(meta, dict):
            source_path = str(meta.get("source_path", "") or "").strip()
            if source_path:
                return source_path
        current_path = str(hit.get("source_path", "") or "").strip()
        if current_path.endswith(".20.txt"):
            return f"{current_path[:-7]}.src.txt"
        return ""

    def _extract_segment_tag(self, hit: Dict[str, Any]) -> str:
        for key in ("excerpt", "summary"):
            text = str(hit.get(key, "") or "")
            found = _SEGMENT_TAG_RE.search(text)
            if found:
                return found.group(1)
        return ""

    def _resolve_twenty_path_from_hit(self, hit: Dict[str, Any], source_ref: str) -> str:
        source_file = str(source_ref or "").strip()
        if source_file.endswith(".20.txt"):
            meta = self._filename_map.get(source_file, {})
            if isinstance(meta, dict):
                path = str(meta.get("source_path", "") or "").strip()
                if path.endswith(".20.txt"):
                    return path
        current_path = str(hit.get("source_path", "") or "").strip()
        if current_path.endswith(".20.txt"):
            return current_path
        return ""

    def _resolve_twenty_path_from_source_file(self, source_file: str) -> str:
        value = str(source_file or "").strip()
        if not value:
            return ""
        if value.endswith(".20.txt"):
            meta = self._filename_map.get(value, {})
            if isinstance(meta, dict):
                path = str(meta.get("source_path", "") or "").strip()
                if path.endswith(".20.txt"):
                    return path
        if value.endswith(".src.txt"):
            candidate = f"{value[:-8]}.20.txt"
            meta = self._filename_map.get(candidate, {})
            if isinstance(meta, dict):
                path = str(meta.get("source_path", "") or "").strip()
                if path.endswith(".20.txt"):
                    return path
        return ""

    def _filter_non_verbatim_agent_items(
        self, agent_items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        if not isinstance(agent_items, list) or not agent_items:
            return [], 0
        kept: List[Dict[str, Any]] = []
        non_verbatim_count = 0
        for item in agent_items:
            if not isinstance(item, dict):
                continue
            kept.append(item)
            source_file = str(item.get("source_file", "") or "").strip()
            excerpt = str(item.get("excerpt", "") or "").strip()
            if not source_file or not excerpt:
                continue
            twenty_path = self._resolve_twenty_path_from_source_file(source_file)
            if not twenty_path:
                continue
            full_text = self._load_text(twenty_path)
            if not full_text:
                continue
            if self._find_excerpt_start_in_text(full_text, excerpt) < 0:
                non_verbatim_count += 1
        return kept, non_verbatim_count

    def _infer_segment_tag_from_twenty_excerpt(self, twenty_path: str, hit: Dict[str, Any]) -> str:
        excerpt = str(hit.get("excerpt", "") or "").strip()
        if not twenty_path or not excerpt:
            return ""
        full_text = self._load_text(twenty_path)
        if not full_text:
            return ""
        start = self._find_excerpt_start_in_text(full_text, excerpt)
        if start < 0:
            return ""
        matches = list(_SEGMENT_TAG_RE.finditer(full_text))
        if not matches:
            return ""
        last_tag = ""
        for match in matches:
            if match.start() > start:
                break
            last_tag = str(match.group(1) or "").strip()
        return last_tag

    def _infer_segment_tag_by_similarity(
        self,
        *,
        twenty_path: str,
        excerpt: str,
        min_similarity: float,
    ) -> str:
        path = str(twenty_path or "").strip()
        value = str(excerpt or "").strip()
        if not path or not value:
            return ""
        full_text = self._load_text(path)
        if not full_text:
            return ""
        matches = list(_SEGMENT_TAG_RE.finditer(full_text))
        if not matches:
            return ""
        candidates = self._excerpt_match_candidates(value)
        if not candidates:
            return ""
        threshold = max(0.0, min(1.0, float(min_similarity)))
        best_tag = ""
        best_score = 0.0
        for idx, match in enumerate(matches):
            tag = str(match.group(1) or "").strip()
            if not tag:
                continue
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
            segment = full_text[start:end]
            if not segment:
                continue
            score = 0.0
            for candidate in candidates:
                score = max(score, self._excerpt_containment_ratio(candidate, segment))
                if score >= 1.0:
                    break
            if score > best_score:
                best_score = score
                best_tag = tag
        return best_tag if best_score >= threshold else ""

    def _excerpt_containment_ratio(self, excerpt: str, segment: str) -> float:
        excerpt_norm, _ = self._normalize_relaxed_with_index_map(excerpt)
        segment_norm, _ = self._normalize_relaxed_with_index_map(segment)
        if not excerpt_norm or not segment_norm:
            return 0.0
        if excerpt_norm in segment_norm:
            return 1.0
        excerpt_len = len(excerpt_norm)
        segment_len = len(segment_norm)
        # Compare against local windows to tolerate minor edits/paraphrase
        # while preserving near-verbatim behavior.
        if segment_len <= excerpt_len:
            return SequenceMatcher(a=excerpt_norm, b=segment_norm, autojunk=False).ratio()
        window = excerpt_len
        step = max(1, window // 8)
        best = 0.0
        max_start = max(0, segment_len - window)
        for start in range(0, max_start + 1, step):
            chunk = segment_norm[start : start + window]
            score = SequenceMatcher(a=excerpt_norm, b=chunk, autojunk=False).ratio()
            if score > best:
                best = score
                if best >= 0.995:
                    break
        if max_start % step != 0:
            tail_chunk = segment_norm[max_start : max_start + window]
            best = max(
                best, SequenceMatcher(a=excerpt_norm, b=tail_chunk, autojunk=False).ratio()
            )
        return best

    def _find_excerpt_start_in_text(self, full_text: str, excerpt: str) -> int:
        full = str(full_text or "")
        needle = str(excerpt or "").strip()
        if not full or not needle:
            return -1
        direct_idx = full.find(needle)
        if direct_idx >= 0:
            return direct_idx

        # Light cleaning to tolerate markdown/code fences and quoted excerpts.
        cleaned_needle = needle.replace("```", "").strip().strip("\"'`")
        if cleaned_needle and cleaned_needle != needle:
            direct_cleaned_idx = full.find(cleaned_needle)
            if direct_cleaned_idx >= 0:
                return direct_cleaned_idx

        norm_full, norm_to_raw = self._normalize_with_index_map(full)
        candidates = self._excerpt_match_candidates(needle)
        for candidate in candidates:
            norm_candidate, _ = self._normalize_with_index_map(candidate)
            if not norm_candidate:
                continue
            pos = norm_full.find(norm_candidate)
            if pos < 0:
                continue
            if pos < len(norm_to_raw):
                return norm_to_raw[pos]

        # Relaxed fallback: ignore punctuation differences.
        relaxed_full, relaxed_to_raw = self._normalize_relaxed_with_index_map(full)
        for candidate in candidates:
            relaxed_candidate, _ = self._normalize_relaxed_with_index_map(candidate)
            if not relaxed_candidate:
                continue
            pos = relaxed_full.find(relaxed_candidate)
            if pos < 0:
                continue
            if pos < len(relaxed_to_raw):
                return relaxed_to_raw[pos]
        return -1

    def _excerpt_match_candidates(self, excerpt: str) -> List[str]:
        value = " ".join(str(excerpt or "").split()).strip()
        if not value:
            return []
        candidates: List[str] = [value]
        for size in (260, 180, 120, 80):
            if len(value) > size:
                prefix = value[:size].strip()
                suffix = value[-size:].strip()
                if prefix:
                    candidates.append(prefix)
                if suffix:
                    candidates.append(suffix)
                if len(value) > size * 2:
                    mid_start = (len(value) - size) // 2
                    middle = value[mid_start : mid_start + size].strip()
                    if middle:
                        candidates.append(middle)
        # Keep order, remove duplicates.
        out: List[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
        return out

    def _normalize_with_index_map(self, text: str) -> Tuple[str, List[int]]:
        value = str(text or "")
        out_chars: List[str] = []
        index_map: List[int] = []
        pending_space = False
        for idx, char in enumerate(value):
            if char.isspace():
                pending_space = len(out_chars) > 0
                continue
            if pending_space:
                out_chars.append(" ")
                index_map.append(idx)
                pending_space = False
            out_chars.append(char.lower())
            index_map.append(idx)
        normalized = "".join(out_chars).strip()
        if not normalized:
            return "", []
        # Keep map aligned with stripped output.
        left_trim = len("".join(out_chars)) - len("".join(out_chars).lstrip())
        if left_trim > 0:
            index_map = index_map[left_trim:]
        right_trim = len("".join(out_chars)) - len("".join(out_chars).rstrip())
        if right_trim > 0:
            index_map = index_map[: len(index_map) - right_trim]
        return normalized, index_map

    def _normalize_relaxed_with_index_map(self, text: str) -> Tuple[str, List[int]]:
        value = str(text or "")
        out_chars: List[str] = []
        index_map: List[int] = []
        pending_space = False
        for idx, char in enumerate(value):
            if char.isalnum():
                if pending_space and len(out_chars) > 0:
                    out_chars.append(" ")
                    index_map.append(idx)
                    pending_space = False
                out_chars.append(char.lower())
                index_map.append(idx)
                continue
            if char.isspace() or not char.isalnum():
                pending_space = len(out_chars) > 0
                continue
        normalized = "".join(out_chars).strip()
        if not normalized:
            return "", []
        left_trim = len("".join(out_chars)) - len("".join(out_chars).lstrip())
        if left_trim > 0:
            index_map = index_map[left_trim:]
        right_trim = len("".join(out_chars)) - len("".join(out_chars).rstrip())
        if right_trim > 0:
            index_map = index_map[: len(index_map) - right_trim]
        return normalized, index_map

    def _get_segment_text(self, source_path: str, segment_tag: str) -> str:
        if not source_path or not segment_tag:
            return ""
        segment_map = self._load_segment_map(source_path)
        return str(segment_map.get(segment_tag, "") or "").strip()

    def _load_segment_map(self, source_path: str) -> Dict[str, str]:
        if source_path in self._segment_map_cache:
            return self._segment_map_cache[source_path]
        text = self._load_text(source_path)
        segment_map: Dict[str, str] = {}
        if not text:
            self._segment_map_cache[source_path] = segment_map
            return segment_map
        matches = list(_SEGMENT_TAG_RE.finditer(text))
        if not matches:
            self._segment_map_cache[source_path] = segment_map
            return segment_map
        for idx, match in enumerate(matches):
            tag = str(match.group(1) or "").strip()
            if not tag:
                continue
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            chunk = text[start:end].strip()
            if chunk:
                segment_map[tag] = chunk
        self._segment_map_cache[source_path] = segment_map
        return segment_map

    def _segment_summary(self, text: str, max_chars: int = 420) -> str:
        cleaned = " ".join(str(text or "").split()).strip()
        if not cleaned:
            return ""
        if len(cleaned) <= max_chars:
            return cleaned
        snippet = cleaned[:max_chars].rsplit(" ", 1)[0].strip()
        return f"{snippet}..." if snippet else f"{cleaned[:max_chars]}..."

    def _expand_src_segment_with_context(
        self,
        *,
        source_path: str,
        segment_tag: str,
        src_segment: str,
        min_chars: int,
        context_chars: int,
    ) -> str:
        segment_text = str(src_segment or "").strip()
        if not segment_text:
            return ""
        if len(segment_text) >= max(1, int(min_chars)):
            return segment_text
        full_text = self._load_text(source_path)
        if not full_text:
            return segment_text
        matches = list(_SEGMENT_TAG_RE.finditer(full_text))
        if not matches:
            return segment_text
        target_idx = -1
        for idx, match in enumerate(matches):
            if str(match.group(1) or "").strip() == str(segment_tag).strip():
                target_idx = idx
                break
        if target_idx < 0:
            return segment_text
        seg_start = matches[target_idx].start()
        seg_end = (
            matches[target_idx + 1].start()
            if target_idx + 1 < len(matches)
            else len(full_text)
        )
        extra = max(0, int(context_chars))
        start = max(0, seg_start - extra)
        end = min(len(full_text), seg_end + extra)
        expanded = full_text[start:end].strip()
        return expanded if expanded else segment_text


def _build_filename_map(index: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    items = index.get("items", []) if isinstance(index, dict) else []
    filename_map: Dict[str, Dict[str, Any]] = {}
    if not isinstance(items, list):
        return filename_map
    for item in items:
        if not isinstance(item, dict):
            continue
        for variant in _item_variants_for_filename_map(item):
            filename = str(variant.get("filename", "") or "").strip()
            if not filename:
                continue
            filename_map[filename] = variant
    return filename_map


def _select_filenames(
    index: Dict[str, Any],
    writing_typology: str,
    language: str,
    library_typologies: List[str],
) -> List[str]:
    items = index.get("items", []) if isinstance(index, dict) else []
    selected_items: List[Dict[str, Any]] = []
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
        selected_items.append(item)
    collapsed_items = _collapse_items_by_filename_variant(selected_items)
    filenames: List[str] = []
    for item in collapsed_items:
        filename = item.get("filename")
        if filename:
            filenames.append(str(filename))
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


def _build_deep_search_settings(
    filenames: List[str], limit: int, profile: str
) -> Dict[str, Any]:
    settings = _build_search_settings(filenames, limit=limit)
    hybrid = settings.get("hybrid_settings", {})
    if not isinstance(hybrid, dict):
        hybrid = {}
        settings["hybrid_settings"] = hybrid
    if profile == "focused":
        settings["search_strategy"] = "rag_fusion"
        settings["num_sub_queries"] = 4
        hybrid["semantic_weight"] = 5.0
        hybrid["full_text_weight"] = 1.0
        hybrid["full_text_limit"] = 220
        hybrid["rrf_k"] = 45
    else:
        settings["search_strategy"] = "rag_fusion"
        settings["num_sub_queries"] = 6
        hybrid["semantic_weight"] = 3.0
        hybrid["full_text_weight"] = 2.0
        hybrid["full_text_limit"] = 260
        hybrid["rrf_k"] = 65
    return settings


def _build_task_prompt(
    context_pack: Dict[str, Any],
    limit: int,
    pass_name: str = "",
    deep_mode: bool = False,
    allowed_filenames: List[str] | None = None,
    context_object: str = "",
) -> str:
    target_path = context_pack.get("target_path", "")
    writing_typology = context_pack.get("writing_typology", "")
    target_label = _target_label_for_llm(
        str(target_path),
        str(writing_typology),
    )
    allowed_files = [
        str(name).strip() for name in (allowed_filenames or []) if str(name).strip()
    ]
    allowed_file_lines = "\n".join([f"  - {name}" for name in allowed_files[:24]])
    if not allowed_file_lines:
        allowed_file_lines = "  - (no explicit allowlist provided)"
    focus_block = _target_focus_block(str(target_path), str(writing_typology))
    if deep_mode:
        return (
            "You are an expert narratology research agent working on retrieval, not final writing.\n"
            f"Pass: {pass_name or 'generic'}.\n"
            f"Target path (internal id): {target_path}\n"
            f"Target objective (human): {target_label}\n"
            f"Writing typology: {writing_typology or 'writing'}.\n"
            "Goal: retrieve diverse, high-signal evidence from allowed files only.\n"
            "Process: (1) identify relevant principles, (2) capture concrete method statements, "
            "(3) avoid generic plot summaries.\n"
            "ALLOWED source_file values (EXACT STRING MATCH, case-sensitive):\n"
            f"{allowed_file_lines}\n"
            "STRICT VALIDATION:\n"
            "- source_file MUST be one of the allowed values above.\n"
            "- NEVER use internal ids (e.g. n0.narrative_presentation) as source_file.\n"
            "- Any item with invalid source_file will be discarded.\n"
            "- excerpt MUST be an exact contiguous quote copied from the source text (verbatim only).\n"
            "- NEVER paraphrase, compress, translate, or rewrite excerpts.\n"
            "- If you cannot provide an exact quote, skip the item.\n"
            "Return ONLY valid JSON with this schema:\n"
            '{ "items": [ { "source_file": "", "summary": "", "key_concepts": [], "excerpt": "" } ] }\n'
            f"- Provide at most {limit} items.\n"
            f"- Excerpts must be verbatim, each under {DEFAULT_EXCERPT_MAX_CHARS} characters.\n"
            "- Summaries must be 1-2 sentences and actionable for writing strategy.\n"
            "- Prefer diversity across distinct sections of source content.\n"
            "CONTEXT_POLICY:\n"
            "- Treat CONTEXT_OBJECT as project context, not as mandatory output wording.\n"
            f"{focus_block}\n"
            f"CONTEXT_OBJECT:\n{context_object.strip()[:1400] if isinstance(context_object, str) else ''}\n"
            "- If unsure, return an empty items list."
        )
    return (
        "You are a research agent. Search the library to extract concepts and passages "
        f"relevant to {writing_typology or 'writing'} for target '{target_label}'. "
        "Return ONLY valid JSON with this schema:\n"
        '{ "items": [ { "source_file": "", "summary": "", "key_concepts": [], '
        '"excerpt": "" } ] }\n'
        f"- Provide at most {limit} items.\n"
        f"- Excerpts must be exact contiguous verbatim quotes from sources and under {DEFAULT_EXCERPT_MAX_CHARS} characters.\n"
        "- NEVER paraphrase, compress, or rewrite excerpts.\n"
        "- Summaries must be concise (1-3 sentences).\n"
        "CONTEXT_POLICY:\n"
        "- Treat CONTEXT_OBJECT as project context, not as mandatory output wording.\n"
        f"{focus_block}\n"
        f"CONTEXT_OBJECT:\n{context_object.strip()[:1200] if isinstance(context_object, str) else ''}\n"
        "- If unsure, return an empty items list."
    )


def _build_exploratory_query(
    query_text: str, context_pack: Dict[str, Any], context_object: str = ""
) -> str:
    target_path = str(context_pack.get("target_path", "")).strip()
    focus_line = _target_focus_query_line(target_path)
    return (
        f"{query_text}\n"
        "EXPLORATORY_RETRIEVAL_GOAL:\n"
        f"- Find complementary principles for target '{target_path}'.\n"
        "- Include alternatives and edge-case guidance, not only obvious matches.\n"
        "- Prefer evidence that can become concrete writing instructions.\n"
        f"- {focus_line}\n"
        "CONTEXT_USAGE:\n"
        "- Use context only to adapt examples and constraints; avoid copying user phrasing.\n"
        f"- Story context (object-level): {str(context_object or '').strip()[:600]}"
    )


def _target_label_for_llm(target_path: str, writing_typology: str) -> str:
    normalized = str(target_path or "").strip()
    if normalized:
        base = normalized.replace(".", " ").replace("_", " ")
    else:
        typology = str(writing_typology or "").strip()
        base = f"{typology} writing target".strip() or "writing target"
    return base


def _build_query_text(context_pack: Dict[str, Any]) -> str:
    n0_context_input = _extract_n0_context_input(context_pack)
    if n0_context_input:
        parts: List[str] = []
        strategy_question = context_pack.get("strategy_question")
        if isinstance(strategy_question, str) and strategy_question.strip():
            parts.append(strategy_question.strip())
        parts.append("CONTEXT_INPUT:")
        parts.append(n0_context_input)
        return "\n".join(parts).strip()

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


def _build_structural_query_text(context_pack: Dict[str, Any]) -> str:
    parts: List[str] = []
    strategy_question = context_pack.get("strategy_question")
    if isinstance(strategy_question, str) and strategy_question.strip():
        parts.append(strategy_question.strip())
    target_path = str(context_pack.get("target_path", "")).strip()
    writing_typology = str(context_pack.get("writing_typology", "")).strip()
    if target_path:
        parts.append(f"target_path={target_path}")
    if writing_typology:
        parts.append(f"writing_typology={writing_typology}")
    parts.append(_target_focus_query_line(target_path))
    return " | ".join([part for part in parts if part]).strip() or "Narrative architecture guidance."


def _build_query_bundle(context_pack: Dict[str, Any]) -> Dict[str, str]:
    structural_query = _build_structural_query_text(context_pack)
    context_object = _extract_n0_context_input(context_pack)
    return {
        "architecture_query": structural_query,
        "context_object": context_object.strip() if isinstance(context_object, str) else "",
    }


def _extract_n0_context_input(context_pack: Dict[str, Any]) -> str:
    if not isinstance(context_pack, dict):
        return ""
    direct_context_input = context_pack.get("context_input")
    if isinstance(direct_context_input, str) and direct_context_input.strip():
        return direct_context_input.strip()
    direct_task_input = context_pack.get("task_input")
    if isinstance(direct_task_input, str) and direct_task_input.strip():
        return direct_task_input.strip()
    target_path = context_pack.get("target_path")
    if not (isinstance(target_path, str) and target_path.startswith("n0.")):
        return ""
    try:
        compiler = RedactorPromptCompiler()
        task_input = compiler._extract_task_input(target_path, context_pack)
    except Exception:
        return ""
    if isinstance(task_input, str):
        return task_input.strip()
    return ""


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
    return _collapse_items_by_filename_variant(selected)


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
    return _collapse_items_by_filename_variant(selected)


def _collapse_items_by_filename_variant(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(items, list) or not items:
        return []
    grouped: Dict[str, Dict[str, Any]] = {}
    for raw_item in items:
        item = _item_preferred_for_retrieval(raw_item)
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename", "") or "").strip()
        if not filename:
            continue
        base_key = _filename_base_key(filename)
        current = grouped.get(base_key)
        if current is None:
            grouped[base_key] = item
            continue
        current_filename = str(current.get("filename", "") or "")
        if _filename_variant_rank(filename) < _filename_variant_rank(current_filename):
            grouped[base_key] = item
    return list(grouped.values())


def _filename_base_key(filename: str) -> str:
    value = str(filename or "").strip().lower()
    if value.endswith(".20.txt"):
        return value[: -len(".20.txt")]
    if value.endswith(".src.txt"):
        return value[: -len(".src.txt")]
    return value


def _filename_variant_rank(filename: str) -> int:
    value = str(filename or "").strip().lower()
    # Prefer compact retrieval corpus first, then normal files, then full .src fallback.
    if value.endswith(".20.txt"):
        return 0
    if value.endswith(".src.txt"):
        return 2
    return 1


def _item_preferred_for_retrieval(item: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    source_path = str(item.get("source_path", "") or "").strip()
    if not source_path:
        return item
    preferred_path = _preferred_variant_source_path(source_path)
    if preferred_path == source_path:
        return item
    clone = dict(item)
    clone["source_path"] = preferred_path
    clone["filename"] = Path(preferred_path).name
    return clone


def _item_variants_for_filename_map(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(item, dict):
        return []
    source_path = str(item.get("source_path", "") or "").strip()
    filename = str(item.get("filename", "") or "").strip()
    variants: List[Dict[str, Any]] = []
    if filename:
        variants.append(dict(item))
    if not source_path:
        return variants
    base = _source_path_base(source_path)
    if not base:
        return variants
    for suffix in (".20.txt", ".txt", ".src.txt"):
        variant_path = f"{base}{suffix}"
        if not _source_path_exists(variant_path):
            continue
        clone = dict(item)
        clone["source_path"] = variant_path
        clone["filename"] = Path(variant_path).name
        variants.append(clone)
    return variants if variants else [dict(item)]


def _preferred_variant_source_path(source_path: str) -> str:
    base = _source_path_base(source_path)
    if not base:
        return source_path
    for suffix in (".20.txt", ".txt", ".src.txt"):
        candidate = f"{base}{suffix}"
        if _source_path_exists(candidate):
            return candidate
    return source_path


def _source_path_base(source_path: str) -> str:
    value = str(source_path or "").strip()
    if value.endswith(".20.txt"):
        return value[: -len(".20.txt")]
    if value.endswith(".src.txt"):
        return value[: -len(".src.txt")]
    if value.endswith(".txt"):
        return value[: -len(".txt")]
    return ""


def _source_path_exists(source_path: str) -> bool:
    if not source_path:
        return False
    return (_NARRATION_BASE_DIR / source_path).exists()


def _extract_agent_items(response: Any) -> List[Dict[str, Any]]:
    message_text = _get_latest_message_text(response)
    if not message_text:
        return []
    json_block = _extract_json_block(message_text)
    parsed: Any = None
    candidates: List[str] = []
    if json_block:
        candidates.append(json_block)
    candidates.append(message_text.strip())
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError:
            parsed = _extract_first_json_object(candidate)
            if parsed is not None:
                break
    if parsed is None:
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
    allowed_sources: set[str] | None = None,
) -> List[LibraryHit]:
    normalized_allowed: set[str] | None = None
    if allowed_sources is not None:
        normalized_allowed = {str(name or "").strip() for name in allowed_sources if str(name or "").strip()}
    merged: Dict[str, LibraryHit] = {}
    for item in agent_items:
        if not isinstance(item, dict):
            continue
        source_file = item.get("source_file", "") or ""
        if not source_file:
            continue
        if normalized_allowed is not None and source_file not in normalized_allowed:
            continue
        if source_file not in filename_map:
            continue
        excerpt = _trim_excerpt(item.get("excerpt", "") or "")
        summary = (item.get("summary", "") or "").strip()
        key = _library_hit_key(source_file, excerpt, summary)
        meta = filename_map.get(source_file, {})
        merged[key] = LibraryHit(
            item_id=meta.get("id", source_file),
            title=meta.get("title", source_file),
            author=meta.get("author", ""),
            source_path=meta.get("source_path", ""),
            writing_typologies=meta.get("writing_typologies", []) or [],
            language=meta.get("language", ""),
            excerpt=excerpt,
            summary=summary,
            key_concepts=item.get("key_concepts", []) if isinstance(item.get("key_concepts"), list) else [],
            score=float(item.get("score", 0) or 0),
            source_file=source_file,
        )
    for hit in citation_hits:
        source_file = hit.get("source_file", "") or ""
        if not source_file:
            continue
        if normalized_allowed is not None and source_file not in normalized_allowed:
            continue
        if source_file not in filename_map:
            continue
        excerpt = _trim_excerpt(hit.get("excerpt", "") or "")
        key = _library_hit_key(source_file, excerpt, "")
        meta = filename_map.get(source_file, {})
        if key in merged:
            existing = merged[key]
            if excerpt and not existing.excerpt:
                existing.excerpt = excerpt
            existing.score = max(existing.score, hit.get("score", 0))
        else:
            merged[key] = LibraryHit(
                item_id=meta.get("id", source_file),
                title=meta.get("title", source_file),
                author=meta.get("author", ""),
                source_path=meta.get("source_path", ""),
                writing_typologies=meta.get("writing_typologies", []) or [],
                language=meta.get("language", ""),
                excerpt=excerpt,
                summary="",
                key_concepts=[],
                score=hit.get("score", 0),
                source_file=source_file,
            )
    return list(merged.values())


def _library_hit_key(source_file: str, excerpt: str, summary: str) -> str:
    src = str(source_file or "").strip()
    ex = str(excerpt or "").strip().lower()[:140]
    sm = str(summary or "").strip().lower()[:100]
    return f"{src}::{ex}::{sm}"


def _fuse_deep_hits(
    focused_hits: List[Dict[str, Any]],
    exploratory_hits: List[Dict[str, Any]],
    final_limit: int,
) -> List[Dict[str, Any]]:
    scored: List[tuple[float, Dict[str, Any]]] = []
    for idx, hit in enumerate(focused_hits or []):
        if not isinstance(hit, dict):
            continue
        base = float(hit.get("score", 0) or 0)
        # Slight bias to focused pass while keeping exploratory options.
        scored.append((base + 0.10 - (idx * 0.001), hit))
    for idx, hit in enumerate(exploratory_hits or []):
        if not isinstance(hit, dict):
            continue
        base = float(hit.get("score", 0) or 0)
        scored.append((base + 0.03 - (idx * 0.001), hit))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    out: List[Dict[str, Any]] = []
    seen_keys: set[str] = set()
    per_source: Dict[str, int] = {}
    for _, hit in scored:
        source = str(hit.get("source_path", "") or "")
        excerpt = str(hit.get("excerpt", "") or "")
        dedupe_key = _library_hit_key(source, excerpt, str(hit.get("summary", "") or ""))
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        source_count = per_source.get(source, 0)
        if source_count >= 5:
            continue
        per_source[source] = source_count + 1
        out.append(hit)
        if len(out) >= max(1, final_limit):
            break
    return out


def _is_deep_agentic_enabled(context_pack: Dict[str, Any]) -> bool:
    if not isinstance(context_pack, dict):
        return False
    if not DEFAULT_DEEP_AGENTIC:
        return False
    target_path = str(context_pack.get("target_path", "")).strip()
    return (
        target_path.startswith("n0.narrative_presentation")
        or target_path.startswith("n0.production_summary")
        or target_path.startswith("n0.art_direction")
        or target_path.startswith("n0.sound_direction")
    )


def _target_focus_query_line(target_path: str) -> str:
    value = str(target_path or "").strip()
    if value.startswith("n0.art_direction"):
        return (
            "Focus on visual direction: palette, lighting, contrast, texture, framing, camera movement, "
            "and coherent aesthetic identity."
        )
    if value.startswith("n0.sound_direction"):
        return (
            "Focus on sound direction: timbre, rhythm, ambience, spatialization, motifs, silence, "
            "and coherent sonic identity."
        )
    return "Focus on abstract narrative architecture: stakes, causality, progression, conflict, arc."


def _target_focus_block(target_path: str, writing_typology: str) -> str:
    value = str(target_path or "").strip()
    typology = str(writing_typology or "").strip().lower()
    if value.startswith("n0.art_direction") or typology in {"art_direction", "art"}:
        return (
            "- Prioritize visual design principles (palette, lighting, textures, framing, movement).\n"
            "- Avoid plot retelling; retrieve aesthetic and stylistic guidance."
        )
    if value.startswith("n0.sound_direction") or typology in {"sound_direction", "sound"}:
        return (
            "- Prioritize sonic design principles (timbre, rhythm, ambience, spatialization, silence).\n"
            "- Avoid plot retelling; retrieve sound and musical direction guidance."
        )
    return (
        "- Prioritize abstract narrative functions first (stakes, causality, progression, arc).\n"
        "- Avoid overfitting to contextual motifs when selecting principles."
    )


def _target_deep_pass_count(target_path: str) -> int:
    value = str(target_path or "").strip()
    if value.startswith("n0.art_direction") or value.startswith("n0.sound_direction"):
        return max(1, _env_int("R2R_DEEP_AGENTIC_PASSES_ART_SOUND", 1))
    return max(1, _env_int("R2R_DEEP_AGENTIC_PASSES_NARRATIVE", 2))


def _agentic_tools_config() -> Dict[str, Any]:
    rag_tools = ["search_file_knowledge", "search_file_descriptions"]
    if DEFAULT_ENABLE_AGENTIC_GET_FILE_CONTENT:
        rag_tools.append("get_file_content")
    if DEFAULT_DISABLE_WEB_AGENTIC:
        # Force local-RAG-only agentic mode to avoid external web tools (web_search/web_scrape).
        return {
            "mode": "rag",
            "rag_tools": rag_tools,
            "research_tools": [],
            "disable_web_agentic": True,
        }
    mode = DEFAULT_MODE if DEFAULT_MODE in ("rag", "research") else "research"
    return {
        "mode": mode,
        "rag_tools": rag_tools,
        "research_tools": ["rag", "reasoning", "critique"],
        "disable_web_agentic": False,
    }


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


def _collect_candidate_source_files(
    citation_hits: List[Dict[str, Any]],
    search_hits: List[Dict[str, Any]],
    allowed_sources: set[str],
) -> List[Dict[str, Any]]:
    by_source: Dict[str, float] = {}
    for hit in citation_hits:
        source_file = str(hit.get("source_file", "") or "").strip()
        if not source_file or source_file not in allowed_sources:
            continue
        score = float(hit.get("score", 0) or 0)
        by_source[source_file] = max(score, by_source.get(source_file, 0.0))
    for hit in search_hits:
        source_file = str(hit.get("source_file", "") or "").strip()
        if not source_file or source_file not in allowed_sources:
            continue
        score = float(hit.get("score", 0) or 0)
        by_source[source_file] = max(score, by_source.get(source_file, 0.0))
    ordered = sorted(by_source.items(), key=lambda pair: pair[1], reverse=True)
    return [{"source_file": src, "score": sc} for src, sc in ordered]


def _coerce_freeform_agent_items(
    message_text: str,
    source_candidates: List[Dict[str, Any]],
    max_items: int,
) -> List[Dict[str, Any]]:
    cleaned = " ".join(str(message_text or "").split()).strip()
    if len(cleaned) < 80:
        return []
    if not source_candidates:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    lead = [s.strip() for s in sentences if s.strip()]
    summary = " ".join(lead[:2]).strip()
    if len(summary) > 320:
        summary = summary[:320].rsplit(" ", 1)[0].strip()
    concepts = _concepts_from_freeform(cleaned, limit=6)
    excerpt = cleaned[:DEFAULT_EXCERPT_MAX_CHARS]
    out: List[Dict[str, Any]] = []
    for candidate in source_candidates[: max(1, max_items)]:
        source_file = str(candidate.get("source_file", "") or "").strip()
        if not source_file:
            continue
        candidate_score = float(candidate.get("score", 0) or 0)
        boosted_score = candidate_score + max(0.0, DEFAULT_POSTPARSE_SCORE_BONUS)
        out.append(
            {
                "source_file": source_file,
                "summary": summary,
                "key_concepts": concepts,
                "excerpt": excerpt,
                "score": boosted_score,
                "post_processed": True,
            }
        )
    return out


def _concepts_from_freeform(text: str, limit: int = 6) -> List[str]:
    chunks = re.split(r"[.;:!?]\s+|\n+", text)
    out: List[str] = []
    for chunk in chunks:
        candidate = " ".join(chunk.split()).strip(" -:;,.")
        if len(candidate) < 20:
            continue
        words = candidate.split()
        if len(words) < 4:
            continue
        if len(words) > 12:
            candidate = " ".join(words[:12]).strip(" -:;,.")
        if candidate and candidate.lower() not in {e.lower() for e in out}:
            out.append(candidate)
        if len(out) >= max(1, limit):
            break
    return out


def _extract_first_json_object(content: str) -> Dict[str, Any] | None:
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text:
        return None
    decoder = json.JSONDecoder()
    for idx, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _as_uuid_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        parsed = uuid.UUID(candidate)
    except Exception:
        return None
    return str(parsed)


def _is_conversation_not_found_error(error: Any) -> bool:
    text = str(error or "").lower()
    return "conversation" in text and "not found" in text


def _extract_conversation_id(response: Any) -> str:
    candidates: List[Any] = []
    if response is not None:
        candidates.append(response)
    if hasattr(response, "results"):
        candidates.append(getattr(response, "results"))
    if isinstance(response, dict):
        candidates.append(response.get("results"))
    for item in candidates:
        if item is None:
            continue
        if isinstance(item, dict):
            value = item.get("id")
        else:
            value = getattr(item, "id", None)
        cid = _as_uuid_or_none(value)
        if cid:
            return cid
    return ""


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, item in value.items():
            out[str(key)] = _to_jsonable(item)
        return out
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, set):
        return [_to_jsonable(item) for item in sorted([str(v) for v in value])]
    return str(value)


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
        return _trim_excerpt(text[: DEFAULT_EXCERPT_MAX_CHARS]), 0.1
    half_window = max(120, DEFAULT_EXCERPT_MAX_CHARS // 2)
    start = max(0, best_index - half_window)
    end = min(len(text), best_index + half_window)
    excerpt = _trim_excerpt(text[start:end])
    return excerpt, 1.0 + (0.1 * len(terms))


def _trim_excerpt(text: str) -> str:
    cleaned = " ".join(str(text).split())
    return cleaned[:DEFAULT_EXCERPT_MAX_CHARS]


def _compact_debug_text(text: str, max_len: int = 2400) -> str:
    cleaned = " ".join(str(text or "").split())
    return cleaned[: max(200, int(max_len or 2400))]
