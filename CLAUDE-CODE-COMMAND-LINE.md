# Claude Code + Local Proxy — Command-Line Quick Reference

## One-Time Setup (Optional but Recommended)

Run this once to initialize everything:

```powershell
# Windows PowerShell
.\setup-claude-code.ps1

# Linux / macOS Bash
chmod +x setup-claude-code.sh
./setup-claude-code.sh
```

This script validates dependencies, creates `.env`, and initializes API keys.

---

## Launch Claude Code from Command Line

### Method 1: Direct Script (Simplest)

**Windows:**
```powershell
.\launch-claude-code.ps1 -Local
```

**Linux/macOS:**
```bash
./launch-claude-code.sh --local
```

✅ **Recommended** — Full automated setup with logging and error handling

---

### Method 2: Batch File Wrapper (Windows Only)

```cmd
# From the repo root:
claude-code

# From anywhere (if repo is in PATH):
claude-code
```

This is a thin wrapper around `launch-claude-code.ps1`.

---

### Method 3: Global Command (Windows)

Add the repo to your PATH:

```powershell
# One-time setup
[System.Environment]::SetEnvironmentVariable(
    "PATH",
    "$env:PATH;c:\Users\swami\qwen-server",
    [System.EnvironmentVariableTarget]::User
)

# Close and reopen terminal, then:
launch-claude-code.ps1 -Local
```

---

### Method 4: Global Command (Linux/macOS)

```bash
chmod +x launch-claude-code.sh
sudo ln -s "$(pwd)/launch-claude-code.sh" /usr/local/bin/claude-code

# Then from anywhere:
claude-code --local
```

---

## Script Invocation Options

### Windows PowerShell Examples

```powershell
# Use local proxy (no internet needed)
.\launch-claude-code.ps1 -Local

# Prompt for user email/department when generating API key
.\launch-claude-code.ps1 -Local -Interactive

# Use a specific Ollama model
.\launch-claude-code.ps1 -Local -Model "deepseek-r1:32b"

# All options combined
.\launch-claude-code.ps1 -Local -Interactive -Model "claude-opus-4-6"

# Use remote tunnel (see docs for setup)
.\launch-claude-code.ps1 -Model "claude-sonnet-4-6"
```

### Linux/macOS Bash Examples

```bash
# Use local proxy (no internet needed)
./launch-claude-code.sh --local

# Prompt for user email/department when generating API key
./launch-claude-code.sh --local --interactive

# Use a specific Ollama model
./launch-claude-code.sh --local --model "deepseek-r1:32b"

# All options combined
./launch-claude-code.sh --local --interactive --model "claude-opus-4-6"

# Use remote tunnel (see docs for setup)
./launch-claude-code.sh --model "claude-sonnet-4-6"
```

---

## Environment Variables (Manual Mode)

If you want to launch Claude Code manually without the wrapper script:

```powershell
# Windows PowerShell
$env:ANTHROPIC_BASE_URL = "http://localhost:8000"
$env:ANTHROPIC_API_KEY = "sk_your-proxy-key-here"
$env:ANTHROPIC_MODEL = "claude-sonnet-4-6"

# Make sure proxy is running first (in another terminal):
# python -m uvicorn proxy:app --port 8000

# Then launch Claude Code:
claude code
```

```bash
# Linux / macOS Bash
export ANTHROPIC_BASE_URL="http://localhost:8000"
export ANTHROPIC_API_KEY="sk_your-proxy-key-here"
export ANTHROPIC_MODEL="claude-sonnet-4-6"

# Make sure proxy is running first (in another terminal):
# python -m uvicorn proxy:app --port 8000

# Then launch Claude Code:
claude code
```

---

## Pre-Launch Checklist

Before running the launch script, ensure:

- [ ] **Python 3** installed and in PATH: `python --version`
- [ ] **Node.js** installed and in PATH: `node --version`
- [ ] **Claude Code CLI** installed: `npm install -g @anthropic-ai/claude-code`
- [ ] **Ollama running** with a model: `ollama run qwen3-coder:30b` (in another terminal)
- [ ] **Proxy dependencies installed**: `pip install -r requirements.txt`

The launch script will verify most of these, but it's good to check manually.

---

## After Launch

### Claude Code CLI Basics

```
❯ claude code
Welcome to Claude Code! Type help for commands.

claude> help
Available commands:
  - Type any question or request
  - @terminal <command> — run shell commands
  - @file <path> — reference specific files
  - exit — quit Claude Code

claude> Help me debug this function
[Claude responds using local model]

claude> @terminal npm test
[Runs tests locally]

claude> @file src/app.py - add error handling
[Claude edits the file]

claude> exit
[Returns to terminal]
```

### Monitor Requests

In another terminal, tail the proxy logs:

```bash
# Windows PowerShell
Get-Content -Path logs/proxy.log -Wait

# Linux / macOS
tail -f logs/proxy.log
```

You'll see:
```
[2026-04-22 10:30:45] POST /v1/messages model=qwen3-coder:30b user=claude-code@localhost
[2026-04-22 10:30:50] ✓ 200 OK (5.2s)
```

---

## Stop the Proxy

When you're done with Claude Code:

**Windows:**
```powershell
.\stop-proxy.ps1

# Or stop both proxy and Ollama:
.\stop-proxy.ps1 -KillOllama
```

**Linux/macOS:**
```bash
./stop-proxy.sh

# Or stop both proxy and Ollama:
./stop-proxy.sh --kill-ollama
```

---

## Troubleshooting Command-Line Issues

### "command not found: launch-claude-code.ps1"

**Windows:** Make sure you're in the repo directory:
```powershell
cd c:\Users\swami\qwen-server
.\launch-claude-code.ps1 -Local
```

Or add repo to PATH permanently:
```powershell
$env:PATH = "$env:PATH;c:\Users\swami\qwen-server"
# Then close/reopen terminal
```

### "Permission denied: launch-claude-code.sh"

**Linux/macOS:** Scripts must be executable:
```bash
chmod +x launch-claude-code.sh setup-claude-code.sh
```

### Port 8000 already in use

Kill the existing process:

**Windows:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
lsof -i :8000
kill -9 <PID>
```

### Claude Code CLI not found

Install it:
```bash
npm install -g @anthropic-ai/claude-code
claude --version  # verify
```

### "No API key available"

Generate a new one:

**Windows:**
```powershell
python scripts/generate_api_key.py --email claude@localhost --department local-dev
```

**Linux/macOS:**
```bash
python3 scripts/generate_api_key.py --email claude@localhost --department local-dev
```

Copy the plaintext key from the output and manually set:

```powershell
# Windows
$env:PROXY_API_KEY = "sk_xxxxxxxx"
.\launch-claude-code.ps1 -Local
```

```bash
# Linux/macOS
export PROXY_API_KEY="sk_xxxxxxxx"
./launch-claude-code.sh --local
```

---

## Full Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE-CODE-QUICKSTART.md](./CLAUDE-CODE-QUICKSTART.md) | Detailed quick reference with examples |
| [CLAUDE-CODE-CLI-SETUP.md](./CLAUDE-CODE-CLI-SETUP.md) | Complete setup guide and architecture |
| [docs/claude-code-setup.md](./docs/claude-code-setup.md) | Technical integration details |
| [docs/configuration-reference.md](./docs/configuration-reference.md) | All configuration options |

---

## One-Liner Invocations

**Windows (from repo root):**
```powershell
& ".\launch-claude-code.ps1" -Local
```

**Linux/macOS (from repo root):**
```bash
./launch-claude-code.sh --local
```

**Windows (from anywhere, if in PATH):**
```powershell
launch-claude-code.ps1 -Local
```

**Linux/macOS (from anywhere, if symlinked):**
```bash
claude-code --local
```

---

## Summary

| Task | Command |
|------|---------|
| **First time setup** | `.\setup-claude-code.ps1` |
| **Launch Claude Code** | `.\launch-claude-code.ps1 -Local` |
| **Stop proxy** | `.\stop-proxy.ps1` |
| **View logs** | `tail -f logs/proxy.log` or `Get-Content logs/proxy.log -Wait` |
| **Generate new API key** | `python scripts/generate_api_key.py --email you@example.com --department dev` |
| **View available models** | `curl http://localhost:8000/health` |

That's all you need! Happy coding! 🚀
