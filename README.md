# Local LLM Remote Access Server

Run powerful open-source AI models on your home PC and access them securely from **any device, anywhere in the world** — using the same API interface as OpenAI.

No cloud costs. No data sent to third parties. Full control over your models.

---

## What You Get

- OpenAI-compatible local model access through `/v1/*`
- Authenticated Ollama passthrough through `/api/*`
- Multi-user key management with an admin UI
- Optional Langfuse tracing
- A local-first coding agent API for planner -> executor -> verifier runs

If you are upgrading from an older version, `API_KEYS` is now the legacy bootstrap path. For team use, `KEYS_FILE` + `ADMIN_SECRET` is the recommended setup.

Detailed release notes live in [docs/changelog.md](docs/changelog.md).

---

## The Problem This Solves

State-of-the-art open-weight LLMs are:

- **Free to download and run locally** — DeepSeek-R1, Qwen3-Coder, Llama 3.3, etc.
- **Expensive via cloud API** — pay per token, rate limited, usage tracked
- **Powerful enough** to replace paid tiers of Copilot, Claude, GPT-4 for most coding tasks

But running them locally only helps you *at your desk*. This project makes them accessible from **any laptop, tablet, or machine** — authenticated, rate-limited, and encrypted via HTTPS — as if they were a hosted API.

---

## Architecture

```
Your Home PC (always on)
├── Ollama                         localhost:11434
│     └── Model weights on fast storage (NVMe recommended for 671B)
│           ├── deepseek-r1:671b   404 GB  Q4_K_M  ← reasoning, research
│           ├── deepseek-r1:32b     18.5 GB Q4_K_M  ← fast reasoning, coding
│           └── qwen3-coder:30b     17.3 GB Q4_K_M  ← code generation, completion
│
├── Auth Proxy  (proxy.py)         localhost:8000
│     ├── Bearer token authentication
│     ├── Per-key rate limiting (configurable req/min)
│     ├── CORS headers for browser clients
│     ├── Full streaming (SSE) support
│     └── OpenAI-compatible /v1/* + Ollama native /api/* routes
│
└── Cloudflare Tunnel (cloudflared)
      └── https://your-name.trycloudflare.com   ← public HTTPS, no port forwarding
                        │
           Any authenticated machine
           ┌─────────────────────────────┐
           │  Cursor · Continue · Aider  │
           │  Python SDK · curl · any    │
           │  OpenAI-compatible client   │
           └─────────────────────────────┘
```

### Agent API

The repo now also exposes an authenticated coding-agent layer on top of the proxy:

- `POST /agent/sessions` creates a session with conversation history
- `POST /agent/sessions/{id}/run` runs a planner -> executor -> verifier loop
- `POST /agent/run` performs a one-off run without managing a session yourself
- `POST /agent/sessions/{id}/rollback-last-commit` reverts the last agent-created git commit when `auto_commit` was enabled

The loop is intentionally strict:

- Planner returns JSON only, maximum 5 steps
- Executor inspects the repo through explicit tools: `read_file`, `list_files`, `search_code`
- Code writes happen as full-file replacements via `apply_diff`
- Verifier returns `pass|fail` JSON and feeds issues back into a bounded retry loop

### Why Each Component

| Component | Role | Why |
|-----------|------|-----|
| **Ollama** | Serves models via REST API | Best cross-platform GPU support, built-in OpenAI-compatible `/v1` routes |
| **FastAPI proxy** | Auth + rate limiting | Ollama has no authentication — proxy guards all access |
| **Cloudflare Tunnel** | Public HTTPS endpoint | No port forwarding, no static IP, free TLS, works behind any NAT/firewall |
| **Batch/Shell launchers** | Process startup | Ensures env vars (model path, API keys) are correctly inherited by child processes |

---

## Models

These are the models currently running in this setup:

| Model | Size | Quant | Parameters | Primary use case |
|-------|------|-------|------------|------------------|
| `deepseek-r1:671b` | 404 GB | Q4_K_M | 671B | **Hard research, multi-step math, long-chain reasoning, “think like a flagship”** tasks where latency and hardware cost are acceptable — not for quick chat or IDE latency-sensitive loops. |
| `deepseek-r1:32b` | 18.5 GB | Q4_K_M | 32.8B | **Fast reasoning and coding**: architecture decisions, debugging, refactors, and agent-style work when you need R1-style thinking without 671B storage or RAM. |
| `qwen3-coder:30b` | 17.3 GB | Q4_K_M | 30.5B | **IDE-first work**: code generation, completion, review, tab autocomplete, and repo-aware edits — optimised for programming over general chat. |

> **Note on 671B:** Requires ~404 GB storage and ideally 236+ GB RAM to run fully in memory. With less RAM, Ollama uses memory-mapped I/O (mmap) from the NVMe SSD — responses in 30–90s on a Gen4 NVMe. The 32B distill from the same training run gives ~85% quality at 5% the size.

All models expose identical API endpoints — switch between them by changing the `model` field in your request.

### Running on modest hardware (local models + this setup)

If you prefer to run models **locally** on a laptop, mini PC, or older desktop, use **smaller** pulls from the same Ollama workflow — the proxy and tunnel work unchanged. Pick a tier that fits **unified RAM** (Mac) or **RAM + VRAM** (PC); see **[docs/device-compatibility.md](docs/device-compatibility.md)** for example devices (e.g. Apple Silicon with **~20 GB** unified memory vs. discrete-GPU PCs) and a fuller compatibility matrix.

**Apple Silicon (e.g. MacBook Pro with M-series, 16–24 GB unified)** — one pool for CPU, GPU, and weights; favour **one** large model at a time or 7B-class models for headroom:

| Model | ~Size (Q4 family) | Primary use case |
|-------|-------------------|------------------|
| `qwen3-coder:7b` | ~4–5 GB | Daily coding assistance, short chats, completion when 30B does not fit. |
| `deepseek-r1:7b` | ~4–5 GB | Lightweight reasoning and coding on low-memory machines. |
| `qwen3-coder:30b` / `deepseek-r1:32b` | ~17–19 GB each | Strong quality **only if** you can dedicate most RAM to a single loaded model (see doc). |

**Windows / Linux with a discrete NVIDIA GPU** — match **VRAM** to model size for GPU offload; if VRAM is tight, use smaller tags or fewer GPU layers and keep the rest on CPU/RAM:

| Model | ~Size (typical Q4) | Primary use case |
|-------|--------------------|------------------|
| `qwen3-coder:7b` | ~4–5 GB | Budget GPUs (e.g. 6–8 GB VRAM), or CPU fallback. |
| `deepseek-r1:7b` | ~4–5 GB | Same — fast reasoning relative to size. |
| `qwen3-coder:30b` | ~17–19 GB | **12–24 GB VRAM** class cards when using GPU-heavy offload. |
| `deepseek-r1:32b` | ~18–19 GB | Strong reasoning on **16–24 GB VRAM** or split offload. |

For more profiles (CPU-only, 8 GB total, home server vs. laptop) and RAM tier shortcuts, use **[docs/device-compatibility.md](docs/device-compatibility.md)**.

---

## Hardware Requirements

| | Minimum | Recommended (for 671B) |
|-|---------|----------------------|
| **RAM** | 16 GB | 128+ GB |
| **Storage** | 100 GB free | 500 GB+ NVMe SSD |
| **GPU VRAM** | 8 GB | 24+ GB (or iGPU with shared RAM) |
| **OS** | Windows 10 / macOS 12 / Ubuntu 20.04 | Any |
| **Internet** | Any | 100 Mbps+ upload for best remote experience |

The 32B and 30B models run comfortably on a modern gaming PC or MacBook Pro with 32+ GB RAM.

For **lower-spec or laptop-class machines** (e.g. Apple Silicon with **16–20 GB** unified memory, or PCs with limited VRAM), see **[docs/device-compatibility.md](docs/device-compatibility.md)** and the **Running on modest hardware** subsection under [Models](#models).

---

## Quick Start

### 1. Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
winget install Ollama.Ollama
# or download from https://ollama.com
```

### 2. Clone this repo

```bash
git clone https://github.com/strikersam/local-llm-server.git
cd local-llm-server
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Legacy fallback key(s). Optional once KEYS_FILE is in use.
API_KEYS=your-secret-key-here

# Recommended for team / multi-user setups
KEYS_FILE=keys.json
ADMIN_SECRET=generate-a-long-random-secret-here

# Where to store model weights (needs lots of free space)
# Windows: D:\ai-models   Linux: /mnt/data/ollama-models   macOS: /Volumes/Data/models
OLLAMA_MODELS=/path/to/your/model/storage

# Optional Langfuse tracing
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Recommended secret generation:

```bash
# Legacy API key (Linux/macOS)
openssl rand -base64 32 | tr '+/' '-_' | tr -d '='

# Admin secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```powershell
# Legacy API key (Windows PowerShell)
$rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
$bytes = New-Object byte[] 32; $rng.GetBytes($bytes)
[Convert]::ToBase64String($bytes).Replace('+','-').Replace('/','_').TrimEnd('=')

# Admin secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`KEYS_FILE` stores only SHA-256 hashes plus metadata. Plaintext user tokens are shown once when created, then never stored in recoverable form.

### 4. Download models

```bash
# Set model path first
export OLLAMA_MODELS=/path/to/your/model/storage  # Linux/macOS
# $env:OLLAMA_MODELS = "D:\ai-models"             # Windows

ollama pull qwen3-coder:30b      # 17 GB — start here
ollama pull deepseek-r1:32b      # 18 GB — fast reasoning
ollama pull deepseek-r1:671b     # 404 GB — flagship, needs big storage
```

### 5. One-time setup

```bash
# Linux / macOS
chmod +x *.sh
./install.sh

# Windows (PowerShell)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\install.ps1
```

Installs Python dependencies and cloudflared.

### 6. Start the server

```bash
# Linux / macOS
./start_server.sh

# Windows
.\start_server.ps1
```

Output:
```
[OK] Loaded .env
[1/3] Starting Ollama...
[OK] Ollama ready (PID 12345)
     - deepseek-r1:671b (404.0 GB)
     - deepseek-r1:32b (18.5 GB)
     - qwen3-coder:30b (17.3 GB)
[2/3] Starting Auth Proxy...
[OK] Auth Proxy running on port 8000 (PID 12346)
[3/3] Starting Cloudflare Tunnel...
[OK] Tunnel started (PID 12347)

  >>> Public URL: https://example-words-here.trycloudflare.com <<<
```

If `ADMIN_SECRET` is configured, the proxy also enables:

- `POST /admin/keys` for scripted user provisioning
- `http://localhost:8000/admin/ui/login` for the browser admin UI

If `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are configured, chat traffic is also traced to Langfuse.

If `AGENT_PLANNER_MODEL`, `AGENT_EXECUTOR_MODEL`, and `AGENT_VERIFIER_MODEL` are configured, `/agent/*` uses those local models by default.

### 7. Auto-start on boot

```bash
# Windows — registers a Task Scheduler job
.\register_task.ps1

# Linux — add to crontab
(crontab -l 2>/dev/null; echo "@reboot cd $(pwd) && ./start_server.sh") | crontab -

# macOS — create a launchd plist
# (see docs/macos-autostart.md — coming soon)
```

### 8. Stop the server

```bash
# Linux / macOS
./stop_server.sh

# Windows
.\stop_server.ps1
```

---

## Repository Structure

```
local-llm-server/
│
├── proxy.py                  # FastAPI auth proxy — the core of this project
├── requirements.txt          # Python dependencies
├── .env.example              # Config template — copy to .env
├── .gitignore
├── docs/
│   └── device-compatibility.md  # Device / RAM / model pairing guide
│
│── Linux / macOS
├── start_server.sh           # Start everything
├── stop_server.sh            # Stop everything
├── install.sh                # One-time setup
├── run_ollama.sh             # Ollama launcher
├── run_proxy.sh              # Proxy launcher
├── run_tunnel.sh             # Cloudflare tunnel launcher
├── get_tunnel_url.sh         # Show current public URL
│
│── Windows
├── start_server.ps1          # Start everything
├── stop_server.ps1           # Stop everything
├── install.ps1               # One-time setup
├── register_task.ps1         # Register auto-start (Task Scheduler)
├── get_tunnel_url.ps1        # Show + copy current public URL
├── run_ollama.bat            # Ollama launcher
├── run_proxy.bat             # Proxy launcher
├── run_tunnel.bat            # Cloudflare tunnel launcher
│
└── client-configs/
    ├── continue_config.json  # Legacy Continue config for older installs
    ├── continue_config.yaml  # Recommended Continue config
    ├── cursor_settings.json  # Cursor IDE
    ├── aider_config.sh       # Aider CLI (Linux/macOS/WSL)
    ├── aider_config.ps1      # Aider CLI (Windows)
    └── python_client_example.py
```

---

## User Management

For personal use, you can still set one or more comma-separated values in `API_KEYS`.

For a team or shared server, use:

- `KEYS_FILE=keys.json`
- `ADMIN_SECRET=<strong random secret>`

That unlocks persistent user records with:

- `email`: shown as the Langfuse `user_id`
- `department`: your seat / cost-center / team allocation label
- `key_id`: stable identifier for rotation and audit logs

### Create a user key from the CLI

```bash
python generate_api_key.py --email alice@company.com --department engineering
```

Example output:

```text
Key created. Distribute this secret once (it cannot be shown again):
sk-qwen-...

key_id:      kid_abc123def456
email:       alice@company.com
department:  engineering
stored in:   /absolute/path/to/keys.json
```

The proxy auto-reloads the JSON file on the next request, so you usually do not need to restart after adding or rotating keys.

### Create a user key via the Admin API

Enable `ADMIN_SECRET` and send:

```bash
curl http://localhost:8000/admin/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: your-admin-secret" \
  -d '{"email":"alice@company.com","department":"engineering"}'
```

You can also use `Authorization: Bearer <ADMIN_SECRET>` instead of `X-Admin-Secret`.

Response:

```json
{
  "api_key": "sk-qwen-...",
  "key_id": "kid_abc123def456",
  "email": "alice@company.com",
  "department": "engineering",
  "created": "2026-03-28T12:34:56Z"
}
```

### Browser Admin UI

With `ADMIN_SECRET` enabled, open:

```text
http://localhost:8000/admin/ui/login
```

After login, the admin dashboard lets you:

- create a user with `email` + `department`
- edit department allocation or email metadata later
- rotate a user token while keeping the same `key_id`
- revoke/delete a user key
- run a Langfuse connectivity diagnostic

### Department Allocation

`department` is a free-text label stored with each key. Use it for whatever internal grouping you need, for example:

- `engineering`
- `design`
- `research`
- `contractors`
- `customer-support`

That value travels with each authenticated chat request and is attached to Langfuse metadata and tags, making it useful for spendback/showback, seat allocation, or simple reporting by team.

---

## Langfuse Setup

Langfuse is optional, but it is the easiest way to see who is using which model and estimate what the same traffic would have cost on a commercial API.

### 1. Configure credentials

Create a project in [Langfuse Cloud](https://cloud.langfuse.com) or use your self-hosted instance, then set:

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

`LANGFUSE_HOST` is also accepted as an alias for `LANGFUSE_BASE_URL`.

Optional tuning:

```env
# Force REST ingestion if the Python SDK has trouble in your environment
LANGFUSE_USE_HTTP_ONLY=true

# Flush SDK events more aggressively
LANGFUSE_FLUSH_AT=1

# Optional custom commercial-equivalent pricing map
# COMMERCIAL_EQUIVALENT_PRICES_FILE=pricing.json
# COMMERCIAL_EQUIVALENT_PRICES_JSON={"my-local-model:tag":{"commercial_name":"GPT-4.1","input_per_million_usd":2,"output_per_million_usd":8}}
```

### 2. What gets recorded

For authenticated chat requests, the proxy records:

- Langfuse `user_id` = the key's `email`
- metadata `department` = the user's department allocation
- metadata `key_id` when the request used a stored key
- tags like `dept:engineering`
- model name
- prompt/completion token counts
- estimated commercial-equivalent USD and estimated savings metadata

Legacy `API_KEYS` still work, but those requests appear as `email=unknown` and `department=legacy`, so `KEYS_FILE` is strongly recommended if you care about observability.

### 3. Test the connection

Use the browser admin UI and click the Langfuse diagnostic action, or verify the credentials manually by starting the proxy and watching for successful traces after a chat request.

If traces are missing:

- confirm both Langfuse keys are set
- verify `LANGFUSE_BASE_URL` points to the correct cloud or self-hosted instance
- try `LANGFUSE_USE_HTTP_ONLY=true`
- check proxy logs for SDK fallback or HTTP errors

---

## API Reference

All routes except `/health` require `Authorization: Bearer <your-key>`.

### OpenAI-Compatible (works with any OpenAI SDK client)

```
POST /v1/chat/completions      # Chat — streaming and non-streaming
POST /v1/completions           # Legacy text completion
GET  /v1/models                # List available models
POST /v1/embeddings            # Embeddings
```

### Ollama Native

```
POST /api/generate             # Text generation
POST /api/chat                 # Chat
GET  /api/tags                 # List models
POST /api/pull                 # Pull a new model
GET  /api/ps                   # Show currently loaded models
```

### Health (no auth)

```
GET /health
→ {"status": "ok", "models": ["deepseek-r1:671b", "deepseek-r1:32b", "qwen3-coder:30b"]}
```

### Admin API

Available only when `ADMIN_SECRET` is set:

```
POST /admin/keys              # Create one user key with email + department
GET  /admin/ui/login          # Browser login page for admin dashboard
GET  /admin/ui/               # Browser dashboard (session after login)
```

---

## Client Setup

### Option 1 — Cursor IDE

The quickest way to get coding assistance using your home PC models inside Cursor.

1. Open Cursor → **Settings** (`Ctrl+,`) → **Models**
2. Scroll to the **OpenAI API Key** section and toggle it **ON**
3. Fill in the two fields:

| Field | Value |
|-------|-------|
| **API Key** | Your key from `.env` (e.g. `jnRLv...`) |
| **Override Base URL** | `https://your-tunnel-url/v1` |

4. Click **Verify** — Cursor confirms the connection
5. In the model input box, type a model name and press **Enter** to add it:
   - `deepseek-r1:671b` — best reasoning and complex tasks
   - `deepseek-r1:32b` — faster, great for coding
   - `qwen3-coder:30b` — optimised for code generation and tab autocomplete

The selected model is now used for chat (`Ctrl+L`), inline edit (`Ctrl+K`), and Composer.

> See `client-configs/cursor_settings.json` for a reference of these values.

---

### Option 2 — Open WebUI (Browser Chat UI with model switcher)

A full ChatGPT-style web interface with a dropdown to switch between all your local models. No IDE required — works in any browser on any device.

**With Docker (recommended):**

```bash
docker run -d \
  --name open-webui \
  -p 3000:8080 \
  -e OPENAI_API_BASE_URL=https://your-tunnel-url/v1 \
  -e OPENAI_API_KEY=your-key \
  ghcr.io/open-webui/open-webui:main
```

Then open **http://localhost:3000** in your browser.
Create an account on first launch, then go to **Settings → Models** — your models (`deepseek-r1:671b`, `deepseek-r1:32b`, `qwen3-coder:30b`) appear automatically, pulled from the `/v1/models` endpoint.

**Without Docker (pip):**

```bash
pip install open-webui
export OPENAI_API_BASE_URL=https://your-tunnel-url/v1
export OPENAI_API_KEY=your-key
open-webui serve
# Open http://localhost:8080
```

**Windows (PowerShell):**

```powershell
pip install open-webui
$env:OPENAI_API_BASE_URL = "https://your-tunnel-url/v1"
$env:OPENAI_API_KEY      = "your-key"
open-webui serve
# Open http://localhost:8080
```

> Open WebUI auto-discovers models — when you add a new model to your server it appears in the dropdown immediately without any config change.

---

### Option 3 — VS Code Continue Extension

Adds an AI chat panel and tab autocomplete directly inside VS Code, with a model switcher in the sidebar.

1. Install the **Continue** extension (`Ctrl+Shift+X` → search "Continue")
2. Use the recommended proxy settings in `.env` before exposing the server to Continue:

```env
PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED=false
PROXY_STRIP_THINK_TAGS=true
PROXY_DEFAULT_MAX_TOKENS=1200
```

This avoids prompt-stacking with Continue's own rules, strips leaked `<think>` blocks from models that expose them, and adds a conservative fallback limit when a client omits `max_tokens`.

3. Copy the recommended YAML config to your home directory:

```bash
# Linux / macOS
cp client-configs/continue_config.yaml ~/.continue/config.yaml

# Windows PowerShell
Copy-Item client-configs\continue_config.yaml "$env:USERPROFILE\.continue\config.yaml"
```

If you are on an older Continue build that still expects `config.json`, use `client-configs/continue_config.json` instead.

4. Open the file and replace the two placeholders:

```yaml
apiBase: https://YOUR_TUNNEL_URL/v1
apiKey: YOUR_API_KEY
```

5. Reload VS Code — models appear in the Continue sidebar dropdown.

Recommended behavior for accuracy and reliability:

- Keep `qwen3-coder:30b` as the primary Continue model for chat, edit, apply, summarize, and autocomplete.
- Use `deepseek-r1:32b` only as an optional manual chat profile when you want extra reasoning and accept slower, less format-disciplined responses.
- Keep Continue context lean: `code`, `diff`, and `folder` are usually enough. Adding `docs`, `terminal`, `problems`, or `codebase` increases prompt size and can reduce determinism.
- Start sensitive evals or tricky refactors in a fresh Continue chat so prior prompt state does not leak into the task.

> See `client-configs/continue_config.yaml` for the recommended setup and `client-configs/continue_config.json` for legacy compatibility.

---

### Option 4 - Zed

`client-configs/zed_settings.json` contains a starting point for Zed's assistant configuration against this proxy. Replace the placeholder base URL and API key with your tunnel URL and a user key from `KEYS_FILE` or `API_KEYS`.

---

### Aider

```bash
# Linux / macOS / WSL
source client-configs/aider_config.sh
aider --model openai/deepseek-r1:671b

# Windows PowerShell
. .\client-configs\aider_config.ps1
aider --model openai/deepseek-r1:671b
```

### Python (openai SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-tunnel-url/v1",
    api_key="your-key"
)

# Streaming
stream = client.chat.completions.create(
    model="deepseek-r1:671b",
    messages=[{"role": "user", "content": "Explain how transformers work"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

### curl

```bash
# List models
curl https://your-tunnel-url/api/tags \
  -H "Authorization: Bearer your-key"

# Generate (streaming)
curl https://your-tunnel-url/api/generate \
  -H "Authorization: Bearer your-key" \
  -d '{"model":"qwen3-coder:30b","prompt":"Write a binary search in Python","stream":true}'

# Chat (OpenAI format)
curl https://your-tunnel-url/v1/chat/completions \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1:32b","messages":[{"role":"user","content":"Hello"}]}'
```

### Coding Agent API

Create a session:

```bash
curl https://your-tunnel-url/agent/sessions \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{"title":"Refactor auth flow"}'
```

Run a task:

```bash
curl https://your-tunnel-url/agent/run \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction":"Add a healthcheck note to the README and keep the wording concise",
    "auto_commit": false,
    "max_steps": 3
  }'
```

The response includes:

- the generated plan
- per-step status
- changed files
- any commit hashes created during the run
- a short summary suitable for UI display

### Tests

Run the lightweight automated checks from the repo root:

```bash
pytest
```

The tests cover:

- workspace tool behavior
- mocked planner/executor/verifier loop behavior
- session and failure handling in the `/agent/*` API

---

## Security

| Threat | Mitigation |
|--------|-----------|
| Unauthorized access | Bearer token on all `/api/*` and `/v1/*` routes |
| Brute force | Rate limiting per key (default 60 req/min, configurable) |
| Man-in-the-middle | Cloudflare handles TLS — all traffic HTTPS end-to-end |
| Direct Ollama exposure | Ollama binds to `127.0.0.1` only — unreachable from outside |
| Key compromise | One key per device — revoke by removing from `API_KEYS` in `.env` |

**Never commit `.env`** — it is listed in `.gitignore`. Use `.env.example` as the template.

---

## Adding More Models

Any model pulled into `OLLAMA_MODELS` appears on the API immediately — no restart needed:

```bash
# Set model path
export OLLAMA_MODELS=/your/model/path

# Pull any Ollama-compatible model
ollama pull llama3.3:70b
ollama pull gemma3:27b
ollama pull phi4
```

Then use the model name directly in any client request.

---

## Permanent URL (Optional)

The default quick-tunnel URL changes on every server restart. For a permanent URL:

1. Create a free account at [cloudflare.com](https://cloudflare.com)
2. Run `./install.sh` (Linux/macOS) or `.\install.ps1` (Windows) and choose option **2 — Named Tunnel**
3. Optionally route a custom domain (e.g. `llm.yourdomain.com`) to the tunnel

Named tunnel URLs survive restarts and can be tied to a domain you own.

---

## Troubleshooting

**Ollama won't start**
```bash
tail -20 logs/ollama-err.log
```

**Proxy not reachable**
```bash
tail -20 logs/proxy-err.log
curl http://localhost:8000/health
```

**Can't find tunnel URL**
```bash
./get_tunnel_url.sh        # Linux/macOS
.\get_tunnel_url.ps1       # Windows
```

**403 Forbidden from remote machine**
Your API key doesn't match `API_KEYS` in `.env`. Keys are case-sensitive.

**671B responses are slow**
Expected when model doesn't fit fully in RAM — Ollama pages from NVMe via mmap. A Gen4 NVMe gives the best experience (~30–90s per response). The 32B model runs entirely in RAM and is much faster.

**Model still shows as downloading**
Check progress: the partial blob file size vs expected total. Restart the pull if interrupted — Ollama resumes from where it left off.

---

## Recommended Models by Hardware

Quick RAM tiers (details and example machines — **Mac M-series vs PC**, CPU-only, etc. — are in **[docs/device-compatibility.md](docs/device-compatibility.md)**):

| Approx. RAM | Recommended models |
|-------------|-------------------|
| 16 GB | `qwen3-coder:7b`, `deepseek-r1:7b` |
| 32 GB | `qwen3-coder:30b`, `deepseek-r1:32b` |
| 64 GB | `llama3.3:70b`, `qwen3:32b` |
| 128 GB+ | `deepseek-r1:671b` (via mmap), all of the above simultaneously |

---

## Why Not Just Use the Cloud?

| | Cloud API | This Setup |
|--|-----------|-----------|
| Cost | Pay per token | Free after hardware |
| Privacy | Data sent to provider | Stays on your machine |
| Rate limits | Enforced by provider | You control them |
| Model choice | Provider's catalogue only | Any open-weight model |
| 671B model access | Very expensive | Free |
| Offline use | No | Yes |

---

## License

MIT — use freely, modify freely, no warranty.

---

## Acknowledgements

- [Ollama](https://ollama.com) — local model serving made simple
- [DeepSeek](https://deepseek.com) — open-weight R1 models
- [Qwen / Alibaba Cloud](https://qwenlm.github.io) — Qwen3-Coder
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps) — free secure tunneling
- [FastAPI](https://fastapi.tiangolo.com) — async Python web framework
