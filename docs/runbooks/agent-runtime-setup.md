# Agent Runtime Setup

## Overview

Agent runtimes are external LLM-powered agents (hermes, opencode, goose, aider) that can be used by the local-llm-server's agent system to execute tasks. This guide covers registering these runtimes in the agent store.

## Supported Runtimes

| Runtime | Role | Task Types | Model |
|---------|------|-----------|-------|
| **hermes** | Fast executor | code_generation, refactoring | hermes:latest |
| **opencode** | Code generator | code_generation, scaffolding | opencode:latest |
| **goose** | Multi-purpose | code_generation, testing, review | goose:latest |
| **aider** | Pair programmer | code_generation, refactoring, debugging | aider:latest |

## Initial Setup

### 1. Register Runtimes

Run the registration script to populate the agent store:

```bash
source .venv/bin/activate
python scripts/register_agent_runtimes.py
```

This creates `AgentDefinition` entries in MongoDB (or in-memory store) for each runtime.

### 2. Verify Installation

```bash
# Check registered agents
python scripts/register_agent_runtimes.py

# Should output:
# ✓ Registered: hermes           → Hermes (Executor)
# ✓ Registered: opencode         → OpenCode (Generator)
# ✓ Registered: goose            → Goose (Multi-Purpose)
# ✓ Registered: aider            → Aider (Pair Programmer)
```

### 3. Access Agents via API

Once registered, agents are accessible via the REST API:

```bash
# List all runtimes
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/agents/

# Get a specific runtime
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/agents/hermes
```

## Using Runtimes in AgentRunner

When an `AgentDefinition` has a `runtime_id` set, the agent loop can select that runtime for execution:

```python
from agent.loop import AgentRunner

runner = AgentRunner(ollama_base="http://localhost:8000")

result = await runner.run(
    instruction="Implement user authentication",
    requested_model="hermes",  # or hermes/opencode/goose/aider
    auto_commit=False,
    max_steps=5,
)
```

## Re-registering Runtimes

To clear and re-register all runtimes:

```bash
python scripts/register_agent_runtimes.py --reset
```

This deletes existing runtime agents and creates fresh ones.

## MongoDB Connection

By default, the script connects to `mongodb://localhost:27017/local_llm_server`.

Override with environment variables:

```bash
python scripts/register_agent_runtimes.py \
  --mongo-url "mongodb://user:pass@remote:27017" \
  --db-name "custom_db"
```

If MongoDB is unavailable, agents are stored in memory (lost on restart).

## Troubleshooting

### No agents showing after registration

1. **Verify MongoDB is running:**
   ```bash
   mongosh mongodb://localhost:27017
   > use local_llm_server
   > db.agent_definitions.find()
   ```

2. **Check permissions on the DB user:**
   ```bash
   # User must have read/write on local_llm_server database
   ```

3. **Fall back to in-memory store:**
   If MongoDB is down, agents are stored in memory. Restart the script when MongoDB is available.

### Agents not appearing in API responses

1. **Check authentication token is valid** (Bearer token in Authorization header)
2. **Verify user role allows agent access** (all roles can see public/workspace agents)
3. **Query MongoDB directly:**
   ```bash
   mongosh mongodb://localhost:27017/local_llm_server
   > db.agent_definitions.countDocuments()  # should be ≥ 4
   ```

## Related

- `agents/store.py` — Agent store CRUD
- `agents/api.py` — REST API routes
- `agent/loop.py` — AgentRunner execution loop
- `agent/CLAUDE.md` — Agent security and design notes
