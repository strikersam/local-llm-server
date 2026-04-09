<div align="center">

# LLM Relay

**Self-hosted AI platform — run frontier models on your own hardware, route to any provider, and control everything from one unified dashboard.**

[![Stars](https://img.shields.io/github/stars/strikersam/local-llm-server?style=flat-square&color=yellow)](https://github.com/strikersam/local-llm-server/stargazers)
[![Forks](https://img.shields.io/github/forks/strikersam/local-llm-server?style=flat-square&color=blue)](https://github.com/strikersam/local-llm-server/network)
[![License](https://img.shields.io/badge/license-Open%20Source-green?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://www.docker.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev/)

*Drop-in OpenAI-compatible proxy. Point Cursor, Claude Code, Aider, or Continue at it and everything just works. Your hardware. Your data. Zero API bills.*

</div>

---

![LLM Relay Login](docs/screenshots/app-login.png)

---

## One platform. Every AI tool you need.

LLM Relay is not just a proxy. It is a complete AI operations platform built around a dark, keyboard-friendly dashboard that lives at `http://localhost:3000`. Everything is in one place:

- **Agent Chat** backed by a persistent knowledge wiki
- **Knowledge Wiki** — searchable, tagged, AI-maintained markdown pages
- **Source Ingestion** — drop files, URLs, or raw text; AI summarises into the wiki
- **Multi-provider routing** — Ollama, OpenRouter, HuggingFace, any OpenAI-compatible API
- **Models Hub** — pull and manage Ollama models without touching a terminal
- **API Key management** — issue scoped keys per user and department
- **Langfuse observability** — token usage, cost, latency, per-user attribution
- **Telegram bot** — control everything from your phone
- **OpenAI-compatible proxy** — plug in Cursor, Claude Code, Aider, Continue

---

## The Dashboard Tour

### Control Room

The landing page after login. Every number is clickable — it drills into the relevant section.

![Control Room](docs/screenshots/app-dashboard.png)

Six live stats (wiki pages, chat sessions, ingested sources, providers, API keys, activity events), a real-time activity feed colour-coded by category, recently updated wiki pages, and a health bar showing MongoDB, Ollama, and Langfuse status at a glance.

---

### Agent Chat

![Agent Chat](docs/screenshots/app-chat.png)

A full chat interface connected to your wiki knowledge base. Sessions are persistent and listed in the sidebar. Quick-prompt buttons get you started immediately:

- *What's in my wiki?*
- *Create a new page about...*
- *Analyze this source...*
- *Run wiki lint*

The agent has context of your entire wiki on every message. Responses are rendered as markdown with syntax highlighting.

---

### Knowledge Wiki

![Knowledge Wiki](docs/screenshots/app-wiki.png)

A searchable, tagged markdown wiki. The left sidebar lists every page with its tags — click to read, edit, or delete. The **NEW PAGE** button opens an inline editor. The lint button runs an AI health check that flags orphan pages, missing cross-references, and stale content.

---

### Source Ingestion

![Source Ingestion](docs/screenshots/app-sources.png)

Three ingestion modes in one panel: drag-and-drop **FILE**, paste a **URL**, or type/paste raw **TEXT**. The AI processes each source and produces a structured wiki entry. The source list tracks everything you've ingested so the agent can always trace where its knowledge came from.

---

### Providers

![Providers](docs/screenshots/app-providers.png)

Add any LLM backend from this single screen. Local Ollama, OpenRouter, HuggingFace, or any OpenAI-compatible endpoint. Hit **TEST** to verify the connection before using it. Star a provider to make it the default for all chat and agent calls.

---

### API Keys

![API Keys](docs/screenshots/app-keys.png)

Issue scoped API keys per user with department labels for cost attribution in Langfuse. Keys are hashed at rest — the plaintext is shown once at creation. One-click revocation, no server restart needed. Use these keys in Cursor, Claude Code, Aider, or Continue.

---

### Observability

![Observability](docs/screenshots/app-observability.png)

Built-in Langfuse integration. The dashboard shows connection status and links directly to your Langfuse project. Every LLM call is traced automatically — token usage, cost-equivalent savings vs. commercial APIs, latency, and per-user attribution.

The actual cost data speaks for itself:

![Langfuse Cost Analysis](docs/screenshots/langfuse-cost-dashboard.png)

> **96.7% cost reduction** — $0.19 actual (electricity) vs $12.84 commercial-equivalent across 1,842 requests.

---

### Telegram Bot Control

Control your entire stack from your phone. No browser, no VPN.

![Telegram Bot](docs/screenshots/telegram-bot-commands.png)

| Command | What it does |
|---------|-------------|
| `/status` | Health of Ollama, proxy, and tunnel + models loaded |
| `/cost` | Real-time electricity estimate and hardware amortisation |
| `/models` | All loaded models with size |
| `/restart tunnel` | Restart Cloudflare tunnel, returns new public URL |
| `/agent <task>` | Dispatch an agent task — confirms before running |

---

## Why Not Just Use Bare Ollama?

| | LLM Relay | Bare Ollama | Paid API |
|---|---|---|---|
| Unified dashboard | ✅ | ❌ | ❌ |
| Agent chat + wiki | ✅ | ❌ | ❌ |
| Multi-provider routing | ✅ | ❌ | ❌ |
| Source ingestion | ✅ | ❌ | ❌ |
| Cost tracking | ✅ | ❌ | ✅ |
| Telegram bot | ✅ | ❌ | ❌ |
| Per-user API keys | ✅ | ❌ | ✅ |
| Zero ongoing cost | ✅ | ✅ | ❌ |
| Zero vendor lock-in | ✅ | ✅ | ❌ |

---

## Quick Start

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

cp .env.example .env   # edit with your settings

docker compose up -d                      # core services
docker compose --profile public up -d     # + Cloudflare tunnel
docker compose --profile full up -d       # + OpenAI proxy for external tools
```

Open **http://localhost:3000** and log in.

```
Email:    admin@llmwiki.local
Password: WikiAdmin2026!
```

> Change these in `.env` before exposing to the internet.

---

## Connecting Your AI Tools

The proxy at port 8000 speaks the OpenAI API. Any tool with a configurable base URL works without modification.

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
```bash
docker exec llm-wiki-ollama ollama pull qwen3-coder:30b
docker exec llm-wiki-ollama ollama pull deepseek-r1:671b
```

### OpenRouter
- Base URL: `https://openrouter.ai/api/v1`
- API Key: your OpenRouter key

### HuggingFace Inference API
- Base URL: `https://api-inference.huggingface.co/v1`
- API Key: your HuggingFace token

### Remote Ollama (another machine)
- Type: `Ollama`
- Base URL: `http://192.168.1.100:11434`

---

## Agent Capabilities

Beyond basic chat, the agent supports advanced modes accessible via the REST API:

| Mode | Description |
|------|-------------|
| **Multi-Agent Swarms** | One coordinator breaks a task into subtasks and runs them on parallel workers. |
| **Background Tasks** | Submit tasks to a queue; the agent processes them without a chat window open. |
| **Self-Resuming Sessions** | Snapshots agent state to disk — resumes exactly where it left off after restart. |
| **Automation Playbooks** | Pre-written multi-step automations invoked by name. |
| **Scheduled Jobs** | Cron-based agent instructions — "run wiki lint every Monday at 9 am". |
| **Resource Watchdog** | Watch a URL or file; fires a callback when content changes. |
| **Browser Automation** | Controls real Chromium via Playwright for navigate, click, screenshot, evaluate. |
| **Voice Transcription** | Submit base64 audio; get text back via Whisper API or local openai-whisper. |
| **Token Budget Caps** | Set max token spend per session; raises BudgetExceededError at the cap. |

---

## Optional Feature Dependencies

All features degrade gracefully when dependencies are absent.

| Feature | Install | Env var |
|---------|---------|---------|
| Browser Automation | `pip install playwright && playwright install chromium` | — |
| Voice (Whisper API) | — | `WHISPER_BASE_URL=http://localhost:9000` |
| Voice (local Whisper) | `pip install openai-whisper` | — |
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
| DELETE | `/api/sources/:id` | Delete |

</details>

<details>
<summary><strong>Providers & Models</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/providers` | List providers |
| POST | `/api/providers` | Add provider |
| PUT | `/api/providers/:id` | Update |
| DELETE | `/api/providers/:id` | Delete |
| POST | `/api/providers/:id/test` | Test connection |
| GET | `/api/models` | List all models |
| POST | `/api/models/pull` | Pull Ollama model |
| DELETE | `/api/models/:name` | Delete model |

</details>

<details>
<summary><strong>Keys & System</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/keys` | List API keys |
| POST | `/api/keys` | Issue key |
| DELETE | `/api/keys/:id` | Revoke key |
| GET | `/api/health` | System health |
| GET | `/api/stats` | Dashboard stats |
| GET | `/api/activity` | Activity log |
| GET | `/api/observability/status` | Langfuse status |

</details>

<details>
<summary><strong>Agent — Advanced</strong></summary>

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/coordinate` | Multi-agent swarm |
| POST | `/agent/background/tasks` | Submit background task |
| GET | `/agent/background/tasks` | List tasks |
| POST | `/agent/memory/:session/snapshot` | Save session state |
| GET | `/agent/memory/:session` | Restore session state |
| POST | `/agent/context/compress` | Compress message history |
| POST | `/agent/scheduler/jobs` | Create scheduled job |
| POST | `/agent/playbooks/:id/run` | Run automation playbook |
| POST | `/agent/watchdog/resources` | Watch a URL or file |
| POST | `/agent/browser/action` | Browser automation action |
| POST | `/agent/voice/transcribe` | Transcribe audio |
| GET | `/agent/budget/:session` | Token budget status |

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
