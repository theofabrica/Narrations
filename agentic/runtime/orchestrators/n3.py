from .base import OrchestratorBase, OrchestratorInputs


class N3Orchestrator(OrchestratorBase):
    def build_narrative_brief(self, inputs: OrchestratorInputs) -> str:
        return (
            "N3 Scenes\n"
            f"Projet: {inputs.project_id}\n"
            f"Demande: {inputs.user_request}\n\n"
            f"N0 resume:\n{inputs.n0_summary or ''}\n\n"
            f"N1 resume:\n{inputs.n1_summary or ''}\n\n"
            f"N2 resume:\n{inputs.n2_summary or ''}\n\n"
            "Consignes:\n"
            "- Developpe les scenes (visuel + son) sans plans camera.\n"
            "- Sortie texte structuree, pas de JSON.\n"
        )
