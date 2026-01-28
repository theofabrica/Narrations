"""CLI entrypoint for narration_agent runtime."""

import argparse

from .agent_factory import AgentFactory
from .context_builder import ContextBuilder
from .llm_client import LLMClient
from .orchestrator import NarrationOrchestrator
from .task_runner import TaskRunner


def build_runtime(model: str) -> dict:
    llm_client = LLMClient(default_model=model)
    agent_factory = AgentFactory(default_model=model)
    context_builder = ContextBuilder()
    orchestrator = NarrationOrchestrator()
    runner = TaskRunner()
    return {
        "llm_client": llm_client,
        "agent_factory": agent_factory,
        "context_builder": context_builder,
        "orchestrator": orchestrator,
        "runner": runner,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Narration agent runtime bootstrap.")
    parser.add_argument("--model", default="gpt-4o", help="LLM model name")
    args = parser.parse_args()
    _ = build_runtime(args.model)
    print("Narration agent runtime ready.")


if __name__ == "__main__":
    main()
