# Configuration Reference

Complete reference for every environment variable in `.env`. Copy `.env.example` to `.env` and fill in the values that apply to your setup. Variables not listed in `.env` use the documented defaults.

---

## Authentication and Keys

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `API_KEYS` | (none) | If no `KEYS_FILE` | Legacy comma-separated bearer tokens. All traffic from these keys appears as `user=unknown` in Langfuse. Prefer `KEYS_FILE` for team use. |
| `KEYS_FILE` | (none) | Recommended | Path to the JSON key store (e.g. `keys.json`). Created automatically by `generate_api_key.py`. Enables per-user email/department tracking. |
| `ADMIN_SECRET` | (none) | For admin UI/API | Strong random secret for the browser admin UI and admin API. Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ADMIN_WINDOWS_AUTH` | `true` on Windows | No | Enable Windows credential-based admin login. Users log in with their Windows machine username and password. |
| `ADMIN_WINDOWS_ALLOWED_USERS` | (empty) | No | Comma-separated Windows usernames allowed to log in (e.g. `HOSTNAME\swami,swami`). Empty = all local users allowed. |
| `ADMIN_WINDOWS_DEFAULT_DOMAIN` | `.` | No | Default domain for username normalization. `.` means local machine. |

---

## Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE` | `http://localhost:11434` | URL of the Ollama server. Change only if running Ollama on a different machine or port. |
| `PROXY_PORT` | `8000` | Port the FastAPI proxy listens on. |
| `RATE_LIMIT_RPM` | `60` | Max requests per minute per API key. Set to `0` to disable. |
| `CORS_ORIGINS` | `*` | Comma-separated allowed browser origins, or `*` for any. Restrict for production: `https://myapp.example.com` |
| `LOG_LEVEL` | `INFO` | Log verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`. Use `DEBUG` during setup. |

---

## Proxy Behavior

| Variable | Default | Description |
|----------|---------|-------------|
| `PROXY_INJECT_STREAM_USAGE` | `true` | Inject token usage into SSE stream chunks. Disable if your Ollama build rejects `stream_options`. |
| `PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED` | `false` | Inject the configured system prompt into requests that don't include one. Disable for Claude Code and Continue (they send their own). |
| `PROXY_DEFAULT_SYSTEM_PROMPT` | (none) | Inline system prompt text. Takes precedence over `PROXY_DEFAULT_SYSTEM_PROMPT_FILE`. |
| `PROXY_DEFAULT_SYSTEM_PROMPT_FILE` | `templates/codex_local_ide_system_prompt.txt` | Path to system prompt file (relative to repo root). |
| `PROXY_STRIP_THINK_TAGS` | `true` | Remove `<think>...</think>` blocks from model responses. Recommended for DeepSeek-R1 and other reasoning models. |
| `PROXY_DEFAULT_MAX_TOKENS` | `8192` | Fallback `max_tokens` applied when the client does not send one. **Must be ≥ 4096 for Claude Code.** The old default of 1200 truncates code generation responses. |

---

## Anthropic API Compatibility / Claude Code

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_MAP` | (built-in defaults) | Maps Anthropic model names to local Ollama model names. Format: `anthropic_name:local_name` — comma-separated. `*` is a catch-all fallback. Example: `claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b` |

Built-in default mappings (active when `MODEL_MAP` is not set):

| Anthropic name | Mapped to |
|----------------|-----------|
| `claude-opus-4-6` | `deepseek-r1:32b` |
| `claude-sonnet-4-6` | `qwen3-coder:30b` |
| `claude-haiku-4-5-20251001` | `qwen3-coder:30b` |
| `claude-3-5-sonnet-20241022` | `qwen3-coder:30b` |
| `claude-3-opus-*` | `deepseek-r1:32b` |
| `*` (catch-all) | `qwen3-coder:30b` |

See [docs/claude-code-setup.md](claude-code-setup.md) for full Claude Code setup instructions.

---

## Agent Models

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_PLANNER_MODEL` | `deepseek-r1:32b` | Model used for task planning (breaks task into ≤5 steps, returns JSON). Reasoning models work best. |
| `AGENT_EXECUTOR_MODEL` | `qwen3-coder:30b` | Model used for code writing and file manipulation. Coding-specialist models recommended. |
| `AGENT_VERIFIER_MODEL` | `deepseek-r1:32b` | Model used to validate each code change (returns pass/fail JSON). |
| `AGENT_WORKSPACE_ROOT` | (repo root) | Absolute path to the workspace the agent operates on. Defaults to the directory containing `proxy.py`. |

---

## Web UI (Claude Code–style)

| Variable | Default | Description |
|----------|---------|-------------|
| `WEBUI_DATA_DIR` | `.data` | Directory for server-side Web UI config storage (providers/workspaces). Not served to clients. Use a persistent volume path in production if you want provider/workspace config to survive restarts. |
| `DATA_DIR` | (unset) | Alias for `WEBUI_DATA_DIR` (kept for convenience). |
| `WEBUI_CMD_ALLOWLIST` | `pytest,rg,git,ls,cat` | Comma-separated allowlist for the admin-only command runner (`POST /admin/api/commands/run`). `git` is further restricted to safe subcommands (`status`, `diff`, `log`, `show`, `rev-parse`). |
| `DEFAULT_TEMPERATURE` | `0.2` | Default temperature used when seeding providers from env (can be overridden per provider in the Admin app). |
| `OPENAI_COMPAT_BASE_URL` | (unset) | Optional: seed a remote OpenAI-compatible provider on first boot (e.g. `https://api.openai.com`). Also accepted as `OPENAI_BASE_URL`. |
| `OPENAI_COMPAT_API_KEY` | (unset) | Optional: API key for the seeded provider. Also accepted as `OPENAI_API_KEY`. |
| `OPENAI_COMPAT_MODEL` | (unset) | Optional: default model for the seeded provider. Also accepted as `OPENAI_MODEL`. |

---

## Dashboard (React UI on :3000, API on :8001)

These settings apply to the "LLM Relay" dashboard (`frontend/` + `backend/server.py`).

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URL` | `mongodb://localhost:27017` | MongoDB connection string for wiki pages, sources, providers, and chat sessions. |
| `DB_NAME` | `llm_wiki_dashboard` | Mongo database name. |
| `JWT_SECRET` | (random per start) | Secret used to sign access/refresh tokens. Set a stable value for production. |
| `ADMIN_EMAIL` | `admin@llmrelay.local` | Seeded admin email for the dashboard login. |
| `ADMIN_PASSWORD` | (none) | Seeded admin password. Set this explicitly before exposing the dashboard. |
| `FRONTEND_URL` | `http://localhost:3000` | Default CORS origin when a request has no Origin header. |
| `LLM_PROVIDER` | `deepseek` | Which seeded provider should be default (`deepseek`, `ollama`, `huggingface`, `openrouter`, `together`). |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL for the default provider. |
| `OLLAMA_MODEL` | `llama3.2` | Default model for the seeded Ollama provider. |
| `HF_TOKEN` | (unset) | Hugging Face token for the seeded HF provider (also accepted as `HUGGINGFACE_API_TOKEN`). Optional but recommended. |
| `HF_BASE_URL` | `https://router.huggingface.co` | OpenAI-compatible Hugging Face router base URL. |
| `HF_MODEL_ID` | `Qwen/Qwen2.5-Coder-7B-Instruct` | Default model for the seeded Hugging Face provider. |

---

## Langfuse Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | (none) | Langfuse project public key (starts with `pk-lf-`). |
| `LANGFUSE_SECRET_KEY` | (none) | Langfuse project secret key (starts with `sk-lf-`). |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Langfuse instance URL. Change for self-hosted. Also accepted as `LANGFUSE_HOST`. |
| `LANGFUSE_USE_HTTP_ONLY` | `false` | Force REST-only ingestion (no Python SDK). Use if SDK has SSL or compatibility issues. |
| `LANGFUSE_FLUSH_AT` | (auto) | SDK event batch size before flush. Set to `1` for low-latency event delivery. |
| `COMMERCIAL_EQUIVALENT_PRICES_FILE` | (none) | Path to JSON file with custom pricing overrides. See [Langfuse observability guide](langfuse-observability.md). |
| `COMMERCIAL_EQUIVALENT_PRICES_JSON` | (none) | Inline JSON pricing override. Takes precedence over file. |

---

## Infrastructure Cost Tracking

Used to calculate the true cost of local inference and emit it to Langfuse.

Measure your actual values with GPU-Z, HWiNFO64 (Windows) or `nvidia-smi` (Linux) under inference load, or use a wall-outlet power meter for the most accurate whole-system reading.

| Variable | Default | Description |
|----------|---------|-------------|
| `INFRA_GPU_ACTIVE_WATTS` | `150` | GPU power draw during active inference (W). Typical ranges: Intel AI PC iGPU: 30–50W; RTX 4080: 150–200W; RTX 4090: 200–300W. |
| `INFRA_GPU_IDLE_WATTS` | `20` | GPU power when model is loaded but idle (W). |
| `INFRA_SYSTEM_WATTS` | `50` | CPU, RAM, SSD, and overhead (W). |
| `INFRA_ELECTRICITY_USD_KWH` | `0.12` | Your electricity rate in USD/kWh. Check your utility bill. US average ~$0.12; EU varies $0.15–0.35. |
| `INFRA_HARDWARE_COST_USD` | `2000` | Total purchase cost of inference hardware (GPU + system). Used for amortization. |
| `INFRA_AMORTIZATION_MONTHS` | `36` | How many months to spread the hardware cost over (36 = 3 years). |
| `INFRA_MODEL_STORAGE_GB` | (optional) | Model weights disk footprint (GB). Informational only. |
| `INFRA_STORAGE_USD_GB_MO` | `0.023` | Storage cost per GB/month. Default: AWS S3 pricing. Adjust for your NAS/SSD cost. |

**Preset examples:**

```env
# Intel AI PC (Lunar Lake / Meteor Lake with Arc iGPU)
INFRA_GPU_ACTIVE_WATTS=35
INFRA_GPU_IDLE_WATTS=8
INFRA_SYSTEM_WATTS=25
INFRA_HARDWARE_COST_USD=1500

# RTX 4090 workstation
INFRA_GPU_ACTIVE_WATTS=250
INFRA_GPU_IDLE_WATTS=20
INFRA_SYSTEM_WATTS=80
INFRA_HARDWARE_COST_USD=3500

# Mac Studio M4 Ultra
INFRA_GPU_ACTIVE_WATTS=90
INFRA_GPU_IDLE_WATTS=15
INFRA_SYSTEM_WATTS=20
INFRA_HARDWARE_COST_USD=3000
```

---

## Telegram Bot

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | (none) | Bot token from @BotFather. Required to run `telegram_bot.py`. |
| `TELEGRAM_ALLOWED_USER_IDS` | (none) | Comma-separated Telegram user IDs that can use the bot (read-only commands). Get IDs via @userinfobot. |
| `TELEGRAM_ADMIN_USER_IDS` | (none) | Subset of `ALLOWED` that can run service control and key management commands. |
| `TELEGRAM_PROXY_API_KEY` | (none) | API key the bot uses to call `/admin/*` endpoints. Use your `ADMIN_SECRET` value here. |
| `PROXY_BASE_URL` | `http://localhost:8000` | Proxy URL the bot calls. Change if running the bot on a different machine than the proxy. |

See [docs/telegram-bot.md](telegram-bot.md) for full setup instructions.

---

## Model Storage and Executable Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODELS` | `~/.ollama/models` | Directory where Ollama stores downloaded model weights. Recommended: `D:\aipc-models` (Windows), `/mnt/data/ollama-models` (Linux). Needs lots of free space. |
| `OLLAMA_EXE` | (auto-detect) | Explicit path to `ollama.exe` or `ollama` binary. Only needed if Ollama is not on `PATH`. Windows AI PC path: `C:\Users\swami\AppData\Roaming\aipc\runtime\ollama\ollama.exe`. |
| `PYTHON_EXE` | (auto-detect) | Explicit path to Python. Needed on Windows if `python` opens the Store app. Example: `C:\Users\swami\AppData\Local\Programs\Python\Python312\python.exe` |
| `CLOUDFLARED_EXE` | (auto-detect) | Explicit path to `cloudflared.exe`. Default install: `C:\Program Files (x86)\cloudflared\cloudflared.exe`. |
| `NGROK_EXE` | (auto-detect) | Explicit path to `ngrok` binary. Auto-detected from pyngrok's download location if blank. |

---

## Tunnel — Permanent Static URL (ngrok)

Run `setup_ngrok.py` once to populate these automatically. Get your token free at [dashboard.ngrok.com](https://dashboard.ngrok.com).

| Variable | Default | Description |
|----------|---------|-------------|
| `PUBLIC_URL` | (empty) | Pinned public URL shown in the Admin UI and returned by `get_tunnel_url()`. Overrides the auto-detected quick-tunnel URL. Set by `setup_ngrok.py` or paste manually in the Admin UI. |
| `NGROK_AUTH_TOKEN` | (empty) | Your ngrok account token. Used by `run_tunnel.sh` / `run_tunnel.bat` after running `setup_ngrok.py`. |
| `NGROK_DOMAIN` | (empty) | Your free static ngrok domain (e.g. `yourword-yourword-1234.ngrok-free.app`). Used by the tunnel scripts. |

---

## Quick Reference — Minimal Configs

### Personal use (single key)

```env
API_KEYS=your-key-here
OLLAMA_MODELS=D:\aipc-models
PROXY_DEFAULT_MAX_TOKENS=8192
PROXY_STRIP_THINK_TAGS=true
```

### Team use with observability

```env
KEYS_FILE=keys.json
ADMIN_SECRET=strong-random-secret
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
OLLAMA_MODELS=D:\aipc-models
PROXY_DEFAULT_MAX_TOKENS=8192
PROXY_STRIP_THINK_TAGS=true
```

### Claude Code setup

```env
API_KEYS=your-key-here
PROXY_DEFAULT_MAX_TOKENS=8192
PROXY_STRIP_THINK_TAGS=true
PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED=false
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
```

### Full setup with Telegram bot

```env
KEYS_FILE=keys.json
ADMIN_SECRET=strong-random-secret
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
OLLAMA_MODELS=D:\aipc-models
PROXY_DEFAULT_MAX_TOKENS=8192
PROXY_STRIP_THINK_TAGS=true
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ALLOWED_USER_IDS=12345678
TELEGRAM_ADMIN_USER_IDS=12345678
TELEGRAM_PROXY_API_KEY=strong-random-secret
INFRA_GPU_ACTIVE_WATTS=150
INFRA_GPU_IDLE_WATTS=20
INFRA_SYSTEM_WATTS=50
INFRA_ELECTRICITY_USD_KWH=0.12
INFRA_HARDWARE_COST_USD=2000
INFRA_AMORTIZATION_MONTHS=36
```
