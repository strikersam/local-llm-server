<div align="center">

# LLM Relay

### Self-hosted OpenAI-compatible proxy that runs as an autonomous AI agency.

**Route any AI tool through 15+ providers. Let agents scan, fix, and ship your codebase continuously. Keep your data yours.**

[![Version](https://img.shields.io/badge/version-4.1.0-4D8CFF?style=for-the-badge)](docs/changelog.md)
[![Stars](https://img.shields.io/github/stars/strikersam/local-llm-server?style=for-the-badge&color=FFD43B&logo=github)](https://github.com/strikersam/local-llm-server/stargazers)
[![Forks](https://img.shields.io/github/forks/strikersam/local-llm-server?style=for-the-badge&color=4D8CFF&logo=git)](https://github.com/strikersam/local-llm-server/network)
[![CI](https://img.shields.io/github/actions/workflow/status/strikersam/local-llm-server/ci.yml?style=for-the-badge&label=CI&logo=github-actions)](https://github.com/strikersam/local-llm-server/actions)
[![License](https://img.shields.io/badge/license-Open%20Source-22C55E?style=for-the-badge)](LICENSE)

[**Quick start**](#quick-start) · [**Agency**](#autonomous-agency) · [**Providers**](#providers) · [**What's new**](#whats-new) · [**Screenshots**](#see-the-product) · [**Docs**](#technical-docs)

</div>

---

## What is LLM Relay?

A **FastAPI proxy** that sits between your AI tools and your models — and also runs as a self-managing AI agency that continuously improves its own codebase.

Point Cursor, Claude Code, Aider, Continue, or any OpenAI SDK client at `http://localhost:8000` and get:

- **Smart routing** — free-first, local-first, cost-aware, or quality-first strategies across 15+ providers
- **Anthropic + OpenAI API compatibility** — both `/v1/messages` and `/v1/chat/completions` on the same server
- **Async agent engine** — plan → execute → verify pipeline with per-role model assignment
- **Team control plane** — React dashboard with an **Intelligent Assistant** that automatically detects coding intent, manages workspaces, and handles interactive task approval.
- **Autonomous agency** — CEO + specialist agents scan, fix, and ship improvements every 15 minutes

No GPU required to start: set `NVIDIA_API_KEY` and free NIM inference handles everything.

<p align="center">
  <img src="docs/screenshots/readme/v4-control-plane.png" alt="LLM Relay control plane" width="100%"/>
  <br/>
  <sub><em>The main control plane: chat, tasks, agents, models, knowledge, and system health in one screen.</em></sub>
</p>

---

## Autonomous Agency

LLM Relay runs itself. The moment the server boots, an autonomous agency starts managing the codebase — scanning for issues, dispatching fixes, and reporting progress. No human needed to keep the code healthy.

```
┌─────────────────────────────────────────────────────────────┐
│                    Autonomous Agency                        │
│                                                             │
│  CEO Agent  (every 15 min)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Read improvement-loop state                      │   │
│  │ 2. Assess: failing tests? security issues? debt?    │   │
│  │ 3. Issue directives to specialist agents            │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │ directives                           │
│          ┌───────────┼───────────┬──────────┐              │
│          ▼           ▼           ▼          ▼              │
│      Dev Agent  Security   Reviewer   Release Agent         │
│     (fix tests)  Agent    (council    (readiness +          │
│                 (CVEs,     review)    changelog)            │
│                 secrets)                                    │
└─────────────────────────────────────────────────────────────┘
```

### How the agency works

**Every 15 minutes — CEO assessment cycle:**

| Priority | Trigger | Action |
|----------|---------|--------|
| P1 | Failing tests detected | Dev Agent: runs pytest, fixes failures, commits to master |
| P2 | Security findings | Security Agent: remediates bandit/CVE/secret issues |
| P4 | Backend errors logged | Dev Agent: fixes root cause from log context |
| P6 | Every 4th cycle | Reviewer Agent: council review of recent changes |
| P8 | Weekly | Release Agent: readiness check, changelog, version bump |

**Every 6 hours — Improvement loop scan:**
- Runs the full test suite and registers failing tests as issues
- Grepping for `FIXME`, `TODO:FIX`, and `HACK:URGENT` markers
- Detecting Python modules with no test coverage
- Running bandit (SAST), safety (CVE audit), and secret-pattern grep

**Real-time — Backend error capture:**
- Every `ERROR`/`CRITICAL` log line from the running server creates a self-healing task (rate-limited: one task per unique error per hour)
- Every unhandled 500 response or exception traceback creates a fix task
- CI failure webhooks arrive from GitHub Actions and trigger the Dev Agent

**GitHub Actions automation:**

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `agency-cycle.yml` | Every 6 hours | CEO assessment + Dev Agent fixes + commits to master |
| `continuous-improvement.yml` | Daily 09:00 UTC | pytest run + auto-creates/closes GitHub issues |
| `security-scan.yml` | Weekly + on push | bandit + safety + secret grep + GitHub issue creation |

### v4 Improvement Dashboard

Browse and control the agency from `remote-admin/v4-dashboard.html`:

```
GET  /v4/status                     — CEO assessment, loop state, recent events
GET  /v4/improvements               — active/resolved issue list
POST /v4/improvements/scan          — trigger immediate full scan
POST /v4/improvements/security-scan — bandit + safety + secrets only
POST /v4/improvements/{id}/resolve  — mark issue resolved
POST /v4/report-bug                 — submit a bug → self-healing queue
GET  /v4/quick-notes                — queued implementation notes
POST /v4/quick-notes                — add a note (URL or plain text)
GET  /v4/scheduler/jobs             — all improvement cron jobs
POST /v4/scheduler/trigger/{id}     — fire a job immediately
GET  /v4/agency/status              — CEO history, directive queue
POST /v4/agency/run-cycle           — trigger an immediate CEO cycle
GET  /v4/log-monitor/stats          — backend error capture stats
POST /v4/ci-failure                 — CI failure webhook endpoint
```

### Standing improvement jobs (auto-registered at startup)

| Job | Schedule | Instruction |
|-----|----------|-------------|
| `daily-test-scan` | Daily 03:00 UTC | pytest → fix failures → changelog |
| `weekly-dep-audit` | Monday 04:00 UTC | pip outdated → safe upgrades |
| `daily-changelog-check` | Daily 05:00 UTC | audit and complete changelog |
| `weekly-todo-cleanup` | Wednesday 06:00 UTC | resolve FIXME/TODO markers |

### Quick Notes — iPhone → Code

Send a URL or plain-text instruction from your iPhone Shortcut and the agency implements it:

```
iPhone Shortcut → POST /v1/quick-notes
                       → queue
                       → processor fetches URL / reads instruction
                       → Claude Code implements it
                       → git commit + push to master
```

---

## Supported Models

### Local (via Ollama)

| Model | Type | Context | Vision |
|---|---|---|---|
| `qwen3-coder:7b` | Coder | 32k | — |
| `qwen3-coder:30b` | Coder | 32k | — |
| `qwen3-coder:235b` | Coder | 131k | — |
| `qwen3.6:35b` | General | 128k | ✓ |
| `deepseek-r1:32b` | Reasoning | 32k | — |
| `deepseek-r1:671b` | Reasoning | 131k | — |
| `deepseek-v3:685b` | Coder | 131k | — |
| `gemma4:9b` | General | 128k | ✓ |
| `gemma4:27b` | General | 128k | ✓ |
| `llama4-scout:17b` | General | 10M | ✓ |
| `llama4-maverick:17b` | General | 1M | ✓ |

> Add any Ollama model at runtime via `ROUTER_EXTRA_MODELS` without touching code.

### NVIDIA NIM (free tier)

Set `NVIDIA_API_KEY` — proxy routes to NIM at highest priority (−10).

| Model slug | Notes |
|---|---|
| `nvidia/nemotron-3-super-120b-a12b` | Default · general purpose |
| Any NIM model | Override with `NVIDIA_DEFAULT_MODEL` |

### Free Cloud APIs

| Provider | Env var | Default model |
|---|---|---|
| Groq | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| DeepSeek API | `DEEPSEEK_API_KEY` | `deepseek-chat` |
| Google Gemini | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | `gemini-2.0-flash` |
| Cerebras | `CEREBRAS_API_KEY` | `llama-3.3-70b` |
| SambaNova | `SAMBANOVA_API_KEY` | `Meta-Llama-3.3-70B-Instruct` |
| Together AI | `TOGETHER_API_KEY` | `Llama-3.3-70B-Instruct-Turbo-Free` |
| Mistral | `MISTRAL_API_KEY` | `mistral-small-latest` |
| Hugging Face | `HF_TOKEN` | serverless inference |
| Cloudflare AI | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` |
| Qwen DashScope | `DASHSCOPE_API_KEY` or `QWEN_API_KEY` | `qwen-plus` |
| ZhipuAI | `ZHIPU_API_KEY` | `glm-4-flash` |
| MiniMax | `MINIMAX_API_KEY` | `MiniMax-Text-01` |

### Commercial Cloud APIs

Tried last, only when all free and local providers are exhausted.

| Provider | Env var | Default model |
|---|---|---|
| AWS Bedrock | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | `us.anthropic.claude-opus-4-7` |
| Anthropic | `ANTHROPIC_API_KEY` | configurable |
| OpenRouter | `OPENROUTER_API_KEY` | configurable |

---

## Providers

Provider chain sorted automatically: **NVIDIA NIM → local Ollama → free cloud → commercial**.

```
Provider priority order (lower = tried first)
──────────────────────────────────────────────
  0  NVIDIA NIM          (free, no local GPU needed)
  1  Local Ollama        (private, on-device)
  3  Free cloud APIs     (Groq, Gemini, DeepSeek, …)
  4  Commercial APIs     (Bedrock, Anthropic, …)
```

Each provider gets a bounded per-request timeout and failure-aware cooldown:
- `401/403` → 5-minute cooldown
- connection error → 15-second cooldown
- other errors → 30-second cooldown

---

## API Compatibility

### OpenAI-compatible endpoints

```
POST /v1/chat/completions     # Streaming + non-streaming chat
GET  /v1/models               # Lists all models including Claude aliases
POST /v1/completions          # Legacy text completion
POST /v1/embeddings           # Embeddings passthrough
```

### Anthropic-compatible endpoints

```
POST /v1/messages             # Full Anthropic Messages API
POST /v1/messages/count_tokens  # Token counting (Claude Code CLI uses this)
```

### Ollama-native passthrough

```
POST /api/chat    # Ollama NDJSON streaming
POST /api/generate
GET  /api/tags
POST /api/pull
```

---

## What's new

### v4.1 — Autonomous Agency (2026-05-16)

The biggest update since launch: LLM Relay now manages itself.

**CEO + Specialist Agent Loop**

A `CEO` agent wakes every 15 minutes, reads the improvement state, and dispatches directives to four specialist roles: `Dev` (fix tests and errors), `Security` (remediate findings), `Reviewer` (council review), and `Release` (readiness + changelog). Directives queue as scheduled jobs, fire via the `TaskDispatcher`, and execute inside the existing `AgentRunner` pipeline — no new infrastructure needed.

**Continuous Improvement Loop**

A background scanner runs every 6 hours and:
- Runs the full pytest suite — failing tests become P1 fix tasks
- Greps for `FIXME`/`TODO:FIX`/`HACK:URGENT` markers
- Detects modules missing test coverage
- Runs bandit SAST, safety CVE audit, and secret-pattern grep

All findings are persisted to `.claude/state/improvement-state.json` and surfaced in the v4 dashboard.

**Self-Healing Agent**

Three entry points for external failure signals:
- `POST /v4/ci-failure` — CI failure webhook from GitHub Actions
- `on_github_issue()` — triggered when a bug-labelled issue is opened
- `POST /v4/report-bug` — manual report from the v4 dashboard

Each signal creates a `DetectedIssue`, schedules a fix job, and tracks resolution.

**Backend Error Capture**

A custom Python `logging.Handler` is attached to the root logger at startup. Every `ERROR`/`CRITICAL` record from non-noisy loggers creates a self-healing fix task (rate-limited: one task per unique error per hour, identified by SHA-256 signature). Unhandled 500 responses are also captured by `ErrorInterceptorMiddleware`.

**GitHub Actions automation**

Three new workflows ship with the repo:
- `agency-cycle.yml` (every 6h) — CEO assessment + automated fixes pushed directly to master
- `continuous-improvement.yml` (daily) — pytest + auto-creates/closes GitHub issues with `auto-detected` label
- `security-scan.yml` (weekly + push) — bandit, safety, secret grep + GitHub issue creation

**v4 Dashboard**

New static SPA at `remote-admin/v4-dashboard.html` with live KPIs, active issue table, bug report form, quick-note queue, scheduler job panel, agency cycle history, and self-healing event feed.

### v4.0 — Async agents, NVIDIA NIM, mobile UI (2026-05-09)

- `agent_mode=true` returns 202 Accepted immediately — no more blocking requests
- NVIDIA NIM as priority-0 free provider; per-role model configuration
- Mobile-first UI with safe-area-aware chrome
- Runtime preflight validation with structured error diagnostics
- Vision routing (`image_url` → vision-capable model)
- `POST /v1/messages/count_tokens` — Claude Code CLI token counting
- Extended thinking → reasoning model routing
- Anthropic `output_format` → Ollama `format` translation
- Langfuse traces from direct chat with token/latency attribution
- JWT `iat`/`jti` claims — replay attacks closed
- AWS Bedrock (Claude 4 Opus/Sonnet via Converse API)

See [`docs/changelog.md`](docs/changelog.md) for the full diff.

---

## Quick start

### Fastest path — free cloud AI, no GPU needed

```bash
git clone https://github.com/strikersam/local-llm-server
cd local-llm-server

cat > .env <<'ENV'
API_KEYS=sk-relay-dev
ADMIN_SECRET=replace-with-a-long-random-secret
ADMIN_EMAIL=admin@llmrelay.local
ADMIN_PASSWORD=replace-with-a-strong-password
JWT_SECRET=replace-with-another-long-random-secret
NVIDIA_API_KEY=nvapi-...
ENV

docker compose up -d
docker compose --profile dashboard up -d
```

| URL | What's there |
|---|---|
| `http://localhost:3000` | Full control plane (chat, tasks, agents, knowledge) |
| `http://localhost:8000/admin/ui/login` | Built-in admin portal (API keys, health) |
| `http://localhost:8000/app` | Built-in web UI |
| `http://localhost:8000/v4/status` | Improvement loop & agency status (JSON) |
| `remote-admin/v4-dashboard.html` | v4 Continuous Improvement Dashboard (open locally) |

### Add local models (Ollama)

```bash
docker exec llm-server-ollama ollama pull qwen3-coder:30b
docker exec llm-server-ollama ollama pull deepseek-r1:32b
```

### Core proxy only (no Docker)

```bash
source .venv/bin/activate
uvicorn proxy:app --reload --port 8000
# Agency, improvement loop, log monitor, and error interceptor start automatically.
```

### Optional agency env vars

```bash
AGENCY_TICK_MINUTES=15        # CEO assessment interval (default: 15)
IMPROVEMENT_SCAN_INTERVAL_HOURS=6  # Full scan interval (default: 6)
QUICK_NOTE_PUSH_BRANCH=master # Branch for quick-note auto-commits
QUICK_NOTE_INTERVAL_HOURS=4   # Note processing interval (default: 4)
```

---

## Sign in

| Surface | Credentials |
|---|---|
| Control plane (`localhost:3000`) | `ADMIN_EMAIL` / `ADMIN_PASSWORD` |
| Built-in admin portal (`localhost:8000/admin/ui/login`) | any username / `ADMIN_SECRET` |
| v4 Dashboard API (`/v4/*`) | `Authorization: Bearer <ADMIN_SECRET>` |

---

## Connect your tools

### Claude Code

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
export ANTHROPIC_API_KEY=sk-relay-...
claude
```

### Cursor

```
API Key:                  sk-relay-...
Override OpenAI Base URL: http://localhost:8000/v1
```

### Python / OpenAI SDK

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-relay-...")
response = client.chat.completions.create(
    model="qwen3-coder:30b",
    messages=[{"role": "user", "content": "hello"}]
)
```

Aider, Continue, Zed, VS Code, and script examples live in [`client-configs/`](client-configs/).

---

## See the product

### 🛬 Login

<p align="center">
  <img src="docs/screenshots/readme/v4-login.png" width="58%" alt="LLM Relay v4 login (desktop)"/>
  &nbsp;
  <img src="docs/screenshots/readme/v4-login-mobile.png" width="28%" alt="LLM Relay v4 login (mobile)"/>
</p>

### 🧙 Setup Wizard

<p align="center">
  <img src="docs/screenshots/readme/v4-setup-wizard.png" width="58%" alt="Setup Wizard v4"/>
  &nbsp;
  <img src="docs/screenshots/readme/v4-setup-mobile.png" width="28%" alt="Setup Wizard v4 mobile"/>
</p>

### 🏠 Dashboard

<p align="center"><img src="docs/screenshots/readme/v4-control-plane.png" width="92%" alt="LLM Relay v4 Dashboard"/></p>

### 💬 Chat

> **Agent Mode async contract:** `agent_mode=true` returns `202 Accepted` with `(session_id, job_id, status, phase, message)`. Poll `/api/chat/agent-jobs/{job_id}` for status. On completion, render `final_message` as the assistant reply.

<p align="center"><img src="docs/screenshots/readme/v4-chat.png" width="92%" alt="Direct Chat v4"/></p>

### 🗂 Task Board

<p align="center"><img src="docs/screenshots/readme/v4-tasks-kanban.png" width="92%" alt="Kanban Task Board v4"/></p>

### 🤖 Agent Roster

<p align="center"><img src="docs/screenshots/readme/v4-agents.png" width="92%" alt="Agent Roster v4"/></p>

### ⚙️ Runtimes

<p align="center"><img src="docs/screenshots/readme/v4-runtimes.png" width="92%" alt="Agent Runtimes v4"/></p>

### 🛣 Routing Policy

<p align="center"><img src="docs/screenshots/readme/v4-routing.png" width="92%" alt="Routing Policy v4"/></p>

### 📚 Knowledge

<p align="center"><img src="docs/screenshots/readme/v4-knowledge.png" width="92%" alt="Knowledge and Wiki v4"/></p>

### 🔭 Logs and Activity

<p align="center"><img src="docs/screenshots/readme/v4-logs.png" width="92%" alt="Logs v4"/></p>

### 🗓 Schedules

<p align="center"><img src="docs/screenshots/readme/v4-schedules.png" width="92%" alt="Schedules v4"/></p>

---

## Feature overview

| Category | What's included |
|---|---|
| **API compatibility** | OpenAI `/v1/chat/completions`, Anthropic `/v1/messages` + `/count_tokens`, Ollama `/api/chat` |
| **Model routing** | Free-first · local-first · cost-aware · quality strategies |
| **Vision routing** | Auto-detects `image_url`, routes to vision-capable model |
| **Thinking routing** | `thinking: {type: "enabled"}` → reasoning model (DeepSeek-R1, QwQ) |
| **Structured outputs** | `json_schema` / `json_object` translated to Ollama `format` automatically |
| **Auth** | Bearer tokens · per-user API keys · JWT (iat/jti) · social login · RBAC |
| **Agent engine** | Async 202 jobs · plan/execute/verify pipeline · per-role models |
| **Autonomous agency** | CEO + Dev/Security/Reviewer/Release agents · 15-min tick · self-healing |
| **Continuous improvement** | 6h scan cycle · test failures · FIXME markers · missing coverage · security |
| **Log monitoring** | ERROR/CRITICAL capture → fix tasks · rate-limited per error signature |
| **Error interception** | 500 responses + unhandled exceptions → fix tasks via middleware |
| **Security scanning** | bandit SAST · safety CVE audit · secret-pattern grep · GitHub issues |
| **Self-healing** | CI webhook + GitHub issue + dashboard report → queued fix tasks |
| **Quick Notes** | iPhone Shortcut → URL/text → Claude Code implements → git push |
| **Task management** | Kanban board · concurrent fanout · approvals · retry |
| **Schedules** | Cron jobs · run-now · webhook triggers · 4 built-in improvement jobs |
| **Observability** | Langfuse traces (chat + agent) · session clustering · token/latency attribution |
| **Knowledge** | Wiki pages · source ingestion (GitHub, URL, file) · agent retrieval |
| **GitHub integration** | Repo · branch · file · PR flows |
| **Secrets** | Encrypted secrets store |
| **Telegram bot** | Remote control via Telegram |
| **Hardware detection** | GPU / CPU / memory profiling |
| **Extensibility** | `ROUTER_EXTRA_MODELS` · `MODEL_MAP` · `FEATURE_DISABLE/ENABLE` |

---

## Technical docs

- [Documentation index](docs/README.md)
- [Architecture overview](docs/architecture/overview.md)
- [Agent orchestration](docs/architecture/agent-orchestration.md)
- [Feature guide](docs/features.md)
- [API surfaces and route map](docs/api-surfaces.md)
- [Configuration reference](docs/configuration-reference.md)
- [Model routing guide](docs/model-routing.md)
- [Claude Code setup](docs/claude-code-setup.md)
- [Agent runtime setup](docs/runbooks/agent-runtime-setup.md)
- [Langfuse observability](docs/langfuse-observability.md)
- [Changelog](docs/changelog.md)

---

## License

Open source. Use it, change it, and make it better.

---

<div align="center">

If LLM Relay saves you time or money, a star helps other people find it.

[![Star this repo](https://img.shields.io/github/stars/strikersam/local-llm-server?style=for-the-badge&logo=github&color=FFD43B)](https://github.com/strikersam/local-llm-server/stargazers)

</div>
