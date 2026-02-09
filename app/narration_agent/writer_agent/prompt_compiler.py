"""Deterministic compiler for redactor prompts.

Goal: build stable, readable user prompts (instructions first, context after),
without feeding debug logs back to the model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PromptParts:
    system_prompt: str
    user_prompt: str


class RedactorPromptCompiler:
    """Compile a deterministic user prompt for the redactor."""

    def build_initial_user_prompt(
        self,
        *,
        target_path: str,
        context_pack: Dict[str, Any],
        allowed_fields: Optional[List[str]],
        redaction_rules: Optional[List[str]],
        extra_rule: str,
        writer_self_question: str,
        writing_mode_hint: str,
        existing_fields: Optional[Dict[str, str]] = None,
    ) -> str:
        existing_fields = existing_fields or {}
        rules_line = self._format_redaction_rules(redaction_rules or [])
        allowed_line = self._format_allowed_fields(allowed_fields or [])
        constraints = context_pack.get("redaction_constraints", {}) if isinstance(context_pack, dict) else {}
        sections: List[str] = []
        is_art_create = (
            isinstance(target_path, str)
            and target_path.startswith("n0.art_direction")
            and str(context_pack.get("writing_mode", "")).strip().lower() == "create"
        )
        is_sound_create = (
            isinstance(target_path, str)
            and target_path.startswith("n0.sound_direction")
            and str(context_pack.get("writing_mode", "")).strip().lower() == "create"
        )

        # Task framing (first)
        sections.append(
            "\n".join(
                [
                    "@Task@",
                    self._build_task_sentence(target_path, context_pack, allowed_fields),
                    "Use the @Task_input@ and the @Guidance@ that follow.",
                ]
            ).strip()
        )

        # Minimal output contract (single line)
        sections.append("Return ONLY valid JSON.")

        # Constraints & rules
        sections.append(
            "\n".join(
                [
                    "@Rules@",
                    rules_line,
                    self._format_constraints_line(constraints),
                    self._format_extra_rule(extra_rule),
                ]
            ).strip()
        )

        # Minimal facts / chat context
        strategy_card = context_pack.get("strategy_card")
        if isinstance(strategy_card, dict) and strategy_card:
            strategy_text = strategy_card.get("strategy_text")
            if isinstance(strategy_text, str) and strategy_text.strip():
                sections.append("@Guidance@\n" + strategy_text.strip())

        task_input = self._extract_task_input(target_path, context_pack)
        if task_input:
            sections.append("@Task_input@\n" + task_input)

        # Optional neighbours/context groups (already sparse upstream)
        if not (is_art_create or is_sound_create):
            context_groups = context_pack.get("context_groups")
            context_groups = self._filter_context_groups(context_groups)
            if isinstance(context_groups, list) and context_groups:
                sections.append(
                    "CONTEXT GROUPS (weighted):\n"
                    + json.dumps(context_groups, ensure_ascii=True, indent=2)
                )

        # Sparse non-empty fields (N0 + deps) if present
        if not (is_art_create or is_sound_create):
            target_strata_data = self._filter_sparse_fields(
                context_pack.get("target_strata_data")
            )
            if isinstance(target_strata_data, list) and target_strata_data:
                sections.append(
                    "PROJECT NON-EMPTY FIELDS (sparse):\n"
                    + json.dumps(target_strata_data, ensure_ascii=True, indent=2)
                )
            dependencies = self._filter_sparse_fields(context_pack.get("dependencies"))
            if isinstance(dependencies, list) and dependencies:
                sections.append(
                    "DEPENDENCIES NON-EMPTY FIELDS (sparse):\n"
                    + json.dumps(dependencies, ensure_ascii=True, indent=2)
                )

        # Existing text (edit mode)
        if existing_fields:
            sections.append(
                "EXISTING CONTENT TO REVISE (do not discard):\n"
                + json.dumps(existing_fields, ensure_ascii=True, indent=2)
            )

        return "\n\n".join([s for s in sections if s.strip()]).strip() + "\n"

    def build_retry_user_prompt(
        self,
        *,
        target_path: str,
        context_pack: Dict[str, Any],
        allowed_fields: Optional[List[str]],
        redaction_rules: Optional[List[str]],
        extra_rule: str,
        length_violations: List[Dict[str, int]],
        meta_violations: List[Dict[str, Any]],
        existing_patch: Dict[str, Any],
    ) -> str:
        rules_line = self._format_redaction_rules(redaction_rules or [])
        allowed_line = self._format_allowed_fields(allowed_fields or [])
        constraints = context_pack.get("redaction_constraints", {}) if isinstance(context_pack, dict) else {}
        length_lines = ""
        if length_violations:
            length_lines = "\n".join(
                [
                    f"- {item.get('field')}: {item.get('length')} chars "
                    f"(min {item.get('min')}, max {item.get('max')})."
                    for item in length_violations
                ]
            )
        meta_lines = ""
        if meta_violations:
            meta_lines = "\n".join(
                [
                    f"- {item.get('field')}: remove meta-writing phrases "
                    f"(matches: {', '.join(item.get('matches', [])[:6])})."
                    for item in meta_violations
                ]
            )

        sections: List[str] = []
        sections.append(
            "\n".join(
                [
                    "INSTRUCTIONS (retry, follow strictly):",
                    "- Return ONLY valid JSON (no markdown fences, no commentary).",
                    '- Output shape: { "target_patch": <object>, "open_questions": [] }',
                    f"- target_patch must contain ONLY the content for '{target_path}'.",
                    allowed_line,
                    "@Rules@",
                    rules_line,
                    self._format_constraints_line(constraints),
                    self._format_extra_rule(extra_rule),
                    "CORRECTION MODE:",
                    "- Adjust the existing content to satisfy constraints.",
                    "- Preserve meaning and do not add new facts.",
                    (length_lines or "").strip(),
                    (meta_lines or "").strip(),
                ]
            ).strip()
        )

        sections.append(
            "EXISTING CONTENT TO REVISE (do not discard):\n"
            + json.dumps(existing_patch, ensure_ascii=True, indent=2)
        )

        # Keep compact authoritative context
        strategy_card = context_pack.get("strategy_card")
        if isinstance(strategy_card, dict) and strategy_card:
            strategy_text = strategy_card.get("strategy_text")
            if isinstance(strategy_text, str) and strategy_text.strip():
                sections.append("@Guidance@\n" + strategy_text.strip())

        task_input = self._extract_task_input(target_path, context_pack)
        if task_input:
            sections.append("@Task_input@\n" + task_input)

        return "\n\n".join([s for s in sections if s.strip()]).strip() + "\n"

    def _format_constraints_line(self, constraints: Any) -> str:
        if not isinstance(constraints, dict):
            return "- Respect redaction_constraints.min_chars / max_chars."
        min_chars = constraints.get("min_chars", 0)
        max_chars = constraints.get("max_chars", 0)
        if min_chars or max_chars:
            return f"- Respect length constraints: min_chars={min_chars}, max_chars={max_chars}."
        return "- Respect redaction_constraints.min_chars / max_chars."

    def _format_allowed_fields(self, allowed_fields: List[str]) -> str:
        if not allowed_fields:
            return "- Only write fields inside the target section."
        return f"- Only write these fields inside the target section: {', '.join(allowed_fields)}."

    def _format_redaction_rules(self, rules: List[str]) -> str:
        cleaned = [str(r).strip() for r in (rules or []) if str(r).strip()]
        if not cleaned:
            return ""
        return "- Redaction rules: " + "; ".join(cleaned) + "."

    def _format_extra_rule(self, extra_rule: str) -> str:
        if not isinstance(extra_rule, str):
            return ""
        rule = extra_rule.strip()
        if not rule:
            return ""
        # Keep as a single instruction line.
        if not rule.endswith("."):
            rule += "."
        return rule

    def _build_task_sentence(
        self,
        target_path: str,
        context_pack: Dict[str, Any],
        allowed_fields: Optional[List[str]],
    ) -> str:
        if target_path in {
            "n1.characters.main_characters.number",
            "n1.characters.secondary_characters.number",
            "n1.characters.background_characters.number",
        }:
            label_map = {
                "n1.characters.main_characters.number": "main_characters",
                "n1.characters.secondary_characters.number": "secondary_characters",
                "n1.characters.background_characters.number": "background_characters",
            }
            project_id = str(context_pack.get("project_id", "")).strip()
            video_type = str(context_pack.get("brief_video_type", "")).strip()
            duration_s = context_pack.get("brief_target_duration_s", 0)
            duration_text = self._format_duration_short_en(duration_s)
            summary = self._extract_n0_summary_from_context(context_pack)
            summary = summary or str(context_pack.get("core_summary", "")).strip()
            label = label_map.get(target_path, "main_characters")
            parts: List[str] = []
            parts.append(f'Evaluate the number of "{label}"')
            if summary:
                parts.append(f'in the story told in "{summary}"')
            if project_id:
                parts.append(f'for the project "{project_id}"')
            if video_type:
                parts.append(f'for a "{video_type}"')
            if duration_text:
                parts.append(f'with a duration of "{duration_text}"')
            return " ".join(parts).strip() + "."

        verb = self._task_verb(context_pack.get("writing_mode", ""))
        target_label = self._target_label(target_path, allowed_fields)
        project_id = str(context_pack.get("project_id", "")).strip()
        video_type = str(context_pack.get("brief_video_type", "")).strip()
        duration_s = context_pack.get("brief_target_duration_s", 0)
        duration_text = self._format_duration_short_en(duration_s)

        parts: List[str] = []
        parts.append(f"{verb} the text for \"{target_label}\"")
        if project_id:
            parts.append(f"for the project \"{project_id}\"")
        if video_type:
            article = "an" if video_type[:1].lower() in ("a", "e", "i", "o", "u") else "a"
            parts.append(f"{article} {video_type}")
        if duration_text:
            parts.append(f"with a duration of {duration_text}")
        return " ".join(parts) + "."

    def _extract_n0_summary_from_context(self, context_pack: Dict[str, Any]) -> str:
        if not isinstance(context_pack, dict):
            return ""
        dependencies = context_pack.get("dependencies")
        if not isinstance(dependencies, dict):
            return ""
        n0_state = dependencies.get("n0")
        if not isinstance(n0_state, dict):
            return ""
        n0_data = n0_state.get("data") if isinstance(n0_state, dict) else {}
        if not isinstance(n0_data, dict):
            return ""
        production_summary = n0_data.get("production_summary", {})
        if not isinstance(production_summary, dict):
            return ""
        summary = production_summary.get("summary", "")
        return summary.strip() if isinstance(summary, str) else ""

    def _task_verb(self, mode: Any) -> str:
        normalized = str(mode or "").strip().lower()
        if normalized == "edit":
            return "Edit"
        if normalized == "propagate":
            return "Rewrite"
        return "Write"

    def _target_label(self, target_path: str, allowed_fields: Optional[List[str]]) -> str:
        mapping = {
            "n0.production_summary.summary": "general summary",
            "n0.art_direction.description": "art direction description",
            "n0.sound_direction.description": "sound direction description",
        }
        if target_path == "n0.production_summary" and allowed_fields == ["summary"]:
            return "general summary"
        if target_path == "n0.art_direction" and allowed_fields == ["description"]:
            return "art direction description"
        if target_path == "n0.sound_direction" and allowed_fields == ["description"]:
            return "sound direction description"
        return mapping.get(target_path, target_path or "target text")

    def _format_duration_short_en(self, value: Any) -> str:
        try:
            seconds = int(value)
        except Exception:
            return ""
        if seconds <= 0:
            return ""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts: List[str] = []
        if hours:
            parts.append(f"{self._to_english(hours)} hour{'s' if hours > 1 else ''}")
        if minutes:
            parts.append(
                f"{self._to_english(minutes)} minute{'s' if minutes > 1 else ''}"
            )
        if secs:
            parts.append(
                f"{self._to_english(secs)} second{'s' if secs > 1 else ''}"
            )
        return " ".join(parts)

    def _to_english(self, value: int) -> str:
        if value < 0:
            return str(value)
        if value == 0:
            return "zero"
        ones = [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ]
        tens = ["", "", "twenty", "thirty", "forty", "fifty"]
        if value < 20:
            return ones[value]
        if value < 60:
            ten = value // 10
            rest = value % 10
            if rest == 0:
                return tens[ten]
            return f"{tens[ten]} {ones[rest]}"
        return str(value)

    def _extract_task_input(self, target_path: str, context_pack: Dict[str, Any]) -> str:
        if not isinstance(context_pack, dict):
            return ""
        if isinstance(target_path, str) and target_path.startswith("n1.characters"):
            summary = self._extract_n0_summary_from_context(context_pack)
            return summary.strip() if isinstance(summary, str) and summary.strip() else ""
        if isinstance(target_path, str) and target_path.startswith("n0.art_direction"):
            video_type = str(context_pack.get("brief_video_type", "")).strip()
            duration_s = context_pack.get("brief_target_duration_s", 0)
            core_summary = context_pack.get("core_summary", "")
            lines: List[str] = []
            if video_type:
                lines.append(f"brief_video_type: {video_type}")
            if isinstance(duration_s, (int, float)) and duration_s:
                lines.append(f"brief_target_duration_s: {int(duration_s)}")
            if isinstance(core_summary, str) and core_summary.strip():
                lines.append(f"core_summary: {core_summary.strip()}")
            return "\n".join(lines).strip()
        if isinstance(target_path, str) and target_path.startswith("n0.sound_direction"):
            summary_value = self._find_sparse_value(
                context_pack.get("target_strata_data"), "n0.production_summary.summary"
            )
            art_value = self._find_sparse_value(
                context_pack.get("target_strata_data"), "n0.art_direction.description"
            )
            lines: List[str] = []
            if isinstance(summary_value, str) and summary_value.strip():
                lines.append("Summary:")
                lines.append(summary_value.strip())
            if isinstance(art_value, str) and art_value.strip():
                if lines:
                    lines.append("")
                lines.append("Art direction:")
                lines.append(art_value.strip())
            return "\n".join(lines).strip()
        core_summary = context_pack.get("core_summary", "")
        if isinstance(core_summary, str) and core_summary.strip():
            return core_summary.strip()
        return ""

    def _find_sparse_value(self, entries: Any, path: str) -> str | None:
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("path") == path:
                value = entry.get("value")
                if isinstance(value, str):
                    return value
        return None

    def _prune_empty_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        cleaned: Dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
                continue
            cleaned[key] = value
        return cleaned

    def _filter_context_groups(self, groups: Any) -> List[Dict[str, Any]]:
        if not isinstance(groups, list):
            return []
        filtered: List[Dict[str, Any]] = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            pruned = {k: v for k, v in group.items() if k != "description"}
            payload = pruned.get("payload")
            if isinstance(payload, dict) and not payload:
                continue
            if pruned:
                filtered.append(pruned)
        return filtered

    def _filter_sparse_fields(self, entries: Any) -> List[Dict[str, Any]]:
        if not isinstance(entries, list):
            return []
        filtered: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path", "")).strip()
            name = str(entry.get("name", "")).strip()
            if self._is_technical_path(path, name):
                continue
            if self._is_redundant_prompt_path(path):
                continue
            filtered.append(entry)
        return filtered

    def _is_technical_path(self, path: str, name: str) -> bool:
        if not path and not name:
            return True
        technical_names = {
            "project_id",
            "strata",
            "updated_at",
            "created_at",
            "version",
            "schema_version",
        }
        if name in technical_names:
            return True
        if ".meta." in path or path.endswith(".meta"):
            return True
        if path.endswith(".project_id") or path.endswith(".strata"):
            return True
        return False

    def _is_redundant_prompt_path(self, path: str) -> bool:
        if not path:
            return False
        redundant_exact = {
            "n0.production_summary.production_type",
            "n0.production_summary.target_duration",
            "dependencies.n1_ref",
        }
        if path in redundant_exact:
            return True
        if path.startswith("n0.deliverables."):
            return True
        return False

    def _format_duration_short_fr(self, value: Any) -> str:
        try:
            seconds = int(value)
        except Exception:
            return ""
        if seconds <= 0:
            return ""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts: List[str] = []
        if hours:
            parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if secs:
            parts.append(f"{secs} seconde{'s' if secs > 1 else ''}")
        return " ".join(parts)

