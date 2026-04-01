# Docker (local or any container host)

The repository includes a `Dockerfile` that bundles the Web UI (`webui/frontend/`) into the FastAPI proxy image.

## Build

```bash
docker build -t local-llm-server:latest .
```

## Run (minimal)

```bash
docker run --rm -p 8000:8000 \
  -e API_KEYS="sk-qwen-CHANGE-ME" \
  -e ADMIN_SECRET="CHANGE-ME" \
  local-llm-server:latest
```

Then open:
- App: `http://localhost:8000/` (or `/app`)
- Admin app: `http://localhost:8000/admin/app`
- Legacy admin UI: `http://localhost:8000/admin/ui/login`

## Provider configuration (recommended for cloud)

If you are not running Ollama inside the same container/network, configure a remote OpenAI-compatible provider:

Option A — env seed (creates a default provider on first boot):
- `OPENAI_COMPAT_BASE_URL`
- `OPENAI_COMPAT_API_KEY`
- `OPENAI_COMPAT_MODEL` (optional)

Option B — configure from the Admin app at `/admin/app` → Providers.

