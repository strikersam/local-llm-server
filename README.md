# Local LLM Remote Access Server

Run powerful open-source AI models on your home PC and access them securely from **any device, anywhere in the world** — with the same API interface as OpenAI.

No cloud costs. No data leaving your network unencrypted. Full control.

---

## The Problem This Solves

State-of-the-art LLMs like **DeepSeek-R1:671B**, **Qwen3-Coder:30B**, and **DeepSeek-R1:32B** are:

- **Free to download and run locally** (open weights)
- **Expensive via cloud API** (pay-per-token)
- **Powerful enough** to replace paid tiers of Claude, GPT-4, Copilot for most coding tasks

But running them locally only helps you *at your desk*. This project makes them available from **any laptop, tablet, or machine** — authenticated, rate-limited, and encrypted — as if they were a hosted API.

---

## Architecture

```
Your Home PC
├── Ollama (model server)          localhost:11434
│     └── Models stored on D:\aipc-models\
│           ├── deepseek-r1:671b   (404 GB, Q4_K_M)
│           ├── deepseek-r1:32b    (18.5 GB, Q4_K_M)
│           └── qwen3-coder:30b    (17.3 GB, Q4_K_M)
│
├── Auth Proxy (FastAPI)           localhost:8000
│     ├── Bearer token authentication
│     ├── Per-key rate limiting (60 req/min default)
│     ├── CORS headers
│     └── Full streaming support (SSE)
│
└── Cloudflare Tunnel (cloudflared)
      └── https://your-url.trycloudflare.com  <-- public HTTPS
                    |
          Any authenticated device
          (Cursor, Continue, Aider, Python, curl)
```

### Why Each Component

| Component | Role | Why This Choice |
|-----------|------|----------------|
| **Ollama** | Serves models via REST API | Best Windows GPU support, OpenAI-compatible `/v1` routes built in |
| **FastAPI proxy** | Adds auth + rate limiting | Ollama has no auth — proxy sits in front and guards access |
| **Cloudflare Tunnel** | Exposes local port to internet | No port forwarding, no static IP needed, free TLS, works behind NAT |
| **Batch launchers** | Start processes with correct env vars | PowerShell `Start-Process` doesn't reliably inherit env vars; `.bat` files do |

---

## Hardware Requirements

| Component | Minimum | This Setup |
|-----------|---------|------------|
| RAM | 32 GB | 111.6 GB |
| GPU VRAM | 8 GB | AMD Radeon 8060S (shared, ~57 GB) |
| Storage | 500 GB free | 1 TB NVMe SSD (D: drive) |
| OS | Windows 10+ | Windows 11 |
| Internet | 10 Mbps up | — |

**Note on the 671B model:** It requires ~404 GB storage and ~236 GB RAM to run fully in memory. With less RAM, Ollama uses memory-mapped I/O from the NVMe SSD. A Gen4 NVMe (like the Kioxia Exceria Plus G4 used here) makes this viable — responses in 30–60s rather than minutes.

---

## Models

| Model | Size | Best For |
|-------|------|----------|
| `deepseek-r1:671b` | 404 GB | Complex reasoning, math, research |
| `deepseek-r1:32b` | 18.5 GB | Fast reasoning, coding |
| `qwen3-coder:30b` | 17.3 GB | Code generation, completion, review |

All use **Q4_K_M** quantization — the best balance of quality and size.

---

## Quick Start

### Prerequisites

- Windows 10/11 PC with 32+ GB RAM
- [Intel AI PC app](https://www.intel.com/content/www/us/en/products/docs/processors/core-ultra/ai-pc.html) or [Ollama](https://ollama.com) installed
- Python 3.10+
- Internet connection

### 1. Clone the repo

```powershell
git clone https://github.com/strikersam/local-llm-server.git
cd local-llm-server
```

### 2. Configure

```powershell
Copy-Item .env.example .env
notepad .env
```

Edit `.env`:
- Set `API_KEYS` to a secure random string (your auth token)
- Set `OLLAMA_MODELS` to your model storage path
- Adjust `PROXY_PORT` and `RATE_LIMIT_RPM` if needed

Generate a secure key (PowerShell):
```powershell
$rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
$bytes = New-Object byte[] 32; $rng.GetBytes($bytes)
[Convert]::ToBase64String($bytes).Replace("+","-").Replace("/","_").TrimEnd("=")
```

### 3. Install dependencies

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\install.ps1
```

This installs:
- Python packages (FastAPI, uvicorn, httpx)
- cloudflared (Cloudflare Tunnel client)
- Optionally sets up a named tunnel for a permanent URL

### 4. Download models

Edit `pull_model.bat` with the model you want, then run it:

```powershell
# Example: pull DeepSeek-R1 32B
$env:OLLAMA_MODELS = "D:\aipc-models"
& "path\to\ollama.exe" pull deepseek-r1:32b
```

Or use the AIPC app's model browser to download models graphically.

### 5. Start the server

```powershell
.\start_server.ps1
```

Output:
```
[OK] Loaded .env
[1/3] Starting Ollama...
[OK] Ollama running (PID 1234)
[2/3] Starting Auth Proxy...
[OK] Auth Proxy running on port 8000
[3/3] Starting Cloudflare Tunnel...
[OK] Tunnel started
  >>> Public URL: https://xxxx-yyyy-zzzz.trycloudflare.com <<<
```

### 6. Auto-start on boot

```powershell
.\register_task.ps1
```

Registers a Windows Task Scheduler job that starts the server automatically every time you log in.

### 7. Stop the server

```powershell
.\stop_server.ps1
```

---

## Files

```
local-llm-server/
├── proxy.py                    # FastAPI auth proxy (main server code)
├── requirements.txt            # Python dependencies
├── .env.example                # Config template (copy to .env)
├── .gitignore
│
├── start_server.ps1            # Start everything (Ollama + proxy + tunnel)
├── stop_server.ps1             # Stop everything
├── install.ps1                 # One-time setup (deps + cloudflared)
├── register_task.ps1           # Register Windows auto-start task
├── setup_autostart.ps1         # Alternative interactive auto-start setup
├── get_tunnel_url.ps1          # Show + copy current public URL
│
├── run_ollama.bat              # Starts Ollama with correct env vars
├── run_proxy.bat               # Starts uvicorn proxy with correct env vars
├── run_tunnel.bat              # Starts cloudflared tunnel
│
└── client-configs/
    ├── continue_config.json    # VS Code Continue extension
    ├── cursor_settings.json    # Cursor IDE
    ├── aider_config.sh         # Aider CLI (Linux/macOS/WSL)
    ├── aider_config.ps1        # Aider CLI (Windows)
    ├── python_client_example.py
    └── vscode_settings.json
```

---

## API Reference

The proxy exposes two route families — both require `Authorization: Bearer <key>`.

### Ollama Native API

```
POST /api/generate          # Text generation
POST /api/chat              # Chat completion
GET  /api/tags              # List models
POST /api/pull              # Pull a new model
GET  /api/ps                # Show loaded models
```

### OpenAI-Compatible API

```
POST /v1/chat/completions   # Drop-in OpenAI replacement
POST /v1/completions        # Legacy completions
GET  /v1/models             # List models
POST /v1/embeddings         # Embeddings
```

### Health Check (no auth required)

```
GET /health
```

Returns:
```json
{"status": "ok", "ollama": "http://localhost:11434", "models": ["deepseek-r1:671b", ...]}
```

---

## Client Setup

### Cursor

`Settings (Ctrl+,) → Models → OpenAI API Key section`:

| Field | Value |
|-------|-------|
| API Key | Your key from `.env` |
| Override Base URL | `https://your-tunnel-url/v1` |

Type model names manually: `deepseek-r1:671b`, `qwen3-coder:30b`, etc.

### VS Code — Continue Extension

Copy `client-configs/continue_config.json` to `~/.continue/config.json`.
Replace `YOUR_TUNNEL_URL` and `YOUR_API_KEY`.

### Aider

```bash
# Linux/macOS
source client-configs/aider_config.sh
aider --model openai/deepseek-r1:671b

# Windows
. .\client-configs\aider_config.ps1
aider --model openai/deepseek-r1:671b
```

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-tunnel-url/v1",
    api_key="your-key"
)

stream = client.chat.completions.create(
    model="deepseek-r1:671b",
    messages=[{"role": "user", "content": "Explain transformers"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

### curl

```bash
curl https://your-tunnel-url/api/generate \
  -H "Authorization: Bearer your-key" \
  -d '{"model":"deepseek-r1:671b","prompt":"Hello","stream":false}'
```

---

## Security

| Threat | Mitigation |
|--------|-----------|
| Unauthorized access | Bearer token auth on all `/api/*` and `/v1/*` routes |
| Brute force | Rate limiting: 60 req/min per key (configurable) |
| Man-in-the-middle | Cloudflare handles TLS — all traffic is HTTPS |
| Direct Ollama access | Ollama binds to `127.0.0.1` only — not reachable externally |
| Key leakage | One key per device — revoke by removing from `.env` |

**Never commit `.env`** — it's in `.gitignore`. Use `.env.example` as the template.

---

## Adding New Models

Any model pulled into `OLLAMA_MODELS` appears instantly on the API — no restart needed:

```powershell
$env:OLLAMA_MODELS = "D:\aipc-models"
& "C:\path\to\ollama.exe" pull llama3.3:70b
```

Then use `llama3.3:70b` as the model name in any client.

Check what's available:
```bash
curl https://your-tunnel-url/api/tags \
  -H "Authorization: Bearer your-key"
```

---

## Permanent Public URL (Optional)

By default, the quick tunnel URL changes on every restart. For a permanent URL:

1. Create a free Cloudflare account at cloudflare.com
2. Add your domain to Cloudflare (or use a free `.workers.dev` subdomain)
3. Run `.\install.ps1` and choose option `2` (Named Tunnel)
4. Your URL becomes permanent and survives restarts

---

## Troubleshooting

**Ollama won't start**
```powershell
Get-Content .\logs\ollama-err.log | Select-Object -Last 20
```

**Proxy not reachable**
```powershell
Get-Content .\logs\proxy-err.log | Select-Object -Last 20
Invoke-WebRequest http://localhost:8000/health
```

**Tunnel URL not showing**
```powershell
.\get_tunnel_url.ps1
# or
Get-Content .\logs\tunnel-err.log | Select-String "trycloudflare"
```

**Model response very slow (671B)**
This is expected if the model doesn't fit entirely in RAM. Responses come from NVMe mmap. A Gen4 NVMe gives the best experience. The 32B model runs fully in RAM and responds much faster.

**403 Forbidden**
Your API key is wrong or not set in `.env`. Check `API_KEYS` in `.env` matches what you're sending.

---

## Why Not Just Use the Cloud API?

| | Cloud API | This Setup |
|--|-----------|-----------|
| Cost | Pay per token | Free after hardware |
| Privacy | Data sent to provider | Stays on your machine |
| Speed | Fast (dedicated infra) | Depends on hardware |
| Model choice | Limited to what they offer | Any open-weight model |
| Availability | 99.9% SLA | Depends on your PC being on |
| 671B model | Very expensive | Free |

---

## License

MIT — use freely, modify freely, no warranty.

---

## Acknowledgements

- [Ollama](https://ollama.com) — local model serving
- [DeepSeek](https://deepseek.com) — open-weight R1 models
- [Qwen](https://qwenlm.github.io) — open-weight Qwen3-Coder
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps) — free secure tunneling
- [FastAPI](https://fastapi.tiangolo.com) — proxy framework
