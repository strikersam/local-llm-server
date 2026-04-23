# Claude Code with Local Models — Complete Setup Guide

This repository now includes complete integration for **Claude Code CLI** to use your local Ollama models through the qwen-server proxy instead of the cloud Anthropic API.

## What You Get

- 🎯 **Claude Code** runs locally with no internet or API costs
- 🚀 **Instant setup** with one command
- 📍 **Model flexibility** — swap between Qwen, DeepSeek, Qwq, or any Ollama model
- 🔐 **Privacy** — all data stays on your machine
- ⚡ **Fast** — after initial model load, responses are quick

---

## Quick Start (30 seconds)

### Windows (PowerShell)

```powershell
# First time only: Initialize everything
.\setup-claude-code.ps1

# Then launch Claude Code:
.\launch-claude-code.ps1 -Local

# That's it!
```

### Linux / macOS (Bash)

```bash
# First time only: Initialize everything
chmod +x setup-claude-code.sh launch-claude-code.sh
./setup-claude-code.sh

# Then launch Claude Code:
./launch-claude-code.sh --local

# That's it!
```

---

## Command-Line Invocation Guide

### Option 1: Direct Script Launch (Recommended)

From the repo root:

**Windows:**
```powershell
.\launch-claude-code.ps1 -Local
```

**Linux/macOS:**
```bash
./launch-claude-code.sh --local
```

### Option 2: Using the Wrapper Batch File (Windows Only)

```cmd
claude-code
```

First-time setup:
```cmd
set PATH=%PATH%;c:\Users\swami\qwen-server
claude-code
```

### Option 3: From Anywhere (Add to PATH)

**Windows PowerShell:**
```powershell
# Add repo to PATH permanently
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "$env:PATH;c:\Users\swami\qwen-server",
    [System.EnvironmentVariableTarget]::User
)

# Close and reopen terminal, then:
launch-claude-code.ps1 -Local
```

**Linux/macOS (Bash):**
```bash
chmod +x setup-claude-code.sh launch-claude-code.sh
sudo ln -s "$(pwd)/launch-claude-code.sh" /usr/local/bin/claude-code

# Then from anywhere:
claude-code --local
```

---

## Setup Steps Explained

### 1. Run One-Time Setup

**Windows:**
```powershell
.\setup-claude-code.ps1
```

**Linux/macOS:**
```bash
./setup-claude-code.sh
```

This script:
- ✓ Validates Python 3 and Node.js are installed
- ✓ Installs Claude Code CLI if missing
- ✓ Creates `.env` configuration
- ✓ Installs proxy dependencies (`pip install -r requirements.txt`)
- ✓ Initializes empty `keys.json` for API keys

### 2. Start Ollama with a Model

In one terminal, run Ollama with your chosen model:

```bash
ollama run qwen3-coder:30b
# or
ollama run deepseek-r1:32b
# or
ollama run qwq:32b
```

The proxy will auto-detect available models.

### 3. Launch Claude Code

**Windows:**
```powershell
.\launch-claude-code.ps1 -Local
```

**Linux/macOS:**
```bash
./launch-claude-code.sh --local
```

The script will:
- ✓ Generate an API key (first run only)
- ✓ Start the proxy on `localhost:8000`
- ✓ Wait for Ollama to be ready
- ✓ Launch Claude Code CLI with correct environment variables
- ✓ Log requests to `logs/proxy.log`

### 4. Use Claude Code Normally

```
❯ claude code

Welcome to Claude Code!

claude> Help me write a Python function for webscraping
<responds using qwen3-coder:30b locally>

claude> @terminal npm test
<executes locally>

claude> exit
```

All code generation, planning, and terminal commands use your local models.

---

## Script Options

### launch-claude-code.ps1 (Windows)

```powershell
# Basic usage:
.\launch-claude-code.ps1

# Use localhost instead of tunnel:
.\launch-claude-code.ps1 -Local

# Prompt for email/department when generating keys:
.\launch-claude-code.ps1 -Local -Interactive

# Use a specific model:
.\launch-claude-code.ps1 -Local -Model "claude-opus-4-6"

# Combine options:
.\launch-claude-code.ps1 -Local -Interactive -Model "claude-opus-4-6"
```

### launch-claude-code.sh (Linux/macOS)

```bash
# Basic usage:
./launch-claude-code.sh

# Use localhost instead of tunnel:
./launch-claude-code.sh --local

# Prompt for email/department when generating keys:
./launch-claude-code.sh --local --interactive

# Use a specific model:
./launch-claude-code.sh --local --model "claude-opus-4-6"

# Combine options:
./launch-claude-code.sh --local --interactive --model "claude-opus-4-6"
```

---

## Stopping the Proxy

### Windows

```powershell
.\stop-proxy.ps1

# Or with Ollama:
.\stop-proxy.ps1 -KillOllama
```

### Linux/macOS

```bash
./stop-proxy.sh

# Or with Ollama:
./stop-proxy.sh --kill-ollama
```

---

## Configuration

### Default .env

The setup creates a `.env` file with sensible defaults:

```env
KEYS_FILE=keys.json
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
CORS_ENABLED=true

OLLAMA_BASE_URL=http://localhost:11434

# Maps Claude model names to Ollama models
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
```

### Custom Model Mapping

Edit `.env` to change which Ollama models Claude Code models map to:

```env
# Route all Claude models to qwen3-coder
MODEL_MAP=*:qwen3-coder:30b

# Custom multi-model routing
MODEL_MAP=\
  claude-sonnet-4-6:qwen3-coder:30b,\
  claude-opus-4-6:deepseek-r1:32b,\
  claude-haiku-4-5:qwen3-coder:8b,\
  *:qwen3-coder:30b
```

After editing, restart Claude Code to pick up changes.

---

## Troubleshooting

### "Claude Code CLI not installed"

```bash
npm install -g @anthropic-ai/claude-code
```

### "Port 8000 already in use"

```powershell
# Windows: Find and kill the process
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -i :8000
kill -9 <PID>
```

### "Proxy failed to start"

Check logs:
```bash
tail -f logs/proxy.log
tail -f logs/proxy-err.log
```

Or start manually with debug output:
```bash
python -m uvicorn proxy:app --port 8000 --log-level debug
```

### "Model not found"

Make sure Ollama is running and the model is pulled:

```bash
ollama ps        # See running models
ollama list      # See all pulled models
ollama run qwen3-coder:30b  # Pull and run a model
```

Verify the proxy sees available models:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok","models":["qwen3-coder:30b",...]}
```

### "First request is slow (5-15 seconds)"

This is normal — Ollama is loading the model into VRAM. Subsequent requests are much faster.

### "API key authentication failed"

The first run generates a key and stores it in `keys.json`. If you need a new key:

```bash
python scripts/generate_api_key.py --email your@email.com --department your-dept
```

Then manually set in your session (Windows):
```powershell
$env:PROXY_API_KEY = "sk_xxxxxxxx"
.\launch-claude-code.ps1 -Local
```

Or Linux/macOS:
```bash
export PROXY_API_KEY="sk_xxxxxxxx"
./launch-claude-code.sh --local
```

---

## Architecture Overview

```
Your Terminal
    ↓
    └─ launch-claude-code.ps1 / .sh
        ├─ Start proxy on localhost:8000
        ├─ Generate/retrieve API key
        └─ Launch 'claude code' with:
            • ANTHROPIC_BASE_URL=http://localhost:8000
            • ANTHROPIC_API_KEY=sk_xxxxx
            • ANTHROPIC_MODEL=claude-sonnet-4-6
    ↓
Claude Code CLI
    ↓ (sends Anthropic API requests)
    ↓
http://localhost:8000/v1/messages (FastAPI proxy)
    ├─ Translates Anthropic → OpenAI format
    ├─ Validates API key from keys.json
    ├─ Routes model name via MODEL_MAP
    └─ Rate limiting, logging, CORS
    ↓ (sends OpenAI-compatible requests)
    ↓
http://localhost:11434/api/generate (Ollama)
    ├─ Loads model into VRAM (first time ~30s)
    ├─ Runs inference with your GPU
    └─ Streams response back
    ↓ (response bubbles back up through layers)
    ↓
Claude Code CLI sees normal Anthropic response
    ↓
You see inference output in claude > prompt
```

---

## Full Documentation

- **[CLAUDE-CODE-QUICKSTART.md](./CLAUDE-CODE-QUICKSTART.md)** — Detailed quick reference
- **[docs/claude-code-setup.md](./docs/claude-code-setup.md)** — Complete technical setup guide
- **[docs/architecture/overview.md](./docs/architecture/overview.md)** — How the proxy works
- **[docs/configuration-reference.md](./docs/configuration-reference.md)** — All config options
- **[router/CLAUDE.md](./router/CLAUDE.md)** — Model routing internals

---

## Next Steps After Setup

1. **Test a quick query:**
   ```
   claude > What are the top 5 Python web frameworks?
   ```

2. **Try file editing:**
   ```
   claude> Edit my_script.py - add type hints
   ```

3. **Use terminal integration:**
   ```
   claude> @terminal npm test
   ```

4. **Monitor requests:**
   ```bash
   tail -f logs/proxy.log
   ```

5. **Enable observability (optional):**
   - Set `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY` in `.env`
   - All requests will be traced in Langfuse dashboard

---

## Support

- Report issues or ask questions in the repo's GitHub issues
- Check [docs/](./docs/) for architectural details
- Search existing issues for common problems

---

## Privacy & Security

- ✓ All requests stay on your machine (localhost)
- ✓ API keys are hashed in storage
- ✓ No telemetry sent to Anthropic
- ✓ No data leaves your network
- ✓ Source code is open and auditable

Enjoy coding with Claude locally! 🚀
