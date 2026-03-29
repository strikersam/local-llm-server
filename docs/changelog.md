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
- Continue setup is now documented with a recommended YAML config, lean context providers, and proxy settings that avoid prompt stacking.
- The proxy now supports exact-output short-circuiting, streamed exact-output responses, optional `<think>` stripping, and a safer fallback max-token cap.
- The agent loop now cleans sloppy generated file output and rejects incomplete shared-utility changes plus unsafe JWT/auth patterns like hardcoded secrets.

### Notes

- The agent layer is designed for OpenAI-compatible local endpoints and intentionally keeps the code layout flat.
- End-to-end agent quality still depends on the chosen local model, prompt discipline, and available context window.
