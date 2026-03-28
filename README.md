# Local LLM Remote Access Server

Run powerful open-source AI models on your home PC and access them securely from **any device, anywhere in the world** — using the same API interface as OpenAI.

No cloud costs. No data sent to third parties. Full control over your models.

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

| Model | Size | Quant | Parameters | Best For |
|-------|------|-------|-----------|----------|
| `deepseek-r1:671b` | 404 GB | Q4_K_M | 671B | Complex reasoning, math, research — matches o1 quality |
| `deepseek-r1:32b` | 18.5 GB | Q4_K_M | 32.8B | Fast reasoning and coding, fits fully in RAM |
| `qwen3-coder:30b` | 17.3 GB | Q4_K_M | 30.5B | Code generation, completion, review, tab autocomplete |

> **Note on 671B:** Requires ~404 GB storage and ideally 236+ GB RAM to run fully in memory. With less RAM, Ollama uses memory-mapped I/O (mmap) from the NVMe SSD — responses in 30–90s on a Gen4 NVMe. The 32B distill from the same training run gives ~85% quality at 5% the size.

All models expose identical API endpoints — switch between them by changing the `model` field in your request.

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
# Your secret auth token (generate one — see .env.example for instructions)
API_KEYS=your-secret-key-here

# Where to store model weights (needs lots of free space)
# Windows: D:\ai-models   Linux: /mnt/data/ollama-models   macOS: /Volumes/Data/models
OLLAMA_MODELS=/path/to/your/model/storage
```

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
    ├── continue_config.json  # VS Code Continue extension
    ├── cursor_settings.json  # Cursor IDE
    ├── aider_config.sh       # Aider CLI (Linux/macOS/WSL)
    ├── aider_config.ps1      # Aider CLI (Windows)
    └── python_client_example.py
```

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

---

## Client Setup

### Cursor IDE

`Settings (Ctrl+,) → Models → OpenAI API Key section`:

| Field | Value |
|-------|-------|
| API Key | Your key from `.env` |
| Override Base URL | `https://your-tunnel-url/v1` |

Type model names to add: `deepseek-r1:671b`, `deepseek-r1:32b`, `qwen3-coder:30b`

### VS Code — Continue Extension

Copy `client-configs/continue_config.json` to `~/.continue/config.json`.
Replace `YOUR_TUNNEL_URL` and `YOUR_API_KEY`.

Models appear in the Continue sidebar dropdown automatically.

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

| RAM | Recommended Models |
|-----|--------------------|
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
