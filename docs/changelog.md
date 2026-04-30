# Changelog

## [Unreleased]

### Changed
- `.github/workflows/process-quick-note.yml` — replaced Anthropic/Groq API routing with free NVIDIA NIM auto-selection; model is now chosen by task complexity mirroring `router/classifier.py` tiers: reasoning/planning → Nemotron Ultra 253B, data analysis/math → DeepSeek R1, code generation → Qwen2.5 Coder 32B, fast/simple → Llama 3.1 8B. Requires `NVIDIA_API_KEY` secret; no paid API keys needed.

### Fixed
- `agent/loop.py` — `_normalize_plan_response()` added: normalises LLM planner output before Pydantic validation; renames `slices` → `steps` (CRISPY-style responses), derives `goal` from the instruction when absent, and infers `type` from file presence (`edit` when files listed, `analyze` otherwise). Fixes the `ValidationError: AgentPlan goal Field required` crash that caused all tasks to fail with "Runtime '*' unavailable".
- `proxy.py` — `REGISTER_RUNTIMES` env var now defaults to `"true"` so system runtime agents (Hermes, OpenCode, Goose, Aider, internal_agent) are always registered in `AgentStore` on startup without requiring an explicit env override.

### Added
- `agents/api.py` — `GET /api/agents/` response now includes a `runtime_health` field per agent (when the agent has a `runtime_id`), exposing `available`, `latency_ms`, and `error` from the live `RuntimeManager` health check — enables multica.ai-style online/offline status in the roster UI.
- `agents/api.py` — new `GET /api/agents/runtimes` endpoint returns all registered runtime adapters merged with their `AgentStore` profiles and live health data, sorted by availability. Use this as the canonical data source for the agent roster UI.

### Added
- `setup/api.py` — `GET /api/setup/detect/providers` endpoint; returns which providers are already configured server-side (e.g. Nvidia NIM key set on Render) without exposing key values.
- `frontend/src/pages/SetupWizardPage.js` — Nvidia NIM card added as first/recommended option in Step 1 with "Free" + "Recommended" badges; wizard auto-detects server-configured Nvidia key on load and shows "already configured" indicator; toggling Nvidia NIM on auto-updates model defaults across Steps 2 and 4; added `free_only` cost policy option.

### Changed
- `setup/api.py` — `Step1Request.use_nvidia_nim` defaulted `True`; `use_ollama` defaulted `False` (no local infra needed by default); `Step2Request` and `Step4Request` model defaults updated to Nvidia NIM models (`qwen/qwen2.5-coder-32b-instruct`, `deepseek-ai/deepseek-r1`); `Step4Request.cost_policy` defaulted to `free_only`.
- `frontend/src/pages/SetupWizardPage.js` — Step 2 renamed from "Local Models" to "Model Selection"; Nvidia NIM model info box shown in Step 2 when Nvidia is selected; draft persistence and `handleSave` payloads include `useNvidiaNim`; `applyDraftState` restores Nvidia NIM selection.

### Fixed
- `agent/models.py` — removed `max_length=5` constraint on `AgentPlan.steps` (truncation already happens in `loop.py:184`); raised `AgentRunRequest.max_steps` ceiling from 5 to 20 — was causing Pydantic `ValidationError` when NIM generated plans with >5 steps, which surfaced as "runtime * unavailable" task failures.
- `runtimes/routing.py` — fallback loop no longer skips the fallback runtime when it shares the same ID as the primary (fixes the case where `internal_agent` is both primary and fallback); last execution error is now included in the final `RuntimeUnavailableError` message for easier debugging.
- `backend/server.py` — `_list_configured_provider_records()` now always prepends Nvidia NIM (from `NVIDIA_API_KEY` env) at priority -10, so Direct Chat uses NIM even when the MongoDB providers collection has stale zhipu/minimax/ollama-local records from an old configuration.
- `frontend/src/index.css` — global `appearance: none` rule on `input` was hiding all native checkboxes; added `input[type="checkbox"]` override restoring native appearance so Setup Wizard Step 3 runtime toggles are visible and clickable again.

### Added
- `backend/server.py` — `_nvidia_nim_provider_record()` helper builds an in-memory provider record from env vars (`NVIDIA_API_KEY`, `NVIDIA_BASE_URL`, `NVIDIA_DEFAULT_MODEL`) without requiring a DB entry.

### Added
- `schedules/api.py` — new `/api/schedules/*` router exposing schedule management (list, create, toggle pause/active, run-now, delete, run history) for the Control Plane UI, backed by the existing `AgentScheduler`.
- `routing/api.py` — new `/api/routing/policy` (GET/PUT) and `/api/routing/stats` (GET) endpoints surfacing the `RuntimeRoutingPolicyEngine` configuration under the control-plane path expected by the UI.
- `agent/scheduler.py` — added `toggle(job_id, enabled=)` method for pause/resume without deletion; added `get_scheduler()` / `set_scheduler()` singleton accessors to avoid circular imports.
- Wired both new routers into `proxy.py` at startup.

### Changed
- `.python-version` — pinned to `3.13` to match CI (`python-version: ["3.13"]` in `.github/workflows/ci.yml`); local pytest environment reinstalled with Python 3.13 so version-specific behaviour (event-loop enforcement, etc.) is caught locally before CI.

### Fixed
- `tests/conftest.py` — aligned `V3_ADMIN_EMAIL` with `ADMIN_EMAIL` so backend limited-mode login fallback uses the same admin email as the test fixtures (`admin@llmrelay.local`); pinned `JWT_SECRET` to a deterministic CI value to prevent random secret mismatch between login and subsequent requests.
- `runtimes/control.py` — added `_is_docker_unavailable()` helper with expanded Docker-socket error patterns (`docker.sock`, `daemon is running`, `failed to connect to the docker`); `POST /runtimes/{id}/start` now returns an informational 200 payload instead of 500 when the Docker socket is absent.
- `backend/server.py` — wrapped all bare MongoDB `await` calls in `chat_send`, `list_providers`, `get_active_provider`, and `_list_configured_provider_records` with `try/except` and sensible limited-mode fallbacks, preventing `ServerSelectionTimeoutError` from propagating to test clients when MongoDB is unreachable.
- `backend/server.py` — `JWTUserStateMiddleware` now applies the same admin-email limited-mode fallback as `get_current_user` when `ObjectId(payload["sub"])` raises `bson.errors.InvalidId`, ensuring `request.state.user` is populated for task/agent routes in CI without MongoDB.
- `backend/server.py` — `get_current_user` outer `except` clause split so `HTTPException` is re-raised as-is instead of being swallowed as `"Invalid token"`, fixing false 401s on the task creation endpoint in limited mode.
- `backend/server.py` — `GET /api/health` no longer propagates `ServerSelectionTimeoutError`; `get_active_provider()` returns `None` gracefully when MongoDB is down.
- `backend/server.py` — `GET /api/providers` returns built-in provider defaults (including `anthropic-universal`) via new `_builtin_provider_records()` helper when MongoDB is unavailable.
- `tests/test_iteration_7_features.py` — `TestHealthEndpoint` assertion updated to accept `"degraded"` alongside `"ok"` since no-MongoDB CI environments correctly report degraded status.
- `runtimes/health.py` — `RuntimeHealthService.stop()` now catches `RuntimeError` alongside `CancelledError`; Python 3.13 raises `RuntimeError: Task attached to a different loop` when a background task created during TestClient startup is awaited during pytest-asyncio teardown.

- Added `self-improve` skill: enables the agent to audit and enhance its own skill library
- Added `issue-resolver` skill: structured end-to-end process for resolving GitHub issues
- Added `skill-composer` skill: orchestration layer for combining multiple skills into coordinated workflows
- Added `git-hygiene` skill: ensures clean git history, valid commit messages, and safe pushes before merging
- Added `task-scoper` skill: prevents scope creep by explicitly defining task boundaries before implementation begins
