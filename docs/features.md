# Feature Guide

This document explains every implemented feature in the qwen-server, what it does, why it exists, how to enable it, and its limitations.

---

## 1. OpenAI-Compatible API Proxy

**What it does:** Exposes Ollama models through a `/v1/` API surface that any OpenAI SDK client can connect to without modification.

**Why it exists:** Ollama serves models locally but has no authentication. This proxy adds auth, rate limiting, and HTTPS exposure while keeping the OpenAI API shape intact.

**How to use it:**

Any client that supports a custom `base_url`:

```python
from openai import OpenAI
client = OpenAI(base_url="https://your-tunnel.trycloudflare.com/v1", api_key="your-key")
```

**Supported endpoints:**

```
POST /v1/chat/completions    # Chat — streaming + non-streaming
GET  /v1/models              # List models (includes Claude aliases)
POST /v1/completions         # Legacy text completion
POST /v1/embeddings          # Embeddings (passed to Ollama)
```

**Limitations:**
- Vision input is not supported (text-only local models)
- Function calling support depends on the model; reliability varies
- No persistent fine-tuning or assistants API

---

## 2. Ollama Native Passthrough

**What it does:** Passes Ollama-format requests through under `/api/` with the same auth and rate-limiting as the OpenAI routes.

**Why it exists:** Some clients (older Ollama-native apps, direct API scripts) use the Ollama JSON format rather than OpenAI format. This proxy supports both.

**Endpoints:**

```
POST /api/chat       # Ollama chat (streaming NDJSON)
POST /api/generate   # Ollama text generation
GET  /api/tags       # List models
POST /api/pull       # Pull a model
GET  /api/ps         # Show loaded models
```

**Config:** No specific config needed — always enabled.

---

## 3. Anthropic API Compatibility (`/v1/messages`)

**What it does:** Translates incoming Anthropic Messages API requests into OpenAI/Ollama format, processes them, and returns responses in Anthropic format.

**Why it exists:** Tools like Claude Code CLI, the `anthropic` Python SDK, and Cursor in Claude mode all send requests to `api.anthropic.com` with the Anthropic request shape. This handler lets them work against local models without code changes.

**How to enable:**

Set `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` in the client environment:

```bash
export ANTHROPIC_BASE_URL=https://your-tunnel.trycloudflare.com
export ANTHROPIC_API_KEY=your-proxy-key
```

**Model name mapping:**

Claude model names are mapped to local models via `MODEL_MAP` env or built-in defaults. See [docs/claude-code-setup.md](claude-code-setup.md) for the full mapping table.

**Limitations:**
- Image/vision content blocks are not supported
- Tool use support is model-dependent
- Prompt caching is not supported

---

## 4. Multi-User Key Management

**What it does:** Issues per-user bearer tokens with associated email and department metadata. Keys are stored hashed on disk — plaintext tokens are shown once and never stored.

**Why it exists:** A shared static key makes it impossible to identify who is using the server or attribute usage to teams. Per-user keys enable Langfuse observability and cost allocation.

**How to enable:**

```env
KEYS_FILE=keys.json
ADMIN_SECRET=<strong-secret>
```

**Key lifecycle:**

1. Create: via CLI, admin API, or browser UI
2. Use: pass as `Authorization: Bearer <token>` or `x-api-key: <token>` header
3. Rotate: generates a new token for the same `key_id`
4. Delete: removes the record permanently

**Key attributes:**

| Attribute | Purpose |
|-----------|---------|
| `key_id` | Stable identifier (survives rotation) |
| `email` | Langfuse `user_id` — who made the request |
| `department` | Cost center / team allocation label |
| `created` | Timestamp |
| `token_hash` | SHA-256 hash of the bearer token |

**Legacy mode:** `API_KEYS=comma,separated,keys` still works for personal use but all traffic appears as `user=unknown, department=legacy` in Langfuse.

---

## 5. Rate Limiting

**What it does:** Limits each API key to a configurable number of requests per minute. Excess requests receive a `429 Too Many Requests` response.

**Why it exists:** Without rate limiting, a runaway script or misuse could starve other users or cause OOM on the machine.

**Config:**

```env
RATE_LIMIT_RPM=60   # Max requests per minute per key (default: 60)
```

Set to 0 to disable.

**Limitations:**
- In-memory only — resets on proxy restart
- Per-key, not per-IP (a single key could be used from multiple machines at the combined rate)

---

## 6. Default System Prompt Injection

**What it does:** Injects a configured system prompt into every request that doesn't already have one.

**Why it exists:** Useful for giving all users consistent behavior (e.g. "You are a coding assistant") without requiring every client to include it.

**Config:**

```env
PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED=false
PROXY_DEFAULT_SYSTEM_PROMPT_FILE=templates/codex_local_ide_system_prompt.txt
# or inline:
PROXY_DEFAULT_SYSTEM_PROMPT=You are a helpful coding assistant.
```

**Important:** Disable this for Claude Code and Continue — those clients send their own system prompt, and stacking a second one causes confusion.

**Limitations:**
- Only injected when the request has no existing system message
- File path is relative to the repo root

---

## 7. Think-Tag Stripping

**What it does:** Removes `<think>...</think>` blocks from model responses before returning them to the client.

**Why it exists:** Reasoning models like DeepSeek-R1 expose their chain-of-thought in `<think>` blocks. Most clients (IDEs, chat UIs) don't know how to handle them and display raw XML-like markup.

**Config:**

```env
PROXY_STRIP_THINK_TAGS=true   # default: true
```

**Behavior:**
- Works in both streaming and non-streaming modes
- Blocks are stripped from the final output text
- Usage token counts are not affected

**When to disable:** If you want to see the model's reasoning (debugging, research) — set to `false`.

---

## 8. Infrastructure Cost Tracking

**What it does:** Calculates the true local cost of each request based on actual power draw, hardware amortization, and configured electricity rates. Emits these values to Langfuse as metadata.

**Why it exists:** "Free" local inference has real costs — electricity and hardware depreciation. This feature makes those visible in Langfuse alongside the commercial API savings estimates.

**Config:**

```env
INFRA_GPU_ACTIVE_WATTS=150        # GPU power during inference (measure with GPU-Z or HWiNFO64)
INFRA_GPU_IDLE_WATTS=20           # GPU idle power (model loaded, no request)
INFRA_SYSTEM_WATTS=50             # CPU/RAM/SSD overhead
INFRA_ELECTRICITY_USD_KWH=0.12   # Your electricity rate
INFRA_HARDWARE_COST_USD=2000     # Total hardware cost to amortize
INFRA_AMORTIZATION_MONTHS=36     # Months over which to spread hardware cost
```

**What gets emitted per request (in Langfuse metadata):**

| Key | Value | Notes |
|-----|-------|-------|
| `infra_electricity_usd` | float | Electricity cost for this request based on latency |
| `infra_hardware_usd` | float | Hardware amortization allocated to this request |
| `infra_energy_kwh` | float | kWh consumed by this request |

See [docs/langfuse-observability.md](langfuse-observability.md) for how to interpret these in Langfuse.

**How to measure your actual wattage:**
- Windows: GPU-Z (GPU Power Draw reading) or HWiNFO64 (sensor view)
- Linux: `nvidia-smi --query-gpu=power.draw --format=csv`
- Wall outlet power meter (most accurate — covers whole system)
- Intel AI PC: typically 30–50W GPU + 20–30W system under load

**Limitations:**
- Calculations are estimates based on total request latency — not instruction-level profiling
- Does not account for pre-load/warm-up time

---

## 9. Commercial Equivalent Savings Estimation

**What it does:** For every request, estimates what the equivalent traffic would have cost on a commercial API (e.g. Claude Sonnet 4.6) and records the "savings" in Langfuse.

**Why it exists:** Makes the business case for local inference visible — you can see in Langfuse exactly how much you saved vs. paying Anthropic/OpenAI.

**Default mappings (2026):**

| Local model | Commercial equivalent | Input $/M | Output $/M |
|-------------|----------------------|-----------|------------|
| `qwen3-coder:30b` | Claude Sonnet 4.6 class | $3.00 | $15.00 |
| `deepseek-r1:32b` | DeepSeek R1 API | $0.55 | $2.19 |
| `deepseek-r1:671b` | DeepSeek R1 API (full) | $0.55 | $2.19 |
| `qwen3-coder:7b` | Claude Haiku 4.5 class | $0.80 | $4.00 |
| `frob/minimax-m2.5:230b-a10b-q4_K_M` | MiniMax M2.5 API | $0.10 | $0.55 |
| `deepseek-v3.2:cloud` | DeepSeek V3.2 API | $0.27 | $1.10 |

**Custom pricing override:**

```env
COMMERCIAL_EQUIVALENT_PRICES_JSON={"my-model:tag":{"commercial_name":"GPT-4.1","input_per_million_usd":2,"output_per_million_usd":8}}
# or as a file:
COMMERCIAL_EQUIVALENT_PRICES_FILE=pricing.json
```

**What gets emitted per request:**

| Key | Value |
|-----|-------|
| `estimated_commercial_equivalent_usd` | What this request would cost on the reference API |
| `estimated_savings_vs_commercial_usd` | Equivalent minus actual infra cost |
| `commercial_reference_model` | The reference API name (e.g. "Claude Sonnet 4.6") |

---

## 10. Langfuse Observability

**What it does:** Traces every authenticated chat request to Langfuse, including the full request/response, token counts, latency, cost metadata, and user/department attribution.

**Why it exists:** Without observability, you have no visibility into who is using the server, which models are popular, how fast responses are, or what the true cost is.

**Config:**

```env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

See [docs/langfuse-observability.md](langfuse-observability.md) for full trace structure, dashboard guidance, and how to read cost metrics.

---

## 11. Coding Agent API

**What it does:** A planner → executor → verifier loop that can read files, write code changes, run syntax checks, and optionally commit to git — all via an authenticated REST API.

**Why it exists:** Makes the local models capable of autonomous coding tasks beyond a single chat turn.

**Architecture:**

```
/agent/run  or  /agent/sessions/{id}/run
    │
    ├─ Planner (deepseek-r1:32b) — breaks task into ≤5 steps (JSON)
    │
    └─ For each step:
         ├─ Executor (qwen3-coder:30b) — uses tools to read context, write code
         │    tools: read_file, list_files, search_code, apply_diff
         │
         └─ Verifier (deepseek-r1:32b) — validates each change (pass/fail JSON)
              └─ Retry up to 3× if verifier fails
```

**Endpoints:**

```
POST /agent/sessions                          # Create a named session
GET  /agent/sessions/{id}                     # Get session state + history
POST /agent/sessions/{id}/run                 # Run a task in this session
POST /agent/run                               # One-off run (no session)
POST /agent/sessions/{id}/rollback-last-commit  # Undo last agent commit
```

**Config:**

```env
AGENT_PLANNER_MODEL=deepseek-r1:32b
AGENT_EXECUTOR_MODEL=qwen3-coder:30b
AGENT_VERIFIER_MODEL=deepseek-r1:32b
AGENT_WORKSPACE_ROOT=C:\path\to\your\repo  # optional
```

**Example request:**

```bash
curl https://your-tunnel/agent/run \
  -H "Authorization: Bearer your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Add input validation to the /admin/keys endpoint",
    "auto_commit": false,
    "max_steps": 3
  }'
```

**Limitations:**
- No vision or multi-modal input
- Auto-commit requires a clean git working tree
- Session history is in-memory only (lost on proxy restart)
- Large codebases may exceed model context windows

---

## 12. Browser Admin UI

**What it does:** A server-rendered HTML dashboard for managing users, services, and running diagnostics.

See [docs/admin-dashboard.md](admin-dashboard.md) for full documentation.

---

## 13. Telegram Remote Control Bot

**What it does:** A Telegram bot that gives you mobile access to service status, service control, cost data, and key management — from anywhere with Telegram.

See [docs/telegram-bot.md](telegram-bot.md) for full documentation.

---

## 14. Tunnel — Permanent Static URL via ngrok

**What it does:** Exposes the local proxy over HTTPS without port forwarding, static IP, or firewall rules. Works behind home NAT, corporate firewalls, and mobile hotspots.

**Why it exists:** Makes the local server accessible from any laptop or device on any network, identical to a cloud API.

**Quick tunnel (default — URL changes on restart):**

```bash
./run_tunnel.sh      # Linux/macOS
.\run_tunnel.bat     # Windows
```

**Permanent static URL via ngrok (recommended):**

Run once on your personal laptop — no domain purchase needed:

```bash
python setup_ngrok.py --token <YOUR_NGROK_AUTH_TOKEN>
```

Get your token free at [dashboard.ngrok.com](https://dashboard.ngrok.com). The script:
- Claims your free static domain (e.g. `yourword-yourword-1234.ngrok-free.app`)
- Saves `PUBLIC_URL`, `NGROK_AUTH_TOKEN`, `NGROK_DOMAIN` to `.env`
- Rewrites `run_tunnel.sh` / `run_tunnel.bat` to use ngrok automatically

After that, `./start_server.sh` starts the tunnel with the same URL every time. The URL is shown in the Admin UI **Public URL** field (which is now editable — paste any URL there to pin it permanently).

The tunnel URL can also be fetched programmatically:

```bash
./get_tunnel_url.sh     # Linux/macOS
.\get_tunnel_url.ps1    # Windows
```

---

## 15. CORS Support

**What it does:** Adds `Access-Control-Allow-Origin` headers to all responses, enabling browser-based clients (web apps, Open WebUI) to call the proxy directly.

**Config:**

```env
CORS_ORIGINS=*                           # Allow any origin (default)
CORS_ORIGINS=https://myapp.example.com  # Restrict to specific origin
```

---

## 16. Streaming Support

**What it does:** Streams tokens back to the client in real time using Server-Sent Events (SSE) for OpenAI/Anthropic format, or NDJSON for Ollama format.

**Why it exists:** Without streaming, users wait for the full response before seeing any output — noticeably worse UX for longer responses.

**Config:** No configuration needed — streaming is enabled when the client sends `"stream": true`.

**Usage injection:** The proxy can inject token usage data into SSE stream chunks (needed by some clients):

```env
PROXY_INJECT_STREAM_USAGE=true   # default: true
```

Disable if your Ollama build rejects the `stream_options` field.
