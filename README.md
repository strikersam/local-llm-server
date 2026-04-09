<div align="center">

# LLM Relay

**A complete self-hosted AI platform — unified dashboard, multi-provider LLM routing, AI agent with memory, knowledge wiki, Telegram bot control, and full Langfuse observability.**

[![Stars](https://img.shields.io/github/stars/strikersam/local-llm-server?style=flat-square&color=yellow)](https://github.com/strikersam/local-llm-server/stargazers)
[![Forks](https://img.shields.io/github/forks/strikersam/local-llm-server?style=flat-square&color=blue)](https://github.com/strikersam/local-llm-server/network)
[![License](https://img.shields.io/badge/license-Open%20Source-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLMs-black?style=flat-square)](https://ollama.com/)

*Drop-in OpenAI-compatible proxy — point Cursor, Claude Code, Aider, or Continue at it and everything just works. Your hardware. Your data. Zero API bills.*

</div>

---

## The Unified Interface

One dark-themed dashboard for everything: chat with your AI agent, manage providers and workspaces, run commands, and control access — all without touching a terminal.

![LLM Relay Unified UI](docs/screenshots/webui-app.png)

> The agent knows your workspace, remembers context across sessions, and executes tasks directly in your project. Hit **New session**, paste your API key, pick a model, and start building.

---

## Why LLM Relay?

Every serious AI developer eventually hits the same wall: API bills that compound with every experiment, models you can't run privately, and a pile of tools that don't talk to each other.

LLM Relay replaces that with a single self-hosted platform. Your existing tools — Cursor, Claude Code, Aider, Continue — keep working without changes. The data never leaves your machine. And the cost difference is stark:

> **Real production numbers:** DeepSeek-R1 671B locally costs ~$0.19/day in electricity. The API equivalent: $12.84 — a **96.7% reduction** across 1,842 requests.

![Langfuse Cost Analysis](docs/screenshots/langfuse-cost-dashboard.png)

---

## What Makes This Different

| | LLM Relay | Bare Ollama | Paid API |
|---|---|---|---|
| OpenAI-compatible API | ✅ | ✅ | ✅ |
| Unified web dashboard | ✅ | ❌ | ❌ |
| Multi-provider routing | ✅ | ❌ | ❌ |
| AI agent with memory | ✅ | ❌ | ❌ |
| Knowledge wiki | ✅ | ❌ | ❌ |
| Background task queue | ✅ | ❌ | ❌ |
| Telegram bot control | ✅ | ❌ | ❌ |
| Cost tracking + attribution | ✅ | ❌ | ✅ |
| Multi-agent swarms | ✅ | ❌ | ❌ |
| Browser automation | ✅ | ❌ | ❌ |
| Zero vendor lock-in | ✅ | ✅ | ❌ |
| Zero ongoing API cost | ✅ | ✅ | ❌ |

---

## Features

### Providers, Workspaces & Command Runner

The admin panel in the unified UI lets you wire up any LLM backend, point the agent at your codebase, and run commands — all from the same interface.

![Unified Admin Panel](docs/screenshots/webui-admin.png)

- **Providers** — Add any OpenAI-compatible endpoint: local Ollama, HuggingFace, OpenRouter, or a remote machine. Test the connection in one click.
- **Workspaces** — Bind the agent to a directory on disk. The agent reads, writes, and searches only within that scope.
- **Command Runner** — Execute shell commands (e.g. `git status`, `pytest`) directly from the dashboard and capture the full output.

---

### Telegram Bot Control

Control your entire AI stack from your phone — no browser, no VPN needed.

![Telegram Bot](docs/screenshots/telegram-bot-commands.png)

| Command | What It Does |
|---------|-------------|
| `/status` | Ollama, proxy, and tunnel health + models loaded and VRAM usage |
| `/cost` | Real-time electricity estimate and hardware amortisation breakdown |
| `/models` | List every loaded model with size |
| `/restart tunnel` | Restart the Cloudflare tunnel and return the new public URL |
| `/agent Fix the typo in README` | Dispatch an agent task — confirms before executing |

The bot prompts for confirmation before any write or restart action, so nothing fires accidentally from your pocket.

---

### Langfuse Observability

Full distributed tracing for every LLM call — latency, token counts, per-request cost, and per-user attribution.

![Langfuse Traces](docs/screenshots/langfuse-traces-list.png)

- Per-request cost in dollars, visible per user and per department
- Model comparison: see exactly what local inference saves vs. the cloud equivalent
- Latency breakdown across every span in the call chain
- Activity audit trail with category filters (chat, wiki, ingest, keys, auth)

---

### Service Controls & API Key Management

The admin control plane lets you start, stop, and restart each service independently, manage your Cloudflare tunnel, and issue scoped API keys — all without SSH.

![Admin Dashboard](docs/screenshots/admin-dashboard-healthy.png)

- **Service controls** — Start/stop/restart Ollama, the proxy, and the tunnel independently. Live PID and URL display.
- **Public URL** — Your current Cloudflare tunnel URL, always visible and ready to paste into Cursor or any other tool.
- **API keys** — Issue per-user keys with department labels for cost attribution. Keys are hashed at rest. Rotate or revoke without restarting the server.

![API Key Created](docs/screenshots/admin-key-created.png)

---

### Agent Chat + Knowledge Wiki

The agent is backed by a structured knowledge base. It reads from and writes to a searchable markdown wiki — so knowledge compounds across sessions instead of vanishing when the chat ends.

- **Agent Chat** — Persistent sessions with full wiki context injection. All configured providers available. Quick-start prompts included.
- **Knowledge Wiki** — Full CRUD markdown wiki with search, tags, and cross-references. AI-maintained.
- **Source Ingestion** — Upload files, paste URLs, or raw text. The AI auto-summarises into structured wiki entries.
- **Wiki Lint** — AI health check that surfaces orphan pages, missing references, and stale content.

---

### Agent Modes

Four gears for how the agent operates.

| Mode | What It Does |
|------|-------------|
| **Background Agent** | Runs continuously. Processes tasks from the queue without a chat window open — submit and forget. |
| **Multi-Agent Swarms** | One coordinator breaks a big task into subtasks, dispatches them to parallel workers (up to `max_concurrent`), and assembles the result. Ideal for large codebases or parallel research. |
| **Self-Resuming Agents** | Saves a full memory snapshot before shutdown and restores it on restart — picks up exactly where it left off without re-explaining the project. |
| **Voice Commands** | Submit base64-encoded audio, get a text transcript back. Supports Whisper API or fully local `openai-whisper` for offline transcription. |

**Agent API**
```
POST   /agent/coordinate                        Run N workers in parallel under one coordinator
POST   /agent/background/tasks                  Submit a task to the background queue
GET    /agent/background/tasks                  List all background tasks (filter by ?status=)
GET    /agent/background/tasks/{task_id}        Get a single task
POST   /agent/voice/transcribe                  Transcribe base64 audio → text
GET    /agent/voice/status                      Check microphone and Whisper availability
```

---

### Automation & Scheduling

Set the agent on a schedule or hook it into your existing event pipeline.

| Feature | What It Does |
|---------|-------------|
| **Scheduled Jobs** | Cron-based schedules for any agent instruction — "run wiki lint every Monday", "summarise open GitHub issues daily". Webhooks can fire jobs immediately via `/trigger`. |
| **Automation Playbooks** | Pre-write a multi-step automation as a named playbook. Each step is an agent instruction. Invoke by name — every step runs in order. Runs are timestamped. |
| **Resource Watchdog** | Point at any URL or file. When content changes (SHA-256 hash comparison), fires your registered callback. No polling loop to write yourself. |

```
POST   /agent/scheduler/jobs                    Create a scheduled job (cron expression)
POST   /agent/scheduler/jobs/{job_id}/trigger   Fire a job immediately (webhook-style)
POST   /agent/playbooks/{id}/run                Start a playbook run
POST   /agent/watchdog/resources                Start watching a URL or file
```

---

### Memory & Context

The agent stays coherent over long tasks and long sessions.

| Feature | What It Does |
|---------|-------------|
| **Session Memory** | Snapshot agent state (history, last plan, last result) to disk. Restart and continue — no external database, no re-explaining. |
| **Smart Context Compression** | Three strategies when history grows too long: **reactive** (drop oldest non-system messages), **micro** (remove duplicates and near-empty messages), **inspect** (stats only, no mutation). |
| **Conversation Surgery** | Remove specific messages by index without wiping the session — cut a bad exchange or an outdated instruction without losing everything else. |

```
POST   /agent/memory/{session_id}/snapshot      Save session state to disk
GET    /agent/memory/{session_id}               Restore saved state
POST   /agent/context/compress                  Compress messages (strategy: reactive|micro|inspect)
POST   /agent/sessions/{id}/snip                Remove messages by index
```

---

### Developer Tooling

| Feature | What It Does |
|---------|-------------|
| **Terminal Panel** | Captures the full rendered terminal buffer via `tmux capture-pane` — interactive prompts, progress bars, coloured output. Not just raw stdout. |
| **Skill Library** | Indexes every `SKILL.md` under `.claude/skills/`. Keyword search across name, description, and content. MCP-hosted skill packs register via the API. |
| **AI Commit Tracking** | Tags every agent git commit with session ID, model, tool, and timestamp as git trailers. Browse attributed commits via `/agent/commits`. |
| **Project Scaffolding** | Three built-in templates (`python-library`, `fastapi-service`, `cli-tool`) plus custom JSON templates. Apply to a directory in one API call. |
| **Browser Automation** | Controls real Chromium via Playwright — navigate, click, fill forms, screenshot, run JavaScript. Graceful stubs when Playwright isn't installed. |
| **Adaptive Permissions** | Infers `read_only`, `read_write`, or `full_access` from the session transcript. Avoids re-asking for actions already authorised. |
| **Token Budget Caps** | Set a max token spend per session. Raises `BudgetExceededError` at the cap. Set `cap=0` for unlimited. |

```
GET    /agent/terminal/snapshot                 Capture current terminal buffer
POST   /agent/terminal/run                      Run a command, capture full output
GET    /agent/skills/search?q=...               Search skills by keyword
GET    /agent/commits?limit=10                  List AI-attributed commits
POST   /agent/scaffolding/apply                 Scaffold a project from a template
POST   /agent/browser/action                    Browser action (navigate|click|fill|screenshot|evaluate)
```

---

## Architecture

```
                        ┌──────────────────────────────┐
                        │    React Dashboard (3000)     │
                        │  Login | Agent Chat | Wiki    │
                        │  Sources | Admin | Providers  │
                        │  Workspaces | Keys | Traces   │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────┴───────────────┐
                        │   FastAPI Backend (8001)      │
                        │   Auth | LLM Engine | CRUD    │
                        │   Providers | Models | Keys   │
                        └──┬────────┬────────┬────────┘
                           │        │        │
                    ┌──────┤  ┌─────┤  ┌─────┤
                    ▼      │  ▼     │  ▼     │
                 MongoDB   │ Ollama │ Cloud  │
                (Storage)  │(Local) │ APIs   │
                           │        │        │
                           │  ┌─────┤  ┌─────┘
                           │  ▼     │  ▼
                           │Langfuse│ Cloudflare
                           │(Trace) │  Tunnel
                           └────────┘
```

**Knowledge architecture — three layers:**

1. **Raw Sources** — Files, URLs, and text ingested and processed by the AI
2. **Wiki** — LLM-maintained structured markdown knowledge base
3. **Agent** — Query, lint, cross-reference, and expand knowledge on demand

---

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

cp .env.example .env   # edit with your settings

docker compose up -d                      # core services
docker compose --profile public up -d     # + Cloudflare tunnel
docker compose --profile full up -d       # + OpenAI proxy for Cursor/Claude Code
```

Open **http://localhost:3000** — the unified dashboard loads immediately.

### Default Credentials

```
Email:    admin@llmwiki.local
Password: WikiAdmin2026!
```

> Change these in `.env` before exposing to the internet.

---

## Connecting External Tools

The proxy speaks the OpenAI API. Any tool that accepts a custom base URL works without modification.

### Cursor IDE
```
Settings → Models → OpenAI API Key:
  API Key:  <from API Keys page>
  Base URL: https://your-tunnel.trycloudflare.com/v1
  Model:    qwen3-coder:30b
```

### Claude Code CLI
```bash
export ANTHROPIC_BASE_URL=https://your-tunnel.trycloudflare.com
export ANTHROPIC_API_KEY=sk-relay-...
claude
```

### Aider
```bash
aider --openai-api-base https://your-tunnel.trycloudflare.com/v1 \
      --openai-api-key sk-relay-...
```

### Continue (VS Code / JetBrains)
```json
{
  "models": [{
    "title": "Local LLM",
    "provider": "openai",
    "model": "qwen3-coder:30b",
    "apiBase": "https://your-tunnel.trycloudflare.com/v1",
    "apiKey": "sk-relay-..."
  }]
}
```

---

## Provider Setup

### Ollama (Local — zero cost)
Runs as a Docker service. Models download on first pull.

```bash
docker exec llm-wiki-ollama ollama pull qwen3-coder:30b
docker exec llm-wiki-ollama ollama pull deepseek-r1:671b
```

### HuggingFace Inference API
**Providers → Add Provider:**
- Type: `OpenAI Compatible`
- Base URL: `https://api-inference.huggingface.co/v1`
- API Key: your HuggingFace token

### OpenRouter
- Base URL: `https://openrouter.ai/api/v1`
- API Key: your OpenRouter key

### Remote Ollama (another machine)
- Type: `Ollama`
- Base URL: `http://192.168.1.100:11434`

---

## Optional Feature Dependencies

All features degrade gracefully — nothing crashes when a dependency isn't installed.

| Feature | Install | Env var |
|---------|---------|---------|
| Browser Automation | `pip install playwright && playwright install chromium` | — |
| Voice (Whisper API) | — | `WHISPER_BASE_URL=http://localhost:9000` |
| Voice (local Whisper) | `pip install openai-whisper` | — |
| Voice recording | `pip install pyaudio` | — |
| Scheduled Jobs | `pip install apscheduler` *(bundled)* | — |

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 3000 | Unified React dashboard |
| **Backend** | 8001 | FastAPI — all API endpoints |
| **Proxy** | 8000 | OpenAI/Anthropic-compatible proxy |
| **MongoDB** | 27017 | Document store |
| **Ollama** | 11434 | Local LLM runtime |
| **Cloudflare Tunnel** | — | Public HTTPS endpoint (optional) |

---

## API Reference

<details>
<summary><strong>Auth</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with email/password |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/me` | Current user |
| POST | `/api/auth/refresh` | Refresh token |

</details>

<details>
<summary><strong>Chat / Agent</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/send` | Send message to agent |
| GET | `/api/chat/sessions` | List sessions |
| GET | `/api/chat/sessions/:id` | Get session |
| DELETE | `/api/chat/sessions/:id` | Delete session |

</details>

<details>
<summary><strong>Wiki</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/wiki/pages` | List/search pages |
| GET | `/api/wiki/pages/:slug` | Get page |
| POST | `/api/wiki/pages` | Create page |
| PUT | `/api/wiki/pages/:slug` | Update page |
| DELETE | `/api/wiki/pages/:slug` | Delete page |
| POST | `/api/wiki/lint` | AI health check |

</details>

<details>
<summary><strong>Sources</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sources/ingest` | Ingest file/URL/text |
| GET | `/api/sources` | List all |
| GET | `/api/sources/:id` | Get with content |
| DELETE | `/api/sources/:id` | Delete |

</details>

<details>
<summary><strong>Providers</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/providers` | List providers |
| POST | `/api/providers` | Add provider |
| PUT | `/api/providers/:id` | Update |
| DELETE | `/api/providers/:id` | Delete |
| POST | `/api/providers/:id/test` | Test connection |

</details>

<details>
<summary><strong>Models</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List all models |
| POST | `/api/models/pull` | Pull Ollama model |
| DELETE | `/api/models/:name` | Delete model |

</details>

<details>
<summary><strong>Keys</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/keys` | List API keys |
| POST | `/api/keys` | Issue key |
| DELETE | `/api/keys/:id` | Revoke key |

</details>

<details>
<summary><strong>System</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health |
| GET | `/api/stats` | Dashboard stats |
| GET | `/api/activity` | Activity log |
| GET | `/api/platform` | Platform info |
| GET | `/api/observability/status` | Langfuse status |

</details>

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Tailwind CSS, React Router, React Markdown, Lucide |
| Backend | Python 3.11, FastAPI, Motor (async MongoDB), PyJWT, bcrypt, httpx |
| Database | MongoDB 7 |
| LLM Runtime | Ollama (local) + any OpenAI-compatible API |
| Observability | Langfuse |
| Tunnel | Cloudflare Tunnel |
| Containers | Docker Compose |

---

## License

Open source. Use it, fork it, ship it.

---

<div align="center">

**If this saves you money or unblocks your workflow, a star helps others find it.**

[![Star this repo](https://img.shields.io/github/stars/strikersam/local-llm-server?style=social)](https://github.com/strikersam/local-llm-server/stargazers)

</div>
