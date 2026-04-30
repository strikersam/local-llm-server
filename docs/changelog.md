# Changelog

## [Unreleased]

### Added
- `setup/api.py` — `GET /api/setup/detect/providers` endpoint; returns which providers are already configured server-side (e.g. Nvidia NIM key set on Render) without exposing key values.
- `frontend/src/pages/SetupWizardPage.js` — Nvidia NIM card added as first/recommended option in Step 1 with "Free" + "Recommended" badges; wizard auto-detects server-configured Nvidia key on load and shows "already configured" indicator; toggling Nvidia NIM on auto-updates model defaults across Steps 2 and 4; added `free_only` cost policy option.

### Changed
- `setup/api.py` — `Step1Request.use_nvidia_nim` defaulted `True`; `use_ollama` defaulted `False` (no local infra needed by default); `Step2Request` and `Step4Request` model defaults updated to Nvidia NIM models (`qwen/qwen2.5-coder-32b-instruct`, `deepseek-ai/deepseek-r1`); `Step4Request.cost_policy` defaulted to `free_only`.
- `frontend/src/pages/SetupWizardPage.js` — Step 2 renamed from "Local Models" to "Model Selection"; Nvidia NIM model info box shown in Step 2 when Nvidia is selected; draft persistence and `handleSave` payloads include `useNvidiaNim`; `applyDraftState` restores Nvidia NIM selection.

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
