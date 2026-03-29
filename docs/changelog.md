# Changelog

## 2026-03-29

### Added

- Local-first coding agent endpoints on top of the existing authenticated proxy.
- Session-based agent runs with conversation history and last-run state.
- Planner, executor, and verifier loop with strict JSON and full-file output contracts.
- Explicit workspace tools for file reads, file listing, repo search, and diff application.
- Optional per-step git commits plus rollback of the latest agent-created commit.
- Test coverage for workspace tools, mocked agent-runner behavior, and agent API failure handling.

### Improved

- README now separates the quick-start story from detailed release notes.
- Agent failures from local model backends are surfaced as structured API responses instead of uncaught exceptions.

### Notes

- The agent layer is designed for OpenAI-compatible local endpoints and intentionally keeps the code layout flat.
- End-to-end agent quality still depends on the chosen local model, prompt discipline, and available context window.
