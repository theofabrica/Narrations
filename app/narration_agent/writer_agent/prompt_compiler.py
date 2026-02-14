"""Deterministic compiler for redactor prompts.

Goal: build stable, readable user prompts (instructions first, context after),
without feeding debug logs back to the model.
"""

from __future__ import annotations

import json
import re
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
        is_n0_create = (
            isinstance(target_path, str)
            and target_path.startswith("n0.")
            and str(context_pack.get("writing_mode", "")).strip().lower() == "create"
        )
        is_n0_narrative_prompt = (
            isinstance(target_path, str)
            and (
                target_path.startswith("n0.narrative_presentation")
                or target_path.startswith("n0.production_summary")
            )
        )
        is_n1_compact_characters = target_path in {
            "n1.characters.main_characters",
            "n1.characters.secondary_characters",
            "n1.characters.background_characters",
        } or (
            isinstance(target_path, str)
            and target_path.startswith("n1.characters.main_characters.characters[")
            and target_path.endswith(".character_description")
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
        if not (is_art_create or is_sound_create or is_n1_compact_characters):
            context_groups = context_pack.get("context_groups")
            context_groups = self._filter_context_groups(context_groups)
            if isinstance(context_groups, list) and context_groups:
                sections.append(
                    "CONTEXT GROUPS (weighted):\n"
                    + json.dumps(context_groups, ensure_ascii=True, indent=2)
                )

        # Sparse non-empty fields (N0 + deps) if present
        if not (
            is_art_create
            or is_sound_create
            or is_n1_compact_characters
            or is_n0_narrative_prompt
        ):
            target_strata_data = self._filter_sparse_fields(
                context_pack.get("target_strata_data")
            )
            if isinstance(target_strata_data, list) and target_strata_data:
                sections.append(
                    "PROJECT NON-EMPTY FIELDS (sparse):\n"
                    + json.dumps(target_strata_data, ensure_ascii=True, indent=2)
                )
            if not is_n0_create:
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
        if target_path == "n1.characters.secondary_characters":
            project_id = str(context_pack.get("project_id", "")).strip()
            video_type = str(context_pack.get("brief_video_type", "")).strip()
            duration_text = self._resolve_duration_text(context_pack)
            main_names = self._extract_n1_main_character_names_from_sparse(context_pack)
            parts: List[str] = []
            parts.append('Evaluate the number of "secondary_characters" and propose their names')
            if project_id:
                parts.append(f'in the story told in the project "{project_id}"')
            else:
                parts.append("in the story told in the current project")
            if video_type:
                parts.append(f'for a "{video_type}"')
            if duration_text:
                parts.append(f'with a duration of "{duration_text}"')
            if video_type and duration_text:
                parts.append(
                    f'Calibrate the number to the narrative economy allowed by "{video_type}" and "{duration_text}"'
                )
            elif video_type:
                parts.append(
                    f'Calibrate the number to the narrative economy allowed by "{video_type}"'
                )
            elif duration_text:
                parts.append(
                    f'Calibrate the number to the narrative economy allowed by "{duration_text}"'
                )
            else:
                parts.append(
                    "Calibrate the number to the narrative economy allowed by the available story scope"
                )
            if main_names:
                parts.append(
                    f'Secondary characters must remain in supporting roles relative to these main characters: "{", ".join(main_names)}"'
                )
            else:
                parts.append(
                    "Secondary characters must remain in supporting roles relative to the main characters already defined in n1.main_characters"
                )
            parts.append(
                "Return JSON where target_patch.number is an integer and target_patch.names is an array of names (no prose)"
            )
            return " ".join(parts).strip() + "."

        if target_path == "n1.characters.background_characters":
            project_id = str(context_pack.get("project_id", "")).strip()
            video_type = str(context_pack.get("brief_video_type", "")).strip()
            duration_text = self._resolve_duration_text(context_pack)
            main_names = self._extract_n1_main_character_names_from_sparse(context_pack)
            secondary_names = self._extract_n1_secondary_character_names_from_sparse(
                context_pack
            )
            parts: List[str] = []
            parts.append('Evaluate the number of "background_characters" and propose their names')
            if project_id:
                parts.append(f'in the story told in the project "{project_id}"')
            else:
                parts.append("in the story told in the current project")
            if video_type:
                parts.append(f'for a "{video_type}"')
            if duration_text:
                parts.append(f'with a duration of "{duration_text}"')
            if main_names:
                parts.append(
                    f'Background characters must remain in minor roles relative to these main characters: "{", ".join(main_names)}"'
                )
            else:
                parts.append(
                    "Background characters must remain in minor roles relative to the main characters already defined in n1.main_characters"
                )
            if secondary_names:
                parts.append(
                    f'and these secondary characters: "{", ".join(secondary_names)}"'
                )
            parts.append(
                "Return JSON where target_patch.number is an integer and target_patch.names is an array of names (no prose)"
            )
            return " ".join(parts).strip() + "."

        if target_path in {
            "n1.characters.main_characters",
            "n1.characters.secondary_characters",
            "n1.characters.background_characters",
        }:
            label_map = {
                "n1.characters.main_characters": "main_characters",
                "n1.characters.secondary_characters": "secondary_characters",
                "n1.characters.background_characters": "background_characters",
            }
            project_id = str(context_pack.get("project_id", "")).strip()
            label = label_map.get(target_path, "main_characters")
            video_type = str(context_pack.get("brief_video_type", "")).strip()
            duration_text = self._resolve_duration_text(context_pack)
            parts: List[str] = []
            parts.append(f'Evaluate the number of "{label}"')
            include_names = isinstance(allowed_fields, list) and "names" in allowed_fields
            if include_names:
                parts.append("and propose their names")
            if project_id:
                parts.append(f'in the story told in the project "{project_id}"')
            else:
                parts.append("in the story told in the current project")
            if video_type:
                parts.append(f'for a "{video_type}"')
            if duration_text:
                parts.append(f'with a duration of "{duration_text}"')
            if include_names:
                parts.append(
                    "Return JSON where target_patch.number is an integer and target_patch.names is an array of names (no prose)"
                )
            else:
                parts.append(
                    "Return JSON where target_patch.number is an integer (no prose)"
                )
            return " ".join(parts).strip() + "."

        if (
            isinstance(target_path, str)
            and target_path.startswith("n1.characters.main_characters.characters[")
            and (
                target_path.endswith(".character_description")
                or target_path.endswith(".character_description.narrativ_role")
                or target_path.endswith(".character_description.appearance")
                or target_path.endswith(".character_description.backstory")
                or target_path.endswith(".character_description.motivation")
            )
        ):
            project_id = str(context_pack.get("project_id", "")).strip()
            character_name = self._extract_main_character_name_from_context(
                target_path, context_pack
            )
            field = "narrativ_role"
            if target_path.endswith(".appearance"):
                field = "appearance"
            elif target_path.endswith(".backstory"):
                field = "backstory"
            elif target_path.endswith(".motivation"):
                field = "motivation"
            parts: List[str] = []
            if character_name:
                parts.append(f'Write the "{field}" for the main character "{character_name}"')
            else:
                parts.append(f'Write the "{field}" for this main character')
            if project_id:
                parts.append(f'in the story told in the project "{project_id}"')
            else:
                parts.append("in the story told in the current project")
            parts.append(
                f"Return JSON where target_patch.{field} is a plain text string (no prose outside JSON)"
            )
            return " ".join(parts).strip() + "."

        if target_path == "n1.characters.main_characters.names":
            project_id = str(context_pack.get("project_id", "")).strip()
            video_type = str(context_pack.get("brief_video_type", "")).strip()
            duration_s = context_pack.get("brief_target_duration_s", 0)
            duration_text = self._format_duration_short_en(duration_s)
            summary = self._extract_n0_summary_from_context(context_pack)
            number = self._extract_n1_number_from_sparse(context_pack, target_path)
            parts: List[str] = []
            if number and number > 0:
                parts.append(
                    f'Propose {self._to_english(number)} distinct names for the "main_characters"'
                )
            else:
                parts.append('Propose distinct names for the "main_characters"')
            if summary:
                parts.append(f'in the story told in "{summary}"')
            if project_id:
                parts.append(f'for the project "{project_id}"')
            if video_type:
                parts.append(f'for a "{video_type}"')
            if duration_text:
                parts.append(f'with a duration of "{duration_text}"')
            parts.append(
                "Return only the names as a JSON array in target_patch.names (no prose)."
            )
            return " ".join(parts).strip() + "."

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
        use_unquoted_label = (
            isinstance(target_path, str)
            and (
                target_path.startswith("n0.narrative_presentation")
                or target_path.startswith("n0.production_summary")
            )
            and target_label == "narrative foundation"
        )
        if use_unquoted_label:
            parts.append(f"{verb} the {target_label}")
        else:
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
        # When sent to the redactor, dependencies are usually sparse (list of {path,value}).
        if isinstance(dependencies, list):
            value = self._find_sparse_value(
                dependencies, "dependencies.n0.data.narrative_presentation.summary"
            )
            if not isinstance(value, str):
                value = self._find_sparse_value(
                    dependencies, "dependencies.n0.data.production_summary.summary"
                )
            return value.strip() if isinstance(value, str) else ""
        if not isinstance(dependencies, dict):
            return ""
        n0_state = dependencies.get("n0")
        if not isinstance(n0_state, dict):
            return ""
        n0_data = n0_state.get("data") if isinstance(n0_state, dict) else {}
        if not isinstance(n0_data, dict):
            return ""
        narrative_presentation = n0_data.get("narrative_presentation")
        if not isinstance(narrative_presentation, dict):
            narrative_presentation = n0_data.get("production_summary", {})
        if not isinstance(narrative_presentation, dict):
            return ""
        summary = narrative_presentation.get("summary", "")
        return summary.strip() if isinstance(summary, str) else ""

    def _extract_n1_number_from_sparse(self, context_pack: Dict[str, Any], target_path: str) -> int:
        """Best-effort extraction of the already computed N1 number from sparse project fields."""
        if not isinstance(context_pack, dict):
            return 0
        target_strata_data = context_pack.get("target_strata_data")
        if not isinstance(target_strata_data, list):
            return 0
        if target_path == "n1.characters.main_characters.names":
            raw = self._find_sparse_value(target_strata_data, "n1.characters.main_characters.number")
            try:
                return int(raw) if raw is not None else 0
            except Exception:
                return 0
        return 0

    def _extract_n1_main_character_names_from_sparse(self, context_pack: Dict[str, Any]) -> List[str]:
        if not isinstance(context_pack, dict):
            return []
        entries = context_pack.get("target_strata_data")
        if not isinstance(entries, list):
            return []
        collected: List[tuple[int, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path", "")).strip()
            if not path.startswith("n1.characters.main_characters.names["):
                continue
            value = entry.get("value")
            if not isinstance(value, str):
                continue
            name = value.strip()
            if not name:
                continue
            idx_text = path.split("[", 1)[1].split("]", 1)[0]
            try:
                idx = int(idx_text)
            except Exception:
                idx = 9999
            collected.append((idx, name))
        collected.sort(key=lambda item: item[0])
        names: List[str] = []
        for _, name in collected:
            if name not in names:
                names.append(name)
        return names

    def _extract_n1_secondary_character_names_from_sparse(
        self, context_pack: Dict[str, Any]
    ) -> List[str]:
        if not isinstance(context_pack, dict):
            return []
        entries = context_pack.get("target_strata_data")
        if not isinstance(entries, list):
            return []
        collected: List[tuple[int, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            path = str(entry.get("path", "")).strip()
            if not path.startswith("n1.characters.secondary_characters.names["):
                continue
            value = entry.get("value")
            if not isinstance(value, str):
                continue
            name = value.strip()
            if not name:
                continue
            idx_text = path.split("[", 1)[1].split("]", 1)[0]
            try:
                idx = int(idx_text)
            except Exception:
                idx = 9999
            collected.append((idx, name))
        collected.sort(key=lambda item: item[0])
        names: List[str] = []
        for _, name in collected:
            if name not in names:
                names.append(name)
        return names

    def _task_verb(self, mode: Any) -> str:
        normalized = str(mode or "").strip().lower()
        if normalized == "edit":
            return "Edit"
        if normalized == "propagate":
            return "Rewrite"
        return "Write"

    def _target_label(self, target_path: str, allowed_fields: Optional[List[str]]) -> str:
        mapping = {
            "n0.narrative_presentation.summary": "narrative foundation",
            "n0.production_summary.summary": "narrative foundation",
            "n0.art_direction.description": "art direction description",
            "n0.sound_direction.description": "sound direction description",
        }
        if target_path in {"n0.narrative_presentation", "n0.production_summary"} and allowed_fields == [
            "summary"
        ]:
            return "narrative foundation"
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

    def _resolve_duration_text(self, context_pack: Dict[str, Any]) -> str:
        if not isinstance(context_pack, dict):
            return ""
        raw_text = context_pack.get("brief_target_duration_text", "")
        if isinstance(raw_text, str) and raw_text.strip():
            raw = raw_text.strip()
            parsed_seconds = self._parse_duration_to_seconds(raw)
            if parsed_seconds > 0:
                words = self._format_duration_short_en(parsed_seconds)
                if words:
                    return words
            return raw
        return self._format_duration_short_en(context_pack.get("brief_target_duration_s", 0))

    def _parse_duration_to_seconds(self, value: Any) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, (int, float)):
            return max(0, int(value))
        if not isinstance(value, str):
            return 0
        text = value.strip().lower()
        if not text:
            return 0
        if text.isdigit():
            return max(0, int(text))

        timecode_match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", text)
        if timecode_match:
            hours = 0
            minutes = int(timecode_match.group(1))
            seconds = int(timecode_match.group(2))
            if timecode_match.group(3) is not None:
                hours = minutes
                minutes = seconds
                seconds = int(timecode_match.group(3))
            return max(0, hours * 3600 + minutes * 60 + seconds)

        hm_match = re.search(r"(\d+)\s*h\s*(\d{1,2})?", text)
        if hm_match:
            hours = int(hm_match.group(1))
            minutes = int(hm_match.group(2)) if hm_match.group(2) else 0
            return max(0, hours * 3600 + minutes * 60)

        total_seconds = 0.0
        for number, unit in re.findall(
            r"(\d+(?:[.,]\d+)?)\s*(h|hr|hour|hours|heure|heures|m|min|minute|minutes|s|sec|secs|second|seconds|seconde|secondes)",
            text,
        ):
            value_f = float(number.replace(",", "."))
            if unit.startswith(("h", "hr", "hour", "heure")):
                total_seconds += value_f * 3600
            elif unit.startswith(("m", "min", "minute")):
                total_seconds += value_f * 60
            else:
                total_seconds += value_f
        return int(total_seconds) if total_seconds > 0 else 0

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
        if target_path in {
            "n1.characters.main_characters",
            "n1.characters.main_characters.names",
        }:
            summary = self._extract_n0_summary_from_context(context_pack)
            if isinstance(summary, str) and summary.strip():
                return "SUMMARY:\n" + summary.strip()
            return ""
        if (
            isinstance(target_path, str)
            and target_path.startswith("n1.characters.main_characters.characters[")
            and (
                target_path.endswith(".character_description")
                or target_path.endswith(".character_description.narrativ_role")
                or target_path.endswith(".character_description.appearance")
                or target_path.endswith(".character_description.backstory")
                or target_path.endswith(".character_description.motivation")
            )
        ):
            summary = self._extract_n0_summary_from_context(context_pack)
            character_name = self._extract_main_character_name_from_context(
                target_path, context_pack
            )
            lines: List[str] = []
            if isinstance(summary, str) and summary.strip():
                lines.append("SUMMARY:")
                lines.append(summary.strip())
            if lines:
                lines.append("")
            lines.append("MAIN_CHARACTER:")
            lines.append(character_name if character_name else "(unknown)")
            return "\n".join(lines).strip()
        if target_path == "n1.characters.secondary_characters":
            summary = self._extract_n0_summary_from_context(context_pack)
            lines: List[str] = []
            if isinstance(summary, str) and summary.strip():
                lines.append("SUMMARY:")
                lines.append(summary.strip())
            main_names = self._extract_n1_main_character_names_from_sparse(context_pack)
            lines.append("")
            lines.append("MAIN_CHARACTERS:")
            if main_names:
                lines.extend([f"- {name}" for name in main_names])
            else:
                lines.append("- (none yet)")
            return "\n".join(lines).strip()
        if target_path == "n1.characters.background_characters":
            summary = self._extract_n0_summary_from_context(context_pack)
            lines: List[str] = []
            if isinstance(summary, str) and summary.strip():
                lines.append("SUMMARY:")
                lines.append(summary.strip())
            main_names = self._extract_n1_main_character_names_from_sparse(context_pack)
            secondary_names = self._extract_n1_secondary_character_names_from_sparse(
                context_pack
            )
            lines.append("")
            lines.append("MAIN_CHARACTERS:")
            if main_names:
                lines.extend([f"- {name}" for name in main_names])
            else:
                lines.append("- (none yet)")
            lines.append("")
            lines.append("SECONDARY_CHARACTERS:")
            if secondary_names:
                lines.extend([f"- {name}" for name in secondary_names])
            else:
                lines.append("- (none yet)")
            return "\n".join(lines).strip()
        if isinstance(target_path, str) and target_path.startswith("n1.characters"):
            summary = self._extract_n0_summary_from_context(context_pack)
            if isinstance(summary, str) and summary.strip():
                return "SUMMARY:\n" + summary.strip()
            return ""
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
                context_pack.get("target_strata_data"), "n0.narrative_presentation.summary"
            )
            if not isinstance(summary_value, str):
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

    def _extract_main_character_name_from_context(
        self, target_path: str, context_pack: Dict[str, Any]
    ) -> str:
        target_current = context_pack.get("target_current")
        if isinstance(target_current, dict):
            raw_name = target_current.get("name", "")
            if isinstance(raw_name, str) and raw_name.strip():
                return raw_name.strip()
        match = re.search(
            r"n1\.characters\.main_characters\.characters\[(\d+)\]\.character_description",
            target_path or "",
        )
        if not match:
            return ""
        index = match.group(1)
        sparse = context_pack.get("target_strata_data")
        value = self._find_sparse_value(
            sparse,
            f"n1.characters.main_characters.characters[{index}].character_description.name",
        )
        return value.strip() if isinstance(value, str) else ""

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
            "n0.narrative_presentation.production_type",
            "n0.narrative_presentation.target_duration",
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

