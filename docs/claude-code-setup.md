# Claude Code + Qwen Local Setup

This guide explains how to use Anthropic's **Claude Code CLI** (and any Anthropic-API-compatible client) against your local Qwen/DeepSeek models via this proxy.

---

## What This Enables

Claude Code normally calls `api.anthropic.com`. By pointing it at this proxy instead, every request is routed to your local Ollama models — no Anthropic API key required, no per-token billing, no data leaving your machine.

The proxy translates between the Anthropic Messages API format (which Claude Code sends) and the OpenAI-compatible format that Ollama speaks. Model names like `claude-sonnet-4-6` are mapped to local equivalents at the proxy layer — Claude Code never needs to know.

---

## Architecture

```
Claude Code CLI (or any Anthropic SDK client)
    │
    │  POST /v1/messages
    │  x-api-key: <your-proxy-key>
    │  model: claude-sonnet-4-6          ← Claude Code sends this
    ▼
FastAPI Proxy  (proxy.py, port 8000 / tunnel URL)
    │
    │  MODEL_MAP resolves:
    │  claude-sonnet-4-6 → qwen3-coder:30b
    │  claude-opus-4-6   → deepseek-r1:32b
    │
    │  POST /v1/chat/completions
    ▼
Ollama  (localhost:11434)
    │
    ▼
Local model weights  (D:\aipc-models)
```

Responses are translated back from the OpenAI format to the Anthropic SSE format before being returned to Claude Code. The client sees a normal Anthropic API response throughout.

---

## Prerequisites

Before starting:

- The proxy is running: `.\start_server.ps1` (Windows) or `./start_server.sh` (Linux/macOS)
- At least one local model is pulled (`qwen3-coder:30b` recommended for Claude Code)
- You have a proxy API key from your `.env` `API_KEYS` or `KEYS_FILE`
- Claude Code CLI is installed: `npm install -g @anthropic-ai/claude-code`

Verify the proxy is reachable:

```bash
curl http://localhost:8000/health
# {"status":"ok","models":["qwen3-coder:30b","deepseek-r1:32b"]}
```

---

## Step-by-Step Setup

### 1. Set environment variables

Point Claude Code at your proxy instead of `api.anthropic.com`:

```bash
# Linux / macOS
export ANTHROPIC_BASE_URL=https://your-tunnel-url.trycloudflare.com
export ANTHROPIC_API_KEY=your-proxy-key-here

# Windows PowerShell
$env:ANTHROPIC_BASE_URL = "https://your-tunnel-url.trycloudflare.com"
$env:ANTHROPIC_API_KEY  = "your-proxy-key-here"
```

If running locally (not through the tunnel):

```bash
export ANTHROPIC_BASE_URL=http://localhost:8000
export ANTHROPIC_API_KEY=your-proxy-key-here
```

> `ANTHROPIC_API_KEY` is validated by the proxy using your configured `API_KEYS` or `KEYS_FILE`.
> The proxy accepts it as an `x-api-key` header, which is exactly what Claude Code sends.

### 2. Start Claude Code

```bash
claude
# or
claude code
```

Claude Code will connect to your proxy. The first request may be slow (~5–15 seconds) while Ollama loads the model into memory.

### 3. Verify model routing

Run a quick test from within Claude Code:

```
> What model are you?
```

Or check the proxy logs:

```bash
tail -f logs/proxy.log
# You should see: POST /v1/messages ... model=qwen3-coder:30b
```

---

## Model Name Mapping

The proxy ships with built-in mappings. When Claude Code sends a model name, it is translated to the best available local model:

| Claude Code model name | Mapped to (default) | Role |
|------------------------|---------------------|------|
| `claude-sonnet-4-6` | `qwen3-coder:30b` | Coding, completions |
| `claude-opus-4-6` | `deepseek-r1:32b` | Reasoning, planning |
| `claude-haiku-4-5-20251001` | `qwen3-coder:30b` | Fast tasks |
| `claude-3-5-sonnet-20241022` | `qwen3-coder:30b` | Legacy requests |
| `claude-3-opus-*` | `deepseek-r1:32b` | Legacy reasoning |
| `*` (catch-all) | `qwen3-coder:30b` | Any unmapped name |

### Customising the mapping

Override the defaults via `MODEL_MAP` in `.env`:

```env
# Format: anthropic_name:ollama_name — comma-separated, * = catch-all
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
```

To route all traffic to a specific model:

```env
MODEL_MAP=*:qwen3-coder:30b
```

To add a new model after pulling it:

```env
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,my-custom-claude:my-model:tag,*:qwen3-coder:30b
```

---

## Required Configuration

These `.env` values must be set for Claude Code to work correctly:

```env
# Must be at least 4096. Claude Code generates multi-thousand-token responses.
# The old default of 1200 will silently truncate all code generation.
PROXY_DEFAULT_MAX_TOKENS=8192

# Claude Code sends ~15-20K tokens of system prompt alone.
# Think-tag stripping prevents <think> blocks from leaking into responses.
PROXY_STRIP_THINK_TAGS=true

# Do NOT enable the default system prompt — Claude Code sends its own.
# Stacking a proxy system prompt on top causes context confusion.
PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED=false
```

---

## Context Window Limitations

Claude Code's built-in system prompt is **15,000–20,000 tokens**. This is a hard constraint:

| Model context window | Available for conversation |
|---------------------|---------------------------|
| 32K tokens | ~12K tokens remaining |
| 128K tokens | ~108K tokens remaining |

With `qwen3-coder:30b` (default 32K context), Claude Code works well for:
- Single-file edits
- Targeted code generation
- Explaining functions or modules

It may struggle with:
- Large multi-file refactors where full context is needed
- Very long conversation histories that fill the 12K remainder

**Workaround:** Start fresh Claude Code sessions frequently for large tasks. The `/clear` command in Claude Code clears conversation history without restarting.

---

## Anthropic SDK (Python)

Any code using `anthropic` Python SDK works the same way:

```python
import anthropic
import os

client = anthropic.Anthropic(
    base_url=os.environ["ANTHROPIC_BASE_URL"],  # your proxy URL
    api_key=os.environ["ANTHROPIC_API_KEY"],     # your proxy key
)

message = client.messages.create(
    model="claude-sonnet-4-6",    # mapped to qwen3-coder:30b by proxy
    max_tokens=4096,
    messages=[
        {"role": "user", "content": "Write a Python function to parse JSON safely"}
    ]
)

print(message.content[0].text)
```

Streaming:

```python
with client.messages.stream(
    model="claude-opus-4-6",      # mapped to deepseek-r1:32b
    max_tokens=4096,
    messages=[{"role": "user", "content": "Explain attention mechanisms"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

---

## How to Verify the Setup is Working

### Health check

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","models":["qwen3-coder:30b","deepseek-r1:32b"]}
```

### Test the /v1/messages endpoint directly

```bash
curl http://localhost:8000/v1/messages \
  -H "x-api-key: your-proxy-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-6",
    "max_tokens": 100,
    "messages": [{"role":"user","content":"Reply with: hello from local"}]
  }'
```

Expected response format (Anthropic-style):

```json
{
  "id": "msg_...",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "hello from local"}],
  "model": "claude-sonnet-4-6",
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 12, "output_tokens": 5}
}
```

### List available models

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer your-proxy-key"
```

This returns the local Ollama models plus their Claude alias names.

---

## Common Failure Cases

### "Authentication error" or 401

- Confirm `ANTHROPIC_API_KEY` matches a key in `API_KEYS` or `KEYS_FILE`
- The proxy accepts both `x-api-key: <key>` and `Authorization: Bearer <key>` headers
- Keys are case-sensitive

### "Model not found" or empty response

- The requested model is not pulled in Ollama
- Run: `ollama list` to see what's available
- Pull the missing model: `ollama pull qwen3-coder:30b`

### Responses get cut off mid-sentence

- `PROXY_DEFAULT_MAX_TOKENS` is too low
- Must be ≥ 4096 for Claude Code; set to 8192 or higher
- The old default of 1200 causes this — check your live `.env`

### `<think>...</think>` blocks appear in output

- `PROXY_STRIP_THINK_TAGS=true` is not set (or set to `false`)
- DeepSeek-R1 and similar reasoning models emit these by default

### Very slow first response

- Ollama is loading the model into memory (normal for first request after startup)
- Subsequent requests are much faster
- `ollama ps` shows what is currently loaded

### Claude Code reports "token limit exceeded"

- The conversation context is full (32K default for most models)
- Run `/clear` in Claude Code to reset the session
- Consider pulling a model with larger context (128K variants if available)

### System prompt injection visible in Claude Code

- `PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED=true` is conflicting with Claude Code's own system prompt
- Set to `false` when using Claude Code

---

## Startup Sequence

For a clean session from scratch:

```
1. Start Ollama            → .\run_ollama.bat  (or .\start_server.ps1 for everything)
2. Wait for model to load  → ollama ps
3. Start proxy             → .\run_proxy.bat   (or included in start_server.ps1)
4. Start tunnel (optional) → .\run_tunnel.bat
5. Set env vars            → $env:ANTHROPIC_BASE_URL = "http://localhost:8000"
6. Launch Claude Code      → claude
```

When using the tunnel for remote access, replace `http://localhost:8000` with the tunnel URL from `.\get_tunnel_url.ps1`.

---

## Unsupported Features

These Anthropic API features are not supported by the local proxy:

| Feature | Status | Notes |
|---------|--------|-------|
| Vision / image input | Not supported | Local models are text-only |
| Tool use / function calling | Partially | Depends on model; results may vary |
| Prompt caching | Not supported | Ollama has no caching API |
| Batch API | Not supported | No equivalent in Ollama |
| Files API | Not supported | — |

Claude Code's core features (chat, file editing, code generation) work fully. Vision-related Claude Code features (screenshot analysis etc.) will fail silently or return errors.
