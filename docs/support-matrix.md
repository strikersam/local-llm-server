# Feature Support Matrix

This document describes the stability classification of every feature in
local-llm-server.  The **single source of truth** is `features/matrix.py` —
this document is generated from the same registry.

For operator override instructions see the [Configuration Reference](configuration-reference.md#feature-flags).

---

## Maturity Tiers

| Tier | Meaning |
|------|---------|
| **stable** | Production-ready.  API and behaviour are stable.  No warnings. |
| **beta** | Usable but may have rough edges.  API may evolve.  Generates a warning log on use. |
| **experimental** | Opt-in only.  Disabled by default.  Not recommended for production. |
| **disabled** | Permanently off.  Cannot be enabled by operators. |

---

## Support Matrix

### Stable Core

| Feature | ID | Notes |
|---------|-----|-------|
| OpenAI / Ollama / Anthropic proxy endpoints | `proxy_endpoints` | Always on |
| Bearer token + key-store auth | `auth` | Always on |
| Per-key rate limiting | `rate_limiting` | Configurable via `RATE_LIMIT_RPM` |
| Multi-provider routing and fallback | `provider_routing` | Always on |
| Local model routing + alias resolution | `model_routing` | Configurable via `MODEL_MAP` |
| API key CRUD (generate / revoke) | `key_management` | Requires `KEYS_FILE` |
| Direct chat (sync, non-blocking) | `direct_chat` | Always on |
| Built-in local agent runtime | `local_runtime` | Always on |
| Langfuse trace / cost observability | `langfuse_observability` | Activated by `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` |

### Beta

| Feature | ID | Notes |
|---------|-----|-------|
| Async agent job queue (202 + job ID) | `async_agent_jobs` | Poll `/api/chat/agent-jobs/<id>` for status |
| Planner / verifier / judge pipeline | `planner_verifier_judge` | Requires `AGENT_*_MODEL` env vars |
| Per-job isolated workspace | `workspace_isolation` | Configurable via `AGENT_WORKSPACE_BASE`, `WORKSPACE_TTL_HOURS` |
| Runtime readiness / preflight validation | `runtime_preflight` | Always on when runtimes are enabled |
| Task-harness runtime | `task_harness_runtime` | Requires Docker sidecar |
| Aider runtime | `aider_runtime` | Requires `aider` binary on PATH |
| Hermes runtime | `hermes_runtime` | Requires Hermes sidecar |
| Per-job progress polling | `per_job_progress` | Poll `GET /api/chat/agent-jobs/<id>` |
| Telegram bot remote control | `telegram_bot` | Requires `TELEGRAM_BOT_TOKEN` |
| Tunnel / ngrok / Cloudflare remote access | `tunnel` | Requires token |
| Admin command runner | `admin_command_runner` | Requires `ADMIN_SECRET` |

### Experimental

| Feature | ID | Notes |
|---------|-----|-------|
| jcode runtime | `jcode_runtime` | Requires binary on PATH or `JCODE_BIN` |
| OpenHands runtime (Docker) | `openhands_runtime` | Opt-in via `OPENHANDS_ENABLED=true` |
| OpenCode runtime (sidecar) | `opencode_runtime` | Requires OpenCode sidecar |
| Goose runtime (sidecar) | `goose_runtime` | Requires Goose sidecar |
| Social / OAuth login | `social_auth` | Requires `GOOGLE_CLIENT_ID` or `GITHUB_CLIENT_ID` |
| Multi-agent swarm orchestration | `multi_agent_swarm` | No dedicated config flag |
| CRISPY workflow engine | `workflow_engine` | No dedicated config flag |

---

## Recommended Production Configuration

For stable production operation, enable only:

- Stable core features (always on)
- `async_agent_jobs` + `workspace_isolation` (beta, well-tested)
- `langfuse_observability` if you have a Langfuse account
- `telegram_bot` if you need remote control

Avoid in production:
- Experimental runtimes (OpenHands, OpenCode, Goose, jcode)
- Multi-agent swarm / CRISPY workflow engine

---

## Operator Overrides

Operators can override the default availability of beta and experimental features
using environment variables:

```bash
# Force-disable beta features
FEATURE_DISABLE=async_agent_jobs,telegram_bot

# Force-enable an experimental feature
FEATURE_ENABLE=openhands_runtime
```

`FEATURE_DISABLE` cannot be overridden by `FEATURE_ENABLE` (disable takes precedence
when applied first).  Features with maturity=`disabled` cannot be enabled by any
operator override.

---

## Admin API

`GET /admin/api/features`  (requires admin auth)

Returns the full matrix as JSON:

```json
{
  "schema_version": "1",
  "total": 27,
  "by_maturity": {
    "stable": 9,
    "beta": 11,
    "experimental": 7
  },
  "entries": [
    {
      "feature_id": "proxy_endpoints",
      "display_name": "OpenAI / Ollama / Anthropic proxy endpoints",
      "maturity": "stable",
      "enabled": true,
      "default_available": true,
      "dependencies": [],
      "config_flags": [],
      "admin_visible": true,
      "notes": "Core proxy; always on."
    }
  ]
}
```

---

## Enforcement

The support matrix is **not documentation-only**.  It is enforced at runtime:

1. Disabled features raise `FeatureUnavailableError` when accessed via
   `require_feature(feature_id)`.
2. Beta and experimental features emit a `WARNING` log on first use.
3. Admin API and UI reflect the actual runtime state (not docs).
4. Operator overrides are applied at startup, not on every request.

See `features/matrix.py` for the full registry.
