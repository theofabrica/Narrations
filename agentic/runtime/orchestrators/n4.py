from .base import OrchestratorBase, OrchestratorInputs


class N4Orchestrator(OrchestratorBase):
    def build_narrative_brief(self, inputs: OrchestratorInputs) -> str:
        return (
            "N4 Prompts\n"
            f"Projet: {inputs.project_id}\n"
            f"Demande: {inputs.user_request}\n\n"
            f"N0 resume:\n{inputs.n0_summary or ''}\n\n"
            f"N1 resume:\n{inputs.n1_summary or ''}\n\n"
            f"N2 resume:\n{inputs.n2_summary or ''}\n\n"
            f"N3 resume:\n{inputs.n3_summary or ''}\n\n"
            "Consignes:\n"
            "- Traduire en plans + prompts selon PM_*.\n"
            "- Sortie texte structuree, pas de JSON.\n"
        )
