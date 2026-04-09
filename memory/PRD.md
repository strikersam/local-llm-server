# LLM Relay — PRD

## Original Problem Statement
Build a unified self-hosted AI platform (rebranded as "LLM Relay") that replicates Emergent/Lovable/Claude Code features. Single unified dashboard combining admin panel, Langfuse observability, knowledge wiki, model management, provider management. Accessible from one place. Connect to HuggingFace, Ollama cloud, or local models. Based on Karpathy's LLM Wiki gist + synthesized ideas from multiple sources including claw-code patterns.

**Tagline**: Route, run, and control LLMs on your own hardware, not someone else's meter.

## Architecture
- **Frontend**: React 18 + Tailwind CSS, unified dashboard on port 3000
- **Backend**: FastAPI on port 8001, MongoDB, JWT auth
- **LLM**: Multi-provider (Ollama local, OpenAI-compatible, HuggingFace, OpenRouter)
- **Observability**: Langfuse (cloud.langfuse.com)
- **Tunnel**: ngrok for public access
- **Containers**: Docker Compose with profiles (public, full)

## What's Been Implemented

### Phase 1 — MVP (2026-04-09)
- [x] Auth (JWT + cookies), Wiki CRUD, Chat agent, Source ingestion, Activity log

### Phase 2 — Unified Platform (2026-04-09)
- [x] Provider CRUD + test + set default
- [x] Models Hub (Ollama pull/delete + cloud refs)
- [x] API Key management (issue/revoke)
- [x] Observability (Langfuse status + dashboard link)
- [x] Enhanced Dashboard (6 stats, health badges, ngrok badge)
- [x] Docker Compose with ngrok + proxy profiles

### Phase 3 — Rebrand + Polish (2026-04-09)
- [x] Rebranded to "LLM Relay"
- [x] Generated hero image for login
- [x] Fixed CORS for credentialed cookie requests
- [x] Created .env.example (no secrets)
- [x] Updated .gitignore
- [x] Comprehensive README with API docs, provider setup, tool connection guides

## Test Status
- Backend: 100% (21/21)
- Frontend: 100% (12/12 requirements)

## Backlog
### P1
- Real-time chat streaming (SSE)
- Wiki knowledge graph visualization
- Source-to-wiki auto-generation
- Token usage tracking with cost estimates

### P2
- Multi-user accounts
- Dark/light theme toggle
- Vector search with embeddings
- Telegram bot integration
- Code workspace panel (Claude Code-style file editor + terminal)
