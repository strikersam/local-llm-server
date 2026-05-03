# AGENTS.md — AI Agent Configuration for local-llm-server

> This file provides workspace-level context for AI agents (Claude Code, OpenClaw,
> or any agentic tool) operating in this repository.

## Workspace Purpose

This repository is a **self-hosted OpenAI-compatible LLM proxy** with a built-in
multi-agent orchestration layer. It routes requests from AI coding tools to locally-
running Ollama models.

## Agent Roles

| Role | File | Model | Responsibility |
|------|------|-------|----------------|
| Planner | `.claude/agents/planner.md` | deepseek-r1:32b | Plan → structured AgentPlan |
| Implementer | `.claude/agents/implementer.md` | qwen3-coder:30b | Execute file changes |
| Reviewer | `.claude/agents/reviewer.md` | deepseek-r1:32b | Verify before apply |
| Judge | `.claude/agents/judge.md` | deepseek-r1:32b | Release gate |
| OpenClaw | `N/A` | `N/A` | Maintenance: vulnerability fixes, code scan fixes, daily quality scans, regular smoke regression tests with bug reporting, issue raising and fixing |

## Operating Instructions

1. **Always read CLAUDE.md first** — it contains the operating guide.
2. **Use skills** from `.claude/skills/` for any non-trivial task.
3. **Write to `.claude/state/`** after each milestone (checkpoint persistence).
4. **Run `pytest -x` before and after any code change.**
5. **Update `docs/changelog.md`** before committing.

## State Files

| File | Purpose |
|------|---------|
| `.claude/state/agent-state.json` | Full session state (machine-readable) |
| `.claude/state/NEXT_ACTION.md` | Next step to execute (human-readable) |
| `.claude/state/checkpoint.jsonl` | Ordered log of completed steps |
| `.claude/state/runner.lock` | Active session lock |
| `.claude/state/session.log` | Session activity log |

## Quick Start for Agents

```bash
# See what skills/commands/agents are available
python scripts/ai_runner.py manifest

# Check current session state
python scripts/ai_runner.py status

# Resume interrupted work
python scripts/ai_runner.py resume

# Run tests
pytest -x
```

## Risky Paths — Require Extra Care

These paths require applying the `risky-module-review` skill before modifying:

- `admin_auth.py` — session auth
- `key_store.py` — API key persistence
- `agent/tools.py` — filesystem write surface
- `proxy.py` (auth middleware section) — request authentication
