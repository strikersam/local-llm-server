# Claude Code + Local Models Setup — Complete

## ✅ What's Been Set Up

You now have a complete, production-ready workflow to use **Claude Code CLI** with your local Ollama models. No cloud API, no costs, full privacy.

---

## 📁 Files Created

### Launch Scripts

| File | Platform | Purpose |
|------|----------|---------|
| **launch-claude-code.ps1** | Windows | Main launch script with auto-setup |
| **launch-claude-code.sh** | Linux/macOS | Main launch script with auto-setup |
| **claude-code.bat** | Windows | Quick wrapper batch file |
| **stop-proxy.ps1** | Windows | Stop proxy and optionally Ollama |
| **stop-proxy.sh** | Linux/macOS | Stop proxy and optionally Ollama |
| **setup-claude-code.ps1** | Windows | One-time environment validation |
| **setup-claude-code.sh** | Linux/macOS | One-time environment validation |

### Documentation

| File | Content |
|------|---------|
| **[CLAUDE-CODE-COMMAND-LINE.md](./CLAUDE-CODE-COMMAND-LINE.md)** ⭐ | **START HERE** — Command-line quick reference |
| **[CLAUDE-CODE-QUICKSTART.md](./CLAUDE-CODE-QUICKSTART.md)** | Detailed setup, examples, troubleshooting |
| **[CLAUDE-CODE-CLI-SETUP.md](./CLAUDE-CODE-CLI-SETUP.md)** | Complete guide with architecture overview |

---

## 🚀 Quick Start (3 Steps)

### Step 1: One-Time Setup (Optional but Recommended)

**Windows:**
```powershell
.\setup-claude-code.ps1
```

**Linux/macOS:**
```bash
chmod +x setup-claude-code.sh
./setup-claude-code.sh
```

This validates your environment, installs dependencies, and initializes API keys.

### Step 2: Start Ollama (in one terminal)

```bash
ollama run qwen3-coder:30b
```

### Step 3: Launch Claude Code (in another terminal)

**Windows:**
```powershell
.\launch-claude-code.ps1 -Local
```

**Linux/macOS:**
```bash
./launch-claude-code.sh --local
```

✅ **Done!** Claude Code is now connected to your local models.

---

## 📖 Documentation Map

### For Quick Command-Line Invocation
👉 Read: **[CLAUDE-CODE-COMMAND-LINE.md](./CLAUDE-CODE-COMMAND-LINE.md)**

This file shows:
- How to invoke from command line
- All available options and flags
- Environment variable setup
- Troubleshooting quick fixes

### For Complete Setup Details
👉 Read: **[CLAUDE-CODE-QUICKSTART.md](./CLAUDE-CODE-QUICKSTART.md)**

This file covers:
- Prerequisites
- Step-by-step setup
- Model mapping
- Detailed troubleshooting
- Advanced configuration

### For Architecture & Implementation
👉 Read: **[CLAUDE-CODE-CLI-SETUP.md](./CLAUDE-CODE-CLI-SETUP.md)**

This file explains:
- How everything works
- Architecture diagram
- Configuration reference
- Privacy & security model
- Next steps

### Original Documentation
👉 Read: **[docs/claude-code-setup.md](./docs/claude-code-setup.md)**

The original technical guide (still valid for deeper details).

---

## 🎯 Common Command-Line Use Cases

### Launch Claude Code (Simplest)

```powershell
# Windows
.\launch-claude-code.ps1 -Local

# Linux/macOS
./launch-claude-code.sh --local
```

### Launch with Specific Model

```powershell
# Windows — use DeepSeek-R1 for reasoning
.\launch-claude-code.ps1 -Local -Model "deepseek-r1:32b"

# Linux/macOS
./launch-claude-code.sh --local --model "deepseek-r1:32b"
```

### Launch with Interactive Key Setup

```powershell
# Windows
.\launch-claude-code.ps1 -Local -Interactive

# Linux/macOS
./launch-claude-code.sh --local --interactive
```

### Stop Everything When Done

```powershell
# Windows
.\stop-proxy.ps1              # Stop proxy only
.\stop-proxy.ps1 -KillOllama  # Stop proxy and Ollama

# Linux/macOS
./stop-proxy.sh               # Stop proxy only
./stop-proxy.sh --kill-ollama # Stop proxy and Ollama
```

### View Proxy Logs in Real-Time

```powershell
# Windows
Get-Content logs/proxy.log -Wait

# Linux/macOS
tail -f logs/proxy.log
```

---

## 🔧 Configuration

### Default Setup

The setup scripts create a `.env` file with sensible defaults:

```env
KEYS_FILE=keys.json
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
CORS_ENABLED=true

OLLAMA_BASE_URL=http://localhost:11434

MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
```

### Customize Model Mapping

Edit `.env` to route Claude model names to different Ollama models:

```env
# Route all Claude models to your preferred model
MODEL_MAP=*:qwen3-coder:30b

# Or route different Claude models to different Ollama models
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,claude-haiku-4-5:qwen3-coder:8b
```

Then restart Claude Code.

---

## ✅ Prerequisites (Auto-Checked)

The setup scripts verify:

- ✓ **Python 3** installed
- ✓ **Node.js** installed
- ✓ **Claude Code CLI** installed (installs if missing)
- ✓ **Proxy dependencies** in `requirements.txt`
- ✓ **.env** configuration file
- ✓ **API keys** (generates first one if needed)

---

## 🏗️ Architecture Overview

```
Your Terminal / IDE
    ↓
    ├─ launch-claude-code.ps1 (orchestrates everything)
    ├─ Generates API key (if first run)
    ├─ Starts proxy on localhost:8000
    └─ Launches: claude code
    ↓
Claude Code CLI
    ↓ (asks for code generation)
    ↓
localhost:8000/v1/messages (FastAPI proxy)
    ├─ Validates API key
    ├─ Maps model name (claude-sonnet-4-6 → qwen3-coder:30b)
    ├─ Rate limits, logs, CORS
    └─ Translates Anthropic → OpenAI protocol
    ↓
localhost:11434/api/generate (Ollama)
    ├─ Loads model (first request: ~30 seconds)
    ├─ Runs inference (your GPU)
    └─ Streams response back
    ↓
Claude Code receives response as if from Anthropic API
    ↓
You see generated code/output in claude > prompt
```

**Key point:** It looks and feels like the cloud API, but it's all running locally.

---

## 📋 File Locations Reference

```
qwen-server/
├── launch-claude-code.ps1          ← Main script (Windows)
├── launch-claude-code.sh           ← Main script (Linux/macOS)
├── claude-code.bat                 ← Quick wrapper (Windows)
├── stop-proxy.ps1                  ← Stop proxy (Windows)
├── stop-proxy.sh                   ← Stop proxy (Linux/macOS)
├── setup-claude-code.ps1           ← Setup validation (Windows)
├── setup-claude-code.sh            ← Setup validation (Linux/macOS)
├── CLAUDE-CODE-COMMAND-LINE.md     ← Quick reference ⭐ START HERE
├── CLAUDE-CODE-QUICKSTART.md       ← Detailed guide
├── CLAUDE-CODE-CLI-SETUP.md        ← Complete setup
├── .env                            ← Configuration (created by setup)
├── keys.json                       ← API key storage (created by setup)
├── logs/
│   ├── proxy.log                   ← Proxy request logs
│   └── proxy-err.log               ← Proxy error logs
├── proxy.py                        ← FastAPI proxy server
├── requirements.txt                ← Python dependencies
├── docs/
│   ├── claude-code-setup.md        ← Original technical guide
│   ├── configuration-reference.md  ← All config options
│   ├── architecture/
│   │   └── overview.md             ← How proxy works
│   └── ...
└── scripts/
    └── generate_api_key.py         ← Generate new API keys
```

---

## 🎓 Learning Path

### Beginner: Just Want to Use It
1. Run `.\setup-claude-code.ps1`
2. Run `.\launch-claude-code.ps1 -Local`
3. Use Claude Code normally!

### Intermediate: Understanding How It Works
1. Skim [CLAUDE-CODE-COMMAND-LINE.md](./CLAUDE-CODE-COMMAND-LINE.md)
2. Read architecture section in [CLAUDE-CODE-CLI-SETUP.md](./CLAUDE-CODE-CLI-SETUP.md)
3. Look at `.env` file and understand MODEL_MAP

### Advanced: Customizing & Extending
1. Read [docs/architecture/overview.md](./docs/architecture/overview.md)
2. Read [router/CLAUDE.md](./router/CLAUDE.md) for routing logic
3. Edit `.env` to customize model mapping
4. Implement custom prompts or model selection logic

---

## 🚨 Troubleshooting Index

| Problem | Solution |
|---------|----------|
| "Claude Code CLI not installed" | `npm install -g @anthropic-ai/claude-code` |
| "Port 8000 in use" | Run `.\stop-proxy.ps1` or kill the process manually |
| "Proxy failed to start" | Check `logs/proxy.log` for details |
| "Model not found" | Run `ollama run qwen3-coder:30b` in another terminal |
| "First request slow (5-15s)" | Normal — model is loading into VRAM |
| "API key authentication failed" | Run `python scripts/generate_api_key.py --email you@example.com --department dev` |

For more help, see:
- **[CLAUDE-CODE-QUICKSTART.md#troubleshooting](./CLAUDE-CODE-QUICKSTART.md#troubleshooting)**
- **[CLAUDE-CODE-COMMAND-LINE.md#troubleshooting](./CLAUDE-CODE-COMMAND-LINE.md#troubleshooting-command-line-issues)**

---

## 📞 Next Steps

1. **Run setup:** `.\setup-claude-code.ps1` (one-time)
2. **Start Ollama:** `ollama run qwen3-coder:30b` (in one terminal)
3. **Launch Claude Code:** `.\launch-claude-code.ps1 -Local` (in another terminal)
4. **Start using:** `claude> help` and explore!

---

## 📚 Complete Documentation

All scripts and guides reference:
- `docs/claude-code-setup.md` — Technical setup
- `docs/configuration-reference.md` — Config options
- `docs/architecture/overview.md` — How it works
- `CLAUDE.md` — Operating guide
- `README.md` — Project overview

---

## 🎉 You're All Set!

Everything is ready. Pick a starting point below:

- **[CLAUDE-CODE-COMMAND-LINE.md](./CLAUDE-CODE-COMMAND-LINE.md)** ← Start here for command-line reference
- **[CLAUDE-CODE-QUICKSTART.md](./CLAUDE-CODE-QUICKSTART.md)** ← Detailed quick start
- **[CLAUDE-CODE-CLI-SETUP.md](./CLAUDE-CODE-CLI-SETUP.md)** ← Complete setup guide

Then run:
```powershell
# Windows
.\setup-claude-code.ps1
.\launch-claude-code.ps1 -Local
```

```bash
# Linux/macOS
./setup-claude-code.sh
./launch-claude-code.sh --local
```

Enjoy coding with Claude locally! 🚀
