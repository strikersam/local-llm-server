# Changelog

## [Unreleased] — 2026-05-09

### Added

- **Vision request routing** (`router/registry.py`, `router/model_router.py`) — the proxy now auto-detects `image_url` content parts in incoming chat requests and routes them to the highest-tier vision-capable model registered in the capability registry. Vision capability is declared via the new `vision: bool` field on `ModelCapability`. Affected models: `gemma4:27b`, `gemma4:9b`, `gemma4:latest`, `llama4-maverick:17b`, `llama4-scout:17b`, `qwen3.6:35b`. Set `VISION_MODEL=<name>` env var to pin to a specific vision model. Manual `X-Model-Override` header still takes priority.

- **`CLAUDE_CODE_SESSION_ID` / `X-Session-Id` propagation in Langfuse traces** (`langfuse_obs.py`, `chat_handlers.py`) — the proxy now extracts `X-Session-Id` and `X-Claude-Code-Session-Id` request headers and attaches them to Langfuse traces as `sessionId` (groups all turns from one session under a single trace in Langfuse) and as a `session:<id>` tag. All streaming and non-streaming paths are covered. The `session_id` field also appears in the trace metadata dict.

- **`FEATURE_DISABLE` / `FEATURE_ENABLE` bulk env vars** (`features/matrix.py`) — operators can now enable or disable multiple features at once via comma-separated lists, e.g. `FEATURE_DISABLE=jcode_runtime,social_auth`. `FEATURE_DISABLE` is authoritative (wins over `FEATURE_ENABLE` if both list the same ID). Unknown IDs in either list emit a WARNING log. Single-feature `FEATURE_<ID>=<tier>` overrides continue to work.

- **`FeatureMatrix.check()` alias** (`features/matrix.py`) — adds `check(feature_id)` as a direct alias for `check_available()`, matching the originally-planned public API.

- **`FeatureMatrix.summary()` method** (`features/matrix.py`) — returns a compact list of all features (feature_id, display_name, maturity, enabled) suitable for status endpoints and admin UI consumers.

- **`proxy_endpoints` feature entry** (`features/matrix.py`) — added the missing stable `proxy_endpoints` registry entry so `FeatureMatrix.check("proxy_endpoints")` works correctly.

- **`as_dict()` enhancements** (`features/matrix.py`) — `FeatureMatrix.as_dict()` now returns `schema_version: "1"`, a top-level `entries` list (for consumers that prefer arrays over keyed maps), and a top-level `by_maturity` dict alongside the existing `features` dict and `summary` block.

- `tests/test_vision_routing.py` — 26 tests covering `has_image_content()`, `best_vision_model()`, `ModelRouter` vision routing, vision-capable registry entries, `emit_chat_observation()` session_id propagation, `_emit_langfuse_http` session tagging, and `_emit_sdk` signature.

### Fixed

- `agent/loop.py` — fixed an `IndentationError` in the step tool-selection loop by restoring the missing `try:` block around `_chat_json()` / `ToolCall` validation, unblocking test collection and backend startup/import paths.
- `agent/loop.py` — removed a trailing duplicated method block that overrode the main implementations, and restored normal edit-step file application bookkeeping (`target_file` loop + `changed_files` tracking), fixing AgentRunner regressions in `spawn_subagent` and mocked edit-flow tests.
- `tests/test_failover_order.py::test_from_env_provider_order_local_first` — test was asserting `ollama-local` is always present without setting `INCLUDE_LOCAL_FALLBACK=true`. Updated to explicitly opt in, matching the current explicit-opt-in behaviour introduced in the previous fix.
- `direct_chat.py` — agent-mode direct chat now appends the user message before queueing the background job (preventing missing-session `KeyError` on async completion) and returns HTTP `202 Accepted` with `job_id` for proper async semantics.

- `tests/test_feature_matrix.py::TestRegistryLoads::test_known_beta_features_are_beta` — `workspace_isolation` and `runtime_preflight` were promoted to STABLE; test updated to reflect their current maturity. Added companion `test_promoted_features_are_stable` to assert the promotion explicitly.

- `features/matrix.py` — `maturity_warning()` now returns `None` for features that are disabled (not just for non-beta/non-experimental features), fixing the contract expected by the test suite.

### Fixed
- Removed automatic Ollama fallback in provider router to prevent connection errors when Ollama is not running. Ollama is now only included when INCLUDE_LOCAL_FALLBACK=true is explicitly set, preserving NVIDIA NIM as highest priority when NVIDIA_API_KEY is set.


## [Unreleased] — 2026-05-08

### Added

- **Workspace isolation model** (`workspace/`) — first-class isolated workspaces per session/job with:
  - Deterministic workspace root derivation from validated, hashed session/job IDs
  - Path safety: canonicalization, traversal rejection, symlink escape blocking
  - Session/job ownership boundaries with RLock concurrency guards
  - Explicit lifecycle states: creating → ready → active → paused → completed → failed → cancelling → cancelled → archived → cleaned
  - Structured `manifest.json` per workspace with session ID, job ID, timestamps, paths, cleanup eligibility, and schema version
  - Five standard subdirectories: `source/`, `checkpoints/`, `logs/`, `artifacts/`, `temp/`
  - Retention TTL and safe cleanup policies that respect active locks
  - Structured, actionable error codes for all failure modes
  - Workspace metrics (active, expired, cleaned, resume success/failure)
  - Admin diagnostics endpoint combining workspace and runtime health
  - Runtime integration hooks in `AgentJobManager`

- **Feature maturity tiers & support matrix** (`features/`) — real support classification:
  - `FeatureMaturity` enum: stable, beta, experimental, disabled
  - `FeatureMatrix` single source of truth with all features classified
  - Enforcement: disabled features raise `FeatureUnavailableError`, beta/experimental surface warnings
  - Config overrides via `FEATURE_<ID>=<tier>` environment variables
  - Admin API at `/admin/features` (list, get, check)
  - Markdown table generation for docs sync

- `docs/architecture/workspace-isolation.md` — full workspace isolation architecture documentation
- `docs/support-matrix.md` — generated feature support matrix documentation
- `features/api.py` — admin API routes for feature support matrix

### Changed

- `agent/job_manager.py` — `AgentJobManager` now accepts an optional `workspace_manager` parameter; job creation automatically provisions isolated workspaces; job lifecycle transitions (start, cancel, complete, fail) update workspace state
- `direct_chat.py` — now uses `WorkspaceManager` instead of legacy `make_isolated_workspace()` for agent mode workspace provisioning
- `proxy.py` — mounts the features admin API router at `/admin/features/*`
- `docs/architecture/overview.md` — added workspace isolation and feature maturity sections
- `docs/architecture/feature-maturity-matrix.md` — updated to reference the canonical `features/matrix.py` source of truth
- `docs/features.md` — added workspace isolation (§17) and feature maturity (§18) feature documentation
- `docs/configuration-reference.md` — added workspace isolation and feature maturity override config sections
- `docs/troubleshooting.md` — added sections for workspace errors and feature maturity issues

### Tests

- `tests/test_workspace_isolation.py` — comprehensive workspace isolation tests covering: ID validation, path derivation, traversal rejection, symlink escape blocking, lifecycle states, resume boundaries, cleanup policies, manifest creation/corruption, cross-session isolation, concurrency, metrics, diagnostics
- `tests/test_feature_maturity.py` — feature maturity and support matrix tests covering: matrix loading, classification, disabled feature gating, maturity warnings, config overrides, serialization, admin API
- `tests/test_v4_reliability_regression.py` — regression tests for claimed v4 behavior: runtime preflight structured errors, direct chat sync behavior, agent mode async 202, job lifecycle transitions, provider cooldown expiry, model role separation, structured runtime errors
- `tests/test_workspace_security.py` — security-oriented tests: path traversal prevention, no internal path leakage, workspace hashing, cleanup isolation, symlink attack prevention
- `tests/test_docs_config_sync.py` — lightweight docs/config sync checks: matrix markdown generation, config flag documentation, feature coverage

### Added
- `agent/workspace.py` — `WorkspaceManager`: first-class isolated workspace lifecycle management. Every agent session/job gets its own hashed workspace root under `AGENT_WORKSPACE_BASE`. Features: deterministic path derivation from SHA-256 hashes (raw IDs never appear in paths), explicit lifecycle states (creating/ready/active/paused/completed/failed/cancelling/cancelled/archived/cleaned), structured workspace manifest (workspace.json), path traversal / symlink escape rejection via `safe_path()`, asyncio lock for concurrent mutation guard, retention TTL / `cleanup_expired()`, and a metrics API.  Backward-compatible with `make_isolated_workspace()`.
- `features/__init__.py` + `features/matrix.py` — Feature maturity / support matrix. Single source of truth (`_REGISTRY_SPEC`) for all feature stability classifications (stable / beta / experimental / disabled). `require_feature(id)` gates endpoints; disabled features raise `FeatureUnavailableError`. Operator overrides via `FEATURE_DISABLE` and `FEATURE_ENABLE` env vars. Beta/experimental features emit `WARNING` log on use.
- `GET /admin/api/features` — Admin endpoint that returns the full feature support matrix (maturity, enabled state, dependencies, config flags) for all admin-visible features.
- `GET /admin/api/workspaces/metrics` — Admin endpoint that returns workspace lifecycle counts (ready/active/completed/failed/…) by scanning the workspace base directory.
- `tests/test_workspace_isolation.py` — 50+ workspace isolation tests covering unique path derivation, ID validation, path traversal/symlink escape rejection, ownership boundaries, lock/concurrency, lifecycle state transitions, cleanup policy, manifest integrity, and structured error contracts.
- `tests/test_feature_matrix.py` — 35+ feature matrix tests covering registry loading, maturity classification, enforcement of disabled features, config-driven overrides, admin visibility output, and singleton behavior.
- `tests/test_v4_reliability.py` — 25+ regression tests for v4 reliability claims: runtime preflight structured errors, direct chat non-blocking routing, agent mode 202+job_id, job lifecycle transitions, provider cooldown/recovery, model role separation constants, legacy `make_isolated_workspace()` path safety, and admin endpoint auth guards.
- `docs/architecture/workspace-isolation.md` — Architecture doc for the workspace isolation model.
- `docs/support-matrix.md` — Full feature support matrix doc with stability tiers, production recommendations, and operator override instructions.
- `docs/configuration-reference.md` — New sections: Workspace Isolation (`AGENT_WORKSPACE_BASE`, `WORKSPACE_TTL_HOURS`) and Feature Flags (`FEATURE_DISABLE`, `FEATURE_ENABLE`).
- `docs/troubleshooting.md` — New sections for workspace errors (not found, manifest corrupt, access denied, lock timeout) and feature availability errors (disabled, beta warning, missing runtime dependency).
- `docs/architecture/feature-maturity-matrix.md` — Updated to point at `features/matrix.py` as single source of truth and reference the full support matrix doc.

- `scripts/claude_setup_audit.py` — New audit script that checks Claude Code setup completeness: CLAUDE.md required sections, hooks directory and git activation, skills inventory (≥5 installed, 4 key skills required), state files, and agents config. Outputs 0-100% weighted score as text or `--json`. Exit 0 when all checks pass, 1 otherwise.
- `tests/test_claude_setup_audit.py` — 12 tests covering all check functions, CLI text/JSON modes, and score arithmetic.
- `runtimes/adapters/jcode.py` — First-class jcode runtime adapter (TIER_2). jcode is a high-performance Rust coding agent that connects to the local proxy as its OpenAI provider. Supports CLI and HTTP API modes; capabilities include MCP connectivity, semantic vector memory, multi-agent swarm, browser automation, repo editing, and streaming. Includes `write_mcp_config()` to generate `.jcode/mcp.json` for project-local MCP server registration.
- `runtimes/manager.py` — `JCodeAdapter` registered in the default RuntimeManager alongside Hermes, OpenCode, Goose, Aider, and TaskHarness.
- `docker-compose.yml` — Added `jcode` service (port 8006) with `JCODE_PROVIDER_URL` pointing at the proxy; added `JCODE_BASE_URL` and `TASK_HARNESS_BASE_URL` to proxy and backend environment blocks. Added missing `task-harness` Docker service (port 8007) so `docker compose up task-harness` works in Docker environments.
- `scripts/register_agent_runtimes.py` — Added jcode to `RUNTIME_ROLES` for agent store registration.
- `frontend/src/pages/SetupWizardPage.js` — Added jcode toggle (badge: New) to Step 3 runtime configuration panel; wired state, persistence, and draft restore.

### Fixed
- `agent/workspace.py` — logger namespace corrected from `qwen-agent` to `qwen-proxy`. Duplicate `create()` guard now uses atomic `root.mkdir(exist_ok=False)` instead of a racy manifest-existence preflight, eliminating TOCTOU window under concurrent creates. TTL clock for `cleanup_after` now anchored to the moment a workspace enters a terminal state (via `transition()`) rather than creation time, so long-running jobs get their full TTL after completion. Blocking filesystem I/O (`cleanup_expired`, `clean_tmp`, mkdir/write in `create`, write in `transition`/`heartbeat`, `root.exists` and `_read_manifest` in `open`) moved to `asyncio.to_thread`. `_write_manifest` now uses `tempfile.NamedTemporaryFile` for a unique temp path per write, preventing concurrent writers from clobbering each other's temp file. Stale-cache validation in `open()` now checks `root.exists()` outside `_registry_lock` to avoid blocking the event loop while holding the lock.
- `features/matrix.py` — experimental features (`jcode_runtime`, `opencode_runtime`, `goose_runtime`, `social_auth`, `multi_agent_swarm`, `workflow_engine`) now default to `enabled=False`; operators must opt in via `FEATURE_ENABLE`. `FEATURE_DISABLE` is now authoritative: IDs it disables cannot be re-enabled by a concurrent `FEATURE_ENABLE` entry.
- `docs/architecture/workspace-isolation.md` — fenced code blocks now carry language labels; `manifest.json` error table entry corrected to `workspace.json`.
- `docs/support-matrix.md` — example JSON `"total"` corrected from `24` to `27` (actual registry count).
- `docs/troubleshooting.md` — log snippet block now carries `text` language label.
- `tests/test_workspace_isolation.py` — test helper `run()` now uses `asyncio.run()` (proper loop lifecycle) instead of `asyncio.new_event_loop().run_until_complete()`.
- `tests/test_feature_matrix.py` — `test_feature_disable_takes_precedence` now asserts the final `enabled` state is `False`.
- `tests/test_v4_reliability.py` — FastAPI `dependency_overrides` cleanup now in `finally` block; traversal tests use specific `ValueError` instead of broad `Exception`; all `asyncio.new_event_loop()` calls replaced with `asyncio.run()`.
- `runtimes/control.py` — `_start_local_runtime` now skips spawning `agent_runtime.py` for CLI-only adapters (those without a `_base_url` attribute, e.g. `task_harness`). Previously the subprocess was spawned uselessly — the task_harness adapter ignores the HTTP port entirely, so health checks continued to show "Binary 'task-harness' not found in PATH" even after "starting" the runtime.
- `runtimes/control.py` — `_start_local_runtime` now verifies the spawned subprocess is still alive after the startup delay. If it crashed (e.g. port already in use), the function returns an error immediately rather than calling `_update_adapter_base_url`, which previously left adapters (notably `AiderAdapter`) pointing at a dead port and caused every subsequent health check to raise `httpx.ConnectError: All connection attempts failed`.
- `provider_router.py` — connection failures (Ollama not running) no longer trigger up to 3 retry attempts; the router breaks immediately on the first connection error, eliminating the "All connection attempts failed × 3" noise in error messages.
- `backend/server.py` — agent chat no longer crashes with a raw `"Agent error: planning: …All configured LLM providers failed"` message; it now falls back to a direct `call_llm()` response and, if that also fails, returns a structured message with actionable fix steps (check API keys, start Ollama, add a fallback provider).
- `direct_chat.py` — agent mode now passes the app's live provider chain (including NVIDIA NIM and all configured fallbacks) to `AgentRunner` instead of an empty list that triggered env-var re-init with only local Ollama.
- `direct_chat.py` — single-provider routing now uses a scoped `ProviderRouter([provider])` instance instead of mutating the shared router (which was not thread-safe under concurrent requests).

### Changed
- `direct_chat.py` — `_is_trivial_message()` extended to also classify short questions (≤ 12 words, no code/file keywords) as conversational so they skip the full plan-execute-verify loop and go straight to the LLM.

- `openclaw-security-automation.yml` — removed `npm install -g openclaw@latest` install step (openclaw is not on npm; the Python security agent never calls it anyway, so the step was both broken and unused).
- `openclaw-maintenance.yml` — replaced `npm install -g openclaw@latest` with the correct install method: `git clone https://github.com/getmoss/openclaw-claude-code` + `npm install`, as documented in `docs/runbooks/openclaw-setup.md`.
- `runtimes/control.py` — `task_harness` and `jcode` were missing from `RUNTIME_CONTAINERS` and `RUNTIME_LOCAL_PORTS`; start/stop API calls for those runtimes returned `{"error": "Unknown runtime: ..."}`. Both are now registered with port assignments (8104 and 8105 respectively).
- `runtimes/control.py` — `asyncio.get_event_loop().create_task(...)` in `_start_local_runtime` was deprecated in Python 3.10+ and could raise `DeprecationWarning`; replaced with `asyncio.create_task(...)`.
- `agent/loop.py` — `AgentRunner._chat_text()` rebuilt a new `ProviderRouter` instance on every LLM call (re-reading env vars and constructing `ProviderConfig` each time); router is now built once in `__init__` and reused, eliminating per-call overhead for jcode and other fast-path clients.
- `agent/loop.py` — `InferenceCache` was implemented but never wired into the agent loop; `_chat_text()` now checks the cache before hitting the LLM and stores results after live calls, so repeated identical prompts (retries, compaction, similar sequential tasks) are served instantly from cache.
- `openclaw-security-automation.yml`: Dependabot and CodeQL alert counts were never captured from Python stdout (shell vars `$DEPENDABOT_COUNT`/`$CODEQL_COUNT` were unset); now captured via command substitution.
- `openclaw-security-automation.yml`: Removed invalid `dependabot-alerts: read` permission key (not a valid GitHub Actions permission).
- `security_fix_agent.py`: Branch cleanup ran unconditionally after both success and failure; now only cleans up on failure and returns early after a successful push.
- `security_fix_agent.py`: pip upgrade path now rewrites `requirements.txt` via `pip freeze` so the change is actually tracked by git.
- `security_fix_agent.py`: Removed `CODEQL_FIX_APPLIED.txt` dummy file creation; CodeQL fix now exits early with a clear message when no edits can be applied automatically.
- `direct_chat.py` — `@direct_chat_router.post("/send")` decorator was accidentally applied to `_is_trivial_message` instead of `send_chat_message` (inserted between the decorator and the handler by commit b172df5); `/api/chat/send` now correctly routes requests.
- `proxy.py` — `app.state.PROVIDER_ROUTER` was never set in the lifespan, causing `AttributeError` in the direct-chat regular-chat path; lifespan now sets it from the module-level singleton.
- `frontend/src/index.css` — attribute selector used single quotes (`input[type='checkbox']`) but regression test expected double quotes; normalised to double quotes.
- `tests/test_direct_chat_async.py` — test content "Implement feature" (2 words) was silently reclassified as trivial and bypassed agent mode; updated to 4-word content that is unambiguously non-trivial.
- `.github/scripts/review_agent.py` — fail closed when diff fetch fails: if `gh pr diff` returns an error the script now writes a FAIL result and exits 1 instead of forwarding the placeholder to the LLM and potentially emitting a PASS/WARN.

### Changed
- `.github/scripts/implement_agent.py` — switched primary NVIDIA NIM model to `qwen/qwen3-coder-480b-a35b-instruct` (correct publisher namespace); fixed `tool_list_files` duplicate-arg `subprocess.run` bug; pipeline now uses NVIDIA APIs for agentic implementation.
- `.github/scripts/review_agent.py` — switched council review model to `qwen/qwen3-coder-480b-a35b-instruct`; fixed `subprocess.run` duplicate-arg bug; added `subprocess.TimeoutExpired` and non-zero returncode handling; wrapped API call in try/except so the result file is always written on failure.
- `provider_router.py` — `ollama-local` is excluded from the provider chain when `NVIDIA_API_KEY` is set (hosted mode); set `INCLUDE_LOCAL_FALLBACK=true` to force-include it even in hosted deployments.

### Fixed
- `.github/workflows/openclaw-security-automation.yml` — fixed `SyntaxError: Octal escape sequences are not allowed in template strings` in the "Create summary issue" step by replacing JS template literal interpolation with string concatenation for GitHub context values (`github.repository`, `github.sha`), and by using `\u{1F527}` Unicode escape instead of raw emoji for the issue title. Also fixed step output propagation: the Python script's alert count is now captured via `$(python ...)` command substitution instead of referencing an unset `$DEPENDABOT_COUNT` / `$CODEQL_COUNT` environment variable, so the summary issue step correctly receives the alert counts.


## [4.0.0] - 2026-05-06

### Added
- `docs/screenshots/webui/mobile-refresh/` — added before/after mobile captures for the login screen and setup wizard so the frontend refresh PR includes visual regression evidence.
- `agent/job_manager.py` — async direct-chat agent job lifecycle with queued/running/succeeded/failed/cancelled states, heartbeat timestamps, and progress events.
- `docs/architecture/runtime-model.md`, `docs/architecture/agent-job-lifecycle.md`, `docs/architecture/feature-maturity-matrix.md`, and `docs/runbooks/runtime-troubleshooting.md` — documented runtime preflight, async agent jobs, maturity tiers, and troubleshooting.

### Changed
- `frontend/src/index.css`, `frontend/src/pages/DashboardLayout.js`, and `frontend/src/pages/LoginPage.js` — introduced a unified mobile-first black design system with layered dark surfaces, safe-area-aware app chrome, thumb-friendly bottom navigation, and a denser native-style authentication shell.
- `frontend/src/pages/SetupWizardPage.js` and `frontend/src/pages/AuthCallback.js` — removed the remaining light-theme onboarding/auth screens and aligned setup completion, step navigation, and OAuth callback states with the new dark mobile app shell.
- `frontend/src/pages/ChatPage.js` — refined the chat surface into a native-feeling mobile layout with pill controls, elevated message bubbles, a card composer above the safe area, and cleaner modal/panel styling across mobile and tablet breakpoints.
- `backend/server.py` / `agent/loop.py` / `setup/api.py` / `frontend/src/pages/SetupWizardPage.js` — hosted Direct Chat agent runs now queue asynchronous jobs instead of blocking the request, and agent role models are now configurable per role (planner, coder/executor, verifier, judge) with NVIDIA-first defaults.
- `frontend/src/pages/ChatPage.js` — mobile Direct Chat now uses a safer dynamic viewport layout, auto-resizing composer, safe-area-aware sticky header/composer spacing, and a collapsible mobile agent workspace so progress/activity no longer consume the full chat surface.
- `direct_chat.py` — split direct chat from async agent workflows; `agent_mode=true` now returns `202 Accepted` plus a pollable job id instead of blocking the request until the full tool loop completes.
- `frontend/src/pages/ChatPage.js` — added a mobile-friendly agent job status card and polling flow for async agent runs.
- `runtimes/base.py`, `runtimes/api.py`, and `runtimes/routing.py` — added runtime readiness/preflight validation so tasks fail early with structured diagnostics.

### Fixed
- `backend/server.py` / `tests/test_chat_mode_regressions.py` — hosted Direct Chat no longer relies on the fragile inline agent timeout fallback path; long-running complex tasks stay in progress through the new job lifecycle and can be polled/cancelled from the UI.
- `agent/loop.py` / `backend/server.py` — planner/verifier/judge selection no longer collapses to a single requested model for every agent phase, so NVIDIA-backed coding flows can keep a Nemotron executor while using separate planner/judge defaults.
- `agent/job_manager.py` / `tests/test_direct_chat_async.py` — direct-chat async agent workspaces now validate session/job ids and derive hashed directory names before creating directories, closing the CodeQL path-traversal finding on isolated workspace creation.
- `proxy.py` / `tests/test_agent_api.py` — `/agent/run` and `/agent/sessions/{id}/run` no longer echo internal failure details back to API callers; they now return only a stable failure summary, resolving the CodeQL information-exposure findings.
- runtime execution now surfaces actionable missing-binary errors, including `task-harness` configuration guidance, instead of late raw PATH failures.
- planner/verifier/judge failures now surface phase-specific structured errors and BLOCKED fallback behavior instead of ambiguous downstream failures.
- `tests/test_iteration_7_features.py` — fixed an accidental indentation error on a skipped test so CI syntax checks and CodeQL can parse the test suite again.
- `tests/conftest.py` — restored a generic `client` fixture alias so `tests/test_v3_auth.py` can run under the shared test harness.
- `tests/conftest.py` — set `V3_ADMIN_PASSWORD` in the shared test env so v3 auth tests use the same seeded admin credentials as the mocked backend.
- `backend/server.py` — `/api/auth/login` now returns `token_type`, `expires_in`, and `id` alongside the tokens, restoring the response contract expected by the v3 auth tests.
- `backend/server.py` — `/api/auth/me` now includes `id` as an alias of `_id`, matching the v3 auth API contract used by the tests and frontend.
- `backend/server.py` — auth tokens now include `iat` and `jti`, so refreshing produces a distinct access token even when requests happen in the same second.
- `backend/server.py` — `/api/auth/logout` now returns `status: "logged out"`, matching the v3 auth test and client expectations.
- `backend/server.py` — `/api/auth/logout` now also returns the authenticated email, preserving the v3 auth response contract.
- `backend/server.py` — `/api/auth/refresh` now falls back cleanly for the limited-mode admin user instead of crashing on a non-ObjectId test user id.
- `Dockerfile.backend` — now copies `commercial_equivalent.py` into the backend image so `langfuse_obs.py` can import it in production; this fixes Render boot failure `ModuleNotFoundError: No module named 'commercial_equivalent'`.
### Fixed
- `frontend/src/pages/ChatPage.js` / `frontend/src/components/AgentStatusPanel.jsx` / `frontend/src/components/AgentActivityFeed.jsx` / `backend/server.py` / `frontend/src/__tests__/agentWorkspaceTransport.test.js` / `frontend/src/__tests__/chatPage.test.jsx` / `tests/test_chat_mode_regressions.py` — Direct Chat live agent workspace polling and streaming now authenticate correctly, fixing the `HTTP 401` agent-status / activity panes that appeared after login in hosted chat sessions.
- `frontend/src/utils/agentWorkspaceTransport.js` / `frontend/src/pages/ChatPage.js` / `frontend/src/components/AgentStatusPanel.jsx` / `frontend/src/components/AgentActivityFeed.jsx` / `frontend/src/__tests__/agentWorkspaceTransport.test.js` / `frontend/src/__tests__/agentWorkspaceConsole.test.jsx` — the Direct Chat live workspace now uses a single control-plane transport path for snapshot polling and event streaming, eliminates duplicate status polling, and shows reconnect / auth-expired banners instead of leaving operators with a silent dead workspace.
- `setup/api.py` / `tests/test_setup_api.py` — the setup wizard now persists through the hosted MongoDB path when available instead of relying only on local files, so admin setup survives Render restarts/redeploys and can be reopened for edits later.
- `backend/server.py` / `langfuse_obs.py` / `tests/test_chat_mode_regressions.py` — hosted direct chat now emits Langfuse observations with token counts and latency metadata, and Langfuse URL detection now accepts `LANGFUSE_URL` alongside the existing host/base env names.
- `tasks/store.py` / `tasks/service.py` / `tasks/dispatcher.py` / `agents/api.py` / `tests/test_task_dispatcher.py` / `tests/test_tasks_workflow.py` / `tests/test_agents_api.py` — task execution now fans out concurrently, auto-assignment prefers less-busy matching agents, and the Agents API reports running/open-task status so the roster no longer leaves free agents looking idle while work is queued.
- `backend/server.py` / `frontend/src/pages/LogsPage.js` / `tests/test_activity_logs.py` — the activity/logs surface now includes recent in-process error logs and renders timestamps from `created_at`, making backend failures visible in the dashboard instead of disappearing silently.
- `frontend/src/pages/SetupWizardPage.js` / `frontend/src/__tests__/setupWizard.test.js` — the setup wizard now has a mobile step toggle, stacked controls, and responsive navigation/action layouts so onboarding remains usable on narrow screens.

### Security
- `backend/server.py` — refreshed JWT access/refresh tokens now include unique `iat`/`jti` claims so a refresh always yields a distinct token even when requests land in the same second.

### Changed
- `frontend/src/pages/ControlPlanePage.js` / `frontend/src/pages/DashboardLayout.js` — replaced the root hosted dashboard with a more refined mobile-first workspace overview: usage and provider priority live at the top, task/routing/agent/provider/runtime/schedule sections are grouped into clearer operational cards, and the primary sidebar entry is now simply **Dashboard**. Legacy `/dashboard`, `/control-plane`, and `/llmrelay` URLs now funnel back to the root dashboard instead of leaving stale entry points behind.
- `frontend/src/pages/SetupWizardPage.js` / `backend/server.py` / `provider_router.py` / `.github/scripts/implement_agent.py` / `.github/scripts/review_agent.py` — NVIDIA defaults now prioritize `nvidia/nemotron-3-super-120b-a12b` wherever the repo chooses a hosted default model, while still keeping the coder-specific Qwen path available for code-heavy execution.

### Fixed
- `backend/server.py` / `provider_router.py` / `tests/test_chat_mode_regressions.py` / `tests/test_provider_router.py` / `tests/test_provider_failover_integration.py` — direct chat now uses bounded per-provider timeouts, retries healthy fallbacks without keeping a broken model pin, and returns a stable in-chat recovery/diagnostic message instead of bubbling raw 502/503 failures when the first provider stalls or goes down.
- `frontend/src/pages/AuthCallback.js` — both social-login callbacks and legacy token callbacks now return users to the root dashboard after auth state sync, avoiding the stale `/control-plane` destination.
- `.github/workflows/ci.yml` — CI now runs the GitHub Pages frontend test suite and production build in addition to the Python suite, so mobile/dashboard regressions and auth UI regressions are caught before merge.
- `tasks/service.py` / `tasks/api.py` / `frontend/src/pages/TasksPage.js` — task execution is now much less flaky in the Multica board: moving a task back to `in_progress` always requeues execution even without a manually assigned agent, duplicate overlapping runs are ignored safely, the API exposes an immediate `run` action, and the Tasks UI now lets users choose an agent/runtime/prompt and trigger `Create & run` / `Run now` flows without waiting on the background poller.

### Added
- `frontend/src/__tests__/controlPlanePage.test.js` / `frontend/src/__tests__/loginPage.test.js` / `frontend/src/__tests__/authCallback.test.js` / `tests/test_provider_router.py` — added regression coverage for the new dashboard summary, preserved GitHub/Google social login affordances, callback redirects, and the new NVIDIA Nemotron default-provider priority.
- `frontend/src/__tests__/tasksPage.test.jsx` / `tests/test_tasks_workflow.py` — added regression coverage for immediate task execution from the Multica task board, no-agent requeue behavior, and duplicate-run suppression.

### Changed
- `README.md` — refined the human-first README again to improve page traction: replaced the potentially friction-heavy “5-year-old” phrasing, added clearer value framing, a simple benefits table, and more team/adoption-oriented positioning for non-technical readers.
- `README.md` — rewrote the README again with a human-first, screenshot-rich product story aimed at non-technical readers: simpler language, clearer use cases, visual tour, friendlier setup path, and links out to technical docs instead of front-loading route details.
- `docs/api-surfaces.md` — added a separate technical route map so API and surface details live outside the README.
- `README.md` — rewrote the top-level documentation to reflect the current product surface: corrected startup and port guidance, documented the built-in admin/web UI and separate dashboard deployment modes, and added an end-to-end feature inventory covering proxy compatibility, routing, agents, workflows, schedules, GitHub, secrets, sync, observability, and operations.
- `frontend/package.json` / `frontend/package-lock.json` — restored `react-scripts` so the GitHub Pages dashboard can run `npm test` and `npm run build` in CI again.
- `.github/workflows/deploy-frontend.yml` — switched the Pages build install step from `npm ci` to `npm install` so GitHub Pages deployments are not blocked by npm lockfile strictness on the hosted runner image.

### Fixed
- `backend/server.py` / `tests/test_chat_mode_regressions.py` — direct chat now respects the Agent Mode toggle strictly, so complex coding prompts stay on the fast LLM path unless the caller explicitly enables agent orchestration. This prevents default chat from failing behind agent-only provider/runtime issues.
- `Dockerfile.backend` — copy the `schedules/` package into the hosted backend image so `backend.server:app` can import `schedules_router` on Render instead of crashing with `ModuleNotFoundError: No module named 'schedules'` during deploy.
- `backend/server.py` — wired the hosted `backend.server:app` deployment to expose authenticated schedule routes (`/api/schedules/*`) and legacy schedule compatibility routes (`/agent/scheduler/jobs*`), and initialised the shared scheduler so hosted schedule creation no longer returns 404.
- `backend/server.py` — added `/api/observability/savings` and `/api/observability/usage` on the hosted backend, plus activity response aliases, so the Control Plane logs/metrics views have the data contracts expected by the GitHub Pages frontend.
- `agents/store.py` / `agents/api.py` — agent profiles now persist Control Plane fields such as `role`, `preferred_runtime`, `fallback_runtimes`, `task_specializations`, and `requires_approval` while staying backward-compatible with `runtime_id` / `task_types`.
- `frontend/src/api.js` / `frontend/src/pages/SchedulesPage.js` — the Schedules UI now uses `/api/schedules/*`, defaults assigned agents correctly, and removes misleading hardcoded “Recent Runs” sample data when there is no real schedule history.
- `frontend/src/pages/LogsPage.js` — the logs dashboard now reads both hosted backend activity payloads (`logs`) and observability summaries (`summary` / `time_series`) instead of silently rendering empty activity or zeroed metrics.
- `frontend/src/pages/DashboardLayout.js` — corrected a broken `NavItem` className ternary that prevented production React builds from compiling.

### Fixed
- `tests/test_iteration_7_features.py` — corrected the placement of the temporary skip decorator on `test_anthropic_universal_provider_exists` so Python 3.13 CI syntax checks pass on pull request builds.
- `tests/conftest.py` — restored a shared `client` fixture alias to `wiki_client` so `tests/test_v3_auth.py` can run under the full Python 3.13 CI suite.
- `tests/test_v3_auth.py` — aligned the test login password fallback with `ADMIN_PASSWORD`, updated the login/me/logout response assertions to match the current limited-mode payload, and skip refresh assertions when CI is using the env-admin fallback instead of a database-backed ObjectId user.

### Security
- requirements.txt — bump multiple dependencies to address security vulnerabilities: pillow>=10.3.0, pygments>=2.20.0, requests>=2.33.0, certifi>=2023.07.22, idna>=3.7, urllib3>=2.6.3, cryptography>=46.0.6, pyasn1>=0.6.3, setuptools>=78.1.1, oauthlib>=3.2.1, PyJWT>=2.12.0, zipp>=3.19.1, wheel>=0.38.1 (fixes CVEs including DoS, credential leakage, and improper validation).

### Security
- `frontend/package-lock.json` — bump `follow-redirects` to latest version (dependabot security update).

### Changed
- webui/frontend: bump esbuild and vite (dependabot)
- webui/frontend: bump npm_and_yarn group (dependabot)
- `.github/scripts/implement_agent.py` and `.github/scripts/review_agent.py` — swapped Anthropic SDK for OpenAI SDK pointing at NVIDIA NIM; both scripts now use `NVIDIA_API_KEY` and the `https://integrate.api.nvidia.com/v1` endpoint with free-tier models (`meta/llama-3.3-70b-instruct`, `nvidia/llama-3.1-nemotron-ultra-253b-v1`, `qwen/qwen2.5-coder-32b-instruct`). `implement_agent.py` probes tool-calling support during model selection and only marks implementation successful on explicit `IMPLEMENTATION_COMPLETE` signal. `review_agent.py` fails closed when API key is missing or model output is unparseable.
- `.github/workflows/process-quick-note.yml` — **complete pipeline rewrite**: quick-note issues now go through a full automated engineering cycle: (1) multi-strategy URL fetch (direct → og:url/canonical resolution → Google Cache → Wayback Machine) with a 500-char content gate that reopens the issue with a clear message instead of hallucinating; (2) dedicated `quick-note/issue-N` feature branch; (3) Claude agentic implementation loop (`implement_agent.py`) using Anthropic tool-use — reads CLAUDE.md and all relevant skills, edits files, runs pytest inside the loop, fixes failures; (4) pytest gate before commit; (5) automatic PR creation with summary; (6) council-review pass (`review_agent.py` — Security / Correctness / Performance / Maintainability) posted as PR comment; (7) auto-merge on PASS/WARN; (8) auto-retry up to 3× on failure — issues reopened with a failure log and a `retry:N` label; after 3 failures the issue receives `quick-note:exhausted` for human triage.
- `.github/scripts/fetch_url.py` — standalone multi-strategy URL fetcher (direct → og:url resolve → Google Cache → Wayback Machine).
- `.github/scripts/implement_agent.py` — Claude claude-opus-4-7 agentic loop with `bash`, `read_file`, `write_file`, `list_files` tools; follows all repo skills (implementation-planner, test-first-executor, changelog-enforcer, issue-resolver); 40-turn limit with `IMPLEMENTATION_COMPLETE` signal.
- `.github/scripts/review_agent.py` — council-review using Claude claude-sonnet-4-6; outputs per-role PASS/WARN/FAIL verdicts; auto-merge on PASS/WARN, leaves PR open on FAIL.

### Fixed
- `.github/workflows/process-quick-note.yml` — removed spurious `.agents/skills/url-reader/` committed by failed issue #24 run and restored `docs/changelog.md` to correct state; root cause was bare `curl` failing on `share.google` JS-redirect URLs and the LLM hallucinating changes from empty input.

### Added
- `agent/loop.py` — `spawn_subagent(instruction, model?, max_steps?)` tool added to the Executor toolkit; lets any in-flight agent delegate a self-contained subtask to a child `AgentRunner` and receive a condensed result, enabling recursive subagent delegation without an explicit API call.
- `agent/loop.py` — `_maybe_run_parallel()`: after planning, if all steps touch disjoint files and there are ≥ 3 steps, `AgentRunner.run()` automatically routes through `MultiAgentSwarm` (via `AgentCoordinator`) instead of the sequential loop, so subagents activate without any caller change.
- `agent/loop.py` — Judge gate (`_run_judge()`): single LLM call after all steps complete; returns APPROVED / APPROVED_WITH_CONDITIONS / BLOCKED verdict mirroring `.claude/agents/judge.md`; verdict included in every `AgentRunner.run()` response dict.
- `agent/loop.py` — `_write_checkpoint()`: writes `.claude/state/agent-state-{session_id}.json` before each planning handoff so sessions are resumable via `scripts/ai_runner.py resume`; each session gets its own file so concurrent runs don't overwrite each other.
- `agent/state.py` — `AgentSessionStore.create_with_id()`: creates a session with a caller-supplied ID (e.g. a UUID from `/agent/chat`), allowing chat sessions to be persistent and addressable by the client.

### Changed
- `proxy.py` — `AGENT_RUNNER` singleton now receives `session_store=AGENT_SESSIONS` and, when `NVIDIA_API_KEY` is set, is pointed at the NVIDIA NIM base URL with the NIM auth header so that session-based `/agent/run` and `/agent/sessions/{id}/run` calls also benefit from free NIM models instead of always hitting local Ollama.
- `proxy.py` — `internal_agent` runtime registered model default updated from `gemma4:latest` to `qwen/qwen2.5-coder-32b-instruct` (NVIDIA NIM free tier) when `NVIDIA_API_KEY` is set.

### Fixed
- `proxy.py` — `/agent/chat` now loads conversation history from `AGENT_SESSIONS` when `session_id` is provided (previously always passed `history=[]`); creates a persistent session for the generated session_id; passes `session_store=AGENT_SESSIONS` and `memory_store=USER_MEMORY` to `AgentRunner` so memory recall/save and event logging work correctly in direct-chat mode. Session owner is stored and enforced — callers cannot read another user's session history (403).
- `agent/models.py` — `AgentStep` gains `risky: bool` and `acceptance: str` fields; `AgentPlan` gains `risks: list[str]` and `requires_risky_review: bool` to align with `.claude/agents/planner.md` spec and enable downstream risky-module gating. `AgentSession` gains `owner_id: str` for access control.
- `agent/prompts.py` — Planner system prompt extended: "you NEVER write implementation code — you only plan"; JSON schema includes `risky`/`acceptance`/`risks`/`requires_risky_review`; instructs LLM to set `risky=true` on steps touching security-sensitive files.
- `agent/loop.py` — `_commit_step()` now catches `FileNotFoundError` and logs a warning instead of crashing with `[Errno 2] No such file or directory: 'git'` on environments where git is not in PATH (e.g. Render.com deployments). Commit message description is now sanitized (newlines stripped, truncated to 200 chars) before being passed to `git commit -m`.
- `agent/loop.py` — `_chat_text()` no longer clobbers non-Ollama provider auth with the NVIDIA API key when `provider_headers` is already set; previously, calling `AgentRunner` via `/agent/chat` with DeepSeek or Anthropic providers produced conflicting `Authorization` headers and auth failures.
- `agent/loop.py` — `_maybe_run_parallel()` early-return now runs `_run_judge()` before returning so the parallel (swarm) branch is subject to the same judge gate as the sequential branch.
- `runtimes/adapters/internal_agent.py` — `success` now requires actual applied steps or changed files (bare summary text no longer counts); a judge `BLOCKED` verdict forces `success=False`.
- `agent/models.py` — added `"spawn_subagent"` to `ToolCall.tool` Literal so Pydantic validates subagent delegation tool calls correctly.
- `agent/prompts.py` — documented `spawn_subagent` in the Executor tool prompt so LLMs know the tool exists and when to use it.
- `agent/state.py` — `create_with_id()` is now idempotent: returns the existing session unchanged when called with a session_id that already exists, preventing history loss on client retries.
- `agent/loop.py` — `_run_judge()` now validates the LLM verdict against `{"APPROVED","APPROVED_WITH_CONDITIONS","BLOCKED"}`; an unrecognised or missing verdict is treated as BLOCKED rather than silently passing; exception fallback also returns BLOCKED (was APPROVED_WITH_CONDITIONS) so judge failures are conservative.
- `agent/loop.py` — `_step_touches_risky()` now normalises backslashes to forward slashes before comparing against `_RISKY_FILES`, fixing false negatives on Windows-style paths.
- `proxy.py` — `/agent/chat` builds the history snapshot before appending the current user instruction, preventing the planner from seeing the new turn twice (once in history, once as the `instruction` argument).

### Fixed
- `frontend/src/pages/AuthCallback.js` — social login (Google/GitHub) no longer bounces the user back to `/login` after a successful OAuth callback. Root cause: `AuthCallback` stored the JWT in localStorage but navigated to `/control-plane` before `AuthContext` re-checked auth state, so `ProtectedRoute` still saw `user = false` and redirected to `/login`. Fix: call `checkAuth()` (already exposed by `AuthContext`) after storing the token and navigate only once it resolves, guaranteeing `ProtectedRoute` sees the authenticated user.
- `agent/scheduler.py` — `ScheduledJob.as_dict()` now includes `id`, `status` ("active"/"paused"), `approval_gate`, `schedule`, `failures`, and `fail_count` fields so the Schedules UI can render and toggle jobs correctly.
- `proxy.py` — added missing `PATCH /agent/scheduler/jobs/{job_id}` endpoint; the frontend's pause/resume toggle was calling this route but it did not exist, leaving all active schedules stuck non-toggleable.
- `frontend/src/pages/SchedulesPage.js` — `NewScheduleForm` now maps human-readable frequency presets ("daily", "weekly", etc.) to proper 5-field cron expressions before submitting; previously sent `schedule: "daily"` which the backend rejected because it requires a `cron` field and an `instruction`.
- `frontend/src/index.css` — Setup Wizard checkboxes were invisible again: changed `appearance: revert` to `appearance: auto` on `input[type="checkbox"]` and `input[type="radio"]`. `revert` is fragile under layered cascade rules in some browsers; `auto` is the explicit W3C standard value that tells the browser to render the native control. Also added `cursor: pointer` for usability.
- `tests/test_frontend_deployment_guards.py` — Added five regression guard tests that verify: (1) the checkbox appearance override rule exists in `index.css`, (2) that it does not set `appearance: none`, (3) that it uses `appearance: auto`, (4) that all Step 1 provider checkboxes are bound to state variables in `SetupWizardPage.js`, and (5) that Step 3 runtime checkboxes are rendered.
- `frontend/src/__tests__/setupWizard.test.js` — Added three DOM-level checkbox rendering tests: all Step 1 provider checkboxes render in the DOM; the Nvidia NIM checkbox is checked by default; all Step 3 runtime checkboxes are rendered.

### Fixed
- `agent/models.py` — `VerificationResult.issues` now coerces LLM-returned dicts to strings via `@field_validator`; previously crashed the agent loop with Pydantic `ValidationError: Input should be a valid string … input_type=dict` whenever the verifier returned structured objects.
- `agent/loop.py` — analyze/github-type steps now call `_synthesize_answer()` after tool-call observations are gathered; `_build_summary()` surfaces these answers as the main response text instead of the useless `"Goal: X | Applied steps: Y/Z"` line; added `Files modified: N` to the meta line so the summary accurately reflects actual file edits.
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

### Added
- direct_chat.py — Added `agent_mode` flag to the `/send` endpoint. When enabled, the endpoint runs an agent loop (similar to the dashboard) to perform the instruction, enabling complex tasks like cloning a repository, editing files, and opening pull requests.

### Added
- .claude/skills/fabric-patterns/ — Implemented a Fabric-like reusable prompt pattern system. Includes tools for listing, retrieving, applying, and stitching patterns. Comes with example patterns: summarize and extract_wisdom.
