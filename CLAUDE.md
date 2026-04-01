# CLAUDE.md — local-llm-server

> **Purpose:** Authoritative operating guide for Claude (and any AI agent) working in this repo.
> Keep this file concise. Deeper truth lives in `docs/`, module-level `CLAUDE.md` files, and ADRs.

---

## What This Repo Does

`local-llm-server` is a **self-hosted, OpenAI-compatible proxy** that sits in front of Ollama.
It lets AI coding tools (Claude Code, Cursor, Continue, Aider) point at `http://localhost:8000`
and receive intelligent routing to locally-running LLMs (Qwen3-Coder, DeepSeek-R1).

Key capabilities: Bearer-token auth, rate limiting, dynamic model routing, Langfuse
observability, multi-agent task execution, Telegram bot control, and a web admin dashboard.

---

## Codebase Map

```
proxy.py              Main FastAPI app — entry point, auth middleware, endpoint wiring
chat_handlers.py      OpenAI & Ollama native chat streaming/non-streaming handlers
handlers/
  anthropic_compat.py Anthropic /v1/messages compatibility surface
agent/
  loop.py             AgentRunner: plan → execute → verify cycle  ← RISKY, read agent/CLAUDE.md
  models.py           Pydantic models for agent I/O
  prompts.py          Prompt builders for planner/executor/verifier
  state.py            In-memory agent session store
  tools.py            WorkspaceTools: read/write/search filesystem
router/
  model_router.py     ModelRouter — central routing logic  ← read router/CLAUDE.md
  classifier.py       Task classification heuristics
  registry.py         Model capability registry
  health.py           Ollama health check + cache
admin_auth.py         Admin session auth (Jinja2 dashboard)   ← RISKY: auth code
key_store.py          API key CRUD + persistence (keys.json)   ← RISKY: secrets
langfuse_obs.py       Langfuse trace emission helper
service_manager.py    Windows service / process management
telegram_bot.py       Telegram bot for remote control
remote-admin/         Static SPA for remote dashboard (optional hosting)
client-configs/       Example configs for Cursor, Aider, Continue, Zed, VSCode
docs/                 All documentation (architecture, runbooks, ADRs)
.claude/              AI engineering system (skills, hooks, agents, state)
scripts/              Automation scripts including ai_runner.py watchdog
```

---

## Key Commands

```bash
# Development
source .venv/bin/activate
uvicorn proxy:app --reload --port 8000     # Start proxy

# Tests — ALWAYS run before committing
pytest -x                                  # Fast fail
pytest -v                                  # Verbose

# Hooks (must be activated once per clone)
git config core.hooksPath .claude/hooks    # Activate blocking hooks

# AI runner (auto-resume watchdog)
python scripts/ai_runner.py start          # Start an AI coding session
python scripts/ai_runner.py status         # Show current session state
python scripts/ai_runner.py resume         # Resume from last checkpoint
python scripts/ai_runner.py stop           # Stop current session
python scripts/ai_runner.py logs           # Tail session logs

# Utilities
python generate_api_key.py                 # Generate a new API key
python scripts/ai_runner.py manifest       # Show available tools/commands
python scripts/ai_runner.py summary        # Summarize last session
```

---

## Coding Rules

1. **Type annotations on all public functions.** Use `from __future__ import annotations`.
2. **No secrets in source.** All config via environment variables. Never hardcode API keys, tokens, or SECRET_KEY values.
3. **Pydantic models for all API I/O.** No raw dicts as function return types for request/response shapes.
4. **Async for all I/O.** FastAPI handlers and agent methods must be `async`.
5. **Log with `logging`, not `print`.** Use the module-level logger: `log = logging.getLogger("qwen-proxy")`.
6. **Auth is risky.** Any change to `admin_auth.py`, `key_store.py`, or `proxy.py` auth middleware MUST be reviewed via the `risky-module-review` skill.
7. **Agent file writes are risky.** The `agent/tools.py` `apply_diff` method writes to the filesystem. Changes require the `risky-module-review` skill.
8. **Router changes need tests.** `router/` changes must include or update tests in `tests/test_model_router.py`.

---

## Testing Expectations

- All tests live in `tests/`. Use `pytest`.
- New features → new test file or expanded existing test file.
- Bug fixes → regression test required.
- CI blocks merge on test failure (see `.github/workflows/ci.yml`).
- Run `pytest -x` locally before every push.

---

## Changelog Rule

**Every meaningful commit must update `docs/changelog.md`.**

Add an entry under `## [Unreleased]` following [Keep a Changelog](https://keepachangelog.com/) format:
- `### Added` for new features
- `### Changed` for behaviour changes
- `### Fixed` for bug fixes
- `### Security` for anything touching auth/keys/secrets
- `### Removed` for removals

The `commit-msg` hook will reject commits with no changelog update (unless the commit is
`chore:`, `docs:`, `style:`, `ci:`, or `test:` prefixed — those are exempt).

---

## Release Expectations

1. Bump version in `docs/changelog.md` (move `[Unreleased]` to a dated version).
2. Run `pytest` — must be green.
3. Tag `git tag vX.Y.Z`.
4. Push tag. CI runs on the tag.
5. See `docs/runbooks/release.md` for the full release checklist.

---

## How Claude Should Work in This Repo

**Always follow this sequence:**

1. **Read the relevant skill** from `.claude/skills/` before starting any non-trivial task.
2. **Run `pytest -x`** before making changes to confirm baseline passes.
3. **Use the implementation-planner skill** for any multi-file change.
4. **Use the risky-module-review skill** for any change to `admin_auth.py`, `key_store.py`, `agent/tools.py`, or auth/billing paths.
5. **Update `docs/changelog.md`** as part of every meaningful change.
6. **Run `pytest -x`** again after changes.
7. **Update `.claude/state/`** checkpoints after milestones.

**When to invoke which skill:**

| Situation | Skill to use |
|-----------|-------------|
| Planning a multi-file feature | `implementation-planner` |
| Writing or fixing tests | `test-first-executor` |
| Any auth/key/agent-tools change | `risky-module-review` |
| Pre-merge code review | `council-review` |
| Updating changelog | `changelog-enforcer` |
| Checking release readiness | `release-readiness` |
| Syncing docs after changes | `docs-sync` |
| Session interrupted/resuming | `cooldown-resume` |
| Adding/upgrading dependencies | `dependency-audit` |
| Updating repo memory/CLAUDE.md | `repo-memory-updater` |

---

## Where Deeper Truth Lives

| Topic | Location |
|-------|----------|
| Architecture overview | `docs/architecture/overview.md` |
| Agent orchestration design | `docs/architecture/agent-orchestration.md` |
| Model routing decisions | `docs/adrs/002-model-routing.md` + `router/CLAUDE.md` |
| Multi-agent design | `docs/adrs/003-multi-agent-orchestration.md` |
| Auto-resume runbook | `docs/runbooks/auto-resume.md` |
| Release procedure | `docs/runbooks/release.md` |
| GitHub admin settings | `docs/admin/github-branch-protection.md` |
| Risky module context | `agent/CLAUDE.md`, `router/CLAUDE.md` |

---

## Risky Modules — Read Local CLAUDE.md

Before touching these paths, read the local `CLAUDE.md` in that directory:

- **`agent/`** → `agent/CLAUDE.md` (file writes, code execution, security surface)
- **`router/`** → `router/CLAUDE.md` (model selection, fallback, health check caching)
- **`admin_auth.py`** → This file handles session cookies and admin identity; treat any change as security-sensitive and follow the `risky-module-review` skill.
- **`key_store.py`** → Stores API keys to disk. Never log key values. Always hash before comparing.
