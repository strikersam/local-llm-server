# Dynamic Model Routing

The proxy includes a centralized model routing system that automatically selects
the best local model for each request, while allowing full manual override from
any client or IDE.

## How automatic selection works

Every request passes through `router.ModelRouter.route()` which returns a
`RoutingDecision` containing the resolved model and a full audit trail.

**Selection priority (highest → lowest):**

| Priority | Trigger | `selection_source` |
|----------|---------|-------------------|
| 1 | `X-Model-Override` header present | `override` |
| 2 | Requested model found in `MODEL_MAP` (or built-in Claude alias table) | `model_map` |
| 3 | Requested model is a known local Ollama model | `passthrough` |
| 4 | Task classification → capability registry lookup | `heuristic` |
| 5 | Fallback to `AGENT_EXECUTOR_MODEL` env var | `default` |

### Task classification

When no explicit mapping is found, the router classifies the request into one of
these task categories and picks the best registered model:

| Category | Signals | Default model |
|----------|---------|---------------|
| `agent_plan` | Agent planning endpoint | `deepseek-r1:32b` |
| `agent_execute` | Agent execution endpoint | `qwen3-coder:30b` |
| `agent_verify` | Agent verification endpoint | `qwen3-coder:30b` |
| `tool_use` | Tool/function definitions present | `qwen3-coder:30b` |
| `long_context` | Estimated tokens > 16 000 | `qwen3-coder:30b` |
| `fast_response` | Streaming + very short message (<200 chars) + no code | `qwen3-coder:7b` (if loaded) |
| `code_debugging` | Debug/error keywords + code fence | `qwen3-coder:30b` |
| `code_review` | Review/audit keywords + code fence | `qwen3-coder:30b` |
| `code_generation` | Implement/write/create keywords or code fence | `qwen3-coder:30b` |
| `reasoning` | Design/analyze/tradeoff/compare keywords | `deepseek-r1:32b` |
| `conversation` | Everything else | `qwen3-coder:30b` |

## Manual override

Force a specific local model regardless of IDE, API format, or task type:

```http
POST /v1/messages
X-Model-Override: deepseek-r1:32b
```

```http
POST /v1/chat/completions
X-Model-Override: qwen3-coder:30b
```

```http
POST /api/chat
X-Model-Override: qwen3-coder:7b
```

The header works identically across all three API formats (Anthropic, OpenAI,
Ollama native).  When set, the response includes:

```
X-Routing-Mode: manual
X-Routing-Model: deepseek-r1:32b
```

### Curl example

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "x-api-key: YOUR_API_KEY" \
  -H "x-model-override: deepseek-r1:32b" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"Hello"}]}'
```

### Python SDK example

```python
import anthropic

client = anthropic.Anthropic(
    api_key="your-key",
    base_url="http://localhost:8000",
    default_headers={"x-model-override": "deepseek-r1:32b"},
)
```

## Configuring model preferences

### Built-in Claude → local alias table

The router includes a built-in table mapping all Claude 3/4 model names to local
models.  Anthropic "opus" models route to `deepseek-r1:32b` (reasoning);
"sonnet" and "haiku" models route to `qwen3-coder:30b` (coding).

### MODEL_MAP env var (per-alias overrides)

Override individual mappings or add a catch-all:

```env
# In .env
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
```

Format: `anthropic_model_name:local_model_name` (comma-separated).
The special key `*` is the catch-all fallback.

### ROUTER_EXTRA_MODELS env var (extend capability registry)

Add custom models to the routing registry without code changes:

```env
# Format: model_name:type:strength1+strength2+strength3  (comma-separated entries)
ROUTER_EXTRA_MODELS=my-coder:latest:coder:code_generation+tool_use,phi4:14b:general:conversation+reasoning
```

Models added here become candidates for heuristic routing.

## Inspecting routing behavior

### Response headers

Every response includes routing headers:

```
X-Routing-Mode: auto         # or "manual"
X-Routing-Model: qwen3-coder:30b
```

### Structured logs

Every request logs a routing summary at INFO level:

```
→ /v1/messages model=claude-opus-4-6 → deepseek-r1:32b [auto/model_map] stream=True tools=0
```

For agent requests, DEBUG logs show per-phase model selection:

```
agent plan: model=deepseek-r1:32b [auto/heuristic]
agent execute: executor=qwen3-coder:30b verifier=qwen3-coder:30b
```

### Langfuse traces

When Langfuse is configured, every observation includes routing metadata:

| Field | Example value |
|-------|---------------|
| `routing_mode` | `auto` or `manual` |
| `routing_requested_model` | `claude-opus-4-6` |
| `routing_resolved_model` | `deepseek-r1:32b` |
| `routing_reason` | `MODEL_MAP: claude-opus-4-6 → deepseek-r1:32b (task: reasoning)` |
| `routing_task_category` | `reasoning` |
| `routing_selection_source` | `model_map` |
| `routing_fallback_chain` | `qwen3-coder:30b` |
| `routing_provider` | `ollama` |

Filter Langfuse generations by `routing_mode=manual` to audit overrides, or by
`routing_task_category` to analyse model usage by workload type.

## Usage tracking

Usage tracking is recorded per actual resolved model, not per requested model.
This means cost estimates and token counts in Langfuse reflect true local model
usage even when clients send Claude aliases.

The `routing_requested_model` and `routing_resolved_model` fields let you
correlate every cloud-side Claude model name with the local model actually used.

## Architecture

```
Client (any IDE / protocol)
    │
    │  [optional] X-Model-Override header
    │
    ▼
ModelRouter.route()
    │
    ├─ 1. Manual override? ──────────────────────→ RoutingDecision(mode=manual)
    │
    ├─ 2. Task classification (classifier.py)
    │      └─ regex heuristics on messages + system prompt
    │
    ├─ 3. MODEL_MAP lookup (built-in + env overrides)
    │      └─ Anthropic alias → local model name
    │
    ├─ 4. Known local model? ────────────────────→ RoutingDecision(source=passthrough)
    │
    ├─ 5. Capability registry (registry.py)
    │      └─ best_model_for(task_category)
    │
    └─ 6. Default fallback (AGENT_EXECUTOR_MODEL)
    │
    ▼
RoutingDecision
    ├─ resolved_model  → sent to Ollama
    ├─ routing_meta   → forwarded to Langfuse
    └─ headers        → returned to client (X-Routing-Mode, X-Routing-Model)
```

## Health check and availability filtering

The router calls `router.health.get_available_models()` before finalising every
model selection.  This queries Ollama's `/api/tags` endpoint and returns the set
of currently-loaded model names.  Results are cached for `ROUTER_HEALTH_CACHE_TTL`
seconds (default 60).

If the chosen model is not in the loaded set, the router walks the fallback chain
and picks the first loaded alternative.  If nothing in the chain is available, the
original model is used anyway so Ollama can return a clear error.

Disable health checks entirely with `ROUTER_HEALTH_CHECK_ENABLED=false`.

## Fallback execution

When Ollama returns a 5xx error (model not loaded, OOM, etc.) on a
**non-streaming** request, the proxy automatically retries with the next model in
`routing.fallback_chain`.  The health cache is invalidated before each retry so
the router reflects the current Ollama state.

**Streaming** requests do not retry — the SSE/NDJSON stream has already started
by the time a failure is detectable, and retrying mid-stream would corrupt the
client's buffer.  The client receives the error and should reconnect.

## Configuring fast_response routing

Short interactive queries (streaming, < 200 chars, no code keywords) are routed to
`qwen3-coder:7b` for minimum latency when it is loaded.  If the 7b model is not
loaded, the router falls back to the default executor.

Tune the threshold:
```env
ROUTER_FAST_RESPONSE_CHARS=300   # raise for longer prompts to still qualify
ROUTER_FAST_RESPONSE_CHARS=0     # disable fast_response routing entirely
```

## Limitations and future improvements

- **Streaming fallback**: streaming paths do not retry on 5xx; the client must
  reconnect.  Future work: buffer the first few bytes before committing to stream
  so a 5xx can be caught and retried transparently.

- **Single provider**: only Ollama is supported today.  The `provider` field in
  `RoutingDecision` is reserved for future multi-provider routing.

- **Static classification**: keyword heuristics are fast but imperfect.  Future
  work: add an optional fast-classify LLM call for ambiguous requests.
