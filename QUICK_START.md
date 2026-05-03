# Quick Start — Tasks & Agents Ready

Your local-llm-server is configured and running. Here's what's ready:

## ✅ Current Status

- **Proxy Server**: Running on `http://localhost:8000`
- **Ollama**: Running with `nemotron-3-super-120b-a12b` model
- **API Key**: `sk-qwen-9Ob7nJSX4vxkr4AbYlXNB0Z-FVO6MitnOZGLZwRhGps`
- **Agent Models**: Configured to use `nemotron-3-super-120b-a12b` for planner, executor, and verifier
- **Health Check**: `curl http://localhost:8000/health`

## 🚀 Using Tasks & Agents

### Method 1: Python Script (Easiest)

Run the included `task_runner.py` script:

```bash
source .venv/bin/activate
python task_runner.py "Your task description here"
```

Example:
```bash
python task_runner.py "List all Python files in this repo and count them"
```

### Method 2: Direct HTTP API

```bash
# Create a task
curl -X POST http://localhost:8000/api/tasks/create \
  -H "Authorization: Bearer sk-qwen-9Ob7nJSX4vxkr4AbYlXNB0Z-FVO6MitnOZGLZwRhGps" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Your task here",
    "agent_type": "planner"
  }'

# Check task status
curl http://localhost:8000/api/tasks/[TASK_ID] \
  -H "Authorization: Bearer sk-qwen-9Ob7nJSX4vxkr4AbYlXNB0Z-FVO6MitnOZGLZwRhGps"
```

### Method 3: Web Dashboard

Open http://localhost:8000/admin/ui/login

Username: admin
Password: (use your ADMIN_SECRET from .env if configured)

## 📋 Common Tasks

### Read files
```bash
python task_runner.py "Read the content of proxy.py and summarize it"
```

### Analyze code
```bash
python task_runner.py "Find all TODO and FIXME comments in this repository"
```

### Write files
```bash
python task_runner.py "Create a new Python file called utils.py with helper functions"
```

### Run tests
```bash
python task_runner.py "Run the test suite with pytest and report results"
```

## 🔧 Configuration

Your `.env` is pre-configured:
- **Agent Planner**: `nemotron-3-super-120b-a12b`
- **Agent Executor**: `nemotron-3-super-120b-a12b`
- **Agent Verifier**: `nemotron-3-super-120b-a12b`
- **API Port**: 8000
- **Ollama Base**: http://127.0.0.1:11434

To change models, edit `.env` and restart the proxy.

## 📡 Checking Status

```bash
# Health check
curl http://localhost:8000/health

# Available models in Ollama
curl http://localhost:8000/health | python3 -m json.tool

# Check logs
tail -f /tmp/proxy.log
```

## 🛑 Stopping Services

```bash
# Stop proxy
pkill -f "uvicorn proxy"

# Stop Ollama (if you want to)
pkill -f "ollama serve"
```

## 🚀 Next Steps

1. Try a simple task: `python task_runner.py "List all .py files"`
2. Check the logs: `tail -50 /tmp/proxy.log`
3. Visit the dashboard: http://localhost:8000/admin/ui/
4. Submit more complex tasks!

