# LLM Wiki — Self-Hosted Agent Dashboard

> Persistent, compounding knowledge base maintained by AI agents.
> Inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern.

## Overview

LLM Wiki is a **fully self-hosted AI agent dashboard** that implements the three-layer knowledge architecture:

1. **Raw Sources** — Files, URLs, and text ingested and processed by AI
2. **Wiki** — LLM-maintained markdown knowledge base with cross-references
3. **Schema** — Structured data extracted from wiki pages for queries

The dashboard provides a complete web interface for interacting with an AI agent that builds and maintains your personal knowledge wiki.

## Features

- **Agent Chat** — Interactive chat with an LLM agent that has context of your entire wiki. Ask questions, request page creation, analyze sources, run health checks
- **Wiki Browser** — Full CRUD for markdown pages with search, tags, inline editing, and markdown rendering
- **Source Ingestion** — Upload files, paste URLs, or input raw text. The AI processes and summarizes each source
- **Wiki Lint** — AI-powered health check that identifies orphan pages, missing references, stale content, and structural issues
- **Activity Log** — Complete audit trail of all system operations with category filtering
- **Dashboard** — Overview stats, recent pages, and activity feed
- **Multi-Provider LLM** — Supports Ollama (local, default) and any OpenAI-compatible API
- **Authentication** — JWT-based auth with static admin credentials
- **Docker-Ready** — Single `docker-compose up` to run everything

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  Login | Dashboard | Chat | Wiki | Sources | Logs   │
├─────────────────────────────────────────────────────┤
│                  Backend (FastAPI)                   │
│  Auth | Chat/Agent | Wiki CRUD | Ingest | Activity  │
├───────────────┬─────────────────┬───────────────────┤
│   MongoDB     │     Ollama      │  OpenAI-compat    │
│  (Storage)    │  (Local LLMs)   │   (Cloud LLMs)    │
└───────────────┴─────────────────┴───────────────────┘
```

## Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose
- (Optional) NVIDIA GPU + drivers for GPU-accelerated Ollama

### Run

```bash
# Clone the repository
git clone <your-repo-url> llm-wiki
cd llm-wiki

# Start all services
docker compose up -d

# Wait for Ollama to pull the default model (~2-3 min first time)
docker logs -f llm-wiki-ollama-init

# Open the dashboard
open http://localhost:3000
```

### Default Credentials

| Field    | Value                |
|----------|----------------------|
| Email    | admin@llmwiki.local  |
| Password | WikiAdmin2026!       |

### Environment Variables

Create a `.env` file in the project root to customize:

```env
JWT_SECRET=your-random-secret-here
ADMIN_EMAIL=admin@llmwiki.local
ADMIN_PASSWORD=WikiAdmin2026!
```

## Services

| Service        | Port  | Description                        |
|----------------|-------|------------------------------------|
| Frontend       | 3000  | React dashboard (nginx in prod)    |
| Backend        | 8001  | FastAPI API server                 |
| MongoDB        | 27017 | Document store                     |
| Ollama         | 11434 | Local LLM runtime                  |

## API Endpoints

### Authentication
| Method | Endpoint           | Description        |
|--------|--------------------|--------------------|
| POST   | /api/auth/login    | Login with email/password |
| POST   | /api/auth/logout   | Clear auth cookies |
| GET    | /api/auth/me       | Get current user   |
| POST   | /api/auth/refresh  | Refresh access token |

### Chat / Agent
| Method | Endpoint                      | Description           |
|--------|-------------------------------|-----------------------|
| POST   | /api/chat/send                | Send message to agent |
| GET    | /api/chat/sessions            | List chat sessions    |
| GET    | /api/chat/sessions/:id        | Get session with messages |
| DELETE | /api/chat/sessions/:id        | Delete a session      |

### Wiki
| Method | Endpoint                | Description           |
|--------|-------------------------|-----------------------|
| GET    | /api/wiki/pages         | List/search pages     |
| GET    | /api/wiki/pages/:slug   | Get page by slug      |
| POST   | /api/wiki/pages         | Create new page       |
| PUT    | /api/wiki/pages/:slug   | Update page           |
| DELETE | /api/wiki/pages/:slug   | Delete page           |
| POST   | /api/wiki/lint          | Run wiki health check |

### Sources
| Method | Endpoint              | Description             |
|--------|-----------------------|-------------------------|
| POST   | /api/sources/ingest   | Ingest file/URL/text    |
| GET    | /api/sources          | List all sources        |
| GET    | /api/sources/:id      | Get source with content |
| DELETE | /api/sources/:id      | Delete source           |

### System
| Method | Endpoint                 | Description       |
|--------|-------------------------|--------------------|
| GET    | /api/health              | System health      |
| GET    | /api/stats               | Dashboard stats    |
| GET    | /api/activity            | Activity log       |
| GET    | /api/settings/providers  | LLM provider info  |

## LLM Providers

### Ollama (Default — Self-Hosted)
- Runs locally via Docker with GPU support
- Default model: `llama3.2`
- No API keys needed
- Set `LLM_PROVIDER=ollama` in environment

### OpenAI-Compatible (Cloud)
- Works with OpenAI, Anthropic, or any compatible API
- Set `LLM_PROVIDER=emergent` and provide API key
- Useful for testing or when GPU is unavailable

## Without GPU (CPU-only Ollama)

Remove the `deploy` block from the `ollama` service in `docker-compose.yml`:

```yaml
ollama:
  image: ollama/ollama:latest
  # Remove the deploy section for CPU-only mode
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
```

Consider using smaller models for CPU: `ollama pull phi3:mini` or `ollama pull gemma2:2b`

## Tech Stack

- **Frontend**: React 18, Tailwind CSS, React Router, React Markdown, Lucide Icons
- **Backend**: Python 3.11, FastAPI, Motor (async MongoDB), PyJWT, bcrypt, httpx
- **Database**: MongoDB 7
- **LLM Runtime**: Ollama (local) / OpenAI-compatible API (cloud)
- **Containerization**: Docker Compose

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend
```bash
cd frontend
yarn install
REACT_APP_BACKEND_URL=http://localhost:8001 yarn start
```

## Design

Swiss brutalist dark theme with:
- **Background**: Deep black (#0A0A0A) with surface (#141414) and elevated (#1A1A1A) layers
- **Typography**: Chivo (headings) + IBM Plex Mono (body) — terminal-grade readability
- **Accent**: Klein Blue (#002FA7) — distinctive, high-contrast
- **Layout**: Control Room grid — dense, functional, information-first

## Synthesized Concepts

This project synthesizes key ideas from:

1. **Karpathy's LLM Wiki** — Three-layer architecture (sources → wiki → schema), persistent compounding knowledge
2. **Docker Sandboxes** — Isolated, safe execution environments for AI agents
3. **Multi-Agent Patterns** — Simple, focused agent design; avoid over-engineering
4. **Local LLM Running** — GPU-accelerated inference via Ollama
5. **Token Efficiency** — Minimal context, focused prompts, activity tracking

## License

Open source. Use it, fork it, improve it.
