# Changelog

## [Unreleased]

### Changed
- `README.md` / `scripts/sync_readme_gallery.py` / `scripts/gen_webui_screenshots.py` — the README UI tour is now generated from a structured screenshot inventory, built-in web UI captures are grouped under `docs/screenshots/webui/`, and `make ui-docs` refreshes the screenshots, README gallery block, and screenshot manifest together.
- `docs/README.md` / `docs/screenshots/` — documentation is now grouped under a canonical docs index, screenshots are organized by area (`readme/`, `webui/`, `admin/`, `langfuse/`, `telegram/`), and setup scripts now point to the maintained docs instead of one-off root guides.

### Fixed
- `backend/server.py` / `provider_router.py` / `tests/test_chat_mode_regressions.py` / `tests/test_provider_router.py` / `tests/test_provider_failover_integration.py` — direct chat now uses bounded per-provider timeouts, retries healthy fallbacks without keeping a broken model pin, and returns a stable in-chat recovery/diagnostic message instead of bubbling raw 502/503 failures when the first provider stalls or goes down.
- `.gitignore` / tracked repo artifacts — removed stale backup files, generated logs, historical test reports, and redundant root-level setup transcripts that were making the repository hard to navigate and easy to desynchronize.
- `launcher.py` / `remote-admin/*.html` / `github-pages-*.html` / docs examples — replaced hardcoded tunnel URLs, personal filesystem paths, and user-specific placeholder names with generic defaults so the repo no longer leaks machine-specific setup details.

### Security
- `QUICK_START.md` / `DEPLOYMENT_GUIDE.md` and related generated root notes — removed outdated setup transcripts that embedded environment-specific API keys, tunnel URLs, and local machine details from versioned top-level docs.

### Changed
- `frontend/src/pages/ControlPlanePage.js` / `frontend/src/pages/DashboardLayout.js` — replaced the root hosted dashboard with a more mobile-first workspace overview: usage and provider priority live at the top, task/routing/agent/provider/runtime/schedule sections are grouped into clearer operational cards, and the primary sidebar entry is now simply **Dashboard**. Legacy `/dashboard`, `/control-plane`, and `/llmrelay` URLs now funnel back to the root dashboard instead of leaving stale entry points behind.
- `frontend/src/pages/SetupWizardPage.js` / `backend/server.py` / `provider_router.py` / `.github/scripts/implement_agent.py` / `.github/scripts/review_agent.py` — NVIDIA defaults now prioritize `nvidia/nemotron-3-super-120b-a12b` wherever the repo chooses a hosted default model, while still keeping the coder-specific Qwen path available for code-heavy execution.
- `backend/server.py` / `agent/loop.py` / `frontend/src/pages/ChatPage.js` / `frontend/src/components/*` — agent-mode chat now creates durable telemetry sessions, exposes live `/api/agent/status` + `/api/agent/stream` updates, logs tool-call progress, and renders a mobile-friendly live workspace in chat so complex tasks show real planning, execution, verification, and tool activity instead of a static spinner.
- `frontend/src/pages/SetupWizardPage.js` / `setup/api.py` / `frontend/src/pages/SettingsPage.js` — the setup wizard now reopens completed setups for editing, preserves saved choices for later changes, surfaces the backend-provided Langfuse host as the default telemetry URL, and adds an explicit Settings shortcut back into the wizard.
- `runtimes/adapters/task_harness.py` / `runtimes/manager.py` / `frontend/src/pages/SetupWizardPage.js` — the external long-running harness integration is now branded generically as **Task Harness**, keeping the same JSON/NDJSON bridge capability for complex multi-file tasks without hard-coding upstream naming into the product.

### Fixed
- `frontend/src/pages/AuthCallback.js` / `frontend/src/pages/LoginPage.js` — both social-login callbacks and legacy token callbacks now return users to the root dashboard after auth state sync, and the refreshed login experience once again exposes GitHub and Google sign-in actions instead of dropping social auth from the hosted page.
- `.github/workflows/ci.yml` — CI now runs the GitHub Pages frontend test suite and production build in addition to the Python suite, so mobile/dashboard regressions and auth UI regressions are caught before merge.
- `backend/server.py` / `frontend/src/pages/ChatPage.js` — direct chat now returns a structured Agent Mode handoff for repo / GitHub / container-backed requests, persists that handoff in session history, keeps UUID fallback sessions reloadable/deletable in limited mode, avoids blocking purely explanatory GitHub/Docker questions, adds a pre-send Agent Mode readiness banner, and now also offers direct workflow routing into tracked Tasks and recurring Schedules instead of forcing everything through immediate chat retries.
- `frontend/src/pages/RuntimesPage.js` — on-demand CLI runtimes no longer pretend to support container lifecycle controls; the UI now explains that harnesses like Aider and Task Harness are spawned per task instead of showing misleading Start/Stop controls.

### Added
- `frontend/src/__tests__/controlPlanePage.test.js` / `frontend/src/__tests__/loginPage.test.js` / `frontend/src/__tests__/authCallback.test.js` / `tests/test_provider_router.py` — added regression coverage for the new dashboard summary, preserved GitHub/Google social login affordances, callback redirects, and the new NVIDIA Nemotron default-provider priority.
- `frontend/src/__tests__/chatPage.test.jsx` / `tests/test_chat_mode_regressions.py` — added regression coverage for the new Agent Mode handoff UX, task/schedule workflow suggestions, pre-send readiness banner, one-click retry behavior, persisted session reload behavior, UUID fallback sessions, GitHub/settings escalation hints, explanatory-prompt false positives, and the expanded direct-chat boundary for GitHub + container execution requests.
- `runtimes/adapters/task_harness.py` / `runtimes/manager.py` / `frontend/src/pages/SetupWizardPage.js` — added first-class runtime registration for a compatible external task harness (`run --json` / `--ndjson` bridge), surfaced it in setup/runtime selection, and covered the adapter with runtime tests so long-running harness tasks can participate in agent routing alongside Hermes/OpenCode/Goose/Aider.

### Changed
- `README.md` — refined the human-first README again to improve page traction: replaced the potentially friction-heavy “5-year-old” phrasing, added clearer value framing, a simple benefits table, and more team/adoption-oriented positioning for non-technical readers.
- `README.md` — rewrote the README again with a human-first, screenshot-rich product story aimed at non-technical readers: simpler language, clearer use cases, visual tour, friendlier setup path, and links out to technical docs instead of front-loading route details.
- `docs/api-surfaces.md` — added a separate technical route map so API and surface details live outside the README.
- `README.md` — rewrote the top-level documentation to reflect the current product surface: corrected startup and port guidance, documented the built-in admin/web UI and separate dashboard deployment modes, and added an end-to-end feature inventory covering proxy compatibility, routing, agents, workflows, schedules, GitHub, secrets, sync, observability, and operations.
- `frontend/package.json` / `frontend/package-lock.json` — restored `react-scripts` so the GitHub Pages dashboard can run `npm test` and `npm run build` in CI again.
- `.github/workflows/deploy-frontend.yml` — switched the Pages build install step from `npm ci` to `npm install` so GitHub Pages deployments are not blocked by npm lockfile strictness on the hosted runner image.

### Fixed
- `frontend/src/App.js`, `frontend/src/pages/LoginPage.js`, `frontend/src/__tests__/appRouting.test.js`, and `frontend/src/__tests__/loginPage.test.js` — GitHub Pages deep links such as `/login` and older workspace aliases now land on the real login experience again. The login screen no longer crashes during render from missing icon imports, and unexpected deep links fall back into the standard auth flow instead of hijacking the app.
- `backend/server.py` / `tests/test_chat_mode_regressions.py` — direct chat now refuses to fabricate repo-specific multi-file edit plans when Agent Mode is off. For repository-bound requests it returns a deterministic boundary message asking the user to enable Agent Mode or paste the relevant files instead of hallucinating framework/file details.
- `backend/server.py` — explicit Agent Mode requests now time out early enough for hosted deployments and fall back to a substantive direct recovery answer instead of returning a generic timeout banner or upstream 502 page; the recovery path also retries with the provider default model when an explicit requested model is unavailable and keeps recovery pinned to the same provider chain instead of drifting back to a broken active-provider default.
- `backend/server.py` / `tests/test_chat_mode_regressions.py` — agent-mode chat now seeds the hosted agent loop with the selected provider's default model when the user does not specify one, avoiding invalid planner/executor model selection on deployed cloud providers.
- `tasks/service.py` / `tests/test_tasks_workflow.py` — task execution now has a hard timeout and fails cleanly instead of remaining stuck in `in_progress` forever when a runtime hangs.
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
