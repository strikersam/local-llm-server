# Changelog

## [Unreleased]

### Added
- **Local AI Stack (Docker):** Added `docker/local-ai-stack/` with a full Docker Compose setup including Ollama (local LLM runner), Open WebUI (chat interface), ChromaDB (vector DB for RAG), and optional N8N automation — enabling a fully self-hosted, privacy-first AI stack inspired by the XDA Developers local AI guide.
- **`local-ai-query` skill:** New Claude skill (`/.claude/skills/local-ai-query/SKILL.md`) for routing prompts to a locally running Ollama instance — useful for sensitive code, offline work, or cost-conscious tasks.
- **Health check script:** `scripts/local-ai-health-check.sh` — verifies all local AI stack services are running.
- **Model pull script:** `scripts/pull-ai-models.sh` — automates pulling curated Ollama models (minimal and full sets).
