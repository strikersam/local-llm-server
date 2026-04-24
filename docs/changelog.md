# Changelog

<!-- Format: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)          -->
<!-- Versions: MAJOR.MINOR.PATCH — bump MAJOR for breaking changes,            -->
<!--           MINOR for new features, PATCH for fixes.                        -->
<!-- Every commit or merge to master MUST add an entry to [Unreleased]         -->
<!-- or to the appropriate version section before merging.                     -->

## [3.1.0] — 2026-04-23

### Overview

Version 3.1 extends the v3 Control Plane with **platform-wide architectural additions**: hardware-aware model routing, GitHub workspace integration with local clone/commit/PR flows, Syncthing-style cross-machine workspace sync, a Power User RBAC tier, per-user encrypted secrets, social login (GitHub + Google OAuth), a 5-step Setup Wizard, comprehensive cost-savings insights, and extended audit visibility. All previously documented v3.0 limitations have been resolved.

### Added — RBAC Power User Role

- **`rbac.py`** — New `UserRole.POWER_USER` intermediate tier. 11 new permissions added (`VIEW_ALL_TASKS`, `MANAGE_WORKSPACE_AGENTS`, `VIEW_WORKSPACE_SECRETS`, `MANAGE_WORKSPACE_SECRETS`, `VIEW_RUNTIME_HEALTH`, `VIEW_ROUTING_DECISIONS`, `MANAGE_WORKSPACE_REPOS`, `VIEW_COST_INSIGHTS`, `UPGRADE_USERS`, etc.). `POWER_USER_ACTIVITY_PERMISSIONS` frozenset exported. UI badge: "Power User" (blue, distinct from Admin amber). New helpers: `is_power_user_or_above()`, `role_label()`, `require_power_user()` FastAPI dependency.
- **Audit log extended** — `audit()` now captures: `secrets_used` (IDs only, never values), `runtime_machine` (runtime ID + hostname), `repo_workspace` (git URL), `agent_id`. New `get_audit_log()` filters: `resource`, `outcome`. Google OAuth token pattern added to `mask_secret()`.

### Added — Hardware-Aware Model Compatibility (`hardware/`)

- **`hardware/__init__.py`** — Package init.
- **`hardware/detector.py`** — `detect_hardware()`: detects CPU (psutil + py-cpuinfo), RAM (psutil), NVIDIA GPU (nvidia-smi), AMD GPU (rocm-smi), Apple Silicon MPS, Intel Arc (xpu-smi). `HardwareProfile`, `GPUDevice` dataclasses. `_MODEL_REQUIREMENTS` database (25 entries covering 0.1B–405B models). `check_model_compatibility()` → `ModelCompatibility` with `COMPATIBLE | DEGRADED | INCOMPATIBLE` labels. `get_hardware_profile()` with 5-min TTL cache. `hardware_router` at `/api/hardware/`: profile, refresh, per-model compat, batch compat.

### Added — User-Scoped Secrets Store (`secrets_store.py`)

- **`secrets_store.py`** — Three scopes: `user` (owner-only), `workspace` (power users+), `global` (admin-only). AES-256-GCM encryption at rest via `cryptography` package (XOR fallback). `SECRET_STORE_KEY` env var. `SecretsStore` with owner isolation. `secrets_router` at `/api/secrets/`. Raw values **never** returned by API. Key hint shown (`sk-pr****xyz`). `MANAGE_WORKSPACE_SECRETS` permission gate for workspace-scope secrets.

### Added — Social Login (`social_auth.py`)

- **`social_auth.py`** — GitHub OAuth (`/api/auth/github/login` → callback) and Google OAuth (`/api/auth/google/login` → callback). CSRF state parameter with 10-min TTL. HMAC-HS256 JWT issuance (`JWT_SECRET` env var, warns if not set). Auto-create `StandardUser` on first login; never auto-downgrades existing roles. `verify_jwt()` for middleware. `/api/auth/me`, `/api/auth/users`, `/api/auth/users/{id}/role` endpoints.
- **`frontend/src/pages/AuthCallback.js`** — Updated to handle both legacy token flow and new v3.1 JWT flow (`?token=...&provider=github|google`).
- **`frontend/src/pages/LoginPage.js`** — Social login buttons already present, now correctly point to `/api/auth/github/login` and `/api/auth/google/login`.

### Added — Setup Wizard (`setup/`)

- **`setup/__init__.py`** and **`setup/api.py`** — 5-step wizard: (1) Provider Setup (Ollama + cloud toggles), (2) Local Model Detection (hardware + Ollama model list), (3) Runtime Config, (4) Default Agent, (5) Policy & Privacy. State persisted per-user in memory. `GET /api/setup/state`, `PUT /api/setup/step/{1-5}`, `POST /api/setup/complete`, `POST /api/setup/reset` (admin). Hardware + model detection endpoints.
- **`frontend/src/pages/SetupWizardPage.js`** — Full 5-step wizard UI with progress bar, hardware display, model picker, and policy toggles. Accessible at `/setup` via nav.

### Added — Cost Insights (`cost_insights.py`)

- **`cost_insights.py`** — `record_usage()`: per-request token/cost tracking. `compute_savings()` and `compute_time_series()`: aggregate savings vs cloud APIs per period (day/week/month). `observability_router` at `/api/observability/`: savings summary, per-user savings (admin), usage breakdown by model.
- **`frontend/src/pages/ObservabilityPage.js`** — Full rewrite with: savings stat cards, time-series bar chart, per-model savings breakdown, savings celebration banner.

### Added — GitHub Workspace Integration (`agent/github_tools.py`)

- **`agent/github_tools.py`** — Extended: `GitHubTools` with `get_repo()`, `list_pull_requests()`, `commit_file()` (backward-compat shims). `LocalWorkspace` class: `clone_or_pull()`, `current_branch()`, `diff()`, `status()`, `create_branch()`, `stage_and_commit()`, `push()` — all using `asyncio.create_subprocess_exec` (never `shell=True`). Token cleared from remote URL after push. `github_router` at `/api/github/`: repos, branches, PRs, workspace init/status/diff/commit.
- Tokens fetched from `SecretsStore` (secrets tagged "github") with env var fallback.

### Added — Workspace Sync (`sync/`)

- **`sync/__init__.py`** and **`sync/service.py`** — `SyncService`: peer management, file index, push/pull per folder, HMAC-authenticated peer-to-peer transfers, conflict detection + `.conflict.{ts}` rename, conflict resolution UI. `sync_router` at `/api/sync/`: status, peers CRUD, push/pull, file index, receive (peer endpoint), conflicts.
- Sync folders: `skills/`, `workspaces/`, `runtime_configs/`, `tool_configs/`. Works offline (queues when peers unavailable).

### Added — Agent Profiles Backend (`agents/`)

- **`agents/store.py`** — `AgentDefinition` model with `owner_id`, `runtime_id`, `task_types`, `cost_policy`, `is_public`, `use_count`. `AgentStore` with MongoDB + in-memory fallback, owner isolation, `list_for_user(include_public=True)`, `list_all()`.
- **`agents/api.py`** — `agent_router` at `/api/agents/`: CRUD, use-count tracking. Power users may create workspace (public) agents. Resolves previous "known limitation" where frontend degraded with empty list.

### Fixed — Paid Escalation

- **`runtimes/routing.py`** — `_escalate_via_provider_manager()`: fully wired to `ProviderManager`. Iterates configured non-local providers, builds OpenAI-compatible chat completion request, logs PAID ESCALATION at WARNING. Daily budget check against `max_paid_escalations_per_day`. Resolves previous "known limitation" with descriptive placeholder error.

### Updated — Frontend

- **`frontend/src/pages/DashboardLayout.js`** — Power User badge (blue). `SetupWizardPage` import + `/setup` route. Version updated to v3.1.
- **`frontend/src/api.js`** — New v3.1 API helpers: hardware (4), secrets (5), auth (3), setup (5), savings (3), GitHub workspace (8), sync (8).

### Updated — Tests

- **`tests/test_rbac.py`** — 12 new tests: Power User permissions, `require_power_user` dependency, audit extended fields, audit filter by user_id.
- **`tests/test_hardware.py`** — 18 new tests: model requirement lookup, COMPATIBLE/DEGRADED/INCOMPATIBLE labelling, GPU VRAM logic, CPU-only fallback, `as_dict` contract.
- **`tests/test_secrets.py`** — 14 new tests: AES-GCM roundtrip, owner isolation, admin bypass, workspace scope, update re-encryption, delete guards.

### Resolved Limitations (from v3.0.0)

1. ✅ Agent profiles backend now implemented (`agents/store.py`, `agents/api.py`).
2. ✅ Paid escalation wired to `ProviderManager` (`runtimes/routing.py`).
3. ✅ Setup Wizard implemented (`setup/`, `SetupWizardPage.js`).
4. ✅ Langfuse cost-savings widgets implemented (`cost_insights.py`, `ObservabilityPage.js`).

---

## [3.0.0] — 2026-04-23

### Overview

Version 3.0 transforms local-llm-server from a smart LLM proxy into a **unified, production-grade, self-hosted AI agent control plane** with multi-runtime orchestration, a task/issue management system, role-based access control, and a comprehensive v3 dashboard.

### Added — v3 Control Plane UI

- **`frontend/src/pages/ControlPlanePage.js`** — New primary post-login landing page (v3). Unified operations dashboard showing: active agents panel, task queue (running/queued/blocked), runtime health grid, schedules due soon, routing decision log, cost-saved summary, alert banner for blocked tasks and circuit-open runtimes.
- **`frontend/src/pages/AgentsPage.js`** — New agent profiles management page. Create/edit/delete agent profiles with name, role, system prompt, preferred runtime, fallback runtimes, task specialization, and cost policy.
- **`frontend/src/pages/TasksPage.js`** — New task/issue management page. Create tasks with title/description/prompt/agent/runtime/priority; track status through todo→in_progress→in_review→blocked→done; retry and escalate actions; execution log display.
- **`frontend/src/pages/RuntimesPage.js`** — New runtime management page. Shows all registered runtimes with health status, capabilities, tier classification, integration mode, and quick-run interface. Routing policy summary panel.
- **`frontend/src/pages/DashboardLayout.js`** — Updated v3 navigation: Operations (Control Plane, Agent Chat, Agents, Tasks), Engineering (GitHub, Wiki, Sources), Infrastructure (Providers, Models, Runtimes, Observability), System (Activity, Admin Portal, Settings). Admin badge in user footer. v3 version label. Lock icon on admin-only nav items.
- **`frontend/src/pages/LoginPage.js`** — Updated version label to "Platform v3.0".
- **`frontend/src/api.js`** — New API methods: listRuntimes, getRuntime, getRuntimeHealth, getRoutingPolicy, updateRoutingPolicy, getDecisionLog, runTaskOnRuntime, listTasks, createTask, getTask, updateTask, deleteTask, retryTask, escalateTask, addTaskComment, approveTaskCheckpoint, getTaskCounts, getDueSoonTasks, listAgents, createAgent, getAgent, updateAgent, deleteAgent, getAuditLog.

### Added — Runtime Abstraction Layer (`runtimes/`)

- **`runtimes/base.py`** — `RuntimeAdapter` ABC, `RuntimeCapability` enum (15 capabilities), `RuntimeTier` enum, `IntegrationMode` enum, `RuntimeHealth`, `TaskResult`, `TaskSpec` dataclasses, `RuntimeUnavailableError`, `RuntimeExecutionError`.
- **`runtimes/registry.py`** — `RuntimeCapabilityRegistry`: adapter registration, capability-based lookup, tier-ordered sorting, task-type capability map.
- **`runtimes/health.py`** — `RuntimeHealthService`: async health polling loop with configurable interval, circuit-breaker (3 failures → OPEN, 60s recovery window), cached health snapshots.
- **`runtimes/routing.py`** — `RuntimeRoutingPolicyEngine`: 8-step routing flow (classify → pick runtime → pick model → execute → retry → fallback → escalate → log), full `RoutingDecision` audit log, `RoutingPolicy` dataclass with local-first defaults.
- **`runtimes/manager.py`** — `RuntimeManager`: top-level orchestrator; owns registry/health/router; singleton via `get_runtime_manager()`; wires all adapters from env config; startup/shutdown lifecycle.
- **`runtimes/api.py`** — FastAPI router at `/runtimes/*`: list, get, health, get/update policy, decision log, per-runtime task execution.
- **`runtimes/adapters/hermes.py`** — Hermes Agent adapter (FIRST CLASS, SIDECAR). Capabilities: code_gen, code_review, file_read_write, tool_use, agent_delegation, scheduled_tasks, memory_sessions, mcp_connectivity, stream_output, autonomous_loop, shell_exec, web_browse.
- **`runtimes/adapters/opencode.py`** — OpenCode adapter (FIRST CLASS, SIDECAR). CLI + HTTP modes. Capabilities: code_gen, code_review, repo_editing, git_ops, file_read_write, tool_use, multi_file_edit.
- **`runtimes/adapters/goose.py`** — Goose adapter (TIER 2, SIDECAR). CLI-based. Capabilities: code_gen, code_review, file_read_write, tool_use, shell_exec.
- **`runtimes/adapters/openhands.py`** — OpenHands adapter (EXPERIMENTAL, EXTERNAL_PROCESS). Docker-based; clearly labelled experimental. REST API integration with conversation polling.
- **`runtimes/adapters/aider.py`** — Aider adapter (TIER 3, EXTERNAL_PROCESS). Git-aware targeted file editing. `--message` non-interactive mode.

### Added — Task / Issue System (`tasks/`)

- **`tasks/models.py`** — Pydantic models: `Task`, `TaskStatus` (todo/in_progress/in_review/blocked/done), `TaskPriority`, `ExecutionLogEntry`, `TaskComment` (with thread reply), `ApprovalCheckpoint`, `TaskCreateRequest`, `TaskUpdateRequest`, `CommentAddRequest`, `ApprovalRequest`.
- **`tasks/store.py`** — `TaskStore`: MongoDB-backed with graceful in-memory fallback. CRUD + filtered list queries (status/priority/agent/tag), count-per-status, due-soon query.
- **`tasks/api.py`** — FastAPI router at `/api/tasks/*`: create, list (with filters), get, patch, delete, add comment, approve checkpoint, retry, escalate. Admin sees all tasks; users see own.

### Added — RBAC (`rbac.py`)

- `UserRole` enum (admin / user).
- `Permission` enum with 17 permission flags.
- `ROLE_PERMISSIONS` mapping: admin gets all, user gets own-resource permissions only.
- `ADMIN_ACTIVITY_PERMISSIONS` set for UI labelling.
- `get_user_role`, `has_permission` helpers.
- `require_admin`, `require_authenticated`, `require_permission(p)` FastAPI dependencies.
- `audit()` helper: append-only audit log, never logs raw secrets, extracts IP from forwarded headers.
- `get_audit_log(limit, user_id)` for admin consumption.
- `mask_secret(str)` and `mask_dict(dict)` for safe logging: redacts OpenAI/GitHub/GitLab/Slack/JWT tokens and common secret key names.

### Changed

- **`proxy.py`** — Wired `runtime_router` at `/runtimes/*` and `task_router` at `/api/tasks/*`. Added `@app.on_event("startup/shutdown")` hooks for `RuntimeManager` lifecycle. App title/version updated to "LLM Relay — Control Plane v3.0.0".
- **`frontend/src/pages/DashboardLayout.js`** — Replaced monolithic nav with role-aware v3 navigation sections. Admin badge and lock icons. Sidebar version updated to v3.0.

### Tests Added

- **`tests/test_runtimes.py`** — 34 tests covering: registry CRUD/capability/tier-ordering, circuit-breaker state machine, routing policy defaults, routing engine happy-path/fallback/no-runtime, adapter metadata for all 5 runtimes, health check returns RuntimeHealth when offline.
- **`tests/test_tasks.py`** — 23 tests covering: task model defaults/validation/add_log, task store CRUD/owner-isolation/filtering/counts/due-soon/admin-view.
- **`tests/test_rbac.py`** — 21 tests covering: role resolution, permission grants/denials, FastAPI dependency enforcement, audit log, secret masking.
- **Total new tests: 78, all passing.**

### Security

- `rbac.py`: secret masking applied at log boundary (never log raw API keys, JWTs, PATs).
- `tasks/api.py`: owner-isolation enforced at store layer; admins can bypass explicitly.
- `runtimes/api.py`: policy update endpoint (`PUT /runtimes/policy`) requires admin role via `_require_admin()`.
- `proxy.py`: new imports validated; no raw secrets in new code paths.

### Performance

- Runtime health polling is fully async with a configurable interval (default 30s).
- Circuit breakers prevent cascading health check failures from blocking request processing.
- Task store uses MongoDB indexes via native motor cursor sorting; falls back to in-memory for dev.

### Known Limitations / TODOs

- Agent profiles (`/api/agents/`) require a backend store (not yet wired — frontend calls will return 404 until `agents_api.py` is implemented; the UI degrades gracefully with an empty list).
- Paid escalation in `RuntimeRoutingPolicyEngine` is architecturally present but not yet wired to `ProviderManager` — it raises a descriptive error instead of calling a paid API.
- OpenHands adapter requires a separately running Docker container — clearly documented in `DESCRIPTION` and `_EXPERIMENTAL_NOTE`.
- Setup Wizard (Phase 2K), Syncthing multi-machine sync (Phase 2L), and Langfuse cost-savings dashboard widgets (Phase 2J) are planned for a subsequent iteration.
- The `OPENHANDS_ENABLED` env var defaults to `false` to avoid registering an experimental runtime unless explicitly opted in.

### Migration Notes

- The login page now shows "Platform v3.0". No breaking changes to existing `/api/*` or `/v1/*` endpoints.
- New environment variables (all optional, see `runtimes/manager.py`): `RUNTIME_NEVER_PAID`, `RUNTIME_MAX_PAID_ESCALATIONS`, `RUNTIME_DEFAULT`, `RUNTIME_CODE_GENERATION`, `RUNTIME_CODE_REVIEW`, `RUNTIME_REPO_EDITING`, `RUNTIME_GIT_OPS`, `HERMES_BASE_URL`, `OPENCODE_BIN`, `GOOSE_BIN`, `AIDER_BIN`, `OPENHANDS_BASE_URL`, `OPENHANDS_ENABLED`, `RUNTIME_HEALTH_POLL_SEC`.
- Existing MongoDB collections are unaffected. New `tasks` collection is created lazily on first task write.

---

## [Unreleased]

### Added

- **`task-alive-updates` skill**: Heartbeat/keep-alive for long-running agent tasks. Emits `[ALIVE]` status lines at configurable intervals so operators know tasks are still progressing; includes `heartbeat.sh` bash helper for shell-based agents. Inspired by Copilot mission control's `copilot_mission_control_task_alive_updates` feature flag.
- **`resource-panel` skill**: Single-pane-of-glass summary of all resources an agent session touched (files read/written, URLs fetched, tools called, new dependencies). Includes `summarise.sh` for git-diff-based auto-generation. Inspired by Copilot's `copilot_resource_panel` feature flag.
- **`duplicate-thread` skill**: Clone an existing plan/task thread to explore an alternative approach without losing the original. Supports fork metadata (`meta.json`), plan stamping, and merge/abandon lifecycle. Inspired by Copilot's `copilot_duplicate_thread` feature flag. Includes `duplicate.sh` shell helper.

### Added — CRISPY Workflow Engine (Phase B)

> **Architecture**: Transforms the platform from a general-purpose agent runner into a
> deterministic, workflow-driven software build system with strict lifecycle control.
> Existing capabilities (proxy, router, agent loop, sessions, background jobs, playbooks,
> memory) are fully preserved and reused.

- **`workflow/` package** — CRISPY phase sequencer (new module, no existing code changed):
  - `workflow/models.py` — all first-class Pydantic types: `WorkflowRun`, `Phase`, `Slice`,
    `Artifact`, `ApprovalGate`, `CheckRun`, `ModelRoutingConfig`, `WorkflowBuildRequest`,
    `WorkflowApproveRequest`, `WorkflowRejectRequest`, `SliceRunRequest`.
  - `workflow/artifact_store.py` — dual-persistence layer: markdown/JSON artifacts written
    to disk under `.data/workflow/artifacts/<run_id>/`; SQLite metadata table for fast
    listing and queryability. Idempotent upsert (`persist`) for resumable re-runs.
  - `workflow/phases.py` — `PhaseRunner`: executes a single CRISPY phase against the
    configured role-model, builds role-specific system prompts (Scout / Architect / Coder /
    Reviewer / Verifier), calls Ollama-compatible endpoint, persists artifact. Verifier phase
    is **execution-only** (subprocess commands via `shell=True`; `CheckRun` JSON is the sole
    output — no LLM subjective verdict).
  - `workflow/engine.py` — `WorkflowEngine`: SQLite-backed phase sequencer.
    - Pre-gate phases run asynchronously: `context → research → investigate → structure → plan`.
    - **Hard ApprovalGate** (`status=awaiting_approval`) after plan phase — no code path can
      advance past it without `engine.approve()`.
    - Post-gate: parses slices from `plan.md`, sequences `execute → review → verify` per slice,
      runs `report` phase, marks run `done`.
    - Full event log (positional, append-only) stored in SQLite alongside run data.
    - `_extract_slices_from_plan()` parser supports `## Slice N: <title>` format with
      optional `Files:` line for target file extraction.
    - `get_engine()` singleton for shared access.
  - `workflow/api.py` — 13 FastAPI endpoints on `workflow_router`:
    - `POST /workflow/build` — create and start a run (202 Accepted)
    - `GET /workflow/` — list runs (paginated, filterable by status)
    - `GET /workflow/{id}` — full WorkflowRun state
    - `POST /workflow/{id}/approve` — lift the ApprovalGate
    - `POST /workflow/{id}/reject` — reject with reason
    - `POST /workflow/{id}/resume` — resume from last completed phase
    - `POST /workflow/{id}/cancel` — cancel a non-terminal run
    - `GET /workflow/{id}/artifacts` — list artifacts (metadata only)
    - `GET /workflow/{id}/artifacts/{name}` — get artifact content (raw text)
    - `GET /workflow/{id}/slices` — list slices
    - `POST /workflow/{id}/slices/{slice_id}/run` — manually trigger a slice
    - `GET /workflow/{id}/checks` — list CheckRuns
    - `POST /workflow/{id}/verify` — trigger full verification pass
    - `GET /workflow/{id}/events` — event log (queryable by position)

- **`agent/models.py`** — `EventType` literal extended with 14 CRISPY workflow event types
  (`workflow_created`, `workflow_done`, `workflow_cancelled`, `workflow_resumed`,
  `phase_started`, `phase_complete`, `phase_failed`, `gate_created`, `gate_approved`,
  `gate_rejected`, `slices_registered`, `slice_started`, `slice_complete`, `slice_failed`).
  Backwards-compatible — all existing event types preserved.

- **3 new test files** (72 tests total, all passing without a running Ollama):
  - `tests/test_workflow_models.py` — 23 tests: validation, helper methods, serialisation
    round-trips, approval gate states, CheckRun pass/fail, Slice defaults.
  - `tests/test_artifact_store.py` — 18 tests: persist idempotency, retrieval by ID/name,
    run isolation, ordering, index generation, deletion, JSON artifacts.
  - `tests/test_workflow_engine.py` — 31 tests: run creation, phase record building,
    approval gate (approve/reject/wrong-state errors), cancellation, event log with
    positional query, slice extraction from plan.md, persistence across simulated restart.

### Model Routing (per-role env vars)

| Role | Env var | Default |
|------|---------|---------|
| Architect | `CRISPY_ARCHITECT_MODEL` | `qwen3-coder:30b` |
| Scout | `CRISPY_SCOUT_MODEL` | `deepseek-r1:32b` |
| Coder | `CRISPY_CODER_MODEL` | `qwen3-coder:30b` |
| Reviewer | `CRISPY_REVIEWER_MODEL` | `deepseek-r1:32b` |
| Verifier | `CRISPY_VERIFIER_MODEL` | `qwen3-coder:7b` |

### Added — CRISPY Multi-Agent System (Phase C)

- **`agents/profiles.py`** — Role-locked `AgentProfile` definitions. Enforces the invariant that `CODER` and `REVIEWER` must use distinct models (by default Qwen3 vs DeepSeek-R1) to prevent shared blind spots.
- **`agents/swarm.py`** — `AgentSwarm` orchestrator. Routes workflow phases to the relevant AgentProfile, injecting profiles into `PhaseRunner`. Enforces permissions (e.g., Scout cannot write, Reviewer cannot execute).
- **`scripts/build_workflow.py` & `build-workflow`** — A standalone Python script and bash wrapper `/usr/local/bin` symlink target. Provides a complete CLI for driving CRISPY via terminal, with streaming updates and a human-in-the-loop approval gate.
- **`workflow/engine.py` & `workflow/api.py`** — `WorkflowEngine` upgraded to use `AgentSwarm` for all slice/phase execution. Added `GET /workflow/agents` to expose the team composition and model mismatch checks.
- **`tests/test_agents.py`** — 25 new tests covering profile resolution, swarm routing, strict permissions, and dual-model invariant warnings.

> **Next**: Phase D (dashboard panel continuation) and full CLI integration.

### Added — CRISPY IDE Bridge + Proxy Wiring (Phase D partial)

- **`workflow/ide_bridge.py`** — OpenAI-compatible SSE bridge. Any IDE that speaks the
  OpenAI chat protocol can now drive CRISPY workflows without plugins:
  - Detects trigger prefixes in the last user message and routes accordingly:
    - `@build <task>` / `@workflow <task>` / `/crispy <task>` — creates a WorkflowRun and
      streams SSE status tokens (phases, gate prompt, slice progress) as if the assistant is typing.
    - `@status [run_id]` — list recent runs or get detailed run state.
    - `@approve <run_id>` — approve the plan gate from the chat box.
    - `@reject <run_id> [reason]` — reject the plan.
  - All other messages pass through transparently to the normal Ollama/LLM handler.
  - `CRISPY_STREAM_TIMEOUT` env var controls SSE stream duration (default 60s).

- **`proxy.py`** — workflow engine wired into the running server:
  - Imports `workflow_router`, `get_engine`, `handle_workflow_ide_chat`.
  - `WORKFLOW_ENGINE = get_engine()` singleton initialised at startup.
  - `app.include_router(workflow_router, dependencies=[Depends(verify_api_key)])` — all
    13 `/workflow/*` endpoints are now live and auth-protected.
  - `POST /v1/workflow/chat` — dedicated IDE bridge endpoint.
  - `GET /v1/models` — injects `crispy-workflow` pseudo-model into the model list so
    Continue, Cursor, and other IDEs can discover and select it from the model picker.
  - `POST /v1/chat/completions` with `model: crispy-workflow` — automatically routed to
    the IDE bridge instead of the LLM, so no IDE config changes are needed beyond model selection.

- **`client-configs/continue_config.yaml`** — updated with:
  - `CRISPY Workflow Engine` model entry (`model: crispy-workflow`, `apiBase: localhost:8000/v1`).
  - Workflow trigger syntax documented in `systemMessage`.
  - Slash commands `/build`, `/status`, `/approve` mapped to trigger prefixes.
  - Direct Qwen3-Coder and DeepSeek models retained as secondary options.

- **`client-configs/vscode_settings.json`** — updated with step-by-step setup guide,
  all three model entries, and tunnel instructions.

- **`client-configs/crispy_client.py`** — new standalone Python CLI:
  `build` · `status` · `approve` · `reject` · `artifacts` · `events` · `watch` (live poll).
  Drop it in any project: `LLM_API_KEY=xxx python crispy_client.py watch wf_abc123`.



### Removed

- **Dashboard SPA: redundant agent + key-management pages consolidated** (`frontend/src/pages/`):
  - Deleted `AgentViewPage.js` (534 lines) — a stripped cross-origin clone of `ChatPage.js` (no sessions sidebar, duplicated model-picker / mode-toggle / thinking-bubble). `ChatPage` is the canonical agent surface; `/agentview` now redirects to `/chat`.
  - Deleted `ApiKeysPage.js` (202 lines) — a feature-incomplete duplicate of `AdminPortalPage.js` (no rotate, no service control). `/keys` now redirects to `/admin`. The dashboard home "API Keys" stat card repoints to `/admin`.
  - Removed "Agent View" and "API Keys" sidebar items from `DashboardLayout.js` nav; removed the corresponding page imports and the unused `Terminal` / `Key` icon imports.
  - Removed the unused `listApiKeys` / `createApiKey` / `deleteApiKey` helpers from `frontend/src/api.js` (sole caller was the deleted `ApiKeysPage`).
  - Not touched in this pass (distinct deployment targets, flagged as future work): `webui/frontend/src/pages/AdminApp.tsx` (providers + workspaces + command runner), `templates/admin/*.html` (Jinja SSR fallback at `/admin/ui/*`), and `remote-admin/*` (pre-dashboard static SPA).

### Security

- **SSRF hardening on admin-supplied URLs** (`webui/url_guard.py`, `webui/providers.py`, `webui/workspaces.py`, `agent/quick_note.py`):
  - New `validate_outbound_url()` helper that unconditionally blocks cloud instance-metadata endpoints (AWS/GCP/Azure `169.254.169.254`, AWS IPv6 IMDS `fd00:ec2::254`, Alibaba `100.100.100.200`, `metadata.google.internal`) — including DNS rebinding via `getaddrinfo` resolution — and restricts schemes (`http`/`https` for providers; `http`/`https`/`ssh`/`git` for workspaces). Applied to `ProviderManager.create/update`, `WorkspaceManager.create/update`, and `agent/quick_note._fetch_text`.
  - Opt-in `STRICT_OUTBOUND=1` mode additionally blocks all loopback/private/RFC1918 ranges (for public-hosted deployments). Off by default since local-first setups legitimately point providers at `localhost` (e.g. Ollama at 127.0.0.1:11434).
- **Git ref injection guard** (`webui/url_guard.validate_git_ref`, `webui/workspaces.py`): Workspace `git_ref` is now validated against `[A-Za-z0-9._/-]` and rejects refs starting with `-` (flag injection via `git checkout --upload-pack=…`), traversal shapes (`..`, `/.`), and shell metacharacters. Applied to both create and update.
- 16 new tests in `tests/test_url_guard.py` cover metadata blocking, scheme restrictions, strict-mode toggling, and git-ref validation.

### Changed

- **Bounded memory for rate-limit buckets** (`proxy.py::check_rate_limit`): The per-API-key request-timestamp dict now sweeps stale entries at most once per window (60 s), evicting keys whose newest request is older than the window. Prevents the dict from growing unbounded across long-running servers with high key churn.
- **Provider model-listing timeout tightened** (`webui/router.py::provider_models`): Reduced from a flat 20 s timeout to `httpx.Timeout(8.0, connect=3.0)` so a misconfigured provider base URL no longer locks the admin UI for 20 seconds per request.
- **Frontend auto-clears stale admin tokens on 401/403** (`webui/frontend/src/api.ts`, `webui/frontend/src/pages/AdminApp.tsx`): New `ApiError` subclass carries the HTTP status; `AdminApp` now detects 401/403 in `refresh`, `createProvider`, `createWorkspace`, `runCmd`, `deleteProvider`, `deleteWorkspace`, and `syncWorkspace`, wipes `lls_admin_token`, and prompts the user to log in again — instead of silently looping with a revoked token.
- **`previewRoute` surfaces auth failures** (`webui/frontend/src/api.ts`): 401/403 now throws `ApiError` (so the caller can clear credentials) while other transient failures still resolve to `null` to keep the routing-preview badge non-critical.

### Fixed

- **End-to-end bug sweep across backend, frontend, networking, and accessibility**:
  - `chat_handlers.py` no longer double-encodes non-JSON upstream bodies — the OpenAI and Ollama native chat paths now inspect the upstream `Content-Type` and stream raw bytes via `Response` when the upstream returns plain text or HTML (e.g. provider 5xx error pages).
  - `webui/router.py::ui_chat` now guards against malformed upstream JSON and missing `choices[0].message.content`, returning `502` on non-JSON upstream and an empty string on partial payloads instead of raising a 500.
  - `admin_auth.py` admin-secret comparison is now timing-safe (`hmac.compare_digest`), replacing the string `==` compare that leaked match length via response timing.
  - `router/health.py::is_model_available` fuzzy-match rewritten with explicit boundary rules — `"qwen3"` no longer matches `"qwen3-coder:30b"`, while legitimate tag expansions (`"qwen3-coder"` → `"qwen3-coder:30b"`) still resolve. Regression test added in `tests/test_model_router.py`.
  - `handlers/anthropic_compat.py` SSE streaming now propagates the upstream `finish_reason` (respecting `tool_calls`/`length`/`content_filter`) in the terminal `message_delta`, replacing a hardcoded `stop_reason: "end_turn"`. Warns when `tool_calls` appear since full Anthropic tool-use block emission is not yet implemented.
  - `remote-admin/main.js` HTML-escapes every server-controlled string (`service.name`, `record.email`, department, key id) before injecting into `innerHTML`, closing an XSS path from admin-writable fields.
  - `webui/frontend/vite.config.ts` dev-proxy target reads `VITE_DEV_PROXY_TARGET` env var (default `http://localhost:8000`) across all six proxied prefixes instead of hardcoding the port in each entry.
  - `ChatApp.tsx` effects now cancel in-flight fetches on unmount (`let cancelled = false`), the model picker falls back to the first available model only when the current selection is missing, and scroll-into-view respects `prefers-reduced-motion`.
  - `AdminApp.tsx` `Delete` and `Sync` actions are now extracted into named async handlers with try/catch error reporting and `disabled={busy}`, and the login row is a real `<form>` submitting on Enter.

### Changed — accessibility

- `ChatApp.tsx`: model picker is a true modal (`role="dialog"`, `aria-modal`, `aria-labelledby`, Escape-to-close); busy/error chips expose `role="status"`/`role="alert"` with `aria-live`; bottom-nav buttons expose `aria-pressed` + `aria-label`; composer textarea has an associated `sr-only` label; decorative emojis are `aria-hidden`.
- `AdminApp.tsx`: every previously unlabeled input in the Add-provider, Add-workspace, and Command-runner forms now has a descriptive `aria-label`; related inputs are grouped with `role="group"` + `aria-labelledby`; command output is wrapped in a `<pre role="region" aria-live="polite">`; the API-key field is now `type="password"` with `autoComplete="off"`.
- `webui/frontend/src/styles.css`: added an `.sr-only` utility for screen-reader-only labels and a global `@media (prefers-reduced-motion: reduce)` block that disables non-essential animations and transitions.

- **Agent view now forwards the caller's API key to same-origin provider URLs**: When an Ollama-backed provider points back at the proxy origin and no provider-specific key is stored, sessioned agent runs reuse the authenticated user's token so `/v1/chat/completions` no longer returns `401 Unauthorized`.
- **`Dockerfile.backend` missing agent/router modules**: Added `COPY agent/ agent/` and `COPY router/ router/` so the deployed backend can import `AgentRunner` — fixes `ModuleNotFoundError: No module named 'agent'` in cloud deployments.
- **`_run_agent_loop` ImportError now surfaces a helpful message**: Wraps the lazy `from agent.loop import AgentRunner` import in a `try/except ImportError` and returns a structured troubleshooting message instead of silently falling back to the LLM.
- **Admin portal shows actionable error when backend URL is stale**: "Load failed" (Safari) / "Failed to fetch" (Chrome) network errors in `AdminPortalPage.js` now display "Cannot reach [URL] — is the proxy running? Click Config to update the backend URL."
- **Ollama health check is now context-aware**: The `/api/health` endpoint skips the Ollama reachability probe when the active LLM provider is not Ollama-based; `SettingsPage` hides the Ollama health badge when `ollama_relevant` is false.
- **Duplicate feature singleton block in `proxy.py`**: Removed the second initialisation of `SESSION_MEMORY`, `SCHEDULER`, `BACKGROUND_AGENT`, etc. that caused every feature singleton to be created twice at startup.
- **Vercel deployments removed**: Added `vercel.json` with `github.enabled: false` to disable Vercel's GitHub integration and stop failing deployment statuses.
- **pytest collection fixed**: Added `pytest.ini` restricting test discovery to `tests/` — prevents root-level integration scripts (`backend_test.py`, `backend_test_iteration3.py`) from breaking CI.

### Added — persistent memory

### Added

- **Advanced RAG context layer** (`agent/rag_context.py`): Three retrieval modes (keyword BM25-style, TF-IDF cosine similarity, hybrid Reciprocal Rank Fusion), conversation memory with exponential recency decay, extractive sentence-level compression to fit a configurable token budget, and a `RAGContextBuilder.build()` returning a `ContextResult` with a `system_block` ready for LLM injection. Pure Python (stdlib only).
- Basic navigation metrics and performance measurements.


- **Claude Opus 4.7 support** (`router/model_router.py`):
  - Added `claude-opus-4-7` to the built-in model alias map; routes to `deepseek-r1:671b` (flagship reasoning model) for local execution.
  - Haiku variants (`claude-haiku-4-5-20251001`, `claude-3-5-haiku-20241022`, `claude-3-haiku-20240307`) now correctly route to `qwen3-coder:7b` (lightweight) rather than the larger 30B coder, matching their speed-first tier.

- **Llama 4 model support** (`router/registry.py`, `router/model_router.py`):
  - Added `llama4-maverick:17b` (17Bx128E MoE, 1M context, code + reasoning + data analysis) to the capability registry.
  - Added `llama4-scout:17b` (17Bx16E MoE, 10M context, fast-response capable) to the capability registry.
  - Short aliases `llama4`, `llama4-maverick`, `llama4-scout` added to `MODEL_MAP` for easy addressing.

- **DeepSeek V3 support** (`router/registry.py`, `router/model_router.py`):
  - Added `deepseek-v3:685b` (685B MoE, 128K context, strong code + reasoning, cost_tier 2) to the capability registry.
  - Short alias `deepseek-v3` added to `MODEL_MAP`.

- **Qwen3-Coder 235B support** (`router/registry.py`, `router/model_router.py`):
  - Added `qwen3-coder:235b` (235B MoE flagship, 128K context, cost_tier 3) to the capability registry with `data_analysis` and `complex_tasks` in strengths.
  - Short aliases `qwen3-coder` and `qwen3-coder-235b` added to `MODEL_MAP`.

- **`data_analysis` task category** (`router/classifier.py`):
  - New classification category for data-science and ML workloads (pandas, numpy, matplotlib, seaborn, scikit-learn, PyTorch, TensorFlow, XGBoost, ETL pipelines, time-series, etc.).
  - Placed in priority just below `code_review`, above `code_generation`, so ML code requests route to models with data-science strengths.
  - All major models with data capabilities (`qwen3-coder:30b`, `qwen3-coder:235b`, `deepseek-r1:32b`, `deepseek-r1:671b`, `llama4-maverick:17b`, `llama4-scout:17b`, `deepseek-v3:685b`) include `data_analysis` in their strengths.

- **Anthropic compat: prompt-cache usage fields** (`handlers/anthropic_compat.py`):
  - `cache_creation_input_tokens` and `cache_read_input_tokens` are now always present in the `usage` block of every `/v1/messages` response (streaming and non-streaming), with value `0`.
  - Prevents Anthropic SDK clients that destructure the usage object from raising `KeyError` or attribute errors when those fields are absent.

- **Anthropic compat: extended thinking parameter handling** (`handlers/anthropic_compat.py`):
  - Requests that include `thinking: {type: "enabled", budget_tokens: N}` are handled gracefully: the parameter is logged at `DEBUG` level and stripped before forwarding to Ollama.
  - DeepSeek-R1 and QwQ models already produce chain-of-thought natively via their `<think>` token protocol; no explicit parameter is required.

### Changed

- **Haiku → lightweight model routing** (`router/model_router.py`): All Haiku-tier Claude aliases now resolve to `qwen3-coder:7b` instead of `qwen3-coder:30b`, consistent with their lightweight/fast-response positioning.
- **`qwen3-coder:30b` and `deepseek-r1` strengths** (`router/registry.py`): Added `data_analysis` to the strengths list of the two primary workhorse models so they are eligible for heuristic selection on data-science tasks.

- **iPhone Quick Note integration** (`agent/quick_note.py`, `proxy.py`):
  - `POST /v1/quick-notes` — authenticated endpoint; add a URL to the implementation queue from an iPhone Shortcut (or any HTTP client).
  - `GET /v1/quick-notes` — returns queue state with counts per status.
  - Background processor thread starts automatically with the proxy; picks one pending note every `QUICK_NOTE_INTERVAL_HOURS` hours (default 4), fetches the URL's text content, runs Claude Code (`claude --print`) to implement the described feature, then commits and pushes to `QUICK_NOTE_PUSH_BRANCH` (default `master`).
  - Queue is persisted to `tasks/quick_notes.json` and survives restarts.
  - Configurable via env vars: `QUICK_NOTE_PUSH_BRANCH`, `QUICK_NOTE_INTERVAL_HOURS`.
  - iPhone Shortcut: Share Sheet action → POST to `http://<your-server>:8000/v1/quick-notes` with `{"url":"<shared URL>"}` and `Authorization: Bearer <api-key>`.



- **Auto / Manual model-selection in Agent UI** (`webui/frontend/src/pages/ChatApp.tsx`):
  - **Auto mode** (default): the proxy router classifies every message (code, reasoning,
    fast-response, etc.) and routes it to the best available local model automatically.
    No model needs to be chosen by the user — just type and send.
  - **Manual mode**: a polished modal pop-up lists all configured providers as tabs.
    Selecting a provider loads its live model list; the user taps a model card to pick it.
    The selection is persisted to `localStorage` so it survives page reloads.
  - Mode toggle is a pair of styled buttons (⚡ Auto / ⚙ Manual) at the top of the
    settings panel.
  - When auto-routing is active the topbar shows a `⚡ Auto` badge and, after each run,
    surfaces the resolved model name if the backend echoes it.

- **Full mobile responsiveness** (`webui/frontend/src/styles.css`):
  - Replaced the hard-coded `320px 1fr 420px` three-column grid with a fluid layout:
    - **≥1101 px (desktop)**: three-column grid (settings | chat | files).
    - **769–1100 px (tablet)**: two-column grid (settings | chat); files panel hidden.
    - **≤768 px (mobile)**: single-column with a fixed bottom tab bar (⚙ Config | 💬 Chat |
      📁 Files). Only the active panel is rendered, preventing horizontal overflow.
  - Composer textarea set to `font-size: 16px` on mobile to suppress iOS auto-zoom.
  - Model-picker modal slides up from the bottom (sheet style) on mobile; centred dialog on desktop.
  - Smooth-scroll chat auto-scroll; thinking dots animation while agent is running.

- **Model-picker modal** (`ChatApp.tsx`):
  - Provider tabs scroll horizontally for overflow.
  - Model cards show the model name + a colour-coded type badge (coder / reasoning / general).
  - Keyboard-accessible (Enter to select, Esc-equivalent close button).
  - Confirm button is disabled until a model is selected.

- **Ctrl+Enter / Cmd+Enter** send shortcut in the composer textarea.

- **Gemma 4 support** (`router/registry.py`, `router/model_router.py`):
  - Added `gemma4:27b` (128 k context, code + reasoning + tool-use, cost_tier 2),
    `gemma4:9b` (128 k, code + fast-response, cost_tier 1), and
    `gemma4:2b` (32 k, ultra-fast conversation, cost_tier 1) to the capability registry.
  - Short aliases `gemma4`, `gemma4-9b`, `gemma4-2b` added to the built-in `MODEL_MAP`
    so clients can request them without specifying a size tag.
  - Gemma 4 models are eligible for heuristic routing: the 27 B variant covers
    `code_generation`, `code_review`, `tool_use`, `reasoning`, and `long_context`;
    the 9 B covers `fast_response`.

- **`POST /ui/api/route`** (`webui/router.py`, `webui/frontend/src/api.ts`):
  - New dry-run endpoint: accepts `{ text }`, runs task classification through the
    `ModelRouter`, and returns `{ resolved_model, task_category, selection_source,
    routing_reason }` with no LLM call. Used by the UI to preview routing decisions.

- **Universal token auth** — a single API key generated by `POST /admin/keys` or
  `generate_api_key.py` now works across *all* API surfaces: `/v1/*` (OpenAI-compat),
  `/api/*` (Ollama native), `/agent/*` (agent loop), and the web UI (`/ui/api/*`).
  Both `Authorization: Bearer <key>` and `x-api-key: <key>` headers are accepted,
  so Claude Code, Cursor, Aider, Continue, and the web UI all share the same credential.

- **Auto / Manual model-selection in dashboard ChatPage** (`frontend/src/pages/ChatPage.js`):
  Replaces the confusing multi-provider dropdown with the same Auto / Manual pattern:
  - **Auto mode** (default): both `model` and `provider_id` sent as `null`; backend router
    classifies the task and picks the best available model. No config required.
  - **Manual mode**: "Select model" button opens a bottom-sheet modal (same UX as the
    Agent UI) with provider tabs and model cards.
  - Agent mode is now **always ON** — every message goes through the full
    Plan → Execute → Verify loop regardless of which mode is active.
  - Mobile: mode toggle and model selector visible in composer area on small screens;
    textarea `font-size: 16px` prevents iOS auto-zoom.

- **Native Agent View page** (`frontend/src/pages/AgentViewPage.js`):
  Replaces the blocked iframe approach with a full native React agent UI:
  - Makes direct `fetch()` calls to the configurable backend URL (default
    `http://localhost:8000`). Browsers allow HTTPS → localhost fetch (localhost is
    "potentially trustworthy") but block HTTPS → HTTP iframes — the iframe approach
    was fundamentally broken on GitHub Pages.
  - Configurable connection bar: backend URL + API key, green/amber/red status dot.
  - Auto / Manual mode toggle identical to ChatPage. Auto lets the router pick the
    best model; Manual opens a provider-tabs + model-cards picker modal.
  - Full chat history display with thinking animation, elapsed timer for long runs,
    error display, and "New session" button.
  - All settings persisted to `localStorage` under `agv_*` keys.
  - UI fully aligned with the parent dashboard: `#002FA7` blue, `#0A0A0A` background,
    `border-white/10` borders, Outfit font, `font-mono` labels — visually identical
    to the rest of the admin UI.

### Fixed

- **Local model list corrected** (`backend/server.py`):
  - Added `deepseek-r1:671b` (flagship 404 GB model) to `PREDEFINED_MODELS["ollama"]` — was missing entirely despite being installed.
  - Renamed `qwen3:30b` → `qwen3-coder:30b` in `PREDEFINED_MODELS["ollama"]` and `AGENT_ROLE_MODELS["ollama"]` to match the actual installed model name.
  - Updated `OLLAMA_MODEL` default from `llama3.2` to `qwen3-coder:30b` to reflect the primary installed coder model.
  - Updated `AGENT_ROLE_MODELS["ollama"]` planner/verifier to use `deepseek-r1:671b` (strongest available model).

- **Cloud Model Expansion** (`backend/server.py`, `commercial_equivalent.py`):
  - Added official cloud providers: **DeepSeek API**, **Zhipu AI (GLM)**, **AliCloud DashScope (Qwen)**, **MiniMax**, **Google Gemini**, and **Moonshot AI (Kimi)**.
  - Configured flagship models: **DeepSeek-V3/R1**, **GLM-4.5 Air**, **Qwen3.5 397B**, **Gemma 4**, **Kimi-K2.5**, and **MiMo-V2-Flash**.
  - Set **DeepSeek** as the default LLM provider for the platform.
  - Added commercial equivalent pricing for accurate savings estimation on all new models.
  - Updated test suite and documentation to cover all new providers.
- **Verification Fixes** (`backend/server.py`, `router/registry.py`, `chat_handlers.py`):
  - Added explicit Claude aliases and `MODEL_MAP` dynamic loading integration natively into `router/registry.py`.
  - Upgraded authentication explicitly verifying `x-api-key` payloads in `get_current_user` (`backend/server.py`).
  - Switched from custom CORS implementation to native explicit `CORSMiddleware` config.
  - Enhanced `_strip_think_blocks` within `chat_handlers.py` using robust regex expression parsing.

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
