from __future__ import annotations

from agents.echo_agent import EchoAgent
from agents.simple_llm_agent import SimpleLLMAgent
from agents.planner_executor_agent import PlannerExecutorAgent
from agents.router_agent import RouterAgent


def main() -> None:
    print("=== Bac à sable agents IA ===")

    echo = EchoAgent()
    simple = SimpleLLMAgent(
        system_prompt="Tu es un assistant pédagogique sur les agents IA."
    )
    planner = PlannerExecutorAgent()

    router = RouterAgent(
        routes={
            "default": simple,
            "plan": planner,
            "echo": echo,
        }
    )

    prompt = "Explique brièvement ce qu'est un agent IA et donne un exemple."
    result = router.run(prompt)
    print("\n--- Résultat ---")
    print(result.output)
    print("\n--- Meta ---")
    print(result.metadata)


if __name__ == "__main__":
    main()
