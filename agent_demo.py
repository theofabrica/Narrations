import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from agents import Agent, Runner
from agents.mcp import MCPServerSse, MCPServerSseParams


MCP_URL = "https://mcp.numeniagen76.com/sse"


async def main():
    # MCP server via HTTP+SSE (context-managed)
    async with MCPServerSse(params=MCPServerSseParams(url=MCP_URL)) as mcp_server:
        agent = Agent(
            name="NarrationsAgent",
            instructions="Tu peux appeler les outils MCP (ping, elevenlabs, higgsfield, pipelines).",
            mcp_servers=[mcp_server],
            model="gpt-4o",
        )

        # 1) Ping MCP
        result_ping = await Runner.run(agent, "Appelle l'action MCP 'ping' puis réponds OK.")
        print("---- Ping ----")
        print(result_ping.final_output)

        # 2) ElevenLabs voice TTS example
        tts_cmd = (
            "Appelle l'action MCP 'elevenlabs_voice' avec "
            "text='Bienvenue au saloon narrations', voice_id='21m00Tcm4TlvDq8ikWAM', "
            "model_id='eleven_multilingual_v2'. Réponds avec le résultat."
        )
        result_tts = await Runner.run(agent, tts_cmd)
        print("---- TTS ----")
        print(result_tts.final_output)


if __name__ == "__main__":
    # Load .env if present
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    # Requires OPENAI_API_KEY in env
    if "OPENAI_API_KEY" not in os.environ:
        raise SystemExit("Missing OPENAI_API_KEY in environment.")
    asyncio.run(main())
