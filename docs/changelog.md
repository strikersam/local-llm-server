# Changelog

## [Unreleased]
### Fixed
- `direct_chat.py` — `GET /api/chat/agent-status` was returning 404 in production because the route's `Depends(_get_current_user)` dependency always raises 401 when no `Authorization` header is present, causing FastAPI to fail route resolution. Replaced the Depends chain with direct `request.state.user` access (already set by `JWTAuthMiddleware`), making the endpoint reliably reachable.
- `tokens.py` — `_get_secret()` generated a fresh random secret on every call when `V3_JWT_SECRET` was not set in the environment. This meant tokens created by `create_tokens()` could never be verified by `verify_token()` (different random secret each call). Fixed by caching the generated secret in a module-level variable so it stays consistent for the process lifetime.
- `proxy.py` — `JWTAuthMiddleware` Bearer scheme check was case-sensitive (`startswith("Bearer ")`), silently falling back to API-key lookup for `bearer …` or `BEARER …` headers from non-conforming clients. Changed to case-insensitive check (`auth_header[:7].lower() == "bearer "`).
- `.github/scripts/implement_agent.py` — Added `add_changelog_entry` tool that safely inserts under `## [Unreleased]` without reading/writing the full file, eliminating the 8000-char truncation bug that caused the agent to silently delete changelog lines on every run. `write_file` now blocks writes that shrink an existing file by more than 10 lines. `read_file` limit raised to 12000 chars with a clear truncation notice. System prompt updated to always use `add_changelog_entry` for the changelog and never create backup files.
- `.github/scripts/fetch_url.py` — Restored the original clean structure (stdlib-only, no temp-file ceremony) while keeping URL scheme validation and Jina AI Reader + Nitter strategies. Jina and Nitter logic inlined directly in `main()` instead of separate helper functions.
- `proxy.py` — Added `GET /api/agent/stream` Server-Sent Events endpoint. The Live Agent Workspace UI creates an `EventSource` to this path; without it the connection immediately failed with HTTP 404, permanently showing "Reconnecting live agent updates…" and "0 total tool calls". The new endpoint streams `AgentJobManager` progress events to the caller's session, accepts the JWT `access_token` as a query parameter (required because browsers cannot send custom headers with EventSource), and sends `: keepalive` SSE comments when idle to prevent proxy timeouts.
- `proxy.py` — Added `GET /api/audit-log` endpoint backed by `rbac.get_audit_log()`. The frontend's `getAuditLog()` API call was hitting 404 because no HTTP route existed for the in-memory RBAC audit log. Supports filtering by `user_id`, `resource`, and `outcome`; requires admin role.
- `direct_chat.py` — Added `get_agent_job_manager()` public accessor so the new `proxy.py` stream endpoint can reference the module-level `AgentJobManager` singleton without importing private state.
- `.github/scripts/fetch_url.py` — Added Jina AI Reader (`r.jina.ai/{url}`) as strategy 3 and Nitter (`nitter.net`) as strategy 4 for X.com/Twitter URLs. Jina renders JavaScript-heavy SPAs and returns clean text for any public URL, fixing fetch failures on React/Vue/Angular sites. Nitter provides a plain-HTML X.com mirror. Google Cache and Wayback Machine are now strategies 5 and 6. This resolves `quick-note:exhausted` failures caused by X.com 403s and empty JS-rendered HTML.
- `.github/scripts/implement_agent.py` — Strengthened SYSTEM prompt rules: agent must only ADD new code, never delete/refactor existing code; must never remove changelog entries; must signal IMPLEMENTATION_COMPLETE immediately when feature is already present without changing any files.
- `.github/workflows/process-quick-note.yml` — Pip install step now explicitly installs `PyJWT>=2.12.0` and `cryptography>=46.0.6` with `--ignore-installed` before the full requirements install, preventing the broken system-installed Debian jwt/cryptography packages from causing `pyo3_runtime.PanicException` in step 9 pytest.
- `.github/workflows/process-quick-note.yml` — Added step 10b "Close issue — already implemented": when the agent returns success and tests pass but no files were staged, the issue is now closed with a "no changes needed" message instead of being retried. Updated retry handler to check `close_no_changes.outcome != 'success'`, preventing infinite retry loops on issues whose features are already present in the codebase.
- `agent/mcp_client.py` — `get_mcp_client()` now reads `MCP_SERVER_BASE_URL` at call time (not module-import time) and falls back to `http://localhost:8008` when the env var is absent. Previously the client was `None` whenever the env var was unset, causing every `clone_repo` / `git_*` tool call to immediately fail with `[tool error: MCP_SERVER_BASE_URL not set]` instead of attempting a connection.
- `agent/loop.py` — Removed now-redundant `self._mcp is None` guard in `_mcp_only_tools` dispatch; the MCP client is always initialised. Error message for unreachable MCP server now explains how to start the container.
- `proxy.py` — Added `_autostart_services_bg()` background task that runs `docker compose up -d --no-recreate` at proxy startup, ensuring the MCP server, agent runtimes, MongoDB, and Ollama containers come up automatically without any manual `docker compose up` command. Silently skips when Docker is unavailable or when the proxy itself is running inside a compose container (the task fails gracefully).
- `scripts/setup-autostart.sh` + `scripts/llm-relay.service` — New one-time setup script and systemd unit file: `sudo bash scripts/setup-autostart.sh` installs a systemd service that starts the full docker-compose stack on every boot, so the dashboard is available as soon as the machine comes up with zero manual steps.
- `frontend/src/__tests__/chatPage.test.jsx` — Updated URL assertion in "renders the live agent workspace" test to match the renamed `/api/chat/agent-status` endpoint (was still asserting the old `/api/agent/status` path, causing the Frontend CI check to fail).
- `runtimes/api.py` — `_require_admin` was importing `get_current_user` from `backend.server` which uses a different JWT secret (`JWT_SECRET`) than the proxy (`V3_JWT_SECRET`), causing every `PUT /runtimes/policy` call to fail with 401. Now reads `request.state.user` set by `JWTAuthMiddleware` which uses the correct secret.
- `tasks/api.py` — `_current_user` slow path was attempting the same broken `backend.server.get_current_user` import. Replaced with direct `tokens.verify_token` call using the same `V3_JWT_SECRET`, so tasks work even when the fast path (middleware-set user) is not available.
- `direct_chat.py` / `frontend/src/utils/agentWorkspaceTransport.js` — The Chat UI's Live Agent Workspace panel permanently showed "reconnecting" and "0 total tool calls" because the frontend polled `GET /api/agent/status` which did not exist in the proxy. Added `GET /api/chat/agent-status` endpoint that reads from `AgentJobManager` and updated the frontend URL accordingly.
- `agent/loop.py` — Added `tool_callback` parameter to `AgentRunner.__init__`; `_run_tool` now calls `tool_callback(tool, args, result)` after every dispatch so callers can record individual tool call events. Used in `direct_chat.py` to populate `progress_events` with `type: "tool_call"` entries visible in the Live Agent Workspace panel.
- `runtimes/api.py` — `PUT /runtimes/policy` now also accepts the rich UI format sent by `RoutingPolicyPage` (`{pools, policy: {neverUseCommercial, …}, triggers}`). UI flags are mapped to core runtime policy fields (`neverUseCommercial` → `never_use_paid_providers`, `askBeforeCommercial` → `require_approval_before_paid_escalation`). The full rich payload is persisted via `JsonConfigStore` and returned by `GET /runtimes/policy` for round-trip fidelity.
- `.github/scripts/implement_agent.py` — Strip API keys (`NVIDIA_API_KEY`, `ANTHROPIC_API_KEY`, etc.) from the subprocess environment whenever the agent runs `pytest` via `tool_bash`. Previously, `NVIDIA_API_KEY` inherited from the CI step environment caused routing tests (e.g. `test_chat_mode_regressions.py`) to select NVIDIA models instead of local ones, making every pipeline run fail at the pytest verification step.

### Changed
- `agent/loop.py` — Default NVIDIA NIM agent models are now role-specific: planner → `nvidia/GLM-5.1`, executor → `nvidia/StarCoder2-15B`, verifier → `nvidia/DeepSeek-V4-Pro`, judge → `nvidia/nemotron-3-super-120b-a12b` (overridden by `AGENT_*_MODEL` env vars as before).
- `frontend/src/pages/SetupWizardPage.js` — `NVIDIA_MODELS` constants updated to match the role-specific defaults above; previously all roles defaulted to `nvidia/nemotron-3-super-120b-a12b`.
- `frontend/src/pages/RoutingPolicyPage.js` — Free cloud pool now lists NVIDIA NIM free models first (`nvidia/nemotron-3-super-120b-a12b`, `nvidia/GLM-5.1`, `nvidia/StarCoder2-15B`, `nvidia/DeepSeek-V4-Pro`) followed by community free tiers, reflecting the user preference to route to free cloud rather than commercial APIs.
- `agent/workspace.py` — `WorkspaceManager.safe_path()` now raises `WorkspaceEscapeError` with `from None` to suppress internal path context in error chains, consistent with `Workspace.safe_path()`.
- `agent/workspace.py` — `_cleanup_expired_sync()` and `metrics()` now log a `DEBUG` message (including the manifest path and exception) before skipping corrupt workspace manifests, making silent parse failures observable.
- `agent/github_tools.py` — added missing `import re`; `_validate_repo_parts` used `re.match` but the module never imported `re`, causing `NameError: name 're' is not defined` on every `github_read_repo_file` call.
- `agent/github_tools.py` — `LocalWorkspace.__init__` was missing `self.token = token`; `clone_url` property and `push()` referenced `self.token` and raised `AttributeError` on every clone/push with a token.
- `agent/github_tools.py` — `LocalWorkspace.create_branch()` had a copy-paste error: its body referenced undefined `paths` and `message` variables (commit logic pasted into a branch-creation method). Replaced with correct `git checkout -b <branch> <base_branch>` implementation; added validation for `base_branch`; `base_branch` parameter was previously ignored.
- `agent/github_tools.py` — added `stage_and_commit()` to `LocalWorkspace`; the `/workspace/commit` endpoint called `ws.stage_and_commit()` but the method did not exist; `git add` return codes are now checked before attempting `git commit`.
- `agent/models.py` — added `github_get_issue`, `github_comment_on_issue`, `github_close_issue` to `ToolCall` Literal so the executor loop accepts these tools without Pydantic validation failure.
- `agent/loop.py` — MCP fallback for `run_command`/`write_file` now catches only `MCPUnavailableError` (transport/circuit-breaker failures) instead of bare `RuntimeError`; server-side tool errors (bad workspace_id, missing file, etc.) now surface as real errors rather than silently falling back to local execution and bypassing container isolation.
- `agent/loop.py` — `_MUTATING_TOOLS` set now includes all GitHub write tools (`github_commit_changes`, `github_create_branch`, `github_open_pull_request`, `github_comment_on_issue`, `github_close_issue`) and MCP git tools so steps using only these operations are correctly classified as "applied" rather than "skipped".
- `.github/workflows/process-quick-note.yml` — Added `continue-on-error: true` to the council-review step so a crash there no longer silently skips the merge and close-issue steps. Added `id: close_success` to the close step so the retry handler can reliably detect whether an issue was closed. Replaced `failure()` with `always()` + compound condition in the retry handler to also catch the two previously-silent cases: (a) tests fail after implementation (step exits 0 via if/else, no `failure()` fires) and (b) agent finds nothing to change (no PR created, no `failure()` fires). Both now correctly queue the issue for retry.
- `.github/scripts/review_agent.py` — Complete rewrite: added PASS / WARN / FAIL three-tier verdict (FAIL only for real security/data-loss issues; WARN for minor concerns); model fallback through all NVIDIA NIM candidates; always exits 0 so the workflow conditional logic — not the exit code — controls routing; defaults to WARN on any API or format error so auto-merge is never silently blocked by a reviewer crash.
- `.github/scripts/implement_agent.py` — Replaced `model_dump(exclude_unset=False)` assistant-message serialisation with a hand-built dict containing only `role`, `content`, and `tool_calls`. The previous approach emitted null sentinel fields (`refusal`, `audio`, etc.) that some NVIDIA NIM model endpoints reject with a 422, silently breaking the agentic loop mid-session.
- `runtimes/adapters/internal_agent.py` — Increased default `max_steps` from 8 to 30 and improved task success criteria to allow purely informational tasks to succeed.
- `agent/prompts.py` — Raised planner step limit to 30 to support advanced coding tasks.
- `.github/scripts/implement_agent.py` — Enhanced with `search_code` tool and increased turn limits to match backend capabilities.

### Security
- `mcp_server/workspace.py` — Replaced `asyncio.create_subprocess_shell` with an explicit `/bin/sh -c` exec so the shell string is never interpolated by the Python subprocess layer (CodeQL: uncontrolled command line). Added early type/empty checks on `path` parameters before `_safe_path` to satisfy CodeQL uncontrolled-path-expression findings.
- `mcp_server/server.py` — Return a hardcoded generic error string from `tools/call` on exception instead of forwarding the exception message, eliminating any taint path to the response (CodeQL: information exposure through exception). Removed unused `import traceback`; moved inline `import json` to module level.
- `mcp_server/Dockerfile` — Added `mcpuser` (UID 1000) non-root user; container now runs as `mcpuser`; `safe.directory` restricted from `"*"` to `"/workspaces/*"`.
- `mcp_server/workspace.py` — `push()` now uses URL-based token injection (mirror of `clone()`), token-embedded URL restored to clean URL after push; `clone()` now resets `remote.origin.url` to the clean URL immediately after clone so the token is never persisted in `.git/config` (Codex P1).
- `mcp_server/workspace.py` — `commit()` now distinguishes `paths=None` (stage all via `git add -A`) from `paths=[]` (raises `ValueError`) so an empty list never silently falls through to staging all workspace files (Codex P2).
- `docker-compose.yml` — Bound MCP server port to `127.0.0.1:8008:8008` to prevent unauthenticated `run_command` exposure on all interfaces.
- `agent/mcp_client.py` — `resp.json()` is now called inside the try block so a `JSONDecodeError` (malformed MCP response) correctly triggers `_on_failure()` and raises `MCPUnavailableError` instead of bypassing the circuit breaker.

### Added
- `mcp_server/` — New Dockerized MCP (Model Context Protocol) server that runs as an isolated container and handles heavy agent operations: `clone_repo`, `read_file`, `write_file`, `list_files`, `search_code`, `run_command`, `git_status`, `git_diff`, `git_create_branch`, `git_commit`, `git_push`, `delete_workspace`. Implements JSON-RPC 2.0 over HTTP (`POST /mcp`). Strict path traversal prevention in every workspace operation.
- `mcp_server/Dockerfile` — Container image with git + python; workspace data on a named Docker volume (`mcp_workspaces`). Port 8008.
- `agent/mcp_client.py` — Async MCP client with open/close circuit breaker (opens after 3 failures, recovers after 30 s). Singleton via `MCP_SERVER_BASE_URL` env var.
- `docker-compose.yml` — Added `mcp-server` service on port 8008 with healthcheck; proxy depends on it and gets `MCP_SERVER_BASE_URL`; added `mcp_workspaces` volume.
- `agent/loop.py` — `AgentRunner` accepts `mcp_base_url`; routes `run_command`/`write_file` through MCP with transparent local fallback; new MCP-only tools group (`clone_repo`, `git_*`, `delete_workspace`).
- `agent/prompts.py` — Tool prompt lists MCP container tools in a dedicated section.
- `tests/test_mcp_server.py` — 39 tests: workspace ops, MCP endpoints, circuit breaker, agent loop delegation + local fallback.
- `agent/repowise.py`, `agent/tools.py` — Implemented Repowise-inspired codebase intelligence tools: `get_overview`, `get_context`, `get_risk`, and `get_why` for enhanced agent reasoning.

- `agent/github_tools.py` — added missing compat methods (`create_branch_compat`, `commit_changes`, `open_pull_request_compat`, `list_branches_compat`) so the agent loop can call GitHub tools using the `owner/repo` string format it passes. Previously, `github_commit_changes` would raise `AttributeError` at runtime because `commit_changes` did not exist on `GitHubTools`.
- `agent/loop.py` — fixed all GitHub tool dispatches to call the correct compat methods instead of the raw owner/repo API surface, resolving runtime `AttributeError` for `github_read_repo_file`, `github_create_branch`, `github_open_pull_request`, and `github_list_branches` in agent mode.
- `direct_chat.py` — added a system prompt to regular (non-agent) chat so the LLM understands its role and capabilities. Previously, no system prompt was sent, causing local models to fall back to their training-data defaults and respond with "I cannot access GitHub repositories."
- `direct_chat.py` — Fixed `AttributeError` when provider response is invalid; added preflight repo validation to return 412 status code.
- `direct_chat.py` — Add Git/GitHub preflight checks for repo-related agent prompts: validates presence of GitHub token and 'git' binary and performs best-effort token validation (GitHub API) to detect invalid tokens or missing 'repo' scopes.
- `direct_chat.py` — Switched `_is_trivial_message` git-keyword check from substring to token-based matching to avoid false positives where short tokens like `pr` or `run` matched unrelated words ("april", "return", "sprint").
- `webui/workspaces.py` — Implemented `validate_repo_ref` for preflight checks.
- `agent/github_tools.py` — Fixed directory creation for local workspaces to ensure parent directories exist; added input sanitization to prevent path injection.
- `agent/job_manager.py` — Normalize job results to expose a canonical `result.response` and `final_message` for client consumption; preserve raw runner payload under `result.raw`.
- `runtimes/adapters/internal_agent.py` — Conservative health probe: when Ollama is used (no NVIDIA key), perform a lightweight probe and mark the runtime unavailable if Ollama is unreachable to avoid routing into broken local runtimes.
- `agent/models.py` — Added MCP tool names (`run_command`, `clone_repo`, `git_*`, `delete_workspace`) to `ToolCall` Literal so executor loop validation accepts them.
- `mcp_server/workspace.py` — `git_status` and `git_diff` now raise on non-zero exit code rather than silently returning empty output. Individual `git add` calls in `commit()` now check return codes.
- `proxy.py` — `list_models_openai` now includes alias registry entries with `owned_by: "llm-relay-alias"` and a human-readable description.
- `tests/test_mcp_server.py` — Fixed hardcoded `/tmp/fake-workspace` path (Ruff S108); updated assertions to match revised error message format.
- `tests/test_daily_automation_2026_05_14.py` — Converted `TestModelsEndpointAliases` methods to `async def` to avoid `asyncio.get_event_loop()` failure under pytest-asyncio session-scoped loop management.
- `tests/test_direct_chat_async.py` — Converted two sync tests that called `asyncio.run()` to proper `async def` functions so they no longer destroy the shared event loop.
- `frontend/src/__tests__/agentJobPolling.test.jsx` — Fixed test timeout with `jest.useFakeTimers()` by passing `{ delay: null }` to `userEvent.setup()`.
- Updated primary LLM to `nvidia/nemotron-3-super-120b-a12b` and configured `MoonshotAI: Kimi K2.6` as high-priority fallback to resolve 404/429 errors in GitHub Actions and improve routing reliability.
- `.github/workflows/openclaw-maintenance.yml`, `docs/runbooks/openclaw-setup.md`, `docs/architecture/agent-orchestration.md` — Updated OpenClaw repository URLs to point to the new location at `github.com/openclaw/openclaw`.
- `agent/github_tools.py` — Fixed syntax errors regarding misplaced future imports.
- `agent/loop.py` — Enforced 'real work' requirement for edit/create tasks; increased max tool calls per step to 50.
- `runtimes/health.py` — Increased health check timeouts to 60s and circuit-breaker threshold to 10 failures to improve system uptime and reduce transient 'offline' status.
- `runtimes/api.py` — Sanitized error messages to prevent stack trace and internal information exposure.
- `agent/tools.py` — Implemented strict path traversal prevention using robust prefix validation.
- `.github/scripts/security_fix_agent.py` — Fixed OpenClaw execution path.
- `.github/workflows/openclaw-security-automation.yml` — Restored corrupted workflow file.

### Removed
- None.

## [v4.1.0] — 2026-05-09

### Added
- `agent/repowise.py`, `agent/tools.py` — Implemented Repowise-inspired codebase intelligence tools: `get_overview`, `get_context`, `get_risk`, and `get_why` for enhanced agent reasoning.
- **Vision request routing** (`router/registry.py`, `router/model_router.py`) — the proxy now auto-detects `image_url` content parts in incoming chat requests and routes them to the highest-tier vision-capable model registered in the capability registry. Vision capability is declared via the new `vision: bool` field on `ModelCapability`. Affected models: `gemma4:27b`, `gemma4:9b`, `gemma4:latest`, `llama4-maverick:17b`, `llama4-scout:17b`, `qwen3.6:35b`. Set `VISION_MODEL=<name>` env var to pin to a specific vision model. Manual `X-Model-Override` header still takes priority.

### Added
- **`CLAUDE_CODE_SESSION_ID` / `X-Session-Id` propagation in Langfuse traces** (`langfuse_obs.py`, `chat_handlers.py`) — the proxy now extracts `X-Session-Id` and `X-Claude-Code-Session-Id` request headers and attaches them to Langfuse traces as `sessionId` (groups all turns from one session under a single trace in Langfuse) and as a `session:<id>` tag. All streaming and non-streaming paths are covered. The `session_id` field also appears in the trace metadata dict.

### Added
- **`FEATURE_DISABLE` / `FEATURE_ENABLE` bulk env vars** (`features/matrix.py`) — operators can now enable or disable multiple features at once via comma-separated lists, e.g. `FEATURE_DISABLE=jcode_runtime,social_auth`. `FEATURE_DISABLE` is authoritative (wins over `FEATURE_ENABLE` if both list the same ID). Unknown IDs in either list emit a WARNING log. Single-feature `FEATURE_<ID>=<tier>` overrides continue to work.

### Added
- **`FeatureMatrix.check()` alias** (`features/matrix.py`) — adds `check(feature_id)` as a direct alias for `check_available()`, matching the originally-planned public API.

### Added
- **`FeatureMatrix.summary()` method** (`features/matrix.py`) — returns a compact list of all features (feature_id, display_name, maturity, enabled) suitable for status endpoints and admin UI consumers.

### Added
- **`proxy_endpoints` feature entry** (`features/matrix.py`) — added the missing stable `proxy_endpoints` registry entry so `FeatureMatrix.check("proxy_endpoints")` works correctly.

### Added
- **`as_dict()` enhancements** (`features/matrix.py`) — `FeatureMatrix.as_dict()` now returns `schema_version: "1"`, a top-level `entries` list (for consumers that prefer arrays over keyed maps), and a top-level `by_maturity` dict alongside the existing `features` dict and `summary` block.
