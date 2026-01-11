from dataclasses import dataclass
from typing import Dict, Any

from ..agents import NarrativeAgent, CanonizerAgent


@dataclass
class OrchestratorInputs:
    project_id: str
    user_request: str
    n0_summary: str | None = None
    n1_summary: str | None = None
    n2_summary: str | None = None
    n3_summary: str | None = None
    json_template: str | None = None


class OrchestratorBase:
    def __init__(self, narrative: NarrativeAgent, canonizer: CanonizerAgent) -> None:
        self.narrative = narrative
        self.canonizer = canonizer

    def build_narrative_brief(self, inputs: OrchestratorInputs) -> str:
        raise NotImplementedError

    def build_canonizer_brief(self, inputs: OrchestratorInputs, narrative_text: str) -> str:
        if not inputs.json_template:
            raise ValueError("json_template is required for canonization")
        return (
            f"N0 resume:\n{inputs.n0_summary or ''}\n\n"
            f"Sortie narrative:\n{narrative_text}\n\n"
            f"Modele JSON:\n{inputs.json_template}"
        )

    def run(self, inputs: OrchestratorInputs) -> Dict[str, Any]:
        narrative_brief = self.build_narrative_brief(inputs)
        narrative_text = self.narrative.run(narrative_brief)
        canonizer_brief = self.build_canonizer_brief(inputs, narrative_text)
        canonical_json = self.canonizer.run(canonizer_brief)
        return {
            "narrative": narrative_text,
            "canonical_json": canonical_json,
        }
