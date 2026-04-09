# LLM Wiki Platform — PRD

## Original Problem Statement
Build a unified self-hosted AI platform replicating Emergent/Lovable/Claude Code features. Single UI that combines: Admin panel, Langfuse dashboard, LLM Wiki dashboard, model management, provider management. Accessible from one place with no chaos. Connect to HuggingFace, Ollama cloud, or local models. Based on Karpathy's LLM Wiki gist + synthesized ideas from Docker sandboxes, multi-agent AI, claw-code patterns.

## User Choices
- LLM Backend: Both Ollama (default with Llama) + OpenAI-compatible
- Features: All — Chat, Wiki, Sources, Activity, Agent mode, Providers, Models, Keys, Observability
- Docker: Single docker-compose.yml with ngrok profile
- UI: Unified platform, killer design, Swiss brutalist dark theme
- Auth: Static admin credentials
- Langfuse: Configured with user's keys
- ngrok: User has existing setup, refined in docker-compose

## Architecture
- **Backend**: FastAPI on port 8001, MongoDB, JWT auth, multi-provider LLM
- **Frontend**: React 18, Tailwind CSS, Lucide Icons — unified dashboard
- **Providers**: Ollama (local), OpenAI-compatible (cloud), HuggingFace, OpenRouter
- **Observability**: Langfuse (cloud.langfuse.com)
- **Tunnel**: ngrok for public access
- **Containerization**: Docker Compose with profiles (public, full)

## Core Requirements (Static)
1. Unified dashboard — single entry point for all features
2. Agent Chat with wiki-aware context
3. Wiki Browser with full CRUD, markdown, search, tags
4. Source Ingestion with AI summarization
5. Provider Management (CRUD, test, set default)
6. Models Hub (Ollama pull/delete, cloud references)
7. API Key Management (issue/revoke for Cursor/Claude Code/Aider)
8. Observability (Langfuse status + dashboard link)
9. Activity Log with category filtering
10. Docker-compose with ngrok for public access

## What's Been Implemented

### Phase 1 (2026-04-09) — MVP
- [x] Full FastAPI backend with all endpoints
- [x] JWT auth with cookie-based sessions
- [x] LLM integration via emergentintegrations
- [x] Wiki CRUD with full-text search
- [x] Chat agent with wiki context
- [x] Source ingestion with AI summarization
- [x] Activity log, Dashboard

### Phase 2 (2026-04-09) — Unified Platform
- [x] Provider Management (CRUD + test + set default)
- [x] Models Hub (list/pull/delete Ollama + cloud references)
- [x] API Key Management (issue/revoke with hashed secrets)
- [x] Observability (Langfuse connection status + dashboard link)
- [x] Enhanced Dashboard (6 stat cards, health badges, ngrok domain)
- [x] Unified sidebar with 3 sections (Core, Infrastructure, System)
- [x] Docker Compose with ngrok profile
- [x] Comprehensive README with full API docs, provider setup, tool connection guides
- [x] CORS fix for credentialed requests

## Test Status
- Backend: 100% (27/27 tests)
- Frontend: 85%+ (all core flows working)

## Backlog
### P1
- Real-time chat streaming (SSE)
- Wiki page interlinking graph
- Source-to-wiki auto-generation
- Provider health polling
- Token usage tracking per session

### P2
- Multi-user accounts
- Dark/light theme toggle
- Export wiki as static site
- Webhook integrations
- Vector search with embeddings
- Telegram bot integration (existing code)
