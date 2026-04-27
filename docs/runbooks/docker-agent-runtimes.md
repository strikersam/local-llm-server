# Docker Agent Runtimes Setup

## Overview

Agent runtimes (hermes, opencode, goose, aider) now run as first-class Docker services that:
- **Auto-start** when you run `docker compose up`
- **Auto-register** in the agent store when the proxy boots
- **Auto-appear** in LLM Relay dashboard (no manual setup needed)
- **Auto-scale** — keep them running for any task that needs them

## Quick Start

```bash
# 1. Start all services (ollama + 4 runtimes + proxy + mongo)
docker compose up -d

# 2. Wait for all to be healthy (~30 seconds)
docker compose ps
# All should show "healthy" status

# 3. Open LLM Relay
open http://localhost:3000

# 4. Or use the proxy directly
curl http://localhost:8000/api/agents/
```

## Architecture

```
docker compose up
        ↓
    ┌───┴───┬───┬──────┬──────┐
    ↓       ↓   ↓      ↓      ↓
 ollama  hermes opencode goose aider
    ↓       ↓   ↓      ↓      ↓
    └───────┴───┴──────┴──────┘
           (all healthy?)
              ↓
             proxy
              ↓
      register_agent_runtimes()
              ↓
         MongoDB (store)
              ↓
       LLM Relay Dashboard
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| ollama | 11434 | LLM engine (qwen3-coder, deepseek, etc.) |
| hermes | 8002 | Fast code executor |
| opencode | 8003 | Code generator & scaffolder |
| goose | 8004 | Multi-purpose agent (code + testing + review) |
| aider | 8005 | Pair programming assistant |
| proxy | 8000 | OpenAI-compatible API + auth |
| mongo | 27017 | Agent store + task persistence |
| dashboard-frontend | 3000 | LLM Relay web UI (optional, `--profile dashboard`) |
| dashboard-backend | 8001 | LLM Relay API (optional, `--profile dashboard`) |

## What Happens on Startup

1. **Ollama starts** (takes 5–10 seconds to be ready)
2. **All 4 runtimes start** and wait for Ollama to be healthy
3. **MongoDB starts** (takes 2–3 seconds)
4. **Proxy starts** and waits for all runtimes + mongo to be healthy
5. **Proxy runs `register_agent_runtimes()`** — creates 4 AgentDefinition entries
6. **All runtimes appear in `/api/agents/`** immediately
7. **LLM Relay dashboard shows them** if you access http://localhost:3000

No manual steps. No registration scripts to run.

## Configuration

### Environment Variables

Set these in `.env` to customize the runtimes:

```bash
# Ollama configuration
OLLAMA_BASE=http://localhost:11434           # default
OLLAMA_MODELS=$HOME/.ollama/models           # local cache

# Runtimes (same for all 4)
DEFAULT_MODEL=qwen3-coder:30b                # model to use for runtime requests
REGISTER_RUNTIMES=1                          # auto-register on startup (default: 1)

# MongoDB (for agent store persistence)
MONGO_URL=mongodb://localhost:27017          # connection string
MONGO_DB=local_llm_server                    # database name
```

### Port Mapping

If the default ports conflict, override in docker-compose:

```yaml
# Override in docker-compose.override.yml (git-ignored)
services:
  hermes:
    ports:
      - "9002:8080"  # Change from 8002 to 9002
  opencode:
    ports:
      - "9003:8080"
  goose:
    ports:
      - "9004:8080"
  aider:
    ports:
      - "9005:8080"
```

## Usage

### Access from LLM Relay Dashboard

1. Open http://localhost:3000
2. Navigate to "Agents" or "Runtimes"
3. All 4 runtimes should be listed and healthy
4. Click any runtime to see:
   - Health status
   - Task types (code_generation, testing, review, etc.)
   - Available models

### Access via REST API

List all registered runtimes:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/agents/

# Response:
# {
#   "agents": [
#     {
#       "agent_id": "hermes",
#       "name": "Hermes (Executor)",
#       "runtime_id": "hermes",
#       "task_types": ["code_generation", "refactoring"],
#       ...
#     },
#     ...
#   ]
# }
```

Get a specific runtime:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/agents/hermes
```

### Use in AgentRunner

```python
from agent.loop import AgentRunner

runner = AgentRunner(ollama_base="http://localhost:8000")

result = await runner.run(
    instruction="Implement user authentication",
    requested_model="hermes",  # or opencode, goose, aider
    auto_commit=False,
    max_steps=5,
)
```

### Direct HTTP Calls to Runtime

Each runtime exposes OpenAI-compatible endpoints on ports 8002–8005:

```bash
# List models available to hermes
curl http://localhost:8002/v1/models

# Chat completion request
curl -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder:30b",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 2048
  }'

# Health check
curl http://localhost:8002/health
```

## Monitoring

### Check Service Health

```bash
# View all services
docker compose ps

# Expected output:
# NAME              STATUS
# llm-server-ollama      healthy
# llm-server-hermes      healthy
# llm-server-opencode    healthy
# llm-server-goose       healthy
# llm-server-aider       healthy
# llm-server-mongo       healthy
# llm-server-proxy       healthy
```

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f proxy
docker compose logs -f hermes

# Real-time runtime registration
docker compose logs proxy | grep -i "register"
# Should see: "✓ Registered runtime: hermes ..."
```

### Query Agent Store

```bash
# Using mongosh
mongosh mongodb://localhost:27017/local_llm_server

> db.agent_definitions.find()
# Should show 4 documents (one per runtime)

> db.agent_definitions.findOne({ agent_id: "hermes" })
# Shows hermes definition with task_types, etc.
```

## Troubleshooting

### Runtimes Not Appearing in Dashboard

1. **Check all services are healthy:**
   ```bash
   docker compose ps
   ```
   All should show "healthy". If any show "unhealthy":

2. **Check logs for registration errors:**
   ```bash
   docker compose logs proxy | grep -i "register\|error"
   ```

3. **Verify MongoDB is running:**
   ```bash
   docker compose exec mongo mongosh --eval "db.adminCommand('ping')"
   # Should return { ok: 1 }
   ```

4. **Verify proxy can reach runtimes:**
   ```bash
   docker compose exec proxy curl http://hermes:8080/health
   # Should return { "status": "ok", "runtime": "hermes", ... }
   ```

### Runtimes Crashing or Restarting

1. **Check what's failing:**
   ```bash
   docker compose logs hermes | tail -20
   ```

2. **Common causes:**
   - Ollama not healthy yet: Wait 10–20 seconds
   - Port conflicts: Change ports in docker-compose.override.yml
   - Out of memory: Increase Docker's memory limit

3. **Restart just one:**
   ```bash
   docker compose restart hermes
   ```

### Proxy Can't Connect to MongoDB

1. **Ensure mongo is healthy:**
   ```bash
   docker compose logs mongo | tail -10
   ```

2. **Test connection:**
   ```bash
   docker compose exec proxy curl mongodb://mongo:27017
   # If fails, mongo service may not be running
   ```

3. **Reset MongoDB:**
   ```bash
   docker compose down -v   # Remove volumes too
   docker compose up
   ```

## Advanced

### Disable Auto-Registration

If you want to manage runtimes manually:

```bash
# In .env or docker-compose.override.yml
REGISTER_RUNTIMES=0

docker compose up
# Runtimes start but are NOT auto-registered
# You must run the setup script manually:
python scripts/register_agent_runtimes.py
```

### Add More Runtimes

Add a new service to `docker-compose.override.yml`:

```yaml
services:
  custom-runtime:
    build:
      context: .
      dockerfile: Dockerfile.runtime
      args:
        RUNTIME_NAME: custom-runtime
    container_name: llm-server-custom
    restart: unless-stopped
    ports:
      - "8006:8080"
    environment:
      - RUNTIME_NAME=custom-runtime
      - OLLAMA_BASE=http://ollama:11434
      - DEFAULT_MODEL=qwen3-coder:30b
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    depends_on:
      ollama:
        condition: service_healthy

  proxy:
    depends_on:
      ...
      custom-runtime:
        condition: service_healthy
```

Then manually register:

```bash
python scripts/register_agent_runtimes.py
# Update the script to include custom-runtime config
```

### Use Remote Runtimes

To use runtimes hosted elsewhere (e.g., cloud):

1. Update `register_agent_runtimes.py` with remote URLs:
   ```python
   "hermes": {
       "base_url": "https://hermes.mycompany.com:8080",
       ...
   }
   ```

2. Disable local runtime containers:
   ```bash
   docker compose up -d ollama proxy mongo
   # (don't start hermes, opencode, goose, aider)
   ```

3. Register runtimes:
   ```bash
   python scripts/register_agent_runtimes.py
   ```

## Related

- [Agent Runtime Registrati](agent-runtime-setup.md)
- `docker-compose.yml` — Orchestration config
- `Dockerfile.runtime` — Runtime container definition
- `docker/agent_runtime.py` — Runtime wrapper implementation
- `agent/CLAUDE.md` — Agent security and design notes
