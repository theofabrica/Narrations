from .base import OrchestratorBase, OrchestratorInputs


class N1Orchestrator(OrchestratorBase):
    def build_narrative_brief(self, inputs: OrchestratorInputs) -> str:
        return (
            "N1 Bible Narrative\n"
            f"Projet: {inputs.project_id}\n"
            f"Demande: {inputs.user_request}\n\n"
            f"N0 resume:\n{inputs.n0_summary or ''}\n\n"
            "Consignes:\n"
            "- Produis la bible N1 (monde, intention, axes, personnages, dynamique globale).\n"
            "- Pas d'architecture (N2), pas de scenes (N3), pas de plans (N4).\n"
            "- Sortie texte structuree, pas de JSON.\n\n"
            "Format attendu:\n"
            "1) Pitch\n"
            "2) Intention\n"
            "3) Axes artistiques\n"
            "4) Dynamique globale\n"
            "5) Personnages (role + fonction)\n"
            "6) Monde/Epoque\n"
            "7) Esthetique\n"
            "8) Son (ambiances, musique, sfx, dialogues)\n"
            "9) Motifs\n"
            "10) Hypotheses / questions\n"
        )
