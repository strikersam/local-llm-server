# Changelog

## [Unreleased]
### Added
- `proxy.py` — `/api/ping` GET endpoint (no auth). Returns `{status: "ok", timestamp: "<ISO-8601 UTC>"}`. Registered before the wildcard `/api/{path:path}` handler so it is never swallowed by the Ollama proxy.
- `tests/test_ping.py` — 4 tests covering status code, response shape, ISO timestamp validity, and auth-free access.
- `agent/agency.py` — CEO agency now handles GitHub `quick-note:*` issues autonomously every cycle: (1) issues with the `quick-note:exhausted` label are auto-closed via the GitHub REST API; (2) open actionable quick-note issues (not exhausted) generate a priority-3 Dev directive dispatched to the ClaudeCode/InternalAgent runtime; (3) quick-note state is surfaced in the CEO LLM prompt so the CEO can reason about pending feature requests. New helpers: `_fetch_github_quick_notes()`, `_close_github_issue()`, `_build_quick_note_instruction()`, `Agency._handle_quick_notes()`.
- `agent/improvement_loop.py` — Added `IssueCategory.QUICK_NOTE` enum value for categorising quick-note feature requests in the improvement state store.

### Added
- `tests/test_mcp_workspace_git.py` — 36 tests covering the full MCP workspace git stack via real JSON-RPC to `/mcp-internal/mcp`: protocol handshake, clone (local bare repo), read/head/list/search, git status/diff, branch creation, commit (all-files and specific-paths), push, full code-change workflow, sequential multi-commit branches, workspace lifecycle, error paths (bad IDs, path traversal, missing files).
- `tests/test_e2e_agent_chat.py` — extended with 13 new tests: GitHub API tools (`create_branch`, `open_pull_request`, `merge_pull_request`, `get_issue`), MCP git agent dispatch (`git_status`, `git_diff`, `git_create_branch`, `git_commit`, `git_push`), full PR workflow (write→commit→push→open PR→merge PR), issue-to-PR workflow, 2-step sequential plan, and post-merge comment chaining.
- `agent/github_tools.py`: `merge_pull_request()` method — merges a PR via `PUT /repos/{owner}/{repo}/pulls/{pr}/merge` with configurable merge method and commit title.
- `agent/loop.py` + `agent/models.py`: `github_merge_pull_request` tool dispatch and `ToolCall` Literal — agents can now merge PRs as part of a workflow.
- `_build_agent_http_mock()` helper in e2e tests — unified httpx mock routing LLM calls, MCP JSON-RPC, and GitHub API (POST/GET/PUT) by URL pattern, enabling full workflow simulation without any real network calls.

### Fixed
- `tests/test_e2e_agent_chat.py`: Reduced `test_agent_full_pr_workflow` and `test_agent_issue_to_pr_workflow` from 5-step to 2-step plans — 5 independent steps exceeded `_PARALLEL_THRESHOLD=3` in `agent/loop.py`, causing `_maybe_run_parallel()` to be invoked instead of the sequential path, which is incompatible with the sequential httpx mock and caused non-deterministic failures on Python 3.13. Also fixed the MCP mock fallback for `tools/call` requests: unknown tools now return `isError: True` instead of an empty success, so mis-dispatched tool calls fail visibly rather than silently succeeding.
- `agent/prompts.py`: `build_tool_prompt()` now lists all GitHub API tools in the executor's "Available tools" section, including `github_create_branch`, `github_open_pull_request`, `github_merge_pull_request`, `github_commit_changes`, `github_list_repos`, `github_list_branches`, and `github_read_repo_file`. Previously only three issue-management tools were listed; the executor model therefore never selected PR/branch tools in real runs. Also fixed parameter name `branch` → `branch_name` in the `github_commit_changes` entry to match the actual dispatch in `_run_tool()`, preventing dropped branch arguments in commit calls.
- `agent/mcp_client.py`: `get_mcp_client()` now constructs a localhost URL (`http://127.0.0.1:{PORT}/mcp-internal`) when `MCP_SERVER_BASE_URL` is not set, instead of returning a no-URL client. The MCP server is mounted in-process, so `clone_repo`, `git_status`, `git_commit` and all other MCP-only tools now reach it automatically without requiring the env var. This fixes the `[tool error: mcp server unreachable]` errors seen on every `clone_repo` call in the Live Agent Workspace, and the downstream `[Errno 2] No such file or directory` failures on `head_file` (which occurred because the repo was never cloned).
- `tests/test_e2e_agent_chat.py`: Strengthened assertions by changing `in {"succeeded", "failed"}` to `== "succeeded"`, ensuring tests fail if the agent job does not succeed.
- `tests/test_browser.py`: Fixed path collision in `test_stub_mode_screenshot` by using the `tmp_path` fixture instead of a hardcoded `/tmp/snap.png`.
- `.github/workflows/agency-cycle.yml`: Added `anthropic` to the dependency installation step to ensure the Anthropic SDK is available for the agency cycle.
- Multiple test files: Added `-> None` return type annotations to async test functions for better type safety and consistency.

- CI: add global git identity (`user.email`, `user.name`, `commit.gpgsign false`, `init.defaultBranch main`) before running pytest — ensures `test_commit_tracker.py` git subprocess calls work correctly across all CI runner configurations.
- CI: add `pytest-timeout>=2.3.1` to requirements and `--timeout=120` to pytest command — prevents hanging tests from occupying the full 6-hour GitHub Actions job limit and makes timeout failures identifiable; 120 s gives slow runners 2-3× headroom over the local 104 s full-suite runtime.
- CI: add `persist-credentials: false` to all `actions/checkout` steps — prevents Post Checkout git credential cleanup from failing with exit code 128 on certain GitHub Actions runners, which was causing all three CI jobs (test, lint, frontend) to report spurious git failures.
- CI: upgrade `github/codeql-action` from v3 to v4 in `codeql.yml` — v3 actions were failing.
- CI: fix `process-quick-note.yml` YAML syntax — bash heredoc content at column 0 conflicted with YAML block scalar indentation rules, causing the parser to fail with "0 jobs". Indented all heredoc content to match the block scalar level (10 spaces); YAML strips the indentation before passing to bash, so the shell correctly sees the heredoc delimiter at column 0.
- Frontend: downgraded `react-router-dom` from `^7.x` to `^6.28.2` — react-router-dom v7 uses ESM sub-path exports (`react-router/dom`) that Jest 27 (bundled with react-scripts@5) cannot resolve, causing all router-dependent tests to fail with "Cannot find module".
- Frontend: added `@testing-library/dom@^10.4.0` to `devDependencies` — `@testing-library/react@16` declares it as a peer dep but npm doesn't auto-install peers, causing "Cannot find module @testing-library/dom" errors.
- Frontend: test isolation — changed CI test command to `--watchAll=false --forceExit --runInBand` to prevent async timer leaks between test suites from causing flaky failures.
- Frontend: updated `controlPlanePage.test.js` to match current v4.1 heading text (was asserting `v4.0`).

- `.github/workflows/auto-merge.yml`, `.github/workflows/pull-request.yml` — Removed reference to non-existent `actions/setup-cli@v1` action (marketplace returns 404). `gh` CLI is pre-installed on `ubuntu-latest` runners; no setup step is needed.
- `.github/workflows/openclaw-security-automation.yml` — Replaced binary-corrupted YAML file with a clean, valid workflow. Also fixed OpenClaw installation to clone from `github.com/openclaw/openclaw` (git clone) instead of `npm install openclaw@latest` (package does not exist on npm).
- `.github/workflows/openclaw-security-automation.yml` — Restored corrupted workflow file.
- `.github/workflows/auto-merge.yml`, `.github/workflows/pull-request.yml` — Removed reference to non-existent `actions/setup-cli@v1` action (marketplace returns 404). `gh` CLI is pre-installed on `ubuntu-latest` runners; no setup step is needed.
- `.github/workflows/openclaw-security-automation.yml` — Replaced binary-corrupted YAML file with a clean, valid workflow. Also fixed OpenClaw installation to clone from `github.com/openclaw/openclaw` (git clone) instead of `npm install openclaw@latest` (package does not exist on npm).
- `.github/workflows/openclaw-security-automation.yml` — Restored corrupted workflow file.
### Added
- `docs/runbooks/ci-troubleshooting.md` — captures all CI/GitHub Actions failure patterns and fixes discovered during v4.1 stabilisation: YAML heredoc indentation rules, `persist-credentials: false`, `pytest-timeout`, react-router-dom v7 + Jest 27 incompatibility, `@testing-library/dom` peer dep, Python 3.13 compatibility status.

- `.github/workflows/auto-merge.yml`, `.github/workflows/pull-request.yml` — Removed reference to non-existent `actions/setup-cli@v1` action (marketplace returns 404). `gh` CLI is pre-installed on `ubuntu-latest` runners; no setup step is needed.
- `.github/workflows/openclaw-security-automation.yml` — Replaced binary-corrupted YAML file with a clean, valid workflow. Also fixed OpenClaw installation to clone from `github.com/openclaw/openclaw` (git clone) instead of `npm install openclaw@latest` (package does not exist on npm).
- `.github/workflows/agency-cycle.yml` (PR #185) — Fixed invalid `actions/checkout@v6` and `actions/setup-python@v6` references; bumped to `@v4` and `@v5` respectively (highest available versions).
- `.github/workflows/openclaw-security-automation.yml` — Restored corrupted workflow file.

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
