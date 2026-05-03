<div align="center">

# LLM Relay (`local-llm-server`)

### Self-hosted OpenAI-compatible proxy, agent runtime, and control plane.

**Run local models, route across providers, manage agents, schedule work, and operate everything from one stack.**

[![Stars](https://img.shields.io/github/stars/strikersam/local-llm-server?style=for-the-badge&color=FFD43B&logo=github)](https://github.com/strikersam/local-llm-server/stargazers)
[![Forks](https://img.shields.io/github/forks/strikersam/local-llm-server?style=for-the-badge&color=4D8CFF&logo=git)](https://github.com/strikersam/local-llm-server/network)
[![License](https://img.shields.io/badge/license-Open%20Source-22C55E?style=for-the-badge)](LICENSE)

[![Python 3.13](https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLMs-000000?style=flat-square)](https://ollama.com/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Langfuse](https://img.shields.io/badge/Langfuse-observability-FF7A1A?style=flat-square)](https://langfuse.com/)

[**Quick start**](#quick-start) · [**Feature inventory**](#feature-inventory) · [**Docs map**](#docs-map) · [**API surfaces**](#api-surfaces)

</div>

---

## What this repo is

`local-llm-server` started as a local LLM proxy and now ships a much broader stack:

- an **OpenAI-compatible** and **Anthropic-compatible** gateway in front of Ollama and remote providers
- a **built-in admin UI** and **built-in web UI** served by the proxy
- an optional **React control plane** for agents, tasks, schedules, knowledge, routing, and observability
- a **multi-agent orchestration layer** with sessions, memory, budgets, verification, judge gates, and background execution
- a **CRISPY workflow engine** for gated multi-phase build flows
- **GitHub, secrets, sync, schedules, browser automation, voice, and telemetry** features around the core proxy

If you want one local URL for Cursor, Claude Code, Aider, Continue, custom SDKs, and your own agent platform, this repo is that stack.

<p align="center">
  <img src="docs/screenshots/v3-control-plane.png" alt="LLM Relay control plane" width="100%"/>
</p>

---

## Feature inventory

### 1) Core proxy + compatibility

| Area | What is included |
|---|---|
| OpenAI compatibility | `/v1/chat/completions`, `/v1/models`, embeddings passthrough, streaming + non-streaming |
| Anthropic compatibility | `/v1/messages` for Claude-style clients including Claude Code |
| Ollama passthrough | `/api/*` passthrough for Ollama-native clients |
| Legacy compatibility | `v1/completions` handling and model aliasing |
| Client support | Cursor, Claude Code, Aider, Continue, Zed, VS Code, curl, Python SDK, iOS Shortcut examples in `client-configs/` |
| Proxy controls | API key auth, per-key rate limiting, CORS, default system prompt injection, think-tag stripping, health endpoints |

### 2) Provider + model routing

| Area | What is included |
|---|---|
| Local-first routing | Ollama local models remain the default path |
| Remote providers | Hugging Face, OpenRouter, DeepSeek, Anthropic, Together, Google-compatible OpenAI endpoints, remote Ollama, NVIDIA NIM, and other OpenAI-compatible bases |
| Dynamic routing | Heuristic task classification + model selection via `provider_router.py` and `router/` |
| Fallbacks | Provider cooldowns, retry paths, availability filtering, health-aware routing |
| Approval-aware escalation | Routing policy supports local → free cloud → paid escalation behavior with explicit gating in the control plane |
| Hardware awareness | Hardware detection + model compatibility APIs under `/api/hardware/*` |

### 3) Agent platform

| Area | What is included |
|---|---|
| Agent sessions | Persistent session IDs, chat history, memory snapshot/restore, ownership checks |
| Agent loop | Planner → executor → verifier → judge pipeline |
| Multi-agent execution | Parallel swarm execution when steps can be split safely |
| Runtime adapters | Hermes, OpenCode, Goose, Aider in Docker Compose; OpenHands adapter exists in code for registration workflows |
| Agent controls | Session permissions, token budgets, context compression/inspection, history snipping |
| Background work | Background task queue, playbooks, watchdog resources, terminal capture, scaffolding, skill search, commit history endpoints |
| Tooling extras | Browser automation, voice transcription, subagent delegation |

### 4) Workflow + task management

| Area | What is included |
|---|---|
| Kanban tasks | CRUD, comments, approvals, retries, escalation, due-soon and count views |
| Schedules | Create, pause, resume, run-now, delete, and run history via `/api/schedules/*` and legacy scheduler routes |
| CRISPY workflow engine | `/workflow/*` APIs, approvals, rejection/resume flow, artifacts, events, verification passes |
| IDE workflow bridge | `crispy-workflow` pseudo-model plus `@build`, `@workflow`, `/crispy`, and `@status` chat triggers |
| Automation | Dispatcher + scheduler wiring for recurring or approval-gated agent work |

### 5) Control plane + UI surfaces

| Surface | What is included |
|---|---|
| Built-in admin portal | Session login, service controls, key management, diagnostics at `/admin/ui/*` |
| Built-in web UI | Proxy-served chat/admin apps at `/app` and `/admin/app` |
| React control plane | Dashboard, Setup Wizard, Chat, Providers, Models, Knowledge, Sources, Agents, Runtimes, Tasks, Schedules, Routing Policy, Logs, Observability, GitHub, Settings, Admin Portal |
| Setup Wizard | Provider detection, hardware/model detection, runtime selection, default agent selection, cost policy |
| Hosted mode | Separate backend/frontend stack under `backend/` + `frontend/` for Render/GitHub Pages-style deployments |

### 6) Knowledge + workspace features

| Area | What is included |
|---|---|
| Wiki | Page CRUD + linting |
| Sources | URL/file/text ingestion and source tracking |
| Direct chat | Persistent chat sessions with provider routing and optional agent mode |
| GitHub workspace | OAuth/PAT flows, repo listing, branches, tree browsing, file read/write, PR listing/creation |
| Secrets | User/workspace secret storage APIs under `/api/secrets/*` |
| Peer sync | Syncthing-style sync for skills, workspaces, runtime configs, and tool configs |

### 7) Security + administration

| Area | What is included |
|---|---|
| Auth modes | API keys, admin secret, JWT auth for the control plane, GitHub + Google OAuth |
| RBAC | Role and permission infrastructure with audit hooks |
| Key management | Per-user keys, rotation, hashed persistence, legacy `API_KEYS` fallback |
| Safe command execution | Allowlisted command runner for the web admin surface |
| Auditability | Activity logging, control plane activity feeds, Langfuse integration |

### 8) Observability + cost controls

| Area | What is included |
|---|---|
| Langfuse tracing | Request/response traces, usage, latency, routing metadata |
| Local cost tracking | Infrastructure electricity + amortization estimates |
| Savings views | Commercial-equivalent cost comparison and savings summaries |
| Control plane dashboards | `/api/observability/*`, activity feeds, stats, logs, metrics |

### 9) Deployment + operations

| Area | What is included |
|---|---|
| Docker Compose stack | Ollama, proxy, MongoDB, runtime containers, optional dashboard, optional tunnels |
| Tunnel options | Cloudflare quick tunnel and ngrok profile/scripts |
| Telegram bot | Remote status/control and admin actions from Telegram |
| Runbooks | Deployment, Claude Code, agent runtimes, observability, troubleshooting |

---

## Architecture at a glance

```text
Clients (Cursor / Claude Code / Aider / Continue / SDKs)
        |
        | OpenAI / Anthropic / Ollama-compatible HTTP
        v
+---------------------------------------------------------+
| proxy.py (FastAPI)                                      |
|                                                         |
|  Auth + Keys + CORS + Rate limits                       |
|  OpenAI + Anthropic + Ollama compatibility              |
|  Provider routing + fallback + health                   |
|  Agent sessions + background tasks + browser/voice      |
|  Workflow engine + schedules + sync + secrets + GitHub  |
|  Built-in admin UI + built-in web UI                    |
+---------------------------------------------------------+
           |                    |                    |
           v                    v                    v
        Ollama             Remote providers      Langfuse

Optional full dashboard profile:
  React frontend (:3000) + FastAPI backend (:8001) + MongoDB
```

For a deeper system breakdown, read [docs/architecture/overview.md](docs/architecture/overview.md).

---

## Deployment modes

| Mode | Start it | What you get |
|---|---|---|
| Proxy only | `uvicorn proxy:app --port 8000` | Core proxy, agent APIs, workflow engine, built-in admin UI, built-in web UI |
| Compose core | `docker compose up -d` | Proxy + Ollama + MongoDB + Hermes/OpenCode/Goose/Aider runtime containers |
| Compose dashboard | `docker compose --profile dashboard up -d` | Separate React control plane on `:3000` and backend on `:8001` |
| Public access | `docker compose --profile tunnel up -d` or `--profile ngrok up -d` | HTTPS tunnel for remote clients |

---

## Quick start

### Docker Compose

> There is currently no committed `.env.example` in the repo, so create `.env` manually.

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

cat > .env <<'ENV'
API_KEYS=sk-relay-dev
ADMIN_SECRET=replace-with-a-long-random-secret
ADMIN_EMAIL=admin@llmrelay.local
ADMIN_PASSWORD=replace-with-a-strong-password
JWT_SECRET=replace-with-another-long-random-secret
ENV

docker compose up -d
```

Then:

- open **http://localhost:8000/health** for the proxy health check
- open **http://localhost:8000/admin/ui/login** for the built-in admin portal
- open **http://localhost:8000/app** for the built-in web UI

If you also want the separate React control plane:

```bash
docker compose --profile dashboard up -d
```

Then open **http://localhost:3000**.

### Pull local models

```bash
docker exec llm-server-ollama ollama pull qwen3-coder:30b
docker exec llm-server-ollama ollama pull deepseek-r1:32b
```

### Minimal local dev

```bash
uvicorn proxy:app --reload --port 8000
```

---

## Default credentials and auth

### Built-in admin portal (`/admin/ui/login` on port 8000)

- **Username:** any value
- **Password:** `ADMIN_SECRET`

### React control plane (`:3000` → backend `:8001`)

- **Email:** `ADMIN_EMAIL` (defaults to `admin@llmrelay.local`)
- **Password:** `ADMIN_PASSWORD`

> Weak values like `admin`, `password`, `secret`, and `change-me` are rejected for `ADMIN_SECRET`.

---

## Connect your tools

### Cursor

```text
API Key:                  sk-relay-...
Override OpenAI Base URL: http://localhost:8000/v1
```

### Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
export ANTHROPIC_API_KEY=sk-relay-...
claude
```

### curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-relay-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder:30b","messages":[{"role":"user","content":"hello"}]}'
```

More examples live in [`client-configs/`](client-configs/).

---

## API surfaces

### Proxy-compatible surfaces (`proxy.py`)

| Surface | Purpose |
|---|---|
| `/v1/*` | OpenAI-compatible routes |
| `/v1/messages` | Anthropic-compatible Messages API |
| `/api/*` | Ollama-native passthrough |
| `/api/auth/*` | JWT auth for the control plane |
| `/api/social/*` | GitHub + Google OAuth flows |
| `/api/chat/*` | Direct chat sessions |
| `/api/models/*` + `/api/providers/*` + `/api/stats` + `/api/activity` | Model, provider, stats, and activity management |
| `/api/hardware/*` | Hardware profile + compatibility checks |
| `/agent/*` | Agent sessions, memory, browser, voice, terminal, schedules, playbooks |
| `/v2/agent/coordinate` | Multi-agent coordination v2 |
| `/workflow/*` | CRISPY workflow engine |
| `/api/tasks/*` | Kanban task APIs |
| `/api/agents/*` | Agent profile APIs |
| `/runtimes/*` | Runtime health/control APIs |
| `/ui/api/*` | Built-in web UI JSON APIs |
| `/api/setup/*` | Setup Wizard APIs |
| `/api/observability/*` | Savings, usage, metrics, status |
| `/api/github/*` | GitHub integration |
| `/api/secrets/*` | Secret storage |
| `/api/sync/*` | Peer sync |
| `/api/schedules/*` | Schedule CRUD + run history |
| `/api/routing/*` | Routing policy + routing stats |
| `/admin/ui/*` + `/admin/api/*` | Admin browser UI and admin API |
| `/app` + `/admin/app` | Built-in proxy-served web UI |

### Separate dashboard backend (`backend/server.py`)

The hosted/standalone backend under `backend/` exposes the same broad control-plane concepts for the React frontend on port `8001`, including:

- auth + social login
- tasks, agents, runtimes, schedules
- wiki and sources
- providers and models
- observability
- GitHub repo/PR/file flows
- setup wizard state
- chat sessions
- platform/activity/stats endpoints

---

## Services and ports

| Service | Port | Default compose | Notes |
|---|---:|---|---|
| Proxy | 8000 | yes | Main API, admin portal, built-in web UI |
| Ollama | 11434 | yes | Local model runtime |
| Hermes runtime | 8002 | yes | Runtime adapter container |
| OpenCode runtime | 8003 | yes | Runtime adapter container |
| Goose runtime | 8004 | yes | Runtime adapter container |
| Aider runtime | 8005 | yes | Runtime adapter container |
| MongoDB | 27017 | yes | Persistence for dashboard/control-plane data |
| Dashboard backend | 8001 | dashboard profile | Separate FastAPI backend |
| Dashboard frontend | 3000 | dashboard profile | Separate React control plane |
| Cloudflare tunnel | n/a | tunnel profile | Public HTTPS URL |
| ngrok tunnel | n/a | ngrok profile | Public HTTPS URL |

> OpenHands support exists as a runtime adapter in `runtimes/adapters/openhands.py`, but it is not started by default in `docker-compose.yml`.

---

## Docs map

| Topic | Where to go |
|---|---|
| Full feature guide | [docs/features.md](docs/features.md) |
| Configuration / env vars | [docs/configuration-reference.md](docs/configuration-reference.md) |
| Architecture overview | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Admin dashboard guide | [docs/admin-dashboard.md](docs/admin-dashboard.md) |
| Model routing | [docs/model-routing.md](docs/model-routing.md) |
| Claude Code setup | [docs/claude-code-setup.md](docs/claude-code-setup.md) |
| Device compatibility | [docs/device-compatibility.md](docs/device-compatibility.md) |
| Agent runtimes | [docs/runbooks/agent-runtime-setup.md](docs/runbooks/agent-runtime-setup.md) |
| Docker agent runtimes | [docs/runbooks/docker-agent-runtimes.md](docs/runbooks/docker-agent-runtimes.md) |
| Langfuse observability | [docs/langfuse-observability.md](docs/langfuse-observability.md) |
| Telegram bot | [docs/telegram-bot.md](docs/telegram-bot.md) |
| Troubleshooting | [docs/troubleshooting.md](docs/troubleshooting.md) |
| Changelog | [docs/changelog.md](docs/changelog.md) |

---

## Repo map

```text
local-llm-server/
├── proxy.py                 # Main FastAPI proxy + agent + admin/UI surfaces
├── chat_handlers.py         # OpenAI/Ollama chat handling
├── handlers/                # Anthropic compat, auth, models/providers helpers
├── router/                  # Model routing, classification, health, registry
├── agent/                   # Planner/executor/verifier/judge loop
├── agents/                  # Agent profile APIs + persistence
├── runtimes/                # Runtime registry, health, control, routing
├── tasks/                   # Kanban task APIs + automation
├── workflow/                # CRISPY workflow engine
├── schedules/               # Schedule APIs
├── setup/                   # Setup Wizard APIs
├── hardware/                # Hardware detection + compatibility
├── sync/                    # Peer sync service
├── webui/                   # Built-in proxy-served web UI
├── frontend/                # Separate React control plane frontend
├── backend/                 # Separate FastAPI control plane backend
├── client-configs/          # Example configs for IDEs and SDKs
├── docs/                    # Architecture, runbooks, screenshots, changelog
└── docker-compose.yml       # Main local stack
```

---

## Notes before production use

- set strong values for `ADMIN_SECRET`, `ADMIN_PASSWORD`, and `JWT_SECRET`
- restrict `CORS_ORIGINS`
- prefer `KEYS_FILE` over legacy `API_KEYS` for teams
- configure Langfuse if you want per-user observability and savings tracking
- review [docs/troubleshooting.md](docs/troubleshooting.md) and [docs/configuration-reference.md](docs/configuration-reference.md)

---

## License

Open source. Use it, fork it, improve it.

---

<div align="center">

If LLM Relay saves you money or unblocks your workflow, a star helps others find it.

[![Star this repo](https://img.shields.io/github/stars/strikersam/local-llm-server?style=for-the-badge&logo=github&color=FFD43B)](https://github.com/strikersam/local-llm-server/stargazers)

</div>
