# TOOLS.md — Available Tools for AI Agents

> This file documents the tools available when an AI agent operates in this repo.
> Compatible with OpenClaw workspace configuration and similar agentic systems.

## File Tools

| Tool | Description |
|------|-------------|
| `read_file(path)` | Read file content from the workspace |
| `write_file(path, content)` | Write (overwrite) a file |
| `list_files(path, limit)` | List files in a directory |
| `search_code(query, limit)` | Search for code patterns across the repo |
| `apply_diff(path, content)` | Apply new content to a file (writes atomically) |

These are implemented in `agent/tools.py` as `WorkspaceTools`.

## Shell / Process Tools

| Command | Purpose |
|---------|---------|
| `pytest -x` | Run tests (fast fail) |
| `pytest -v` | Run tests (verbose) |
| `python -m py_compile <file>` | Syntax check a Python file |
| `git diff --cached` | Show staged changes |
| `git diff HEAD` | Show all changes since last commit |
| `git log --oneline -10` | Recent commits |

## AI Runner Tools

```bash
python scripts/ai_runner.py status       # Session state
python scripts/ai_runner.py resume       # Resume interrupted session
python scripts/ai_runner.py manifest     # List all capabilities
python scripts/ai_runner.py audit        # Security audit
python scripts/ai_runner.py changelog-check   # Validate changelog
python scripts/ai_runner.py test-resume  # Prove resume works
```

## API Endpoints (when proxy is running)

| Endpoint | Purpose |
|----------|---------|
| `POST /v1/chat/completions` | OpenAI-compatible chat |
| `POST /v1/messages` | Anthropic-compatible chat |
| `POST /api/chat` | Ollama-native chat |
| `POST /v1/agent/run` | Run an agent task |
| `GET /health` | Health check |
| `GET /v1/models` | List available models |

## Skills (invoke via CLAUDE.md instructions)

All skills are in `.claude/skills/`. See `python scripts/ai_runner.py manifest` for the full list.

## OpenClaw Integration

To use this repo as an OpenClaw workspace:

1. Install OpenClaw: see `docs/runbooks/openclaw-setup.md`
2. Point OpenClaw at this directory as the workspace root
3. OpenClaw will read `AGENTS.md` and `TOOLS.md` for workspace context
4. Sessions are persisted in `.claude/state/` and survive process restarts
