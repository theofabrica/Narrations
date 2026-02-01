"""Strategy finder to select writing strategy from the library index."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from app.narration_agent.narration.library_rag import LibraryRAG
from app.narration_agent.spec_loader import load_json


@dataclass
class StrategyCard:
    strategy_id: str
    target_path: str
    writing_typology: str
    library_item_ids: List[str]
    style_guidelines: List[str]
    structure_guidelines: List[str]
    source_refs: List[str]
    notes: str


class StrategyFinder:
    """Select a strategy card based on context pack and library index."""

    def __init__(self) -> None:
        self._library_index = load_json("writer_agent/library/index.json") or {}
        self._rag = LibraryRAG()

    def build_strategy(self, context_pack: Dict[str, Any]) -> Dict[str, Any]:
        target_path = context_pack.get("target_path", "")
        writing_typology = context_pack.get("writing_typology", "")
        language = context_pack.get("style_constraints", {}).get("language", "") or ""

        candidates = self._filter_library_items(writing_typology, language)
        rag_hits = self._rag.retrieve(context_pack, limit=3)
        library_item_ids = [hit.get("id") for hit in rag_hits if hit.get("id")]
        if not library_item_ids:
            library_item_ids = [item.get("id") for item in candidates if item.get("id")]
        source_refs = []
        for hit in rag_hits:
            title = hit.get("title", "").strip()
            author = hit.get("author", "").strip()
            excerpt = hit.get("excerpt", "").strip()
            summary = hit.get("summary", "").strip()
            concepts = hit.get("key_concepts", [])
            if title or author or excerpt or summary:
                ref = f"{title} - {author}".strip(" -")
                detail = summary or excerpt
                if detail:
                    ref = f"{ref}: {detail}" if ref else detail
                if isinstance(concepts, list) and concepts:
                    ref = f"{ref} | Concepts: {', '.join(concepts[:6])}"
                source_refs.append(ref)
        if not source_refs:
            source_refs = [
                f"{item.get('title', '').strip()} - {item.get('author', '').strip()}"
                for item in candidates
            ]

        card = StrategyCard(
            strategy_id=f"{writing_typology or 'general'}_v1",
            target_path=target_path,
            writing_typology=writing_typology,
            library_item_ids=library_item_ids,
            style_guidelines=self._default_style_guidelines(writing_typology),
            structure_guidelines=self._default_structure_guidelines(writing_typology),
            source_refs=[ref for ref in source_refs if ref.strip(" -")],
            notes="Auto-selected based on writing typology and language.",
        )
        return {
            "strategy_id": card.strategy_id,
            "target_path": card.target_path,
            "writing_typology": card.writing_typology,
            "library_item_ids": card.library_item_ids,
            "style_guidelines": card.style_guidelines,
            "structure_guidelines": card.structure_guidelines,
            "source_refs": card.source_refs,
            "notes": card.notes,
        }

    def _filter_library_items(self, writing_typology: str, language: str) -> List[Dict[str, Any]]:
        items = self._library_index.get("items", [])
        if not isinstance(items, list):
            return []

        def matches(item: Dict[str, Any]) -> bool:
            if writing_typology:
                typologies = item.get("writing_typologies", [])
                if writing_typology not in typologies:
                    return False
            if language:
                if item.get("language") != language:
                    return False
            return True

        filtered = [item for item in items if isinstance(item, dict) and matches(item)]
        return filtered if filtered else [item for item in items if isinstance(item, dict)]

    def _default_style_guidelines(self, writing_typology: str) -> List[str]:
        if writing_typology == "summary":
            return ["Concise", "Objective", "No new information"]
        if writing_typology == "pitch":
            return ["Punchy", "Clear stakes", "One-paragraph arc"]
        if writing_typology == "character":
            return ["Concrete traits", "Actionable descriptors", "Consistent tone"]
        if writing_typology == "scene":
            return ["Visual clarity", "Action-driven", "Maintain continuity"]
        if writing_typology == "prompting":
            return ["Tool-ready", "Precise tokens", "Avoid ambiguity"]
        return ["Clear", "Consistent", "No invention"]

    def _default_structure_guidelines(self, writing_typology: str) -> List[str]:
        if writing_typology == "summary":
            return ["1-2 sentences", "Lead with the core idea", "Keep to target length"]
        if writing_typology == "pitch":
            return ["Protagonist", "Goal", "Obstacle", "Stakes"]
        if writing_typology == "character":
            return ["Role", "Function", "Description", "Visual markers"]
        if writing_typology == "scene":
            return ["Situation", "Action", "Outcome", "Continuity note"]
        if writing_typology == "prompting":
            return ["Goal", "Prompt", "Inputs/Outputs", "Notes"]
        return ["Structured", "Ordered", "Concise"]
