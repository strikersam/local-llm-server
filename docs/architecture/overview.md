# Architecture Overview — local-llm-server

## System Purpose

`local-llm-server` is a self-hosted OpenAI-compatible API proxy that:
1. Authenticates requests with Bearer token auth
2. Routes them to locally-running Ollama LLMs
3. Applies intelligent model selection based on task type
4. Emits observability traces to Langfuse
5. Provides a multi-agent orchestration API for agentic coding tasks

## High-Level Architecture

```
Client (Claude Code / Cursor / Aider / Continue)
  │
  │  HTTP (OpenAI API format)
  ▼
┌─────────────────────────────────────────────────────┐
│                    proxy.py (FastAPI)                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  Auth layer  │  │ Rate limiter │  │   CORS    │  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
│         │                                            │
│  ┌──────┴─────────────────────────────────────┐      │
│  │           Request routing                  │      │
│  │  /v1/messages  /v1/chat/completions  /api/ │      │
│  └──────┬──────────────┬───────────────┬──────┘      │
│         │              │               │              │
│  ┌──────┴──────┐ ┌─────┴──────┐ ┌─────┴──────┐       │
│  │  Anthropic  │ │  OpenAI    │ │  Ollama    │       │
│  │  compat     │ │  handlers  │ │  native    │       │
│  └──────┬──────┘ └─────┬──────┘ └─────┬──────┘       │
│         └──────────────┴──────────────┘              │
│                        │                             │
│               ┌────────┴──────────┐                  │
│               │   router/         │                  │
│               │  ModelRouter      │                  │
│               │  classify_task()  │                  │
│               │  best_model_for() │                  │
│               │  health_check()   │                  │
│               └────────┬──────────┘                  │
└────────────────────────┼────────────────────────────┘
                         │
                  HTTP (Ollama API)
                         │
                ┌────────┴────────┐
                │     Ollama      │
                │  qwen3-coder    │
                │  deepseek-r1    │
                └─────────────────┘
```

## Key Components

### `proxy.py`
Main FastAPI application. Handles auth middleware, rate limiting, CORS, and request routing.
All three API surfaces (Anthropic, OpenAI, Ollama) are dispatched from here.

### `chat_handlers.py`
Implements streaming and non-streaming chat for OpenAI and Ollama native formats.
Integrates with the router for model selection and Langfuse for observability.

### `handlers/anthropic_compat.py`
Implements `/v1/messages` (Anthropic Messages API format). Translates Anthropic requests
to Ollama format, enabling Claude Code and other Anthropic-format clients to work directly.

### `router/`
Central model selection layer. See `router/CLAUDE.md` for full details.
Priority: manual override → MODEL_MAP → heuristic classification → default.

### `agent/`
Multi-agent orchestration layer. See `agent/CLAUDE.md` for full details.
Three-role pipeline: Planner → Implementer (with tool loop) → Verifier.

### `admin_auth.py` + `admin_gui.py`
Web admin dashboard. Session-based auth with Jinja2 templates.

### `key_store.py`
API key CRUD with JSON persistence. Keys hashed before storage.

### `langfuse_obs.py`
Langfuse trace emission helper. Wraps all LLM calls with cost and routing metadata.

## Multi-Agent Orchestration

The agent system uses a **plan-execute-verify** loop:

```
Instruction
    │
    ▼
Planner (deepseek-r1:32b)
    │  AgentPlan JSON
    ▼
For each step:
    │
    ├─ Tool loop (read/list/search context)
    │
    ▼
Implementer (qwen3-coder:30b)
    │  FILE + ACTION + content
    │
    ▼
Verifier (deepseek-r1:32b)
    │  VerificationResult (pass/fail + issues)
    │
    ├─ pass → apply_diff() → next step
    └─ fail → retry (max 3) → step failed

    │
    ▼
Judge (release gate)
    │
    ▼
Summary + Commits
```

## Resumability

All agent sessions write to `.claude/state/agent-state.json` and `.claude/state/checkpoint.jsonl`.
After interruption, `scripts/ai_runner.py resume` reads the checkpoint log, skips completed steps,
and continues from the next unfinished step. See `docs/runbooks/auto-resume.md`.

## Observability

Langfuse traces are emitted for every LLM call when `LANGFUSE_SECRET_KEY` is configured.
Each trace includes routing metadata: `routing_mode`, `routing_resolved_model`, `routing_task_category`.

## Deployment

The proxy runs as a FastAPI app on `PROXY_PORT` (default 8000).
An ngrok tunnel can expose it publicly for remote AI tool access.
A Telegram bot provides remote status and control.
A Windows Task Scheduler / systemd service can autostart the proxy.


## Workspace Isolation

Every agent session/job operates in its own **isolated workspace** managed by `workspace/manager.py:WorkspaceManager`. See [docs/architecture/workspace-isolation.md](workspace-isolation.md) for full details.

Key properties:
- Deterministic, opaque workspace roots derived from hashed session/job IDs
- Path safety: canonicalization, traversal rejection, symlink escape blocking
- Session/job ownership boundaries with concurrency guards
- Explicit lifecycle states (creating → ready → active → paused → completed → failed → cancelled → archived → cleaned)
- Structured manifest per workspace (`manifest.json`)
- Retention TTL and safe cleanup policies
- Structured, actionable error codes for all failure modes

The `AgentJobManager` integrates with `WorkspaceManager` to automatically provision and manage isolated workspaces for each agent job.

## Feature Maturity Tiers

The system classifies every feature into a maturity tier: **stable**, **beta**, **experimental**, or **disabled**. The `features/matrix.py:FeatureMatrix` is the single source of truth.

- **stable** — production-ready, no known major issues
- **beta** — functional, may have edge cases or behavioral changes
- **experimental** — proof-of-concept, may be unstable or incomplete
- **disabled** — turned off, requires explicit override

The matrix is enforced, not just documented:
- `matrix.check_available(feature_id)` gates disabled features
- `matrix.maturity_warning(feature_id)` surfaces warnings for beta/experimental
- Admin API at `/admin/features` exposes the matrix for operators
- Config overrides via `FEATURE_<ID>=<tier>` allow runtime adjustments

See [docs/support-matrix.md](../support-matrix.md) for the full feature matrix.
