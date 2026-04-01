# local-llm-server

Open-source, self-hosted **OpenAI API–compatible** + **Anthropic Messages API–compatible** LLM proxy for **Ollama**, with a **Claude Code / Codex–style Web UI** and an **agentic coding backend**.

Keywords: OpenAI-compatible proxy, Anthropic Messages API proxy, Ollama gateway, Claude Code web UI, agentic coding.

Use it to:
- Run local models (Ollama) and access them securely from anywhere (tunnel) with familiar `/v1/*` APIs.
- Point dev tools at it (Cursor, Continue, Aider, Zed, VSCode clients, Claude Code CLI).
- Use the built-in Web UI for chat + repo-aware coding workflows.

## Screenshots

| Web UI (Agentic coding) | Admin app (Login) | Admin app (Providers + Workspaces) |
|---|---|---|
| ![Web UI](/docs/screenshots/webui-app.png) | ![Admin login](/docs/screenshots/webui-admin-login.png) | ![Admin app](/docs/screenshots/webui-admin.png) |

## What you get (high-level)

- **OpenAI-compatible endpoints**: `/v1/chat/completions`, `/v1/models`, `/v1/embeddings`
- **Anthropic-compatible endpoint**: `/v1/messages` (Claude Code CLI / Anthropic SDK)
- **Ollama passthrough**: `/api/*`
- **Claude Code–style Web UI**:
  - App: `/` or `/app`
  - Admin app: `/admin/app`
  - Web UI API: `/ui/api/*`
- **Agentic coding runner**: planner → executor → verifier with workspace tools (read/list/search/apply diff)
- **Security basics for public hosting**: API key auth, admin auth, per-key rate limiting, CORS
- **Observability (optional)**: Langfuse traces + cost metadata
- **Remote control (optional)**: Telegram bot + service manager scripts

## Quick start (local)

Prereqs: Python 3.13+, Node 22+, Ollama installed.

```bash
cp .env.example .env
```

Edit `.env` (minimum):

```env
API_KEYS=sk-qwen-...               # or use KEYS_FILE=keys.json for per-user keys
ADMIN_SECRET=...                   # generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Install and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

chmod +x *.sh
./start_server.sh
```

Open:
- Web UI: `http://localhost:8000/`
- Admin app: `http://localhost:8000/admin/app`
- Legacy admin dashboard: `http://localhost:8000/admin/ui/login`

Admin login note:
- **Windows-credential login works only when the server host OS is Windows** (`ADMIN_WINDOWS_AUTH=true`).
- On macOS/Linux hosts, log in with **`ADMIN_SECRET`** as the password (username can be anything).

## Public URL (worldwide access)

You can expose the proxy + Web UI publicly with a tunnel. The quickest option:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

This prints an `https://*.trycloudflare.com` URL you can use anywhere in the world.

## Web UI: Providers + Workspaces (what “host the full codebase” means)

This project supports two practical modes:

1) **Bundled workspace (default)**: the deployed app includes this repo’s files, so the agent can operate on “Current repo (bundled)” immediately.

2) **Additional workspaces (optional)**: in `/admin/app`, add a workspace via:
- **Local path** (server filesystem), or
- **Git clone** (clones server-side into `WEBUI_DATA_DIR`)

For most “free-tier cloud hosting” deployments, durable git-cloned workspaces require persistent disk; otherwise config/workspaces reset on restart.

## LLM connectivity (models in the cloud)

Running and persisting large downloadable model weights on true free-tier cloud compute is usually not feasible (GPU/RAM/disk/uptime constraints).

This repo’s best-practice setup is:
- Host **UI + agent backend** publicly
- Configure **remote OpenAI-compatible providers** in `/admin/app` (keys stored server-side)
- Optionally keep Ollama running on your own machine and connect via tunnel/VPN

## Deployment (Vercel replacement)

- Cloud Run (recommended “as-free-as-possible”): `docs/deploy/cloud-run.md`
- Docker (any host): `docs/deploy/docker.md`

## Docs (pick what you need)

Core:
- Web UI + Admin guide: `docs/admin-dashboard.md`
- Full feature list: `docs/features.md`
- Configuration/env vars: `docs/configuration-reference.md`
- Troubleshooting: `docs/troubleshooting.md`

Integrations:
- Claude Code CLI: `docs/claude-code-setup.md`
- Telegram bot: `docs/telegram-bot.md`
- Observability (Langfuse): `docs/langfuse-observability.md`

## Security model (short)

- **User access**: API key required on `/api/*`, `/v1/*`, `/agent/*`, and most `/ui/api/*`.
- **Admin access**: session token via `/admin/api/login` (or legacy `/admin/ui/login`). Use a strong `ADMIN_SECRET`.
- **Rate limiting**: per-key request limit via `RATE_LIMIT_RPM`.
- **No secrets to client**: provider keys are stored server-side; APIs return `has_api_key` only.

## License / contributions

PRs welcome. If you’re adding endpoints or changing behavior, update `docs/changelog.md` under `## [Unreleased]` (Keep a Changelog).
