# Changelog

<!-- Format: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)          -->
<!-- Versions: MAJOR.MINOR.PATCH — bump MAJOR for breaking changes,            -->
<!--           MINOR for new features, PATCH for fixes.                        -->
<!-- Every commit or merge to master MUST add an entry to [Unreleased]         -->
<!-- or to the appropriate version section before merging.                     -->

## [Unreleased]

- **Cloud Model Expansion** (`backend/server.py`, `commercial_equivalent.py`):
  - Added official cloud providers: **DeepSeek API**, **Zhipu AI (GLM)**, **AliCloud DashScope (Qwen)**, **MiniMax**, **Google Gemini**, and **Moonshot AI (Kimi)**.
  - Configured flagship models: **DeepSeek-V3/R1**, **GLM-4.5 Air**, **Qwen3.5 397B**, **Gemma 4**, **Kimi-K2.5**, and **MiMo-V2-Flash**.
  - Set **DeepSeek** as the default LLM provider for the platform.
  - Added commercial equivalent pricing for accurate savings estimation on all new models.
  - Updated test suite and documentation to cover all new providers.

## [2.4.1] — 2026-04-11

### Added

- **Enhanced Langfuse Tracking** (`langfuse_obs.py`, `agent/loop.py`, `agent/coordinator.py`, `proxy.py`):
  - Standardised `emit_chat_observation` to support granular `task_name` metadata, enabling better categorization in Langfuse (e.g., "agent-plan", "agent-execute", "generation").
  - Universal Auth Propagation: Passing authenticated user context (`email`, `department`, `key_id`) down into internal agent model calls. Internal agent planning, execution, and verification steps are now correctly attributed to the calling user in Langfuse.
  - Legacy Endpoint Tracking: Added tracking for direct (non-streaming) model calls to `/api/generate` and `/v1/completions` in `proxy.py`.
  - Instrumented `AgentRunner` and `AgentCoordinator` to ensure all internal LLM interactions are recorded with token usage, latency, and user metadata.

## [2.4.0] — 2026-04-11

### Fixed

- **E701 lint errors in `update_wiki_page`** (`backend/server.py`): Three inline
  `if body.X is not None: updates[...] = ...` statements were split onto separate
  lines to comply with PEP 8 (pycodestyle E701). No behaviour change.

- **Agent chat infinite loading fixed** (`backend/server.py`, `backend/llm_providers.py`, `frontend/src/pages/ChatPage.js`, `frontend/src/index.css`): 
  Fixed an issue where the frontend chat would get stuck in a "thinking" state.
  Added hard `asyncio.wait_for` timeouts (5 min for agent loop, 3 min for simple LLM calls) to prevent backend hangs.
  Stripping of `<think>` tags in `chat_completion_text` is now robust and falls back to `reasoning_content` if the model does not produce ordinary `content`.
  Frontend updated with an animated `ThinkingBubble`, showing a time-elapsed warning after 10s of wait time.

- **Orphaned Google OAuth fragment removed** (`backend/server.py`): ~50 lines of
  indented Google user-upsert code (steps 2-4 of the OAuth callback) were floating
  outside any function body between `@app.post("/api/auth/refresh")` and the LLM
  Engine section — a merge artifact that was unreachable at runtime. The identical
  logic already exists inside the proper `google_oauth_callback` handler; the dead
  copy has been removed.
- **GitHub Integration** (`backend/server.py`, `agent/loop.py`, `frontend/src/`):
  - Full GitHub repo integration available from the GitHub Pages dashboard after login.
  - Expanded GitHub OAuth flow to request `repo` scopes for repository write access and one-click connection.
  - New endpoints for listing user repositories and authorizing specific repos for agent use (`/api/github/repos`, `/api/github/authorize-repos`).
  - File-tree explorer with recursive directory expansion and inline file editor for direct commits.
  - Pull-request panel for viewing and creating PRs without leaving the dashboard.
  - Agent loop migration: Fully transitioned from the legacy three-role orchestration to a unified, tool-capable `AgentRunner` architecture.
  - Secure token injection: The authenticated user's `github_repo_token` is now automatically provided to the agent for direct repository operations (read, branch, commit, PR).
  - UI updates in Settings and chat to manage repository permissions and show connected GitHub identity.

### Fixed

- **GitHub OAuth blocked on mobile browsers** (`backend/server.py`, `frontend/src/api.js`, `frontend/src/pages/SettingsPage.js`):
  Mobile browsers block all popup windows, making the OAuth flow completely non-functional.
  Added a redirect-based OAuth fallback: when `window.open()` returns null (popup blocked),
  both the main Settings connect button and the Re-Auth button now automatically start a new
  OAuth request with `redirect=true` and navigate the current tab to the GitHub authorization
  URL. The backend callback detects the flag from the stored state document and issues a
  `RedirectResponse` to `/settings?github_authorized=true` (or `?github_error=<msg>` on
  failure) instead of the popup postMessage page. The settings page detects these query
  params on mount, refreshes GitHub status, shows feedback, and cleans up the URL.

- **Settings page GitHub buttons broken** (`frontend/src/pages/SettingsPage.js`):
  - "Open GitHub Repos" button used a plain `<a href="/github">` anchor causing a full
    page reload in the React SPA; replaced with React Router `<Link to="/github">` for
    proper client-side navigation.
  - Re-Auth / Connect GitHub buttons in `GitHubAccessSection` silently swallowed all
    errors (`catch { setConnecting(false); }`), leaving the user with no feedback when
    OAuth was not configured or the popup was blocked. Now shows an inline error message
    for each failure case (OAuth not configured, popup blocked, postMessage auth failure,
    API error).
  - Re-Auth button is now hidden when `oauth_enabled` is false (no GitHub OAuth
    credentials set) instead of being clickable but non-functional.
  - "Connect GitHub" button in the not-connected state of `GitHubAccessSection` now
    shows a configuration hint instead of a broken button when OAuth is not set up.

- **`@app.on_event("startup")` deprecation warning** (`backend/server.py`): Replaced the
  deprecated FastAPI startup event hook with a proper `@asynccontextmanager` lifespan
  handler, eliminating the deprecation warning on every import.

- **Anthropic compat + OpenAI chat return 500 when Ollama is unreachable** (`handlers/anthropic_compat.py`,
  `chat_handlers.py`): `httpx.ConnectError` was unhandled in `_post_anthropic_with_fallback`
  and the OpenAI chat fallback loop. Both now catch `httpx.ConnectError` and raise HTTP 503
  with a readable `"LLM backend unreachable: …"` message — consistent with `webui/router.py`.

- **`bash` and `text_editor` 2025 variants not stripped from Anthropic tool list**
  (`handlers/anthropic_compat.py`): `_SERVER_TOOL_TYPES` was missing `bash_20250124` and
  `text_editor_20250124`. These newer Claude Code tool variants were forwarded to Ollama
  unchanged, causing downstream errors. Both variants are now stripped alongside their
  2024 counterparts.

- **`/agent/terminal/run` field named `cmd` instead of `command`** (`proxy.py`):
  `TerminalRunRequest.cmd` renamed to `command` (list of strings) to match the naming
  convention used across every other command-running endpoint in the codebase and the
  README description.

- **`/agent/commits` returns phantom entries from multiline commit bodies** (`agent/commit_tracker.py`):
  `CommitTracker.log()` was splitting `git log` output on `\n\n` which also matches blank
  lines inside multi-paragraph commit bodies. Switched to a NUL-byte record separator
  (`--format=%x00%H|%s|%b`, split on `\x00`) so blank lines in bodies are harmless.

- **`/admin/api/status` crashes on Linux** (`service_manager.py`): `_find_pid()` now
  returns `None` immediately on non-Windows platforms instead of attempting to invoke
  `powershell`, which does not exist on Linux/macOS. The endpoint now returns a valid
  JSON response with all services reported as `running: false` on non-Windows hosts.

- **`/ui/api/providers/{id}/models` returns 500 when provider unreachable** (`webui/router.py`):
  `httpx.ConnectError` and other network errors are now caught and re-raised as HTTP 503
  with a human-readable `detail` message instead of leaking an internal server error.

### Added

- **Social Login (GitHub & Google)** (`backend/server.py`, `frontend/src/`):
  Added support for social sign-in/sign-up via GitHub and Google to the LLM Relay dashboard. Features include:
  - Automatic user registration on first social sign-in.
  - Persistent user tracking in MongoDB (provider, avatar, last login).
  - Activity logging for social authentication events.
  - CSRF protection via state parameter and session-based flow.
  - New frontend buttons and `/auth/callback` route for seamless integration.

- **OpenRouter + Together AI cloud providers** (`backend/server.py`):

  Both providers are now seeded automatically as `openrouter` and `together-ai`. Set
  `OPENROUTER_API_KEY` or `TOGETHER_API_KEY` env vars on Render; the seed logic picks them up
  and applies them to the DB records on every restart (fixing the HF_TOKEN drift bug too).

- **Predefined model catalog** (`backend/server.py`):
  `PREDEFINED_MODELS` lists flagship, balanced, and fast models for every supported provider
  (OpenRouter, HuggingFace, Ollama, Together AI). `GET /api/models/catalog` exposes the full
  catalog with role and tier metadata. `GET /api/providers/{id}/models` now merges live
  models with the predefined catalog so models are always shown even if the API call fails.

- **Multi-agent Planner → Executor → Verifier orchestration** (`backend/server.py`):
  Chat messages are automatically classified as `simple` or `complex`. Complex requests (≥25
  words or containing keywords like "write", "create", "analyze") route through the three-role
  orchestration loop: DeepSeek-R1 plans, Qwen3 executes, DeepSeek-R1 verifies. Each provider
  type maps to optimal role models via `AGENT_ROLE_MODELS`. Applies Anthropic context
  efficiency principles: observation masking (truncate old outputs to ≤300 chars) and context
  compaction (LLM-summarize history >16 messages).

- **Agent mode toggle in chat UI** (`frontend/src/pages/ChatPage.js`, `frontend/src/api.js`):
  A "Agent ON/OFF" button (with a Zap icon) in the chat header forces multi-agent
  orchestration for any message regardless of auto-classification. State persists in
  localStorage. The `agent_mode` flag is sent in every `POST /api/chat/send` request.

### Fixed

- **HF_TOKEN env-var changes not applied to existing DB records** (`backend/server.py`):
  `seed_default_providers` now syncs `api_key` and `base_url` from env vars against existing
  provider records on every startup. Previously, setting `HF_TOKEN` on Render after the first
  deployment had no effect because the seeder skipped existing records.

- **"Input should be a valid string" error on new agent chat sessions** (`backend/server.py`):
  `ChatMessage.session_id` and `ChatMessage.model` were typed as `str` with default `None`,
  which Pydantic v2 rejects when the frontend sends `null`. Fixed both to `str | None = None`.

- **`[object Object]` error in LLM RELAY agent chat** (`frontend/src/pages/ChatPage.js`):
  Used the existing `fmtErr()` helper (already in `api.js`) to format FastAPI's `detail` array
  in the chat error display. Previously the raw array was coerced to string in the template
  literal, producing `Error: [object Object]`.

- **`[object Object],[object Object]` error in agent chat UI** (`webui/frontend/src/api.ts`):
  All API error handlers now parse FastAPI's `{"detail": ...}` response format — plain string
  details are shown as-is, and validation error arrays (Pydantic 422 responses) have their
  `msg` fields joined with `; ` separators. Previously the raw array was coerced to string,
  producing the useless `[object Object],[object Object]` message.

### Added

- **Dashboard provider support: Hugging Face (serverless) + Ollama** (`backend/server.py`, `backend/llm_providers.py`, `frontend/src/pages/ChatPage.js`, `frontend/src/api.js`):
  The dashboard chat can now select a provider + model, with a seeded **Hugging Face (Serverless)** provider (HF router)
  and a robust **Ollama** default (OpenAI-compat with fallback to native `/api/chat`).

- **Context compaction** (`agent/context_manager.py`, `agent/loop.py`, `agent/prompts.py`):
  When session history exceeds the compaction threshold (default 16 messages) the harness
  asks the planner model to summarise the old portion into a concise note.  The summary
  replaces old messages; the most recent context is kept verbatim.  Implements the
  compaction strategy described in Anthropic's "Scaling Managed Agents" article (April 2026).

- **Observation masking** (`agent/context_manager.py`, `agent/loop.py`):
  Old tool outputs in the executor inspection loop are now truncated to ≤300 chars while
  tool-call records remain visible.  The last 4 observations are passed verbatim; earlier
  ones are summarised.  Pattern from JetBrains Junie, cited in the Anthropic managed-agents
  article.

- **Just-in-time retrieval tools** (`agent/tools.py`, `agent/prompts.py`, `agent/models.py`):
  Two new executor tools implement the three-tier JIT hierarchy:
  - `head_file(path, lines=50)` — reads only the first N lines; avoids bloating context with
    large files during the inspection phase.
  - `file_index(path, max_entries=100)` — lightweight listing with line counts and byte sizes
    (~150 chars per entry); always-loaded tier for workspace orientation.
  The tool-selection prompt now guides the executor to start with `file_index`/`search_code`,
  escalate to `head_file`, and only call `read_file` when the full file is truly needed.

- **Append-only event log** (`agent/state.py`, `agent/models.py`):
  `AgentSessionStore` now maintains a durable `agent_events` table — a positional, append-only
  event stream that lives outside the LLM context window.  Mirrors the session design in
  Anthropic's Managed Agents architecture.  New public API:
  - `append_event(session_id, event_type, payload)` — append a typed event
  - `get_events(session_id, from_position=0, limit=200)` — positional slice query
  The harness logs key events (`user_message`, `step_start`, `step_complete`, `compaction`,
  `assistant_message`) automatically during `AgentRunner.run()`.

- **Sub-agent condensed summaries** (`agent/context_manager.py`, `agent/loop.py`):
  `ContextManager.condense_step_result()` trims step results to ~2k tokens before storing
  in the event log, keeping the orchestrator's context lean.  Implements the 1–2k token
  sub-agent summary pattern from the Anthropic managed-agents article.

- **Resilient tool dispatch** (`agent/loop.py`):
  `_run_tool` now wraps all tool invocations in a try/except and returns `[tool error: ...]`
  strings instead of raising.  The harness catches sandbox failures as tool-call errors and
  feeds them back to the model — matching Anthropic's decoupled Brain/Hands model where
  container failures are handled gracefully.

- **`ContextManager` class** (`agent/context_manager.py`):
  New standalone module implementing all context-engineering strategies.  Tuneable via
  constructor kwargs (`mask_after`, `compact_after`, `jit_file_limit`).

- **`AgentEvent` model** (`agent/models.py`):
  New Pydantic model for event log entries with `event_type`, `payload`, `timestamp`,
  and monotonic `position` fields.

- **`AgentSession.event_count`** (`agent/models.py`, `agent/state.py`):
  Sessions now track the total number of events appended so the harness can know the
  current log position without loading all events.

- **New test files**:
  - `tests/test_context_manager.py` — 14 tests covering masking, compaction, JIT hints,
    and condensed summaries.
  - `tests/test_event_log.py` — 8 tests covering append, positional slicing, isolation,
    and persistence across store restarts.
  - `tests/test_agent_tools.py` — extended with 6 new tests for `head_file` and
    `file_index` including path-escape rejection.



- **Advisor strategy support in Anthropic compat layer** (`handlers/anthropic_compat.py`):
  Server-side beta tool types (`advisor_20260301`, `computer_use_*`, `web_search_20250305`,
  `text_editor_20241022`, `bash_20241022`) are now stripped before forwarding to Ollama
  instead of being passed through (which caused downstream errors). Advisor result blocks
  in message history (`server_tool_use`, `advisor_tool_result`) are converted to plain-text
  context so local models still benefit from advice generated by the real Anthropic API.
- **`docs/architecture/advisor-strategy.md`**: New doc explaining the Anthropic advisor
  strategy, how this proxy handles it (graceful degradation), and how the local
  Planner/Executor/Verifier system parallels the advisor pattern.

### Fixed

- **Dashboard OpenAI-compatible calls fixed** (`backend/server.py`): providers now call their OpenAI-compatible base URL directly (no extra SDK), with `Authorization: Bearer ...` support when an API key is configured.
- **Docker dashboard profile added** (`docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.dashboard.frontend`): `docker compose --profile dashboard up` starts Mongo + API + Web UI on ports 27017/8001/3000.
- **Browser automation stability** (`agent/browser.py`): browser automation is disabled by default unless `BROWSER_AUTOMATION_ENABLED=true`, preventing flaky Playwright shutdown hangs in tests/CI.

- **render.yaml completely rewritten**: Previous file deployed a MongoDB-based wiki project instead of the actual FastAPI proxy. Now correctly uses the main `Dockerfile`, correct health-check path (`/health`), and the right env vars (`OLLAMA_BASE`, `API_KEYS`, `ADMIN_SECRET`, `KEYS_FILE`, etc.).
- **docker-compose.yml rewritten**: Removed stale MongoDB/LLM-wiki services. Default stack is now `ollama` + `proxy`. Optional profiles: `--profile tunnel` (Cloudflare Tunnel, free) and `--profile ngrok`. The proxy is now the default service instead of being buried under the `full` profile.
- **deploy-frontend.yml workflow fixed**: Was deploying the old `frontend/` (llm-wiki CRA project) instead of `webui/frontend/` (the actual Vite-based web UI). Fixed all paths, replaced `REACT_APP_*` env vars with `VITE_*`, corrected build output from `build/` to `dist/`.
- **Dockerfile.frontend updated**: Now builds the correct `webui/frontend/` Vite project (was building `frontend/` stale CRA project). Supports `VITE_API_BASE` build arg for GitHub Pages deployment.
- **`/v1/models` now includes Claude model aliases**: The endpoint previously only listed live Ollama models and registry entries. Claude Code and Anthropic SDK clients now see all configured model aliases (e.g. `claude-sonnet-4-6`, `claude-opus-4-6`) in the model list, enabling automatic model discovery.
- **.env.example cleaned up**: Removed stale `MONGO_URL` / `DB_NAME` vars. Added Cloudflare Tunnel and ngrok setup instructions, Claude Code / Cursor / Aider configuration guide.
- **`MODEL_MAP` parser bug fixed** (`router/model_router.py`): `pair.index(":")` was used to split alias pairs, which only works when the destination model name contains no colons. Model names like `qwen3-coder:30b` contain a colon, so `MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b` was silently misparsed. Fixed to `pair.split(":", 1)`.
- **`KeyStore` corruption handling added** (`key_store.py`): `_load_unlocked` previously crashed silently if `keys.json` contained invalid JSON (disk corruption, partial write, etc.). Now catches `JSONDecodeError` / `OSError`, logs a warning, and resets to an empty store instead of leaving keys in an undefined state.
- **`Dockerfile` health check added**: Container now declares a `HEALTHCHECK` using Python's built-in `urllib` (no extra dependency) so Docker, Render, and `docker-compose` all get live readiness signals from `/health`.
- **Vercel deployments removed**: Added `vercel.json` with `github.enabled: false` to disable Vercel's GitHub integration and stop failing deployment statuses.
- **pytest collection fixed**: Added `pytest.ini` restricting test discovery to `tests/` — prevents root-level integration scripts (`backend_test.py`, `backend_test_iteration3.py`) from breaking CI.

### Added

- **`VITE_API_BASE` support in web UI**: `webui/frontend/src/api.ts` now reads `VITE_API_BASE` at build time. When empty (default), all API calls use relative paths (works on Render single-container). When set to an absolute URL (e.g. the Render service URL), the frontend can be hosted separately on GitHub Pages and still reach the backend.
- **Cloudflare Tunnel profile in docker-compose.yml**: `docker compose --profile tunnel up` starts a `cloudflared` container providing a free public HTTPS URL for the proxy — no account or port-forwarding required for quick tunnels.
- **Persistent agent memory** (`agent/user_memory.py`): SQLite-backed `UserMemoryStore` lets agents save and recall per-user key/value facts across sessions and server restarts. New `save_memory` / `recall_memory` tools are available to the agent executor.
- **Durable session history** (`agent/state.py`): `AgentSessionStore` now writes sessions and message history to SQLite (`.data/agent.db`, overridable via `AGENT_DB_PATH`). All sessions survive server restarts.
- **Memory-aware planning** (`agent/prompts.py`): the planner system prompt is injected with the user's stored profile preferences so the agent can personalise responses from the first message.
- **`.claude/agents/scout.md`** — Scout agent: 5-dimension confidence scoring returns GO (≥70) or HOLD (<70) with gap list. Supports DEV/REVIEW/RESEARCH context modes.
- **`.claude/skills/pro-workflow/SKILL.md`** — Master workflow skill: Research → Plan → Implement with 8 core patterns, model selection guide, and validation gates between phases.
- **9 additional `.claude/skills/`** — smart-commit, wrap-up, learn-rule, replay-learnings, parallel-worktrees, session-handoff, insights, deslop, plus `CLAUDE.md` updated with full skill reference.

### Added — 19 new agent features (fully implemented + tested)

New modules in `agent/`:

- **`agent/memory.py`** (`SessionMemory`) — snapshot and restore agent session state to/from disk; no external DB required
- **`agent/context.py`** (`ContextCompressor`) — three context compression strategies: `reactive` (drop oldest), `micro` (deduplicate), `inspect` (stats only)
- **`agent/permissions.py`** (`AdaptivePermissions`) — infer `read_only` / `read_write` / `full_access` from session transcript
- **`agent/token_budget.py`** (`TokenBudget`, `BudgetExceededError`) — per-session token spend cap with `record()` / `check()` / `reset()`
- **`agent/coordinator.py`** (`AgentCoordinator`, `WorkerSpec`) — run N worker AgentRunners in parallel under one coordinator with `max_concurrent` semaphore
- **`agent/background.py`** (`BackgroundAgent`, `BackgroundTask`) — always-on worker thread that drains a task queue; wires webhooks, scheduler, and watchdog events
- **`agent/scheduler.py`** (`AgentScheduler`, `ScheduledJob`) — cron-based job scheduling via APScheduler; manual webhook trigger via `trigger(job_id)`
- **`agent/playbook.py`** (`PlaybookLibrary`, `Playbook`, `PlaybookRun`) — named multi-step automation playbooks; register from code or JSON files, start/finish runs
- **`agent/watchdog.py`** (`ResourceWatchdog`, `WatchedResource`, `WatchEvent`) — poll URLs/files by SHA-256 hash; fire `on_change` callback on state change
- **`agent/commit_tracker.py`** (`CommitTracker`, `CommitAttribution`) — add `Agent-Session / Agent-Model / Agent-Tool / Agent-Timestamp` git trailers to attributed commits
- **`agent/scaffolding.py`** (`ProjectScaffolder`, `Template`) — three built-in project templates (`python-library`, `fastapi-service`, `cli-tool`); custom JSON templates supported
- **`agent/skills.py`** (`SkillLibrary`, `Skill`) — auto-index `.claude/skills/**/SKILL.md`; keyword search; MCP-hosted skill registration
- **`agent/terminal.py`** (`TerminalPanel`, `TerminalSnapshot`) — capture rendered terminal buffer via `tmux capture-pane`; run+capture helper for commands
- **`agent/browser.py`** (`BrowserSession`, `BrowserAction`) — Playwright-backed browser automation (navigate, click, fill, screenshot, evaluate); stub mode when Playwright not installed
- **`agent/voice.py`** (`VoiceCommandInterface`, `TranscriptionResult`) — base64 audio → text transcription via Whisper API or local `openai-whisper`; stub mode when neither available

New API routes in `proxy.py` (45 new endpoints across 10 groups):
- `/agent/memory/*` — snapshot, restore, list, delete session memory
- `/agent/context/*` — compress and inspect context history
- `/agent/sessions/{id}/snip` — conversation surgery (remove messages by index)
- `/agent/sessions/{id}/permissions` — adaptive permission assessment
- `/agent/budget/*` — set/get/list token spend caps
- `/agent/coordinate` — multi-agent coordinator dispatch
- `/agent/background/*` — background task queue
- `/agent/scheduler/*` — cron job CRUD + trigger
- `/agent/playbooks/*` — playbook CRUD + run lifecycle
- `/agent/watchdog/*` — resource watch CRUD + manual check
- `/agent/scaffolding/*` — template list + apply
- `/agent/skills/*` — skill list, search, MCP registration
- `/agent/commits` — AI-attributed commit log
- `/agent/terminal/*` — terminal snapshot + command capture
- `/agent/browser/*` — browser start/stop/action
- `/agent/voice/*` — voice status + transcription

Tests: 155 new tests across 11 new test files; total suite 210 tests, all passing.

- `README.md`: updated with all 19 features documented in plain language with API reference tables for each group.

### Security

- `README.md`: removed hardcoded tunnel domain from documentation; use `NGROK_DOMAIN`
  and placeholders instead.
- `webui/providers.py`: provider API keys are stored server-side only and are never returned in API responses (only `has_api_key`).
- `webui/commands.py`: added an admin-only, allow-listed command runner suitable for public deployments.

### Added — Claude Code–style Web UI

- `webui/frontend/`: Vite + React SPA served by the proxy (App at `/` + `/app`, Admin at `/admin/app`) with chat + agent run UI, repo/workspace browsing, and provider/workspace management.
- `webui/router.py`: Web UI JSON API (`/ui/api/*`) and Admin config APIs (`/admin/api/providers`, `/admin/api/workspaces`, `/admin/api/commands/run`).
- `webui/providers.py` + `webui/workspaces.py`: provider/workspace registries (local workspace by default; optional git-cloned workspaces).
- `Dockerfile` + `.dockerignore`: container build that bundles the SPA and serves it from FastAPI (no external static hosting required).
- `docs/deploy/cloud-run.md` + `docs/deploy/docker.md`: deployment guides for a public, worldwide URL and for container hosts.

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

- `proxy.py`: agent run endpoints now accept optional `provider_id`/`workspace_id` to run against a selected provider and workspace (backwards-compatible defaults preserved).
- **`.gitignore`** — replaced blanket `.claude/` exclusion with targeted exclusions for
  ephemeral Claude Code session files only; project-level AI engineering files in `.claude/`
  are now tracked.

- **`.githooks/prepare-commit-msg`** — updated to reference the new `.claude/hooks/`
  path and clarify that it is soft-reminder only; the blocking version is in `.claude/hooks/commit-msg`.

### Fixed

- `tests/conftest.py`: ensure repo root modules (e.g. `proxy.py`) are importable under newer pytest import modes.
- `start_server.sh` + `run_proxy.sh`: automatically prefer the repo `.venv` Python when present (avoids “No module named uvicorn” when system Python lacks deps).
- `templates/admin/login.html`: clarify login method when Windows auth is unavailable (use `ADMIN_SECRET`).
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
