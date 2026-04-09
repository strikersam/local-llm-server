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

## Features

### Core

| Feature | What It Does |
|---------|-------------|
| **Agent Chat** | LLM-powered chat with wiki context. Supports all configured providers. Quick prompts to get started. |
| **Knowledge Wiki** | Full CRUD markdown wiki with search, tags, cross-references. AI-maintained. |
| **Source Ingestion** | Upload files, paste URLs, raw text. AI auto-summarizes into structured knowledge. |
| **Wiki Lint** | AI health check that finds orphan pages, missing refs, stale content. |

### Agent Modes

These control *how* the agent operates — think of them as gears on a gearbox.

| Feature | What It Does |
|---------|-------------|
| **Background Agent** | The agent runs continuously in the background, watching for events. It can listen for GitHub webhooks (new PR, issue comment, push), send you a Telegram notification when something needs attention, and act on its own without you opening a chat window. Think of it as an always-on assistant that never sleeps. |
| **Multi-Agent Swarms** | One coordinator agent breaks a big task into subtasks and hands each one to a worker agent with just the tools it needs. Workers run in parallel, report back, and the coordinator assembles the result. Good for large codebases, parallel research, or anything too big for one agent in one shot. |
| **Self-Resuming Agents** | The agent can pause itself ("I'll check back in 10 minutes"), wait for an external event, and pick up exactly where it left off — without you having to re-explain the task. Useful for long-running builds, deployment waits, or overnight batch jobs. |
| **Voice Commands** | Talk to the agent out loud. A dedicated CLI entrypoint (`llm-relay voice`) captures your microphone, transcribes it, and sends it as a prompt. Hands-free coding while you think. |

### Automation & Scheduling

Set the agent loose on a schedule or hook it into your existing event pipeline.

| Feature | What It Does |
|---------|-------------|
| **Scheduled Jobs** | Create cron-based schedules for any agent task — "run the wiki lint every Monday at 9am", "summarize new GitHub issues daily". List and delete jobs from the dashboard. External webhooks can also fire jobs instantly. |
| **Automation Playbooks** | Pre-write a multi-step automation as a named playbook ("deploy-and-notify", "summarize-and-file"). The agent runs the whole playbook as a single unit — you invoke it by name, it handles the rest. |
| **Resource Watchdog** | Point the watchdog at any URL, file, or service endpoint. When it detects a state change (new data, error response, file modification), it automatically triggers the agent action you defined. No polling loops to write yourself. |

### Remote & Browser Control

Reach your agent from anywhere, and let it reach the web for you.

| Feature | What It Does |
|---------|-------------|
| **Browser Automation** | The agent controls a real browser — clicks buttons, fills forms, navigates pages, takes screenshots. Built on Playwright. This is not URL fetching; it's a full browser the agent can drive interactively. Useful for testing UIs, scraping dynamic pages, or automating web workflows. |
| **Remote Access via SSH** | SSH into your agent session from any machine. A `relay://` URI scheme lets external tools (your IDE, CI runner, another agent) connect directly to a running session without going through a web interface. |

### Memory & Context

The agent stays useful over long tasks and long sessions.

| Feature | What It Does |
|---------|-------------|
| **Session Memory** | The agent saves a snapshot of what it knows and what it was doing before it shuts down. When it restarts, it picks up its memory from disk — no external database needed, no re-explaining the project from scratch. |
| **Smart Context Compression** | When a conversation gets long and starts hitting model limits, three strategies kick in: *reactive* (compress the oldest messages), *micro* (compress just the redundant bits), or *inspect* (show you what's taking up space so you decide). The agent stays coherent across long sessions. |
| **Conversation Surgery** | Remove a specific bad exchange, an outdated instruction, or a confusing tangent from history — without wiping everything. Surgical, not nuclear. |

### Intelligence & Planning

Make the agent think harder before it acts.

| Feature | What It Does |
|---------|-------------|
| **Deep Planning Mode** | Before writing a single line of code, the agent produces a full implementation plan: what to build, in what order, how to verify each step worked. Then it checks the plan itself for gaps before starting. Fewer rabbit holes, fewer half-finished features. |
| **Adaptive Permissions** | The agent reads what it has been doing in the session and adjusts its permission posture automatically. If it's been doing read-only research, it stays in read-only mode. If you've explicitly asked it to write files, it knows it has that permission. No more repetitive "are you sure?" dialogs for things you've already said yes to. |

### Developer Tooling

Utilities that make building on top of LLM Relay easier.

| Feature | What It Does |
|---------|-------------|
| **Full Terminal Visibility** | The agent reads the full rendered terminal buffer — not just raw stdout. It sees interactive prompts, color output, progress bars, and UI elements in the terminal exactly as you would. This means it can respond to programs that ask questions mid-run. |
| **Skill Library** | A local directory of reusable agent skills (like "run tests then summarize failures" or "create PR with changelog"). You can also install MCP-hosted skill packs from the network — they work like plugins. Search skills by name or keyword from the dashboard. |
| **AI Commit Tracking** | Every git commit the agent makes is tagged with the session ID that created it. You can always trace which AI session wrote which code change — useful for audits, rollbacks, and understanding what the agent did while you were away. |
| **Project Scaffolding** | Pre-built project templates the agent uses when you ask it to start a new project. Instead of an empty folder, you get a working skeleton with the right structure for your stack, ready for the agent to build on. |
| **Token Spend Caps** | Set a maximum number of tokens the agent is allowed to spend per session or per sub-agent. When the cap is reached, the agent stops and reports back rather than running up an unexpected bill. Useful for metered cloud backends. |

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
