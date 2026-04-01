# Changelog

<!-- Format: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)          -->
<!-- Versions: MAJOR.MINOR.PATCH — bump MAJOR for breaking changes,            -->
<!--           MINOR for new features, PATCH for fixes.                        -->
<!-- Every commit or merge to master MUST add an entry to [Unreleased]         -->
<!-- or to the appropriate version section before merging.                     -->

## [Unreleased]

### Security

- `README.md`: removed hardcoded tunnel domain from documentation; use `NGROK_DOMAIN`
  and placeholders instead.

### Added — Repo-native AI engineering system retrofit

- **`CLAUDE.md`** — root operating guide for Claude: codebase map, key commands, coding
  rules, testing expectations, changelog rule, skill-to-situation mapping table, and
  pointers to all deeper docs. Local `CLAUDE.md` files added to `agent/` and `router/`
  (risky modules).

- **`AGENTS.md` + `TOOLS.md`** — workspace context files for agentic tools (OpenClaw,
  Claude Code). Describes agent roles, state file locations, and available tool manifest.

- **`.claude/skills/`** — 11 reusable repo-specific skills: `implementation-planner`,
  `test-first-executor`, `changelog-enforcer`, `council-review`, `risky-module-review`,
  `release-readiness`, `docs-sync`, `cooldown-resume`, `dependency-audit`,
  `repo-memory-updater`, and `modularity-review` (inspired by Vlad Khononov's
  balanced-coupling model).

- **`.claude/hooks/`** — three blocking git hooks activated via
  `git config core.hooksPath .claude/hooks`:
  - `pre-commit`: blocks `.env`/`keys.json` commits, hardcoded `SECRET_KEY`, Python syntax errors
  - `commit-msg`: rejects commits with code changes but no `docs/changelog.md` staged
  - `pre-push`: runs `pytest -x` before any push

- **`.claude/agents/`** — persona definitions for Planner, Implementer, Reviewer, and
  Judge agents used by the orchestration layer.

- **`.claude/commands/`** — slash-command definitions: `/plan`, `/review`, `/resume`.

- **`.claude/state/`** — durable checkpoint system: `agent-state.json` (machine-readable
  full session state), `NEXT_ACTION.md` (human-readable resume guide), `checkpoint.jsonl`
  (append-only completed-step log).

- **`scripts/ai_runner.py`** — auto-resume watchdog. Starts named Claude Code sessions,
  detects rate-limit/cooldown/token-exhaustion patterns, retries with exponential backoff
  (60s→120s→240s→480s→960s), resumes from last checkpoint with idempotency guarantees.
  Provides `start`, `status`, `resume`, `stop`, `logs`, `summary`, `manifest`, `audit`,
  `changelog-check`, and `test-resume` commands.

- **`Makefile`** — developer command surface: `make test`, `make test-fast`, `make lint`,
  `make hooks-install`, `make changelog-check`, `make ai-start/status/resume/stop/logs`,
  `make manifest/summary/audit`.

- **`.github/workflows/ci.yml`** — GitHub Actions CI: pytest + Python syntax check +
  hardcoded-secret scan on every push and PR.

- **`.github/workflows/changelog-check.yml`** — blocks PR merge if `docs/changelog.md`
  has no `[Unreleased]` content (exempt prefixes: `chore:`, `docs:`, `ci:`, `test:`).

- **`.github/PULL_REQUEST_TEMPLATE.md`** — structured PR template with testing,
  changelog, risky-module, and council-review checklists.

- **`.github/CODEOWNERS`** — code ownership for auth, key store, agent tools, routing,
  and CI config paths.

- **`docs/architecture/overview.md`** — full system architecture: component map,
  multi-agent flow diagram, observability, deployment modes.

- **`docs/architecture/agent-orchestration.md`** — four-agent design: plan-first pathway,
  tool loop, execution pathway, review pathway, release-readiness pathway.

- **`docs/runbooks/auto-resume.md`** — how auto-resume works, where state lives, how to
  inspect stuck runs, force-resume, abort, and simulation proof.

- **`docs/runbooks/release.md`** — step-by-step release procedure with rollback plan.

- **`docs/runbooks/openclaw-setup.md`** — OpenClaw installation, workspace linking, and
  shared-vs-personal memory separation.

- **`docs/adrs/001-local-llm-proxy.md`** — ADR: self-hosted OpenAI-compatible proxy.
- **`docs/adrs/002-model-routing.md`** — ADR: dynamic model routing with task classification.
- **`docs/adrs/003-multi-agent-orchestration.md`** — ADR: plan-execute-verify loop design.

- **`docs/admin/github-branch-protection.md`** — exact GitHub branch protection settings
  required to make CI and changelog checks mandatory merge gates.

### Changed

- **`.gitignore`** — replaced blanket `.claude/` exclusion with targeted exclusions for
  ephemeral Claude Code session files only; project-level AI engineering files in `.claude/`
  are now tracked.

- **`.githooks/prepare-commit-msg`** — updated to reference the new `.claude/hooks/`
  path and clarify that it is soft-reminder only; the blocking version is in `.claude/hooks/commit-msg`.

### Fixed

- `proxy.py`: allow `ADMIN_SECRET` as a Bearer token for admin API routes (useful for
  bot/API clients).

---

## [2.3.0] — 2026-03-31

### Added — Dynamic model routing + health check + fallback execution

- **`router/` package** — centralized model routing system with `ModelRouter`,
  `RoutingDecision`, task `classifier`, model capability `registry`, and Ollama
  `health` check.  Every chat and agent request now flows through a single routing
  layer instead of scattered per-handler logic.

- **`RoutingDecision` dataclass** — immutable record of every routing event:
  `resolved_model`, `requested_model`, `mode` (`auto`/`manual`), `routing_reason`,
  `task_category`, `selection_source`, `fallback_chain`, `provider`.

- **Automatic task classification** (`router/classifier.py`) — lightweight regex
  heuristics, no LLM call.  Categories: `code_generation`, `code_debugging`,
  `code_review`, `reasoning`, `tool_use`, `long_context`, `fast_response`,
  `conversation`.

- **`fast_response` category** — short streaming requests (< 200 chars combined,
  no code keywords) are routed to the lightest registered model (`qwen3-coder:7b`,
  `cost_tier=1`).  Threshold via `ROUTER_FAST_RESPONSE_CHARS` (default `200`).

- **Model capability registry** (`router/registry.py`) — declarative registry with
  built-in entries for `qwen3-coder:30b`, `deepseek-r1:32b`, `deepseek-r1:671b`,
  `qwen3-coder:7b`.  Extend at runtime via `ROUTER_EXTRA_MODELS` env var
  (`model_name:type:strength1+strength2`, comma-separated) without code changes.

- **Manual model override** — any client, any IDE, any API format can force a
  specific model via the `X-Model-Override` HTTP header.  Recorded as `mode=manual`
  in all Langfuse traces.  Response includes `X-Routing-Mode` and `X-Routing-Model`
  headers.

- **Ollama health check** (`router/health.py`) — queries `/api/tags` with 2 s
  timeout; caches for 60 s (`ROUTER_HEALTH_CACHE_TTL`).  Router skips unavailable
  models and walks `fallback_chain` automatically.  Silently degrades if Ollama is
  unreachable.  Disable with `ROUTER_HEALTH_CHECK_ENABLED=false`.

- **Fallback execution** — non-streaming paths on all three API surfaces
  (`/v1/messages`, `/v1/chat/completions`, `/api/chat`) retry with the next model
  in `fallback_chain` on Ollama 5xx.  Health cache is invalidated before each
  retry.  Streaming paths fail fast (mid-stream buffering is unsafe).

- **Routing metadata in Langfuse** — `emit_chat_observation()` gains optional
  `routing_meta: dict | None`.  Every generation now includes `routing_mode`,
  `routing_requested_model`, `routing_resolved_model`, `routing_reason`,
  `routing_task_category`, `routing_selection_source`, `routing_fallback_chain`,
  `routing_provider`.

- **`tests/test_model_router.py`** — 40 unit tests covering manual override,
  MODEL_MAP translation, local model passthrough, heuristic routing, task
  classification, `fast_response` routing, health check enable/disable, fallback
  on unavailable model, `ROUTER_EXTRA_MODELS` extension, `to_meta()` fields,
  singleton behaviour.

- **`docs/model-routing.md`** — complete reference: automatic selection logic,
  manual override, health check, fallback execution, `fast_response` config,
  Langfuse fields, architecture diagram, limitations.

### Changed

- `handlers/anthropic_compat.py` — replaced inline `get_local_model()` + dict
  lookup with `get_router().route()`; `X-Model-Override` header support; fallback
  retry on 5xx.  `get_local_model()` kept as backwards-compatible shim.
- `chat_handlers.py` — OpenAI and Ollama native handlers route through
  `ModelRouter`, carry `routing_meta` to Langfuse, retry on 5xx via
  `_post_with_fallback()`.
- `agent/loop.py` — planner, executor, and verifier model selection flows through
  `ModelRouter` per phase (`agent_plan`, `agent_execute`, `agent_verify`).
- `langfuse_obs.py` — `emit_chat_observation()` gains optional `routing_meta`
  parameter (fully backwards-compatible).
- `.env.example` — routing section added: `ROUTER_EXTRA_MODELS`, corrected 3-part
  format docs, `ROUTER_HEALTH_CHECK_ENABLED`, `ROUTER_HEALTH_CACHE_TTL`,
  `ROUTER_FAST_RESPONSE_CHARS`.

---

## [2.2.1] — 2026-03-31

### Added
- `docs/screenshots/` (new directory — 12 screenshots): live browser screenshots
  of the admin UI (login, dashboard, key-creation flash, Langfuse diagnostic,
  tunnel URL) and representative mockups for Langfuse (traces list, trace detail
  with all metadata fields, cost analysis dashboard) and Telegram bot (full command
  exchange: /status, /cost, /models, /restart, /agent with approval workflow).
  Captured with Playwright headless Chromium.
- `scripts/gen_screenshots.py`: Playwright script that regenerates all mockup
  screenshots from HTML templates — run after UI changes to keep docs in sync.

### Changed
- `README.md`: screenshot gallery table added (admin dashboard, Langfuse traces,
  cost dashboard, Telegram bot). Screenshots wired into `admin-dashboard.md`,
  `langfuse-observability.md`, and `telegram-bot.md` with captions and
  field-level interpretation.

---

## [2.2.0] — 2026-03-31

### Added — Complete documentation overhaul

- `docs/claude-code-setup.md` — end-to-end guide for Claude Code CLI and the
  Anthropic Python SDK against local models. Covers architecture, prerequisites,
  env var setup, model name mapping table and customisation, required proxy config,
  context window limitations, step-by-step verification, common failure cases.
- `docs/telegram-bot.md` — complete Telegram bot setup guide: @BotFather creation,
  @userinfobot ID lookup, `.env` config, authorization model (two tiers), full
  command reference with example output, approval workflow, rate limiting, security
  considerations, running as a service (Windows Task Scheduler + Linux systemd).
- `docs/admin-dashboard.md` — section-by-section dashboard walkthrough: login
  modes, service controls, public URL display, key management (create/rotate/delete),
  department summary chips, Langfuse diagnostic, remote admin frontend, admin API
  reference.
- `docs/features.md` — structured reference for all 16 implemented features (what,
  why, how to enable, limitations). Covers OpenAI proxy, Ollama passthrough,
  Anthropic compat, key management, rate limiting, system prompt injection,
  think-tag stripping, infra cost tracking, commercial savings estimation, Langfuse,
  agent API, admin UI, Telegram, tunnel, CORS, streaming.
- `docs/langfuse-observability.md` — complete observability guide: setup, full
  trace structure, field-by-field explanations (perf, savings, infra cost), exact
  cost formulas with worked example, Langfuse dashboard navigation, custom pricing
  JSON format, what is NOT traced, four instrumentation gap recommendations.
- `docs/configuration-reference.md` — exhaustive `.env` reference (every variable
  in every section). Preset examples for Intel AI PC, RTX 4090, Mac Studio, and
  four ready-to-paste minimal config blocks.
- `docs/troubleshooting.md` — structured troubleshooting guide by domain: startup
  failures, auth (401/403/429), model issues (not found, truncation, think tags,
  slow responses, eviction), Claude Code specifics, admin dashboard, Langfuse,
  Telegram, agent API, network/tunnel, performance.

### Changed
- `README.md` — full rewrite: documentation navigation table, new model tables
  (extended local + cloud-proxy + not-yet-available), cleaner architecture diagram,
  updated quick start, concise client setup section, full repo structure. MiniMax
  acknowledgement added.
- `commercial_equivalent.py` — updated 2026 equivalence map: `qwen3-coder:30b`
  references Claude Sonnet 4.6 class ($3/$15 per M tokens); `deepseek-r1:32b`/`:671b`
  retain DeepSeek R1 API pricing ($0.55/$2.19); added `qwen3-coder:7b` (Haiku
  class) and `qwen2.5-coder:32b` (GPT-4.1-mini class).

---

## [2.1.0] — 2026-03-31

### Added
- `download_models.ps1` — one-command model pull to `D:\aipc-models`. Three modes:
  default coding stack (`qwen3-coder:30b` + `deepseek-r1:32b`, ~36 GB),
  `-Lightweight` (7B tier, ~10 GB), `-IncludeFlagship` (adds `deepseek-r1:671b`).
  Checks free disk space, resolves Ollama binary from `.env`, prints a
  ready-to-paste `.env` snippet on completion.
- `download_models.ps1 -Extended` — pulls `frob/minimax-m2.5:230b-a10b-q4_K_M`
  (138 GB), the only model from the MiMo-V2-Pro / Step 3.5 Flash / DeepSeek V3.2 /
  MiniMax M2.x / GLM-5 Turbo set with local GGUF weights available in Ollama today.
- `download_models.ps1 -CloudProxy` — pulls Ollama cloud-proxy stubs for
  `deepseek-v3.2:cloud`, `minimax-m2.7:cloud`, and `glm-5:cloud`. No local weights;
  vendor API keys required.
- `commercial_equivalent.py` — 2026 equivalence entries for `frob/minimax-m2.5`,
  `deepseek-v3.2:cloud`, `minimax-m2.7:cloud`, `glm-5:cloud` with vendor pricing.

### Changed
- `handlers/anthropic_compat.py` — added `claude-opus-4-6`, `claude-sonnet-4-6`,
  `claude-haiku-4-5-20251001` to `_BUILTIN_MODEL_MAP` (Claude 4.6 model IDs).
- `.env.example` — `OLLAMA_MODELS` default updated to `D:\aipc-models`; `MODEL_MAP`
  example extended with Claude 4.6 IDs and notes on extended / cloud-proxy / not-yet-
  available models (MiMo-V2-Pro proprietary, Step 3.5 Flash HuggingFace path noted).

---

## [2.0.1] — 2026-03-31

### Fixed
- Live `.env`: `PROXY_DEFAULT_MAX_TOKENS` corrected from `1200` to `8192`. The old
  value truncated virtually every Claude Code code-generation response.
- Live `.env`: Added missing `AGENT_PLANNER_MODEL`, `AGENT_EXECUTOR_MODEL`,
  `AGENT_VERIFIER_MODEL`, `CORS_ORIGINS`, `ADMIN_WINDOWS_AUTH` explicitly so
  runtime configuration is self-documenting.
- Live `.env`: Added `INFRA_*` defaults calibrated for Intel AI PC (Arc iGPU:
  40 W active, 8 W idle, 25 W system) so the infrastructure cost model runs
  out of the box.

### Changed
- `generate_api_key.py` (root) converted to a backward-compat shim delegating to
  `scripts/generate_api_key.py`. Old invocation path still works.
- `tests/test_agent_runner.py` and `tests/test_agent_tools.py`: updated imports
  from flat shims to canonical package paths (`agent.loop`, `agent.tools`). All
  tests pass.

### Chores
- `.gitignore`: added `.claude/` to exclude Claude Code session state.

---

## [2.0.0] — 2026-03-30

### Added — Claude Code Compatibility
- `POST /v1/messages` — full Anthropic Messages API compatibility layer
  (`handlers/anthropic_compat.py`). Enables Claude Code CLI, Anthropic SDK, any
  tool that sets `ANTHROPIC_BASE_URL`.
- `x-api-key` header support — Claude Code's default auth method. Both
  `Authorization: Bearer <key>` and `x-api-key: <key>` accepted on all routes.
- `MODEL_MAP` env var — maps Anthropic model names to local Ollama model names.
  Built-in defaults for all Claude 3/4 model names.
- `GET /v1/models` returns both local Ollama names and Claude name aliases.

### Added — Infrastructure Cost Model
- `infra_cost.py` — real-cost model (electricity + amortised hardware + idle
  overhead). Produces `RequestInfraCost` per request and `SessionCostProjection`.
- `langfuse_obs.emit_chat_observation` annotates every generation with
  `infra_electricity_usd`, `infra_hardware_usd`, `infra_energy_kwh`.

### Added — Observability Enhancements
- `latency_ms`, `ttft_ms`, `tokens_per_sec` emitted in every Langfuse trace.

### Added — Telegram Control Plane
- `telegram_bot.py` — secure Telegram bot for remote command/control. Auth by
  user ID allowlist; admin commands require elevated ID; high-risk commands require
  explicit in-chat confirmation.

### Changed — File Organisation
- Agent subsystem moved into `agent/` Python package. Old flat files are
  backward-compat shims.
- `generate_api_key.py` moved to `scripts/generate_api_key.py`.
- `handlers/` package created for request handling modules.

### Fixed
- `PROXY_DEFAULT_MAX_TOKENS` default changed 1200 → 8192 in `.env.example`.

---

## [1.x] — 2026-03-29 and earlier

### Added
- Local-first coding agent endpoints (session-based, planner/executor/verifier
  loop, workspace tools, optional git commits).
- Admin UI and key management.
- Langfuse observability integration.
- Rate limiting, CORS, think-tag stripping, exact-output short-circuit.
- Continue and Cursor IDE setup documentation.
- Device compatibility guide (Intel AI PC, Mac Studio, RTX 4090).
