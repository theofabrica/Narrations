import json
import os
from pathlib import Path

from .agents import NarrativeAgent, CanonizerAgent
from .llm_client import LLMClient
from .rag_client import R2RClientWrapper
from .orchestrators.base import OrchestratorInputs
from .orchestrators.n1 import N1Orchestrator


def load_template(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main() -> None:
    project_id = os.environ.get("PROJECT_ID", "demo")
    user_request = os.environ.get("USER_REQUEST", "Construire la bible N1.")
    template_path = os.environ.get("N1_TEMPLATE_PATH", "")
    if not template_path:
        raise RuntimeError("N1_TEMPLATE_PATH is required")
    n0_summary = os.environ.get("N0_SUMMARY", "")

    llm = LLMClient()
    rag = R2RClientWrapper()
    narrative = NarrativeAgent(llm=llm, rag=rag)
    canonizer = CanonizerAgent(llm=llm)

    orchestrator = N1Orchestrator(narrative, canonizer)
    inputs = OrchestratorInputs(
        project_id=project_id,
        user_request=user_request,
        n0_summary=n0_summary,
        json_template=load_template(template_path),
    )
    result = orchestrator.run(inputs)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
