# Repository Guidelines

## Project Structure and Module Organization
The core FastAPI server lives in `app/` with key areas split by responsibility:
- `app/mcp/` for request/response schemas and the MCP handler.
- `app/tools/` for provider clients and tool handlers (Higgsfield, ElevenLabs).
- `app/pipelines/` for multi-step workflows (image-to-video, audio stack).
- `app/utils/` for IDs, logging, storage, and error helpers.
- `app/config/` for settings loaded from environment variables.

Supporting folders include `tests/` for pytest coverage, `docs/` for provider notes, `Media/` for generated assets, `mailbox/` for polling helpers, and `scripts/` or `run.sh` for startup utilities.

## Build, Test, and Development Commands
- `pip install -r requirements.txt` installs Python dependencies.
- `python -m uvicorn app.main:app --host 0.0.0.0 --port 3333 --reload` runs the API in dev mode.
- `./run.sh` launches the server and can optionally start a Cloudflare tunnel.
- `pytest` runs the full test suite.
- `pytest -v` adds verbose output.
- `pytest tests/test_mcp.py -v` runs a focused test file.

Configuration is read from `.env` (see `.env.example`), including API keys and storage settings.

## Coding Style and Naming Conventions
Use standard Python conventions: 4-space indentation, PEP 8 layout, `snake_case` for functions and modules, and `PascalCase` for classes. Keep action names aligned with MCP handlers (for example, `elevenlabs_voice`, `higgsfield_video`, `pipeline_image_to_video`) so registry lookups stay consistent. No formatter is enforced, so match existing style and keep diffs minimal.

## Testing Guidelines
Tests use `pytest`, `pytest-asyncio`, and `respx`. Name files `test_*.py` and test functions `test_*`. Focus coverage on MCP actions, provider client behavior, and pipeline orchestration. Run targeted tests before changing tool handlers or schemas.

## Commit and Pull Request Guidelines
Commit messages are short, imperative, and often in French (examples: `Ajoute client local`, `Fix tunnel launch`). For pull requests, include a brief summary, test results (or a note if skipped), and any required configuration changes. If an endpoint or payload changes, add a curl example in the description.

## Security and Configuration Tips
Never commit API keys; keep them in `.env`. Generated assets are stored under `Media/` and can be served via `/assets/{project}/{type}/{filename}`. If enabling FTP or tunneling, document the related environment variables in your change.
