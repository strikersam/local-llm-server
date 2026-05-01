# Changelog

## [Unreleased]

### Fixed
- `frontend/src/pages/AuthCallback.js` — social login (Google/GitHub) no longer bounces the user back to `/login` after a successful OAuth callback. Root cause: `AuthCallback` stored the JWT in localStorage but navigated to `/control-plane` before `AuthContext` re-checked auth state, so `ProtectedRoute` still saw `user = false` and redirected to `/login`. Fix: call `checkAuth()` (already exposed by `AuthContext`) after storing the token and navigate only once it resolves, guaranteeing `ProtectedRoute` sees the authenticated user.

### Fixed
- `agent/models.py` — `VerificationResult.issues` now coerces LLM-returned dicts to strings via `@field_validator`; previously crashed the agent loop with Pydantic `ValidationError: Input should be a valid string … input_type=dict` whenever the verifier returned structured objects.
- `agent/loop.py` — analyze/github-type steps now call `_synthesize_answer()` after tool-call observations are gathered; `_build_summary()` surfaces these answers as the main response text instead of the useless `"Goal: X | Applied steps: Y/Z"` line; added `Files modified: N` to the meta line so the summary accurately reflects actual file edits.
- `agent/loop.py` — `_build_rich_report()` added: generates a full markdown execution report (per-step status icons, files changed, synthesized answers for analysis steps, issues) used as the task discussion comment — eliminates "tasks complete but nothing happened" confusion.
- `runtimes/adapters/internal_agent.py` — agent comment is now the full rich markdown report; `TaskResult.artifacts` is populated with all files written to disk; `auto_commit` is configurable via `spec.context["auto_commit"]` (default `False`).
- `backend/server.py` — Nvidia NIM added to `seed_default_providers()` with `priority: -10`; it now appears in the Providers page and is always the first provider attempted when `NVIDIA_API_KEY` is set.
- `provider_router.py` — failure-type-aware cooldowns (auth 401/403 → 300 s; connection error → 15 s; other → 30 s); last-resort bypass retries all cooldown-skipped providers once when no providers were attempted, preventing "no providers attempted" dead-end.

### Fixed
- `backend/server.py` — replaced hardcoded `use_agent = True` with `use_agent = body.agent_mode or _classify_complexity(body.content) == "complex"`, so simple conversational messages (e.g. "Hello") use the fast direct-LLM path instead of the full Plan→Execute→Verify pipeline that was causing "Agent error: All configured LLM providers failed" for every message.
- `backend/server.py` — `_run_agent_loop` now re-raises `ProviderFallbackError` instead of catching it as a generic exception; the outer `chat_send` handler converts it to a clean HTTP 503, so provider failures surface as real errors instead of being swallowed into an "Agent error: …" assistant message.
- `backend/server.py` — reduced agent `max_steps` from 20 to 8 and `_AGENT_TIMEOUT_SEC` from 900 s to 120 s, preventing excessively long hangs for complex tasks.
- `frontend/src/pages/ChatPage.js` — removed hardcoded `agentMode: true` from `chatSend()`; agent mode is now controlled by the UI toggle and defaults to OFF (direct chat).
- `frontend/src/pages/ChatPage.js` — "Agent ON" static badge replaced with a real toggle button; state is persisted to localStorage; chat experience now defaults to fast direct LLM and only invokes the agent pipeline when the user explicitly enables it or the backend classifies the task as complex.
- `frontend/src/pages/ChatPage.js` — empty state updated: heading, description, placeholder, and quick-prompt suggestions now reflect the actual mode (direct chat vs. agent) instead of always showing wiki-specific prompts.

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
