# Advisor Strategy — Local Proxy Handling

## What the Anthropic Advisor Strategy Is

The [advisor strategy](https://claude.com/blog/the-advisor-strategy) is an Anthropic API beta
feature (`anthropic-beta: advisor-tool-2026-03-01`) that lets a fast, low-cost **executor**
model (Sonnet or Haiku) consult a higher-intelligence **advisor** model (Opus) mid-generation
for strategic guidance.

The executor model decides when to call the advisor, just like any other tool. When it does:

1. The executor emits a `server_tool_use` block with `name: "advisor"`.
2. Anthropic runs a separate Opus inference server-side, passing the executor's full transcript.
3. The Opus response returns to the executor as an `advisor_tool_result` block (400–700 text tokens).
4. The executor continues, informed by the advice.

All of this happens inside a single `/v1/messages` request — no extra round-trips for the client.

Benchmark result from Anthropic: Sonnet + Opus advisor achieves a **2.7 pp lift on SWE-bench
Multilingual** while **reducing cost per task by 11.9%** compared to Sonnet alone.

---

## How This Proxy Handles Advisor Requests

This proxy cannot execute the server-side Opus sub-inference — that is a closed Anthropic
platform feature. It gracefully degrades instead:

### Outgoing requests (tools array)

`_tools_to_openai()` in `handlers/anthropic_compat.py` filters out `advisor_20260301` (and all
other server-side beta tool types) before forwarding to Ollama. Ollama does not understand these
types and would return an error if they were passed through.

```python
_SERVER_TOOL_TYPES = frozenset({
    "advisor_20260301",
    "computer_use_20241022", "computer_use_20250124",
    "text_editor_20241022", "bash_20241022",
    "web_search_20250305",
})
```

### Incoming message history (advisor blocks)

When a client that has used the real Anthropic API sends follow-up turns, the message history
may contain `server_tool_use` and `advisor_tool_result` blocks. `_content_block_to_text()` converts
these to human-readable text so the local model still benefits from any advice that was already
generated:

| Block type | Converted to |
|---|---|
| `server_tool_use` (name: advisor) | `[advisor consultation requested]` |
| `advisor_tool_result` → `advisor_result` | `[Advisor guidance]: <text>` |
| `advisor_tool_result` → `advisor_redacted_result` | `[Advisor guidance: redacted by server]` |
| `advisor_tool_result` → error | `[Advisor error: <error_code>]` |

---

## Local Equivalent: The Planner Role

The repo's own agent system in `agent/loop.py` implements a structurally equivalent pattern
using local models:

| Advisor strategy concept | Local equivalent |
|---|---|
| Executor model | `qwen3-coder:30b` (env: `AGENT_EXECUTOR_MODEL`) |
| Advisor model | `deepseek-r1:32b` (env: `AGENT_PLANNER_MODEL` / `AGENT_VERIFIER_MODEL`) |
| Advisor consults before execution | `_generate_plan()` — Planner produces an ordered step plan |
| Advisor consults after file writes | `_execute_step()` — Verifier reviews each change before `apply_diff` |

The key architectural difference: the Anthropic advisor strategy keeps the executor in the driver
seat and lets it escalate on demand. The local system uses a **plan-first** approach where the
Planner always runs before the Executor. The effect is similar: a cheaper model does the bulk
of the token generation while a higher-reasoning model provides the strategic direction.

See `docs/architecture/agent-orchestration.md` for the full local agent design.

---

## Using the Real Advisor Strategy via This Proxy

The proxy is a local-model proxy — it cannot forward advisor tool calls to Anthropic. If you
want the real advisor strategy with Opus-level intelligence, point your client directly at the
Anthropic API:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# Use the Anthropic API directly, not this proxy
```

To use this proxy for local-model work while still applying the advisor pattern concept,
use the agent endpoint:

```bash
POST /v1/agent/run
{
  "instruction": "...",
  "model": "qwen3-coder:30b",
  "auto_commit": false,
  "max_steps": 10
}
```

The agent runner automatically routes planning and verification to `deepseek-r1:32b` regardless
of the executor model specified.
