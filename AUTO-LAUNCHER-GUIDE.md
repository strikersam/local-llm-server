# Cross-Platform Auto-Detecting Launcher

I've created **auto-detecting launchers** that work on Windows, Linux, and macOS. No manual OS detection needed!

---

## 🚀 Simplest Way to Launch

### Windows (PowerShell or CMD)
```cmd
# Simplest - auto-detects and launches
run.bat

# Or with options:
python run-claude-code.py --local
python run-claude-code.py --setup
python run-claude-code.py --status
```

### Linux / macOS (Bash)
```bash
# Simplest - auto-detects and launches
./run.sh

# Or with options:
python3 run-claude-code.py --local
python3 run-claude-code.py --setup
python3 run-claude-code.py --status
```

---

## 📋 Available Commands

### Launch Claude Code (Auto-Detects OS & Scripts)
```bash
# Windows
run.bat
python run-claude-code.py

# Linux / macOS
./run.sh
python3 run-claude-code.py
```

### One-Time Setup
```bash
# Windows
python run-claude-code.py --setup

# Linux / macOS
python3 run-claude-code.py --setup
```

### Launch with Options
```bash
# Windows
python run-claude-code.py --local                    # Use localhost
python run-claude-code.py --interactive              # Prompt for setup
python run-claude-code.py --model deepseek-r1:32b   # Use specific model

# Linux / macOS (same commands)
python3 run-claude-code.py --local
python3 run-claude-code.py --interactive
python3 run-claude-code.py --model deepseek-r1:32b
```

### Stop Proxy
```bash
# Windows
python run-claude-code.py --stop            # Stop proxy only
python run-claude-code.py --stop --kill-ollama  # Stop both

# Linux / macOS (same commands)
python3 run-claude-code.py --stop
python3 run-claude-code.py --stop --kill-ollama
```

### Show System Info
```bash
# Windows
python run-claude-code.py --status

# Linux / macOS
python3 run-claude-code.py --status
```

---

## 🎯 Quick Start: Just Use This!

### Windows (Any Terminal - PowerShell, CMD, Git Bash)
```cmd
cd c:\Users\swami\qwen-server
run.bat
```

That's it! The script will:
1. ✅ Auto-detect Windows
2. ✅ Auto-select PowerShell
3. ✅ Validate setup
4. ✅ Start proxy
5. ✅ Launch Claude Code

### Linux / macOS
```bash
cd ~/path/to/qwen-server
chmod +x run.sh
./run.sh
```

That's it! The script will:
1. ✅ Auto-detect Linux/macOS
2. ✅ Auto-select Bash
3. ✅ Validate setup
4. ✅ Start proxy
5. ✅ Launch Claude Code

---

## 📊 What Gets Auto-Detected

The `run-claude-code.py` script automatically detects:

| Detection | Values |
|-----------|--------|
| **OS** | Windows, Linux, macOS |
| **Shell** | PowerShell (Windows), Bash (Unix) |
| **Python** | 3.8+ |
| **Available Scripts** | Checks for .ps1 / .sh files |

---

## 💡 How It Works

```
Your Terminal
    ↓ run.bat (Windows) or ./run.sh (Linux/macOS)
    ↓
Python OS Detection (run-claude-code.py)
    ├─ platform.system() → Detects Windows/Linux/macOS
    ├─ Selects PowerShell (Windows) or Bash (Unix)
    └─ Validates interpreter availability
    ↓
Auto-Select Correct Script
    ├─ Windows: launch-claude-code.ps1
    └─ Linux/macOS: launch-claude-code.sh
    ↓
Execute with Error Handling
    └─ Reports clear errors if anything fails
    ↓
Claude Code Launches
```

---

## 🔧 Full Command Reference

```bash
# Basic usage (all platforms)
python run-claude-code.py                      # Launch with defaults
python run-claude-code.py --local              # Use local proxy
python run-claude-code.py --setup              # Setup only
python run-claude-code.py --stop               # Stop proxy

# Advanced options
python run-claude-code.py --local --interactive        # Interactive setup
python run-claude-code.py --model claude-opus-4-6     # Use specific model
python run-claude-code.py --stop --kill-ollama        # Stop proxy & Ollama
python run-claude-code.py --status                    # Show system info

# With custom models
python run-claude-code.py --model "qwen3-coder:30b"
python run-claude-code.py --model "deepseek-r1:32b"
python run-claude-code.py --model "qwq:32b"
```

---

## ✅ Pre-Flight Checklist

The launcher checks:
- ✓ Python 3 installed
- ✓ PowerShell (Windows) or Bash (Unix) available
- ✓ Script files exist
- ✓ File permissions (Unix)

If any check fails, you'll get a clear error message.

---

## 📁 Files

| File | Purpose |
|------|---------|
| **run-claude-code.py** | Main cross-platform launcher (Python) |
| **run.bat** | Windows quick-launch wrapper |
| **run.sh** | Linux/macOS quick-launch wrapper |

---

## 🎉 That's It!

**Windows:**
```cmd
run.bat
```

**Linux/macOS:**
```bash
./run.sh
```

No configuration needed. No manual OS selection. Just run and go! 🚀

---

## Troubleshooting Auto-Launcher

### Error: "Python not found"
Install Python 3:
- **Windows:** https://www.python.org/downloads/
- **Linux:** `apt-get install python3` (Debian/Ubuntu) or `brew install python3` (macOS)

### Error: "PowerShell not found" (Windows)
PowerShell comes with Windows 10+. If missing, the launcher falls back to `cmd.exe`.

### Error: "Bash not found" (Linux/macOS)
Bash is standard on Unix. Install if missing: `apt-get install bash`

### Permission denied (Linux/macOS)
Make script executable:
```bash
chmod +x run.sh
```

### Still having issues?
Run with status to see what's detected:
```bash
python3 run-claude-code.py --status
# Shows: OS, Python, Interpreter, system info
```

---

## Advanced: Make It Global (Optional)

### Windows - Add to PATH
```powershell
# Add repo directory to PATH
$repoPath = "c:\Users\swami\qwen-server"
[Environment]::SetEnvironmentVariable(
    "PATH",
    "$env:PATH;$repoPath",
    [EnvironmentVariableTarget]::User
)

# Then restart terminal and just use:
run.bat
```

### Linux/macOS - Create Symlink
```bash
chmod +x run.sh
sudo ln -s "$(pwd)/run.sh" /usr/local/bin/run-claude

# Then from anywhere:
run-claude
```

---

## Summary

**Before:** Manual OS detection, platform-specific commands
```
Windows:  .\launch-claude-code.ps1 -Local
Linux:    ./launch-claude-code.sh --local
```

**After:** One universal command
```
Windows:  run.bat
Linux:    ./run.sh
Both:     python run-claude-code.py
```

Much simpler! ✨
