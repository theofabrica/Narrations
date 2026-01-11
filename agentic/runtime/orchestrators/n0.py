from .base import OrchestratorBase, OrchestratorInputs


class N0Orchestrator(OrchestratorBase):
    def build_narrative_brief(self, inputs: OrchestratorInputs) -> str:
        return (
            "N0 Cadre de production\n"
            f"Projet: {inputs.project_id}\n"
            f"Demande: {inputs.user_request}\n\n"
            "Consignes:\n"
            "- Definir format, duree, ratio, livrables, contraintes, pipeline.\n"
            "- Pas de narration, pas de personnages, pas d'architecture.\n"
            "- Sortie texte structuree, pas de JSON.\n"
        )
