from .base import OrchestratorInputs


def route_level(request: str) -> str:
    lowered = request.lower()
    if any(keyword in lowered for keyword in ("prompt", "plan", "n4")):
        return "n4"
    if any(keyword in lowered for keyword in ("scene", "n3")):
        return "n3"
    if any(keyword in lowered for keyword in ("architecture", "sequence", "n2")):
        return "n2"
    if any(keyword in lowered for keyword in ("bible", "n1")):
        return "n1"
    return "n0"


def build_core_summary(inputs: OrchestratorInputs) -> str:
    return (
        f"Projet: {inputs.project_id}\n"
        f"Demande: {inputs.user_request}\n"
    )
