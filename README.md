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
