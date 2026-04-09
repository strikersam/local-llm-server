# LLM Wiki Dashboard — PRD

## Original Problem Statement
Build a complete setup based on Karpathy's LLM Wiki gist, synthesizing ideas from multiple resources about multi-agent AI, Docker sandboxes, local LLM running, and coding agents. Implement a high-quality UI/dashboard running in Docker, fully self-hosted with no paid infrastructure, with a dashboard experience for managing everything.

## User Choices
- LLM Backend: Both Ollama (default with Llama) + OpenAI-compatible API
- Features: All — Chat, Wiki, Sources, Activity, Agent mode
- Docker: Single docker-compose.yml bundling everything
- UI: Killer, standout redesign with Swiss brutalist dark theme
- Auth: Static admin credentials

## Architecture
- **Backend**: FastAPI on port 8001, MongoDB, JWT auth, emergentintegrations for cloud LLM
- **Frontend**: React 18, Tailwind CSS, React Router, React Markdown, Lucide Icons
- **Database**: MongoDB
- **LLM**: Ollama (local/self-hosted) or OpenAI-compatible (cloud demo)
- **Containerization**: Docker Compose (MongoDB + Ollama + Backend + Frontend)

## Core Requirements
1. Agent Chat with LLM (wiki-aware context)
2. Wiki Browser with full CRUD, markdown rendering, search, tags
3. Source Ingestion (file, URL, text) with AI summarization
4. Wiki Lint (AI health check)
5. Activity Log with category filtering
6. Dashboard with stats overview
7. Multi-provider LLM (Ollama + OpenAI-compatible)
8. JWT auth with static admin credentials
9. Docker-compose for self-hosting

## What's Been Implemented (2026-04-09)
- [x] Full FastAPI backend with all endpoints
- [x] JWT auth with cookie-based sessions
- [x] LLM integration via emergentintegrations (cloud) and Ollama (local)
- [x] Wiki CRUD with full-text search, tags, markdown
- [x] Wiki lint (AI-powered health check)
- [x] Source ingestion with AI summarization (file, URL, text)
- [x] Chat agent with wiki context
- [x] Activity log with category filtering
- [x] Dashboard with stats, recent pages, activity feed
- [x] Settings page with health status and provider info
- [x] Swiss brutalist dark theme (Chivo + IBM Plex Mono)
- [x] Docker Compose (MongoDB + Ollama + Backend + Frontend)
- [x] Comprehensive README with API docs, setup guide
- [x] Static admin credentials seeded on startup

## Backlog
### P0 (Critical)
- All P0 features implemented

### P1 (Important)
- Wiki page interlinking/graph visualization
- Real-time chat streaming (SSE)
- Source-to-wiki page auto-generation
- Token usage tracking per session

### P2 (Nice to Have)
- Multiple user accounts
- API key management UI
- Dark/light theme toggle
- Export wiki as static site
- Webhook integrations
- Full-text search with vector embeddings

## Test Status
- Backend: 100% (21/21 tests passed)
- Frontend: 95%+ (all core flows working)
- Integration: 100% (LLM chat fully working)

## Credentials
- Email: admin@llmwiki.local
- Password: WikiAdmin2026!
