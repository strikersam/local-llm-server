# Changelog

<!-- Format: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)          -->
<!-- Versions: MAJOR.MINOR.PATCH — bump MAJOR for breaking changes,            -->
<!--           MINOR for new features, PATCH for fixes.                        -->
<!-- Every commit or merge to master MUST add an entry to [Unreleased]         -->
<!-- or to the appropriate version section before merging.                     -->

## [Unreleased]

### Added
- `download_models.ps1` — one-command model pull to `D:\aipc-models`. Supports three
  modes: default coding stack (`qwen3-coder:30b` + `deepseek-r1:32b`, ~36 GB),
  `-Lightweight` (7B tier, ~10 GB), and `-IncludeFlagship` (also pulls `deepseek-r1:671b`).
  Checks free disk space, resolves the Ollama binary from `.env`, and prints a
  ready-to-paste `.env` snippet on completion.
- `download_models.ps1 -Extended` — pulls `frob/minimax-m2.5:230b-a10b-q4_K_M` (138 GB),
  the only model from the MiMo-V2-Pro / Step 3.5 Flash / DeepSeek V3.2 / MiniMax M2.x /
  GLM-5 Turbo set that has local GGUF weights available via Ollama today (2026-03-31).
- `download_models.ps1 -CloudProxy` — pulls Ollama cloud-proxy stubs for
  `deepseek-v3.2:cloud`, `minimax-m2.7:cloud`, and `glm-5:cloud`. These route requests
  to vendor APIs; no weights are stored locally — vendor API keys are required.
- `commercial_equivalent.py`: added 2026 equivalence entries for `frob/minimax-m2.5`,
  `deepseek-v3.2:cloud`, `minimax-m2.7:cloud`, and `glm-5:cloud` with vendor API pricing.
- `.env.example`: documented `MODEL_MAP` entries for the new extended and cloud-proxy
  models; added availability notes for MiMo-V2-Pro (proprietary) and Step 3.5 Flash
  (open-source Apache 2.0 but not yet in Ollama — HuggingFace GGUF download path noted).

### Documentation (complete rewrite — v2.2 docs initiative)
- `README.md`: full rewrite — added documentation navigation table, new model tables
  (extended local + cloud-proxy + not-yet-available), cleaner architecture diagram,
  updated quick start with `-Extended` and `-CloudProxy` flags, concise client setup
  section, full repo structure. MiniMax acknowledgement added.
- `docs/claude-code-setup.md` (new): end-to-end guide for using Claude Code CLI and
  the Anthropic Python SDK against local models. Covers architecture, prerequisites,
  env var setup, model name mapping table and customisation, required proxy config,
  context window limitations, step-by-step verification, common failure cases.
- `docs/telegram-bot.md` (new): complete Telegram bot setup guide. Covers @BotFather
  bot creation, @userinfobot ID lookup, `.env` config, authorization model (two tiers),
  full command reference with example output, approval workflow, rate limiting,
  security considerations, running as a service (Windows Task Scheduler + Linux
  systemd), and a list of missing screenshots to capture.
- `docs/admin-dashboard.md` (new): section-by-section dashboard walkthrough. Covers
  login modes (Windows credentials vs secret), service controls (stack + per-service
  with expected/abnormal states), public URL display, key management (create/rotate/
  delete), department summary chips, Langfuse diagnostic, remote admin frontend
  (Vercel), and admin API reference. Screenshots inventory included.
- `docs/features.md` (new): structured reference for all 16 implemented features.
  For each: what it does, why it exists, how to enable/configure, limitations.
  Covers OpenAI proxy, Ollama passthrough, Anthropic compat, key management, rate
  limiting, system prompt injection, think-tag stripping, infra cost tracking,
  commercial savings estimation, Langfuse, agent API, admin UI, Telegram, tunnel,
  CORS, streaming.
- `docs/langfuse-observability.md` (new): complete observability guide. Covers setup,
  full trace structure with all metadata fields, field-by-field explanations (perf,
  savings, infra cost), exact cost formulas with worked example, Langfuse dashboard
  navigation (traces view, department filtering, cost dashboard, performance trends),
  custom pricing JSON format, what is NOT traced, and four instrumentation gap
  recommendations with specific fixes.
- `docs/configuration-reference.md` (new): exhaustive `.env` reference — every variable
  in every section (auth, server, proxy behavior, Anthropic compat, agent, Langfuse,
  infra cost, Telegram, model storage). Includes preset examples for Intel AI PC,
  RTX 4090, and Mac Studio, and four ready-to-paste minimal config blocks.
- `docs/troubleshooting.md` (new): structured troubleshooting guide organized by
  problem domain: startup failures (proxy, Ollama, tunnel), auth issues (401/403/429),
  model issues (not found, truncation, think tags, slow responses, eviction), Claude
  Code specifics, admin dashboard, Langfuse, Telegram, agent API, network/tunnel,
  and performance. Each section includes diagnostic commands and fix table.

### Changed
- `handlers/anthropic_compat.py`: added `claude-opus-4-6`, `claude-sonnet-4-6`, and
  `claude-haiku-4-5-20251001` to `_BUILTIN_MODEL_MAP` (Claude 4.6 model IDs released
  post-August 2025).
- `commercial_equivalent.py`: updated 2026 equivalence map — `qwen3-coder:30b` now
  references Claude Sonnet 4.6 class ($3/$15 per M tokens); `deepseek-r1:32b`/`:671b`
  retain DeepSeek R1 API pricing ($0.55/$2.19); added `qwen3-coder:7b` (Haiku class)
  and `qwen2.5-coder:32b` (GPT-4.1-mini class).
- `.env.example`: `OLLAMA_MODELS` default changed from `D:\ai-models` → `D:\aipc-models`
  (matches actual configured path). `MODEL_MAP` example extended to include Claude 4.6
  model IDs (`claude-sonnet-4-6`, `claude-opus-4-6`, `claude-haiku-4-5-20251001`).
- `README.md`: Models section rewritten with 2026 open-vs-closed equivalence table and
  "default coding stack" framing. Quick Start step 4 updated to lead with
  `download_models.ps1` and corrected model storage path to `D:\aipc-models`.

## [2.0.1] — 2026-03-31

### Fixed
- Live `.env`: `PROXY_DEFAULT_MAX_TOKENS` corrected from `1200` to `8192`. The old value
  truncated virtually every Claude Code code-generation response.
- Live `.env`: Added missing `AGENT_PLANNER_MODEL`, `AGENT_EXECUTOR_MODEL`,
  `AGENT_VERIFIER_MODEL`, `CORS_ORIGINS`, `ADMIN_WINDOWS_AUTH` explicitly so runtime
  configuration is self-documenting and not silently depending on code defaults.
- Live `.env`: Added `INFRA_*` defaults calibrated for Intel AI PC (Arc iGPU: 40W active,
  8W idle, 25W system overhead) so infrastructure cost model runs out of the box.

### Changed
- `generate_api_key.py` (root) converted to a backward-compat shim delegating to
  `scripts/generate_api_key.py`. Old invocation path still works.
- `tests/test_agent_runner.py` and `tests/test_agent_tools.py`: updated imports from
  flat shims (`agent_loop`, `agent_tools`) to canonical package paths (`agent.loop`,
  `agent.tools`). All 12 tests pass.

### Chores
- `.gitignore`: added `.claude/` to exclude Claude Code session state from version control.

---

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
