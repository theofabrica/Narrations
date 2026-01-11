from .base import OrchestratorBase, OrchestratorInputs


class N2Orchestrator(OrchestratorBase):
    def build_narrative_brief(self, inputs: OrchestratorInputs) -> str:
        return (
            "N2 Architecture\n"
            f"Projet: {inputs.project_id}\n"
            f"Demande: {inputs.user_request}\n\n"
            f"N0 resume:\n{inputs.n0_summary or ''}\n\n"
            f"N1 resume:\n{inputs.n1_summary or ''}\n\n"
            "Consignes:\n"
            "- Produis l'architecture (actes/sequences) avec fonctions, enjeux, sorties.\n"
            "- Pas de scenes (N3), pas de plans (N4).\n"
            "- Sortie texte structuree, pas de JSON.\n"
        )
