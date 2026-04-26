# Agent Runtime Configurations for Render Deployment

## Local Runtime Services (from docker-compose.yml)

The local stack runs **4 agent runtime containers** plus an **internal agent**:

| Runtime | Port | Default Model | Tier | Capabilities |
|---------|------|---------------|------|--------------|
| **hermes** | 8002 | qwen3-coder:30b | FIRST_CLASS | code_gen, code_review, repo_edit, git_ops, file_rw, tool_use, agent_delegation, scheduled_tasks, memory_sessions, mcp, stream, autonomous_loop, shell_exec, web_browse |
| **opencode** | 8003 | qwen3-coder:30b | FIRST_CLASS | code_gen, code_review, repo_edit, git_ops, file_rw, tool_use, stream, multi_file_edit, shell_exec |
| **goose** | 8004 | qwen3-coder:14b | TIER_2 | code_gen, code_review, file_rw, tool_use, shell_exec, stream |
| **aider** | 8005 | ollama/qwen3-coder:14b | TIER_3 | code_gen, repo_edit, git_ops, file_rw, multi_file_edit |
| **internal_agent** | in-process | — | TIER_2 | code_gen, code_review, repo_edit, file_rw, tool_use, shell_exec, autonomous_loop |
| **openhands** | 3000 (external) | — | EXPERIMENTAL | code_gen, code_review, repo_edit, git_ops, file_rw, tool_use, shell_exec, web_browse, multi_file_edit, autonomous_loop |

---

## Environment Variables to Add to Render

Add these to `render.yaml` or set in the Render dashboard:

```yaml
# Runtime base URLs (point to wherever you host the runtime services)
- key: HERMES_BASE_URL
  sync: false
- key: OPENCODE_BASE_URL
  sync: false
- key: GOOSE_BASE_URL
  sync: false
- key: AIDER_BASE_URL
  sync: false
- key: OPENHANDS_BASE_URL
  sync: false

# Runtime policy / behaviour
- key: RUNTIME_NEVER_PAID
  value: "true"
- key: RUNTIME_MAX_PAID_ESCALATIONS
  value: "0"
- key: RUNTIME_DEFAULT
  value: "hermes"
- key: RUNTIME_CODE_GENERATION
  value: "opencode"
- key: RUNTIME_CODE_REVIEW
  value: "opencode"
- key: RUNTIME_REPO_EDITING
  value: "opencode"
- key: RUNTIME_GIT_OPS
  value: "aider"
- key: RUNTIME_HEALTH_POLL_SEC
  value: "30"

# OpenHands (experimental, opt-in)
- key: OPENHANDS_ENABLED
  value: "false"

# Internal agent Ollama endpoint (if using internal agent on Render)
- key: OLLAMA_BASE
  value: ""  # Set if you have an external Ollama instance
```

---

## Runtime Adapter-Specific Env Vars

| Adapter | Env Var | Default | Description |
|---------|---------|---------|-------------|
| Hermes | `HERMES_BASE_URL` | `http://localhost:8100` | Hermes server URL |
| Hermes | `HERMES_API_KEY` | `""` | Optional API key |
| Hermes | `HERMES_TIMEOUT_SEC` | `300` | Task timeout |
| OpenCode | `OPENCODE_BIN` | `opencode` | CLI binary name |
| OpenCode | `OPENCODE_BASE_URL` | `""` | HTTP API URL (optional) |
| OpenCode | `OPENCODE_MODEL` | `qwen3-coder:30b` | Default model |
| OpenCode | `OPENCODE_WORKSPACE` | `.` | Workspace root |
| Goose | `GOOSE_BIN` | `goose` | CLI binary name |
| Goose | `GOOSE_BASE_URL` | `""` | HTTP API URL (optional) |
| Goose | `GOOSE_MODEL` | `qwen3-coder:14b` | Default model |
| Goose | `GOOSE_PROFILE` | `default` | Goose profile |
| Aider | `AIDER_BIN` | `aider` | CLI binary name |
| Aider | `AIDER_BASE_URL` | `""` | HTTP API URL (optional) |
| Aider | `AIDER_MODEL` | `ollama/qwen3-coder:14b` | Default model |
| Aider | `AIDER_NO_AUTO_COMMIT` | `false` | Skip auto-commit |
| OpenHands | `OPENHANDS_BASE_URL` | `http://localhost:3000` | OpenHands server URL |
| OpenHands | `OPENHANDS_API_KEY` | `""` | Optional API key |
| Internal Agent | `OLLAMA_BASE` | `http://localhost:11434` | Ollama endpoint |

---

## Routing Policy Defaults (from runtimes/manager.py)

```python
RoutingPolicy(
    never_use_paid_providers=True,          # RUNTIME_NEVER_PAID=true
    require_approval_before_paid_escalation=True,
    max_paid_escalations_per_day=0,         # RUNTIME_MAX_PAID_ESCALATIONS=0
    preferred_runtime_id="hermes",          # RUNTIME_DEFAULT=hermes
    task_type_runtime_overrides={
        "code_generation": "opencode",      # RUNTIME_CODE_GENERATION=opencode
        "code_review": "opencode",          # RUNTIME_CODE_REVIEW=opencode
        "repo_editing": "opencode",         # RUNTIME_REPO_EDITING=opencode
        "git_operations": "aider",          # RUNTIME_GIT_OPS=aider
    },
)
```

---

## How to Expose Runtimes on Render

Option A — **Deploy each runtime as a separate Render service:**
1. Create a new Web Service for each runtime (hermes, opencode, goose, aider)
2. Use `Dockerfile.runtime` with `RUNTIME_NAME` build arg
3. Set `OLLAMA_BASE` to your external Ollama URL
4. Set the corresponding `*_BASE_URL` in the main proxy service

Option B — **Deploy runtimes within the main service:**
- Not recommended; Render free tier has limited resources

Option C — **Use only Internal Agent + external Ollama:**
- Set `OLLAMA_BASE` to an externally reachable Ollama instance
- The `InternalAgentAdapter` runs in-process (no extra container needed)
- This is the lightest option for Render free tier

