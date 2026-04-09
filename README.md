# LLM Wiki — Self-Hosted Unified AI Platform

> A self-hosted, open-source alternative to Emergent/Lovable/Claude Code with a unified dashboard.
> Persistent, compounding knowledge base maintained by AI agents.
> Inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern.

## What Is This?

LLM Wiki is a **fully self-hosted AI agent platform** that gives you everything you do in Emergent, Claude Code, or Lovable — but on your own infrastructure, for free. One unified dashboard to manage:

- **AI Agent Chat** with wiki-aware context
- **Knowledge Wiki** (markdown-based, AI-maintained)
- **Source Ingestion** (files, URLs, text)
- **LLM Provider Management** (Ollama local, HuggingFace, OpenRouter, any OpenAI-compat API)
- **Model Management** (pull/delete Ollama models)
- **API Key Management** (issue keys for Cursor, Claude Code, Aider)
- **Observability** (Langfuse integration for cost/usage tracking)
- **Public Access** (ngrok tunnel for sharing)

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Unified React Dashboard                       │
│  Dashboard │ Chat │ Wiki │ Sources │ Providers │ Models │ Keys   │
├──────────────────────────────────────────────────────────────────┤
│                     FastAPI Backend (8001)                        │
│  Auth │ Chat │ Wiki CRUD │ Ingest │ Providers │ Models │ Keys    │
├──────────────┬──────────────┬─────────────┬──────────────────────┤
│   MongoDB    │   Ollama     │  Cloud APIs  │    Langfuse          │
│  (Storage)   │ (Local LLM)  │ (HF/OpenAI) │  (Observability)     │
├──────────────┴──────────────┴─────────────┴──────────────────────┤
│          ngrok / Cloudflare Tunnel (Public Access)                │
└──────────────────────────────────────────────────────────────────┘
```

Three-layer knowledge architecture (Karpathy pattern):
1. **Raw Sources** → Files, URLs, text ingested and AI-processed
2. **Wiki** → LLM-maintained markdown knowledge base with cross-references
3. **Agent** → Query, lint, cross-reference, and expand the knowledge base

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

# Copy and edit environment
cp .env.example .env
# Edit .env with your settings

# Start all services
docker compose up -d

# With public access (ngrok)
docker compose --profile public up -d

# With full proxy (Claude Code/Cursor/Aider compatibility)
docker compose --profile full up -d

# Open dashboard
open http://localhost:3000
```

### Default Credentials

| Field    | Value                |
|----------|----------------------|
| Email    | admin@llmwiki.local  |
| Password | WikiAdmin2026!       |

## Features

### Core
| Feature | Description |
|---------|-------------|
| Agent Chat | LLM-powered chat with wiki context. Supports all configured providers |
| Wiki Browser | Full CRUD, markdown rendering, search, tags, interlinking |
| Source Ingestion | Upload files, paste URLs, raw text. AI summarizes automatically |
| Wiki Lint | AI health check — finds orphans, missing refs, stale content |
| Activity Log | Complete audit trail with category filtering |

### Infrastructure
| Feature | Description |
|---------|-------------|
| Providers | Add/configure/test LLM providers. Set default. Supports Ollama, HuggingFace, OpenRouter, any OpenAI-compat API |
| Models Hub | List local Ollama models, pull new ones, delete unused. See cloud model references |
| API Keys | Issue/revoke API keys for external tools (Cursor, Claude Code, Aider) |

### System
| Feature | Description |
|---------|-------------|
| Observability | Langfuse integration — token usage, cost tracking, latency, user attribution |
| Health Dashboard | Real-time status for MongoDB, Ollama, Langfuse |
| ngrok Integration | One-click public access via ngrok tunnel |

## LLM Provider Setup

### Ollama (Local — Default for Self-Hosted)
```bash
# Ollama runs as a Docker service automatically
# Models are pulled via the dashboard or CLI
docker exec llm-wiki-ollama ollama pull llama3.2
docker exec llm-wiki-ollama ollama pull qwen3-coder:30b
```

### HuggingFace Inference API
1. Get API token from https://huggingface.co/settings/tokens
2. Go to **Providers** → **Add Provider**
3. Set:
   - Type: OpenAI Compatible
   - Base URL: `https://api-inference.huggingface.co/v1`
   - API Key: your HuggingFace token
   - Default Model: e.g., `meta-llama/Llama-3.2-3B-Instruct`

### OpenRouter
1. Get API key from https://openrouter.ai/keys
2. Add provider with Base URL: `https://openrouter.ai/api/v1`

### Local Ollama (Remote Machine)
1. Add provider with Base URL: `http://your-machine-ip:11434`
2. No API key needed

## Public Access (ngrok)

```bash
# Set in .env
NGROK_AUTHTOKEN=your-token
NGROK_DOMAIN=your-domain.ngrok-free.dev

# Start with ngrok profile
docker compose --profile public up -d
```

Your dashboard is now accessible at `https://your-domain.ngrok-free.dev`

## Connecting External Tools

### Cursor IDE
```
Settings → Models → OpenAI API Key section:
  API Key: (issue from API Keys page)
  Base URL: https://your-domain.ngrok-free.dev/v1
  Model: qwen3-coder:30b
```

### Claude Code CLI
```bash
export ANTHROPIC_BASE_URL=https://your-domain.ngrok-free.dev
export ANTHROPIC_API_KEY=sk-wiki-...  # from API Keys page
claude
```

### Aider
```bash
aider --openai-api-base https://your-domain.ngrok-free.dev/v1 \
      --openai-api-key sk-wiki-...
```

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Login |
| POST | /api/auth/logout | Logout |
| GET | /api/auth/me | Current user |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/chat/send | Send message to agent |
| GET | /api/chat/sessions | List sessions |
| GET | /api/chat/sessions/:id | Get session |
| DELETE | /api/chat/sessions/:id | Delete session |

### Wiki
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/wiki/pages | List/search pages |
| GET | /api/wiki/pages/:slug | Get page |
| POST | /api/wiki/pages | Create page |
| PUT | /api/wiki/pages/:slug | Update page |
| DELETE | /api/wiki/pages/:slug | Delete page |
| POST | /api/wiki/lint | Run health check |

### Sources
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/sources/ingest | Ingest file/URL/text |
| GET | /api/sources | List sources |
| GET | /api/sources/:id | Get source |
| DELETE | /api/sources/:id | Delete source |

### Providers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/providers | List providers |
| POST | /api/providers | Add provider |
| PUT | /api/providers/:id | Update provider |
| DELETE | /api/providers/:id | Delete provider |
| POST | /api/providers/:id/test | Test connection |

### Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/models | List all models |
| POST | /api/models/pull | Pull Ollama model |
| DELETE | /api/models/:name | Delete model |

### Keys
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/keys | List API keys |
| POST | /api/keys | Issue new key |
| DELETE | /api/keys/:id | Revoke key |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | System health |
| GET | /api/stats | Dashboard stats |
| GET | /api/activity | Activity log |
| GET | /api/platform | Platform info |
| GET | /api/observability/status | Langfuse status |

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Unified React dashboard |
| Backend | 8001 | FastAPI API server |
| Proxy | 8000 | OpenAI/Anthropic-compat proxy (for Cursor/Claude Code) |
| MongoDB | 27017 | Document store |
| Ollama | 11434 | Local LLM runtime |
| ngrok | — | Public tunnel (optional) |

## Tech Stack

- **Frontend**: React 18, Tailwind CSS, React Router, React Markdown, Lucide Icons
- **Backend**: Python 3.11, FastAPI, Motor (async MongoDB), PyJWT, bcrypt, httpx
- **Database**: MongoDB 7
- **LLM Runtime**: Ollama (local) / Any OpenAI-compatible API (cloud)
- **Observability**: Langfuse
- **Tunnel**: ngrok
- **Containerization**: Docker Compose

## Synthesized From

| Resource | Key Idea |
|----------|----------|
| [Karpathy LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | Three-layer knowledge architecture |
| [Docker Sandboxes](https://www.docker.com/blog/docker-sandboxes-run-agents-in-yolo-mode-safely/) | Isolated agent execution |
| [Multi-Agent AI](https://www.infoworld.com/article/4154335/multi-agent-ai-is-the-new-microservices.html) | Simple, focused agent design |
| [Claw Code](https://github.com/ultraworkers/claw-code) | CLI agent patterns, session management |
| [Claude Code Token Analyzer](https://gist.github.com/kieranklaassen/7b2ebb39cbbb78cc2831497605d76cc6) | Usage tracking best practices |

## License

Open source. Use it, fork it, improve it.
