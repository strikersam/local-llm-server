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

### `webui/`
Claude Code–style Web UI (SPA + JSON APIs) served directly by the proxy. Provides chat + agentic coding UI at `/` and an Admin app at `/admin/app`.

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
