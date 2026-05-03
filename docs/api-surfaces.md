# API Surfaces and Route Map

This file is the technical companion to the README.
If you want the human-friendly product story, start with [../README.md](../README.md).

---

## Main proxy (`proxy.py`)

### OpenAI-compatible
- `POST /v1/chat/completions`
- `GET /v1/models`
- `POST /v1/messages` (Anthropic-compatible messages)
- passthrough support for additional `/v1/*` routes

### Ollama-compatible
- `/api/*` passthrough for Ollama-native routes such as chat and generate

### Built-in admin and web UI
- `/admin/ui/*`
- `/admin/api/*`
- `/app`
- `/admin/app`
- `/ui/api/*`

### Agent and workflow surfaces
- `/agent/*` — agent sessions, memory, budgets, browser, voice, schedules, playbooks, terminal, skills, commits, scaffolding
- `/v2/agent/coordinate` — multi-agent coordination
- `/workflow/*` — CRISPY workflow engine

### Control-plane style routers mounted in the proxy
- `/api/auth/*`
- `/api/social/*`
- `/api/chat/*`
- `/api/models/*`
- `/api/providers/*`
- `/api/stats`
- `/api/activity`
- `/api/hardware/*`
- `/api/secrets/*`
- `/api/setup/*`
- `/api/observability/*`
- `/api/github/*`
- `/api/sync/*`
- `/api/tasks/*`
- `/api/agents/*`
- `/api/schedules/*`
- `/api/routing/*`
- `/runtimes/*`

---

## Separate hosted dashboard backend (`backend/server.py`)

The `backend/` app powers the separate React control plane and includes routes for:

- auth and social login
- chat sessions
- wiki pages and linting
- source ingestion
- providers and models
- API key management
- observability summaries and metrics
- platform info and activity
- GitHub repo, branch, file, and PR flows
- schedules and legacy scheduler compatibility routes

This backend is typically used with:
- `frontend/` on port `3000`
- `backend/server.py` on port `8001`

---

## Supporting technical docs

- [Feature guide](features.md)
- [Configuration reference](configuration-reference.md)
- [Architecture overview](architecture/overview.md)
- [Model routing guide](model-routing.md)
- [Claude Code setup](claude-code-setup.md)
