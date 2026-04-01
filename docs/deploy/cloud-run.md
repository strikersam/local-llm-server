# Deploy to Google Cloud Run (Vercel replacement)

This repo now includes a built-in Claude Code–style Web UI served by the FastAPI proxy:
- App: `/` or `/app`
- Admin app: `/admin/app`
- Legacy admin dashboard: `/admin/ui/login`

Cloud Run is recommended as an “as-free-as-possible” hosting option (pay only beyond the monthly free tier). It provides a public HTTPS URL reachable worldwide.

## What’s realistically “free” in the cloud (models)

Running and persisting **large downloadable LLM weights** on free-tier cloud compute is usually not feasible (GPU scarcity, low RAM/disk, short-lived instances).

This deployment targets:
- Hosting the **UI + agent backend** on Cloud Run
- Connecting to **remote hosted OpenAI-compatible endpoints** (recommended) via `/admin/app` → Providers

If you want local models, keep running Ollama on a machine you control and expose it (or this proxy) via a tunnel / VM.

## Prereqs

- A Google Cloud project with billing enabled
- `gcloud` installed and authenticated
- Docker installed (or use Cloud Build)

## Build + deploy (Dockerfile)

From the repo root:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# Build a container (Cloud Build)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/local-llm-server

# Deploy
gcloud run deploy local-llm-server \
  --image gcr.io/YOUR_PROJECT_ID/local-llm-server \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000
```

After deploy, Cloud Run prints a public URL. Open it in a browser.

## Required configuration

### 1) Admin protection (required)

Set a strong admin secret in Cloud Run environment variables:

- `ADMIN_SECRET` — strong random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`)

### 2) User API keys (required)

You must configure at least one API key so `/agent/*` and `/ui/api/*` are usable:

- `API_KEYS` — comma-separated keys (simple) **or**
- `KEYS_FILE` — path to a JSON file for key persistence (recommended for non-ephemeral disks)

On Cloud Run, the filesystem is ephemeral, so `API_KEYS` is simplest.

### 3) LLM provider (recommended)

Cloud Run won’t have Ollama by default. Add a remote OpenAI-compatible provider:

- Either set env vars (auto-seeded provider):
  - `OPENAI_COMPAT_BASE_URL` (or `OPENAI_BASE_URL`)
  - `OPENAI_COMPAT_API_KEY` (or `OPENAI_API_KEY`)
  - `OPENAI_COMPAT_MODEL` (optional)

- Or (recommended) add providers from `/admin/app` after deployment.

## Verification checklist (Cloud Run)

1. Open `https://YOUR_RUN_URL/` → UI loads
2. Open `https://YOUR_RUN_URL/admin/app` → log in with `ADMIN_SECRET`
3. In Admin app:
   - Add a Provider (OpenAI-compatible base URL + API key + default model)
   - Confirm Workspaces list shows “Current repo (bundled)”
4. Create a user API key (legacy UI at `/admin/ui/login`, or set `API_KEYS`)
5. In `/app`:
   - Paste API key
   - Choose Provider + Workspace + Model
   - Create session → send an instruction → see plan + steps

## Notes / limitations on Cloud Run

- **Workspace persistence:** additional git-cloned workspaces are stored under `WEBUI_DATA_DIR` (default `.data`). On Cloud Run this is ephemeral; for durable workspaces/config, use a platform with a persistent disk.
- **Command runner:** admin-only and allow-listed (`pytest`, `rg`, `git status|diff|log|show|rev-parse`, `ls`, `cat`). Configure allowlist with `WEBUI_CMD_ALLOWLIST`.

