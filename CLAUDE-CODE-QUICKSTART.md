# Claude Code + Local Qwen Setup — Quick Start

## TL;DR Quickest Path

### Windows (PowerShell)
```powershell
# Make sure Claude Code CLI is installed first
npm install -g @anthropic-ai/claude-code

# Then just run:
.\launch-claude-code.ps1 -Local

# Or from anywhere in your PATH after running once:
claude-code
```

### Linux / macOS (Bash)
```bash
npm install -g @anthropic-ai/claude-code
chmod +x launch-claude-code.sh
./launch-claude-code.sh --local
```

---

## What This Does

This setup **redirects Claude Code** from `api.anthropic.com` to your local Ollama models:

```
Claude Code CLI
    ↓
Local proxy (localhost:8000) ← You run this
    ↓
Ollama (qwen3-coder, deepseek-r1, etc.)
    ↓
Your GPU
```

**Benefits:**
- No internet required
- No Anthropic API costs
- Full privacy — data stays local
- Works offline
- Use latest open models (Qwen 3.6, DeepSeek R1, etc.)

---

## Step 1: Prerequisites

### Install Claude Code CLI
```bash
npm install -g @anthropic-ai/claude-code

# Verify:
claude --version
```

### Start Ollama with a Model
```bash
# In another terminal, run Ollama:
ollama run qwen3-coder:30b

# Or any other model, e.g.:
# ollama run deepseek-r1:32b
# ollama run qwq:32b
```

### Verify Proxy Can Start
```bash
# In the qwen-server repo directory:
cd c:\Users\swami\qwen-server

# Check dependencies:
python -m pip install -r requirements.txt

# Test proxy startup (Ctrl+C to stop):
uvicorn proxy:app --port 8000
```

---

## Step 2: Launch Claude Code

### Windows
```powershell
.\launch-claude-code.ps1 -Local
```

**Flags:**
- `-Local` — Use `http://localhost:8000` (default if running locally)
- `-Interactive` — Prompt for email/dept when generating keys
- `-Model` — Override model name (default: `claude-sonnet-4-6`)

### Linux / macOS
```bash
./launch-claude-code.sh --local
```

**Flags:**
- `--local` — Use `http://localhost:8000`
- `--interactive` — Prompt for email/dept when generating keys
- `--model` — Override model name (default: `claude-sonnet-4-6`)

---

## Step 3: Use Claude Code Normally

Once the script launches Claude Code, you interact with it exactly as normal:

```
❯ claude
Welcome to Claude Code! Type help for commands.

claude> Help me debug this Python function
<responds using qwen3-coder:30b locally>

claude> @terminal run tests
<executes locally>
```

Everything is powered by your local Ollama models. Requests are routed automatically:

| Model  | Maps To | Use Case |
|--------|---------|----------|
| `claude-sonnet-4-6` | `qwen3-coder:30b` | General coding |
| `claude-opus-4-6` | `deepseek-r1:32b` | Reasoning/planning |
| `claude-haiku-*` | `qwen3-coder:30b` | Fast tasks |

---

## Troubleshooting

### Error: "Claude Code CLI not installed"
```bash
npm install -g @anthropic-ai/claude-code
```

### Error: "Proxy failed to start"
1. Check if port 8000 is in use:
   ```powershell
   netstat -ano | findstr :8000
   ```
   Kill the process if needed:
   ```powershell
   taskkill /PID <PID> /F
   ```

2. Check logs:
   ```
   cat logs/proxy.log
   cat logs/proxy-err.log
   ```

3. Manually start proxy to debug:
   ```powershell
   python -m uvicorn proxy:app --port 8000 --log-level debug
   ```

### Error: "No API key available"
The script auto-generates API keys in `keys.json`. If this fails:

```powershell
python scripts/generate_api_key.py --email claude@localhost --department local-dev
```

Then manually set in your session:
```powershell
$env:PROXY_API_KEY = "sk_..."  # from output above
.\launch-claude-code.ps1 -Local
```

### Error: "Ollama model not found"
Make sure Ollama is running with a model loaded:

```bash
ollama run qwen3-coder:30b
```

The proxy checks for available models on startup. Verify:
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok","models":["qwen3-coder:30b",...]}
```

### Slow first request (5-15 seconds)
This is normal — the model is being loaded into VRAM. Subsequent requests are much faster.

---

## Advanced Configuration

### Custom Model Mapping

Edit `.env` to map Claude model names to your Ollama models:

```env
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
```

Then restart Claude Code.

### Use Remote Tunnel (ngrok / Cloudflare)

If running Ollama on a machine other than your Claude Code client:

1. Expose the proxy via ngrok or Cloudflare Tunnel
2. Get the URL (e.g., `https://abc123.trycloudflare.com`)
3. Launch Claude Code without `-Local`:
   ```powershell
   $env:ANTHROPIC_BASE_URL = "https://abc123.trycloudflare.com"
   $env:ANTHROPIC_API_KEY = "<your-proxy-key>"
   claude code
   ```

### Add to PATH (Windows)

Make `claude-code` available from any terminal:

```powershell
# Option 1: Use the .bat wrapper
# Ensure c:\Users\swami\qwen-server is in your PATH environment variable

# Option 2: Copy wrapper into a PATH directory
Copy-Item .\claude-code.bat "C:\Users\swami\AppData\Local\Programs\Python\Python312\Scripts\"
```

Then just run:
```powershell
claude-code
```

---

## Next Steps

1. **Explore model routing:** Read [router/CLAUDE.md](../router/CLAUDE.md) for how models are selected
2. **Monitor requests:** Tail logs in another terminal:
   ```bash
   tail -f logs/proxy.log
   ```
3. **Add more models:** Pull via Ollama and update `.env` `MODEL_MAP`
4. **Integrate with CI/CD:** See [docs/](docs/) for multi-agent runs

---

## Full Documentation

- Architecture: [docs/architecture/overview.md](../docs/architecture/overview.md)
- API Reference: [docs/configuration-reference.md](../docs/configuration-reference.md)
- Anthropic Compatibility: See `handlers/anthropic_compat.py`
