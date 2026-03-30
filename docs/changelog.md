# Changelog

<!-- Format: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)          -->
<!-- Versions: MAJOR.MINOR.PATCH — bump MAJOR for breaking changes,            -->
<!--           MINOR for new features, PATCH for fixes.                        -->
<!-- Every commit or merge to master MUST add an entry to [Unreleased]         -->
<!-- or to the appropriate version section before merging.                     -->

## [Unreleased]

## [2.0.0] — 2026-03-30

### Added — Claude Code Compatibility (Critical)
- `POST /v1/messages` endpoint — full Anthropic Messages API compatibility layer
  (`handlers/anthropic_compat.py`). Enables Claude Code CLI, Anthropic SDK, and any
  tool that sets `ANTHROPIC_BASE_URL`.
- `x-api-key` header support in `verify_api_key` — Claude Code's default auth method.
  Both `Authorization: Bearer <key>` and `x-api-key: <key>` now accepted on all routes.
- `MODEL_MAP` environment variable — maps Anthropic model names (`claude-3-5-sonnet-20241022`)
  to local Ollama model names. Built-in defaults included for all Claude 3/4 model names.
- `GET /v1/models` now returns both local Ollama model names AND Claude model name aliases.

### Added — Infrastructure Cost Model
- `infra_cost.py` — real-cost model tracking electricity, amortised hardware, and idle
  overhead. Produces `RequestInfraCost` per request and `SessionCostProjection`.
- `infra_cost.py` is now called from `langfuse_obs.emit_chat_observation` to annotate
  every Langfuse generation with `infra_electricity_usd`, `infra_hardware_usd`, and
  `infra_energy_kwh` alongside the existing commercial-equivalent cost field.

### Added — Observability Enhancements
- `latency_ms` and `ttft_ms` (time-to-first-token) now emitted in every Langfuse trace.
- `tokens_per_sec` derived metric emitted per request.
- All new fields are in the generation `metadata` dict for Langfuse filtering/dashboards.

### Added — Telegram Control Plane
- `telegram_bot.py` — secure Telegram bot for remote command/control.
  Auth by Telegram user ID allowlist. Admin commands require elevated ID.
  High-risk commands (agent runs) require explicit in-chat confirmation.
  See `.env.example` for `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`,
  `TELEGRAM_ADMIN_USER_IDS`.

### Changed — File Organisation
- Agent subsystem (`agent_loop`, `agent_models`, `agent_prompts`, `agent_state`,
  `agent_tools`) moved into `agent/` Python package.
  Old flat files at root are now backward-compat shims (import from `agent.*`).
- `generate_api_key.py` moved to `scripts/generate_api_key.py`.
  Old root file removed.
- `handlers/` package created for request handling modules by API surface.

### Fixed — Critical Configuration
- `PROXY_DEFAULT_MAX_TOKENS` default changed from 1200 → 8192 in `.env.example`.
  1200 tokens truncated virtually every Claude Code code-generation response.

### Documentation
- Architecture review, Claude Code compatibility matrix, AWS Bedrock vs local TCO
  comparison, OpenClaw decision memo, and Telegram control-plane design added to
  repository knowledge base.

---

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
