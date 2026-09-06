# AGENTS.md — Codebase Map & Operations Reference

> **The rules are in [`CLAUDE.md` §1](CLAUDE.md#1-the-rules).** All 44 of them, binding on
> every agent — Claude, Codex, Cursor, Aider, or anything else. Read that section before
> changing code.
>
> This file is reference: where things are, how big they are, how the system is deployed
> and monitored. It deliberately does not restate a single rule. If you catch it doing
> so, delete the copy — see `.claude/rules-archive/CONFLICTS.md` for what duplicated rule
> sets did to this repo.

---

## Architecture

```
Client: Claude Code / Cursor / Aider / Continue / Telegram / SPA
                          │  HTTP (OpenAI / Anthropic / Ollama format)
                    Bearer Auth / JWT
                          ▼
              proxy.py (FastAPI :8000)
              Auth → Rate Limit → Route
                          │
     ┌────────────────────┼────────────────────┐
 /v1/messages   /v1/chat/completions        /api/*
 Anthropic compat   OpenAI handlers      Ollama native
     └────────────────────┼────────────────────┘
                          ▼
                    router/ModelRouter
                    classify_task()
                          ▼
                       Ollama
                          ▲
                 agent/AgentRunner
                 Plan → Execute → Verify
```

`backend/server.py` (FastAPI :8001) is the second app: dashboard API, company graph,
onboarding, workflow orchestrator, secrets, skills.

---

## Codebase map

Line counts re-measured 2026-08-10 (`wc -l`). Re-run before trusting them — the previous
version of this table was off by up to 4,179 lines on a single file.

| Path | Purpose | Lines | Risk |
|------|---------|------:|------|
| `backend/server.py` | Dashboard API server | 10,666 | HIGH |
| `proxy.py` | Main entry point, auth, rate limit, routing | 4,116 | HIGH |
| `agent/loop.py` | AgentRunner — plan/execute/verify loop | 2,940 | **RISKY** |
| `packages/ai/router.py` | Multi-provider backend with fallback | 1,988 | Medium |
| `services/workflow_orchestrator.py` | Workflow execution engine | 1,940 | HIGH |
| `services/scanner.py` | Tech stack scanner (Playwright) | 1,726 | Medium |
| `services/company_graph_store.py` | Company knowledge graph persistence | 1,722 | Medium |
| `services/ceo_dispatcher.py` | CEO delegation + supervised escalation | 1,083 | HIGH |
| `packages/config/control_catalogue.py` | Declarative platform-control table | 1,064 | Low |
| `direct_chat.py` | Direct chat sessions, intent classification | 892 | Medium |
| `agent/repowise.py` | RepowiseIntelligence — codebase analysis | 867 | Low |
| `chat_handlers.py` | OpenAI/Ollama streaming handlers | 866 | Medium |
| `handlers/anthropic_compat.py` | Anthropic API adapter | 739 | Medium |
| `router/registry.py` | Model capability registry | 671 | Medium |
| `services/ceo_micromanager.py` | Tier ladder, decomposition, subtask briefs | 643 | Medium |
| `services/ceo_ledger.py` | Durable goal/subtask/attempt record | 616 | Medium |
| `router/model_router.py` | ModelRouter — central routing logic | 529 | HIGH |
| `services/ceo_supervisor.py` | 24x7 sweep: close / re-drive / abandon goals | 497 | HIGH |
| `agent/web_reach.py` | Zero-key read-only internet access | 460 | **RISKY** |
| `langfuse_obs.py` | Langfuse trace emission | 451 | Low |
| `packages/config/settings.py` | Central settings / env resolution | 415 | Medium |
| `packages/auth/rbac.py` | Role-based access control | 391 | **RISKY** |
| `key_store.py` | API key CRUD, SHA-256 hashing, persistence | 305 | **RISKY** |
| `services/ceo_quality.py` | Anti-slop gate + bounded escalation ladder | 222 | Medium |
| `agent/tools.py` | WorkspaceTools — filesystem read/write | 210 | **RISKY** |
| `handlers/v3_auth.py` | JWT validation | 177 | **RISKY** |
| `router/classifier.py` | Task classification | 172 | Medium |

### Risky modules

Rule 15 gates these behind the `risky-module-review` skill. The auth modules moved into
`packages/auth/` — the old top-level `admin_auth.py`, `rbac.py`, and `social_auth.py`
paths no longer exist, so any document still naming them is stale and the gate it
describes cannot fire.

| Module | Risk |
|--------|------|
| `packages/auth/admin.py` | Admin session auth, cookie signing |
| `packages/auth/rbac.py` | Permission enforcement |
| `packages/auth/oauth.py` | GitHub/Google OAuth flows |
| `packages/auth/service_token.py` | Service-token issuance and checks |
| `key_store.py` | API key storage, hash operations |
| `agent/tools.py` | Filesystem write surface |
| `agent/web_reach.py` | Outbound fetch surface — the SSRF boundary |
| `handlers/v3_auth.py` | JWT validation |
| `proxy.py` auth middleware | Request authentication |

### File-size exceptions

Two files are past rule 28's 800-line limit with justification on record. Add to this
list rather than silently exceeding it.

**`packages/config/control_catalogue.py`** (1,064) is one flat declarative table — the
platform controls an operator can set from the dashboard — with no executable logic. The
types and builders live in `control_specs.py` and the lookup, grouping, and coercion API
in `control_registry.py`, both well inside the limit. Cutting the table at a group
boundary would not shrink any reader's working set, only make "where is control X
declared" a two-step question. Revisit if logic accumulates in the catalogue, which is
what the limit exists to catch.

**`services/ceo_dispatcher.py`** (1,083) is a pre-existing orchestration hub sitting on
the EXECUTE hot path, so splitting it is a standalone refactor rather than a rider on a
behaviour change. Decompose along the seam the CEO work already exposes: delegation and
planning, supervised execution, ledger writes. `services/ceo_micromanager.py` was split
at that seam — the judging half became `services/ceo_quality.py`.

`backend/server.py` and `proxy.py` are also over the limit and are being migrated per
`REWRITE_PLAN.md`. Neither is licence to add more.

---

## Deployment

| Service | Platform | Trigger |
|---------|----------|---------|
| Proxy + Backend | Render (`deploy-backend.yml`) | Push to `master` |
| Frontend SPA | **GitHub Pages** (`deploy-frontend.yml`, `actions/deploy-pages`) | Push to `master` |
| Remote Admin / Worker | Cloudflare Workers (`deploy-cloudflare.yml`) | Push to `master` |

There is no Vercel deployment. Earlier versions of this file said there was; no workflow
has ever referenced it (`grep -rli vercel .github/workflows/` returns nothing).

Local development:

```bash
source .venv/bin/activate
uvicorn proxy:app --reload --port 8000            # AI proxy
uvicorn backend.server:app --reload --port 8001   # dashboard API
```

### Release

1. Move `## [Unreleased]` to `## [vX.Y.Z] — YYYY-MM-DD` in both changelogs.
2. `pytest` green.
3. `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. CI runs on the tag; deployment follows.

Full checklist: `docs/runbooks/release.md`. Run the `release-readiness` skill first.

---

## Monitoring

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /health` | None | Process liveness |
| `GET /api/doctor/public` | None | System-level checks |
| `GET /api/doctor/diagnostics` | JWT | Authenticated diagnostics |
| `GET /api/ping` | JWT | Backend liveness |
| `GET /api/status` | JWT | System status summary |

LLM traces go to Langfuse (`LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`), errors to
Sentry when `SENTRY_DSN` is set, and verbosity is controlled by `LOG_LEVEL`.

Conditions worth an alert: 5xx rate above 1% over 5 minutes; Ollama health failing for
more than 60 seconds; an agent session with no progress for 10 minutes; rate-limit
buckets above 80% of capacity; memory above 85%.

---

## Agent roles

`agents/` holds 24 specialist profiles. The six with matching slash commands in
`.claude/commands/`:

| Agent | Scope | Skills it leans on |
|-------|-------|--------------------|
| Security | Vulnerability scanning, auth review, CVE monitoring | `risky-module-review`, `security-review`, `dependency-audit` |
| QA | Test coverage, regression detection, CI monitoring | `test-first-executor`, `council-review` |
| Architecture | Module boundaries, technical debt, ADRs | `implementation-planner`, `modularity-review` |
| DevOps | CI/CD, Docker, Render/Cloudflare deploys | `release-readiness`, `docs-sync` |
| Documentation | README, changelogs, API docs, runbooks | `docs-sync`, `changelog-enforcer` |
| Bug Fix | Reproduce, isolate, fix, test, PR | `test-first-executor`, `risky-module-review` |

---

## Claude Code subagents (cost-aware routing)

`.claude/agents/*.md` files with **YAML frontmatter** (`name`, `description`,
`tools`, `model`) are Claude Code project subagents — orchestrated by a human's
Claude Code session, not by the product runtime. Do not confuse them with two
neighbours: `agents/` above holds the 24 product specialist profiles, and the
**frontmatter-less** files in this same directory (`planner.md`, `implementer.md`,
`reviewer.md`, `judge.md`) are documentation of the internal
`nvidia`-model plan→execute→verify loop, which Claude Code ignores because they
carry no frontmatter.

The routing principle: **use the smallest model that reliably passes the task's
own evaluation.** Optimise for cost per *accepted* task, not raw token cost — a
cheaper model whose work is reworked costs more. Model tiers map to task shape:

| Subagent | Model | Tools | Why this tier |
|----------|-------|-------|---------------|
| `docs-auditor` | haiku | Read, Grep, Glob | Bounded, read-only doc accuracy review |
| `codebase-explorer` | haiku | Read, Grep, Glob | Read-only discovery; explicitly overrides the built-in Explore model choice |
| `feature-implementer` | sonnet | Read, Edit, Write, Bash, Grep, Glob | Routine scoped implementation with clear acceptance criteria |
| `verification-reviewer` | sonnet | Read, Grep, Glob, Bash | Independent, evidence-based correctness check; runs the tests itself (rule 46) |
| `risk-reviewer` | opus | Read, Grep, Glob | Independent ship / no-ship judgment over security, privacy, migration, rollback |

Discipline for the orchestrating session (the parent task is the contract):

- **Investigate before implementing.** Use `docs-auditor` / `codebase-explorer`
  first; call `feature-implementer` only once the plan and acceptance criteria are
  clear. Do not widen its write scope because a task "sounds small".
- **Separate implementation from review.** After implementation, run the two
  reviews independently and read-only. Never have multiple agents implement the
  same feature — that multiplies cost and merge work. Parallelism is for genuinely
  independent research or review.
- **Reserve Opus** for difficult architecture, ambiguous failure analysis, or
  high-risk changes where the added capability is justified by evidence — not by
  default, and not the reverse (Haiku is not the default just because it is cheaper).
- **Verify on evidence, not confidence** (rules 45-47). The human owns
  consequential decisions, approvals, and final ownership (rule 40).

Whether the routing actually pays off is a measured question, not an assumed one.
The harness for it is `evals/cost_aware_routing/` (`make eval-routing`, or
`python -m evals.cost_aware_routing --example`): a fixed task catalogue and a
**cost-per-accepted-task** score in which rework and rejected work count against
a cheap model. It ships the instrument, not results — record real runs per its
README and score them; do not quote the illustrative sample as a finding.

---

## Session state

Rules 43 and 44 govern what may be written where. The files:

| File | Content |
|------|---------|
| `.claude/state/active-tasks.md` | Live task tracker — injected at session start |
| `.claude/state/NEXT_ACTION.md` | Next step, read by `scripts/ai_runner.py` |
| `.claude/state/agent-state.json` | Machine-readable session state |
| `.claude/state/checkpoint.jsonl` | Ordered step log |
| `.claude/state/learnings.md` | Append-only session learnings |
| `.claude/state/runner.lock` | Active session lock |
| `.claude/state/archive/` | Completed task rows, moved out of the live tracker |

The parent directory is tracked in git and team-shared. `.claude/state/sessions/<id>/` is
gitignored and is the only place session-private material — anything that may contain the
operator's literal credentials — may go. The convention is documented in
`.agents/SKILLS-CATALOG.md`, and the redaction discipline in the `replay-learnings` skill.

---

## Git hooks

`git config core.hooksPath .claude/hooks` activates four blocking hooks. They enforce
mechanically what would otherwise have to be prose:

| Hook | Blocks on |
|------|-----------|
| `pre-commit` | Staged `.env` or `keys.json`; hardcoded `SECRET_KEY`; Python syntax errors |
| `commit-msg` | Code changes with no `docs/changelog.md` entry, unless the subject carries an exempt prefix |
| `pre-push` | `pytest -x` failing |
| `post-commit` | (non-blocking) refreshes the graphify knowledge graph |

`.claude/settings.json` adds two SessionStart hooks — `graphify-refresh` and
`session-plan-bootstrap` — plus a Stop hook that refreshes the graph in the background.

---

## Further reading

| Topic | Location |
|-------|----------|
| **The rules** | `CLAUDE.md` §1 |
| Naming, log levels, fixtures, performance targets | `ENGINEERING_STANDARDS.md` |
| Architecture overview | `docs/architecture/overview.md`, `ARCHITECTURE.md` |
| Model routing | `docs/architecture/model-routing.md`, `router/CLAUDE.md` |
| Agent orchestration | `docs/architecture/agent-orchestration.md`, `agent/CLAUDE.md` |
| Configuration | `docs/configuration-reference.md` |
| Runbooks, ADRs, changelog | `docs/` |
| Rules audit — what was cut and why | `.claude/rules-archive/` |
