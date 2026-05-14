# Changelog

## [Unreleased]
### Fixed
- `.github/workflows/process-quick-note.yml` — Added `continue-on-error: true` to the council-review step so a crash there no longer silently skips the merge and close-issue steps.  Added `id: close_success` to the close step so the retry handler can reliably detect whether an issue was closed.  Replaced `failure()` with `always()` + compound condition in the retry handler to also catch the two previously-silent cases: (a) tests fail after implementation (step exits 0 via if/else, no `failure()` fires) and (b) agent finds nothing to change (no PR created, no `failure()` fires).  Both now correctly queue the issue for retry.
- `.github/scripts/review_agent.py` — Complete rewrite: added PASS / WARN / FAIL three-tier verdict (FAIL only for real security/data-loss issues; WARN for minor concerns); model fallback through all NVIDIA NIM candidates; always exits 0 so the workflow conditional logic — not the exit code — controls routing; defaults to WARN on any API or format error so auto-merge is never silently blocked by a reviewer crash.
- `.github/scripts/implement_agent.py` — Replaced `model_dump(exclude_unset=False)` assistant-message serialisation with a hand-built dict containing only `role`, `content`, and `tool_calls`.  The previous approach emitted null sentinel fields (`refusal`, `audio`, etc.) that some NVIDIA NIM model endpoints reject with a 422, silently breaking the agentic loop mid-session.

### Added
- `agent/repowise.py`, `agent/tools.py` — Implemented Repowise-inspired codebase intelligence tools: `get_overview`, `get_context`, `get_risk`, and `get_why` for enhanced agent reasoning.
### Fixed
- `direct_chat.py` — Fixed `AttributeError` when provider response is invalid; added preflight repo validation to return 412 status code.
- `webui/workspaces.py` — Implemented `validate_repo_ref` for preflight checks.
- Updated primary LLM to `nvidia/nemotron-3-super-120b-a12b` and configured `MoonshotAI: Kimi K2.6` as high-priority fallback to resolve 404/429 errors in GitHub Actions and improve routing reliability.
- `.github/workflows/openclaw-maintenance.yml`, `docs/runbooks/openclaw-setup.md`, `docs/architecture/agent-orchestration.md` — Updated OpenClaw repository URLs to point to the new location at `github.com/openclaw/openclaw`.
- `agent/github_tools.py` — Fixed syntax errors regarding misplaced future imports.
- `agent/loop.py` — Enforced 'real work' requirement for edit/create tasks; increased max tool calls per step to 50.
- `runtimes/health.py` — Increased health check timeouts to 60s and circuit-breaker threshold to 10 failures to improve system uptime and reduce transient 'offline' status.
- `runtimes/api.py` — Sanitized error messages to prevent stack trace and internal information exposure.
- `agent/tools.py` — Implemented strict path traversal prevention using robust prefix validation.
- `.github/scripts/security_fix_agent.py` — Fixed OpenClaw execution path.
- `.github/workflows/openclaw-security-automation.yml` — Restored corrupted workflow file.
- `direct_chat.py` — Improved triviality filters to better handle coding-related requests in agent mode; fixed syntax errors.


### Fixed
- `direct_chat.py` — Fixed `AttributeError` when provider response is invalid; added preflight repo validation to return 412 status code.
- `webui/workspaces.py` — Implemented `validate_repo_ref` for preflight checks.
- `runtimes/control.py` — Expanded Docker-socket error detection to handle overlay mount failures in CI; added port-conflict resolution by killing existing processes on target ports before starting local runtimes.
- `runtimes/api.py` — Updated `/start` and `/stop` endpoints to return informational 200 payloads for remote-managed or Docker-unavailable environments; sanitized error messages to prevent stack trace exposure.
- `agent/loop.py`, `direct_chat.py`, `runtimes/adapters/internal_agent.py` — Prioritized Nvidia free cloud LLMs by setting `nvidia/nemotron-3-super-120b-a12b` as the default model across all agent phases and direct chat when an Nvidia API key is present.
- `agent/github_tools.py` — Fixed directory creation for local workspaces to ensure parent directories exist; added input sanitization to prevent path injection.
- `direct_chat.py` — Add Git/GitHub preflight checks for repo-related agent prompts: validates presence of GitHub token and 'git' binary and performs best-effort token validation (GitHub API) to detect invalid tokens or missing 'repo' scopes.
- `agent/job_manager.py` — Normalize job results to expose a canonical `result.response` and `final_message` for client consumption; preserve raw runner payload under `result.raw`.
- `runtimes/adapters/internal_agent.py` — Conservative health probe: when Ollama is used (no NVIDIA key), perform a lightweight probe and mark the runtime unavailable if Ollama is unreachable to avoid routing into broken local runtimes.

### Changed
- `runtimes/adapters/internal_agent.py` — Increased default `max_steps` from 8 to 30 and improved task success criteria to allow purely informational tasks to succeed.
- `agent/prompts.py` — Raised planner step limit to 30 to support advanced coding tasks.
- `.github/scripts/implement_agent.py` — Enhanced with `search_code` tool and increased turn limits to match backend capabilities.

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
