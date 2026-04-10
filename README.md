# LLM Relay

> **Route, run, and control LLMs on your own hardware, not someone else's meter.**

A self-hosted, open-source AI platform that gives you everything Emergent, Lovable, and Claude Code offer — on your infrastructure, with zero vendor lock-in.

![LLM Relay Dashboard](https://static.prod-images.emergentagent.com/jobs/6bf7aa0e-927a-4851-95e4-78f9c580e21a/images/6d1e1a17e7631bc5783700099b8bd99b3256c85b7d78807597ae8cea63ae6ad4.png)

---

## What Is LLM Relay?

LLM Relay is a **unified dashboard** that replaces the patchwork of tools you're juggling today. One interface to:

- **Route** requests to any LLM — local Ollama, HuggingFace, OpenRouter, or any OpenAI-compatible API
- **Run** an AI agent that builds a compounding knowledge wiki (Karpathy's LLM Wiki pattern)
- **Control** who accesses what — API key management, Langfuse observability, activity audit trail

No subscriptions. No metered API calls on someone else's bill. Your hardware, your data, your rules.

---

## What's New

19 new capabilities drawn from the Claude Code architecture analysis — all implemented, tested, and live on this server.

### Agent Modes

| Feature | What It Does |
|---------|-------------|
| **Background Agent** | The agent runs continuously in the background, watching for events. It can listen for webhooks, process tasks from a queue, and act without you opening a chat window. Think of it as an always-on assistant that never sleeps. |
| **Multi-Agent Swarms** | One coordinator agent breaks a big task into subtasks and hands each to a worker agent with just the tools it needs. Workers run in parallel, report back, and the coordinator assembles the result. Good for large codebases or anything too big for one agent in one shot. |
| **Self-Resuming Agents** | The agent saves a memory snapshot before it shuts down and reloads it on restart — picking up exactly where it left off without you re-explaining the project. No external database needed. |
| **Voice Commands** | Submit audio to the agent and get a text transcript back. Supports a Whisper-compatible REST endpoint or local `openai-whisper`. Degrades to stub mode gracefully when neither is available. |

### Automation & Scheduling

| Feature | What It Does |
|---------|-------------|
| **Scheduled Jobs** | Create cron-based schedules for any agent instruction — "run wiki lint every Monday at 9 am". Jobs track last-run time and run count. External webhooks can fire any job immediately via `/trigger`. |
| **Automation Playbooks** | Pre-write a multi-step automation as a named playbook. Each step is an agent instruction. Invoke the whole playbook by name and it runs every step in order. Track runs with start/finish timestamps. |
| **Resource Watchdog** | Point the watchdog at any URL or file. When the content hash changes, the registered callback fires so you can trigger agent actions or send notifications. No polling loops to write yourself. |

### Memory & Context

| Feature | What It Does |
|---------|-------------|
| **Session Memory** | Save a snapshot of the agent's current session to disk and restore it on restart. History, last plan, and last result all come back — no re-explaining the project from scratch. |
| **Smart Context Compression** | Three strategies when conversation history gets too long: **reactive** (drop oldest non-system messages), **micro** (remove duplicates and near-empty messages), **inspect** (return token stats without modifying anything). |
| **Conversation Surgery** | Remove specific messages from session history by index without wiping everything. Cuts out a bad exchange or outdated instruction without a full reset. |

### Intelligence & Planning

| Feature | What It Does |
|---------|-------------|
| **Adaptive Permissions** | Analyses the session transcript and infers the appropriate permission level: read-only, read-write, or full-access. The agent uses this to avoid asking for approval on things the session has already authorised. |
| **Token Spend Caps** | Set a maximum token budget per session. When the total hits the cap a `BudgetExceededError` is raised and the agent stops rather than running up an unexpected bill. |

### Developer Tooling

| Feature | What It Does |
|---------|-------------|
| **Terminal Panel** | Captures the full rendered terminal buffer via `tmux capture-pane` — not just raw stdout. The agent sees interactive prompts, progress bars, and coloured output exactly as you would. |
| **Skill Library** | Automatically indexes every `SKILL.md` under `.claude/skills/`. Supports keyword search across name, description, and content. MCP-hosted skill packs can be registered via API and are searchable alongside local skills. |
| **AI Commit Tracking** | Every commit the agent makes is tagged with `Agent-Session`, `Agent-Model`, `Agent-Tool`, and `Agent-Timestamp` git trailers. Browse attributed commits at `GET /agent/commits` to trace which AI session wrote which change. |
| **Project Scaffolding** | Three built-in project templates (`python-library`, `fastapi-service`, `cli-tool`) plus support for custom JSON templates. Apply a template to any directory in one API call. |
| **Browser Automation** | Controls a real Chromium browser via Playwright — navigate pages, click, fill forms, take screenshots, evaluate JavaScript. Runs in stub mode when Playwright is not installed. |

---

## Features

### Core

| Feature | What It Does |
|---------|-------------|
| **Agent Chat** | LLM-powered chat with wiki context. Supports all configured providers. Quick prompts to get started. |
| **Knowledge Wiki** | Full CRUD markdown wiki with search, tags, cross-references. AI-maintained. |
| **Source Ingestion** | Upload files, paste URLs, raw text. AI auto-summarizes into structured knowledge. |
| **Wiki Lint** | AI health check that finds orphan pages, missing refs, stale content. |

---

### Agent Modes

These control *how* the agent operates — think of them as gears on a gearbox.

| Feature | What It Does |
|---------|-------------|
| **Background Agent** | The agent runs continuously in the background, watching for events. It processes tasks from webhooks, the scheduler, and the watchdog without you opening a chat window. Submit a task to the queue and the agent handles it whenever the worker is free. |
| **Multi-Agent Swarms** | One coordinator agent breaks a big task into subtasks and hands each one to a worker agent. Workers run in parallel (up to `max_concurrent`), report back, and the coordinator assembles the result. Good for large codebases, parallel research, or anything too big for one agent in one shot. |
| **Self-Resuming Agents** | The agent saves a memory snapshot before it shuts down and reloads it on restart — picking up exactly where it left off without you having to re-explain the project. Pairs with `POST /agent/memory/{session_id}/snapshot`. |
| **Voice Commands** | Submit base64-encoded audio to the agent and get a text transcript back. Supports a Whisper-compatible REST API (`WHISPER_BASE_URL` env var) or local `openai-whisper` for fully offline transcription. |

**API — Agent Modes**

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

Set the agent loose on a schedule or hook it into your existing event pipeline.

| Feature | What It Does |
|---------|-------------|
| **Scheduled Jobs** | Create cron-based schedules for any agent instruction — "run wiki lint every Monday at 9 am", "summarise open GitHub issues daily". Jobs store their last-run timestamp and run count. External webhooks can fire jobs immediately via `/trigger`. |
| **Automation Playbooks** | Pre-write a multi-step automation as a named playbook. Each step is an agent instruction. Invoke the whole playbook by name and it runs every step in order. Track runs with start/finish timestamps. |
| **Resource Watchdog** | Point the watchdog at any URL or file. When it detects a content change (via SHA-256 hash comparison), it fires your registered callback. No polling loops to write yourself — just register and start. |

**API — Automation**

```
POST   /agent/scheduler/jobs                    Create a scheduled job (cron expression)
GET    /agent/scheduler/jobs                    List all jobs
GET    /agent/scheduler/jobs/{job_id}           Get a job
POST   /agent/scheduler/jobs/{job_id}/trigger   Fire a job immediately (webhook-style)
DELETE /agent/scheduler/jobs/{job_id}           Delete a job

POST   /agent/playbooks                         Register a playbook
GET    /agent/playbooks                         List playbooks (filter by ?tag=)
GET    /agent/playbooks/{id}                    Get a playbook
DELETE /agent/playbooks/{id}                    Delete a playbook
POST   /agent/playbooks/{id}/run                Start a playbook run
GET    /agent/playbooks/{id}/runs               List runs for a playbook

POST   /agent/watchdog/resources                Start watching a URL or file
GET    /agent/watchdog/resources                List watched resources
DELETE /agent/watchdog/resources/{id}           Stop watching
POST   /agent/watchdog/resources/{id}/check     Check a resource right now
```

---

### Memory & Context

The agent stays useful over long tasks and long sessions.

| Feature | What It Does |
|---------|-------------|
| **Session Memory** | Save a snapshot of the agent's current session state to disk. On restart the agent restores its history, last plan, and result from the snapshot — no external database needed, no re-explaining the project from scratch. |
| **Smart Context Compression** | Three strategies when conversation history gets too long: **reactive** (drop oldest non-system messages until under the token threshold), **micro** (remove exact duplicates and near-empty messages), **inspect** (return statistics without modifying anything). |
| **Conversation Surgery** | Remove specific messages from session history by index without wiping everything. Good for cutting out a bad exchange, an outdated instruction, or a confusing tangent. |

**API — Memory & Context**

```
POST   /agent/memory/{session_id}/snapshot      Save session state to disk
GET    /agent/memory/{session_id}               Restore saved state
GET    /agent/memory                            List all snapshots
DELETE /agent/memory/{session_id}               Delete a snapshot

POST   /agent/context/compress                  Compress messages (strategy: reactive|micro|inspect)
POST   /agent/context/inspect                   Get token stats for a message list

POST   /agent/sessions/{id}/snip                Remove messages by index from session history
```

---

### Intelligence & Planning

Make the agent think harder before it acts.

| Feature | What It Does |
|---------|-------------|
| **Adaptive Permissions** | Analyses the session transcript and infers the appropriate permission level: `read_only`, `read_write`, or `full_access`. Signals include write-intent words (create, edit, commit) and risky words (sudo, exec, destroy). The agent can use this to avoid asking for approval on actions the session has already authorised. |
| **Token Spend Caps** | Set a maximum token budget per session. Record prompt and completion token counts; when the total reaches the cap a `BudgetExceededError` is raised. Set `cap=0` for unlimited. Useful for metered cloud backends. |

**API — Intelligence**

```
GET    /agent/sessions/{id}/permissions         Infer permission level from session history
PUT    /agent/budget/{session_id}               Set a token cap  {"cap": 50000}
GET    /agent/budget/{session_id}               Get current usage and remaining budget
GET    /agent/budget                            List all session budgets
```

---

### Developer Tooling

Utilities that make building on top of LLM Relay easier.

| Feature | What It Does |
|---------|-------------|
| **Terminal Panel** | Captures the full rendered terminal buffer via `tmux capture-pane`, or falls back to running a command and capturing stdout+stderr. The agent can read interactive prompts, progress bars, and coloured output — not just raw stdout. |
| **Skill Library** | Automatically indexes every `SKILL.md` found under `.claude/skills/`. Supports keyword search across name, description, and full content. MCP-hosted skill packs can be registered via the API and are searchable alongside local skills. |
| **AI Commit Tracking** | Every git commit the agent makes can be tagged with `Agent-Session`, `Agent-Model`, `Agent-Tool`, and `Agent-Timestamp` git trailers. Browse attributed commits via `/agent/commits` to trace which AI session wrote which change. |
| **Project Scaffolding** | Three built-in project templates (`python-library`, `fastapi-service`, `cli-tool`) plus support for loading custom templates from JSON files. Apply a template to a directory in one API call. |
| **Browser Automation** | Controls a real Chromium browser via Playwright. Navigate pages, click, fill forms, take screenshots, evaluate JavaScript. Install Playwright to activate; runs in stub mode (graceful failures) when not installed. |

**API — Dev Tooling**

```
GET    /agent/terminal/snapshot                 Capture current terminal buffer
POST   /agent/terminal/run                      Run a command and capture full output

GET    /agent/skills                            List skills (filter by ?source=local|mcp)
GET    /agent/skills/search?q=...               Search skills by keyword
POST   /agent/skills/mcp                        Register an MCP-hosted skill

GET    /agent/commits?limit=10                  List recent AI-attributed commits

GET    /agent/scaffolding/templates             List available project templates
POST   /agent/scaffolding/apply                 Scaffold a new project from a template

POST   /agent/browser/start                     Start a browser session
POST   /agent/browser/stop                      Stop the browser session
POST   /agent/browser/action                    Execute a browser action (navigate|click|fill|screenshot|evaluate|get_state)
```

---

### Infrastructure

| Feature | What It Does |
|---------|-------------|
| **Providers** | Add/configure/test LLM backends. Switch between local Ollama, HuggingFace, OpenRouter, custom endpoints. Set a default with one click. |
| **Models Hub** | Pull/delete Ollama models. View cloud model references. One-line model downloads. |
| **API Keys** | Issue/revoke API keys for external tools — Cursor, Claude Code, Aider, Continue. Hashed storage. |

### System

| Feature | What It Does |
|---------|-------------|
| **Observability** | Langfuse integration — token usage, cost tracking, latency metrics, per-user attribution. |
| **Activity Log** | Complete audit trail with category filtering (chat, wiki, ingest, provider, keys, auth). |
| **Health Dashboard** | Real-time status for MongoDB, Ollama, Langfuse. ngrok domain display. |

---

## Architecture

```
                        ┌──────────────────────────────┐
                        │    React Dashboard (3000)     │
                        │  Login | Dashboard | Chat     │
                        │  Wiki | Sources | Providers   │
                        │  Models | Keys | Observability│
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
                           │Langfuse│ ngrok
                           │(Trace) │(Tunnel)
                           └────────┘
```

Three-layer knowledge architecture (Karpathy LLM Wiki pattern):

1. **Raw Sources** — Files, URLs, text ingested and AI-processed
2. **Wiki** — LLM-maintained markdown knowledge base
3. **Agent** — Query, lint, cross-reference, expand

---

## Quick Start

### Docker Compose (recommended)

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

cp .env.example .env   # edit with your settings

docker compose up -d                      # core services
docker compose --profile public up -d     # + ngrok tunnel
docker compose --profile full up -d       # + proxy for Cursor/Claude Code
```

Open **http://localhost:3000** and log in.

### Default Credentials

```
Email:    admin@llmwiki.local
Password: WikiAdmin2026!
```

Change these in `.env` before deploying publicly.

---

## Optional Feature Dependencies

Some features require additional packages. All degrade gracefully when not installed.

| Feature | Install command | Env var |
|---------|-----------------|---------|
| Browser Automation | `pip install playwright && playwright install chromium` | — |
| Voice (Whisper API) | — | `WHISPER_BASE_URL=http://localhost:9000` |
| Voice (local Whisper) | `pip install openai-whisper` | — |
| Voice recording | `pip install pyaudio` | — |
| Scheduled Jobs (cron) | `pip install apscheduler` *(bundled)* | — |

---

## Provider Setup

### Ollama (Local — zero cost)
Runs as a Docker service. Models auto-downloaded.

```bash
# Pull additional models via dashboard or CLI
docker exec llm-wiki-ollama ollama pull qwen3-coder:30b
docker exec llm-wiki-ollama ollama pull deepseek-r1:32b
```

### HuggingFace Inference API
Go to **Providers** → **Add Provider**:
- Type: OpenAI Compatible
- Base URL: `https://api-inference.huggingface.co/v1`
- API Key: your HuggingFace token
- Model: `meta-llama/Llama-3.2-3B-Instruct`

### OpenRouter
- Base URL: `https://openrouter.ai/api/v1`
- API Key: your OpenRouter key

### Remote Ollama (another machine)
- Type: Ollama
- Base URL: `http://192.168.1.100:11434`

---

## Connecting External Tools

### Cursor IDE
```
Settings → Models → OpenAI API Key:
  API Key: <from API Keys page>
  Base URL: https://your-domain.ngrok-free.dev/v1
  Model: qwen3-coder:30b
```

### Claude Code CLI
```bash
export ANTHROPIC_BASE_URL=https://your-domain.ngrok-free.dev
export ANTHROPIC_API_KEY=sk-relay-...
claude
```

### Aider
```bash
aider --openai-api-base https://your-domain.ngrok-free.dev/v1 \
      --openai-api-key sk-relay-...
```

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 3000 | Unified React dashboard |
| **Backend** | 8001 | FastAPI API server |
| **Proxy** | 8000 | OpenAI/Anthropic-compat proxy (Cursor/Claude Code) |
| **MongoDB** | 27017 | Document store |
| **Ollama** | 11434 | Local LLM runtime |
| **ngrok** | — | Public tunnel (optional) |

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
| POST | `/api/chat/send` | Send message to wiki agent |
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
| LLM Runtime | Ollama (local) / Any OpenAI-compatible API |
| Observability | Langfuse |
| Tunnel | ngrok |
| Containers | Docker Compose |

## Synthesized From

| Source | Key Pattern Adopted |
|--------|-------------------|
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Three-layer knowledge architecture |
| [Docker Sandboxes](https://www.docker.com/blog/docker-sandboxes-run-agents-in-yolo-mode-safely/) | Isolated, safe agent execution |
| [Multi-Agent AI](https://www.infoworld.com/article/4154335/multi-agent-ai-is-the-new-microservices.html) | Simple agent design, avoid over-engineering |
| [Claw Code](https://github.com/ultraworkers/claw-code) | CLI agent patterns, session management, provider routing |
| [Claude Code Token Analyzer](https://gist.github.com/kieranklaassen/7b2ebb39cbbb78cc2831497605d76cc6) | Usage tracking, cost awareness |

---

## License

Open source. Use it, fork it, ship it.
