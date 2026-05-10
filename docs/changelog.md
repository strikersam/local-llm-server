# Changelog

## [Unreleased]
### Fixed
- `agent/github_tools.py` — Fixed syntax errors regarding misplaced future imports.
- `agent/loop.py` — Enforced 'real work' requirement for edit/create tasks; increased max tool calls per step to 50.
- `runtimes/health.py` — Increased health check timeouts to 60s and circuit-breaker threshold to 10 failures to improve system uptime and reduce transient 'offline' status.
- `runtimes/api.py` — Sanitized error messages to prevent stack trace and internal information exposure.
- `agent/tools.py` — Implemented strict path traversal prevention using robust prefix validation.
- `.github/scripts/security_fix_agent.py` — Fixed OpenClaw execution path.
- `.github/workflows/openclaw-security-automation.yml` — Restored corrupted workflow file.
- `direct_chat.py` — Improved triviality filters to better handle coding-related requests in agent mode; fixed syntax errors.


### Fixed
- `runtimes/control.py` — Expanded Docker-socket error detection to handle overlay mount failures in CI; added port-conflict resolution by killing existing processes on target ports before starting local runtimes.
- `runtimes/api.py` — Updated `/start` and `/stop` endpoints to return informational 200 payloads for remote-managed or Docker-unavailable environments; sanitized error messages to prevent stack trace exposure.
- `agent/github_tools.py` — Fixed directory creation for local workspaces to ensure parent directories exist; added input sanitization to prevent path injection.

### Changed
- `runtimes/adapters/internal_agent.py` — Increased default `max_steps` from 8 to 30 and improved task success criteria to allow purely informational tasks to succeed.
- `agent/prompts.py` — Raised planner step limit to 30 to support advanced coding tasks.
- `.github/scripts/implement_agent.py` — Enhanced with `search_code` tool and increased turn limits to match backend capabilities.

## [v4.1.0] — 2026-05-09

### Added
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
