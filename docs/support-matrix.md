# Feature Support Matrix

This document is generated from the single source of truth in `features/matrix.py`.

## Maturity Tiers

| Tier | Meaning | Recommended for Production |
|------|---------|---------------------------|
| **stable** | Fully tested, production-ready, no known major issues | ✅ Yes |
| **beta** | Functional but may have edge cases or behavioral changes | ⚠️ With caution |
| **experimental** | Proof-of-concept, may be unstable or incomplete | ❌ Not recommended |
| **disabled** | Turned off, cannot be used without explicit override | ❌ No |

## Feature Matrix

<!-- AUTO-GENERATED from features/matrix.py -->

| Feature | ID | Maturity | Enabled | Dependencies | Config Flags | Notes |
|---------|----|----------|---------|--------------|-------------|-------|
| Direct Chat | `direct_chat` | stable | ✅ | Ollama or cloud provider | — | Core synchronous chat feature. |
| OpenAI API Compatibility | `openai_compat` | stable | ✅ | Ollama | — | /v1/ chat completions endpoint. |
| Anthropic API Compatibility | `anthropic_compat` | stable | ✅ | Ollama | — | /v1/messages endpoint for Claude Code etc. |
| Ollama Native Passthrough | `ollama_passthrough` | stable | ✅ | Ollama | — | /api/* endpoints. |
| Multi-User Key Management | `key_management` | stable | ✅ | — | KEYS_FILE, API_KEYS | |
| Provider Routing & Fallback | `provider_routing_fallback` | stable | ✅ | — | PROVIDER_COOLDOWN_SECONDS | Timeout/cooldown/failover for providers. |
| Rate Limiting | `rate_limiting` | stable | ✅ | — | RATE_LIMIT_RPM | Per-key RPM limiting. |
| Runtime Preflight Validation | `runtime_preflight` | stable | ✅ | — | — | Structured readiness checks before execution. |
| Admin Dashboard | `admin_dashboard` | stable | ✅ | — | ADMIN_SECRET | |
| Langfuse Observability (Direct Chat) | `observability_langfuse` | stable | ✅ | Langfuse account | LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY | Traces + cost metadata. |
| Workspace Isolation | `workspace_isolation` | stable | ✅ | — | WORKSPACE_BASE_ROOT, WORKSPACE_RETENTION_TTL_SECONDS | Per-session/job isolated workspaces with manifests. |
| Planner / Executor / Verifier Pipeline | `agent_planner_executor_verifier` | stable | ✅ | Ollama or cloud provider | AGENT_PLANNER_MODEL, AGENT_EXECUTOR_MODEL, AGENT_VERIFIER_MODEL | Three-role plan-execute-verify loop. |
| Judge (Release Gate) | `agent_judge` | stable | ✅ | Ollama or cloud provider | AGENT_JUDGE_MODEL | Quality gate after verification. |
| Local Runtime (internal_agent) | `local_runtime` | stable | ✅ | — | RUNTIME_DEFAULT | Built-in agent loop, always available. |
| Local-First Model Routing | `local_model_routing` | stable | ✅ | Ollama | — | |
| Async Agent Jobs | `async_agent_jobs` | beta | ✅ | Agent runtime | DIRECT_CHAT_AGENT_WORKSPACE_ROOT | Agent mode returns 202 + pollable job ID. |
| Runtime Readiness Diagnostics | `runtime_readiness_diagnostics` | beta | ✅ | — | — | Preflight validation with structured issues. |
| Policies & Governance | `policies_governance` | beta | ✅ | — | — | Approval gates, RBAC, admin controls. |
| CRISPY Workflow Engine | `crispy_workflow` | beta | ✅ | — | CRISPY_ARTIFACTS_ROOT | Structured build workflow with approval gates. |
| Task-Harness Runtime | `task_harness_runtime` | beta | ✅ | task-harness binary | TASK_HARNESS_REQUIRED, TASK_HARNESS_BIN | Requires external harness binary. |
| OpenHands Runtime | `openhands_runtime` | experimental | ❌ | Docker, OpenHands image | OPENHANDS_ENABLED | Opt-in, requires Docker. Set OPENHANDS_ENABLED=true. |
| Sidecar Runtimes (Hermes/OpenCode/Goose) | `sidecar_runtimes` | experimental | ✅ | Sidecar process running | — | Registered but may be unhealthy if sidecar is not running. |
| Telegram Bot | `telegram_bot` | experimental | ✅ | Telegram Bot Token | TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS | Remote control via Telegram. |
| Tunnels (Cloudflare/ngrok) | `tunnels` | experimental | ✅ | cloudflared or ngrok | NGROK_AUTH_TOKEN, CLOUDFLARED_EXE | Exposes proxy over HTTPS. |
| Multi-Agent / Swarm | `multi_agent_swarm` | experimental | ✅ | — | — | Agent coordination and swarm dispatch. |
| OpenClaw Integration | `openclaw_integration` | experimental | ✅ | OpenClaw | — | Maintenance: vulnerability fixes, code scans. |
| JCode Runtime | `jcode_runtime` | experimental | ✅ | JCode | — | JCode execution runtime. |
| Quick Actions / iOS Shortcuts | `quick_actions_ios` | experimental | ✅ | — | — | iOS Shortcuts integration for remote commands. |
| Machine Sync / Peer Sync | `machine_peer_sync` | experimental | ✅ | — | — | Sync service for multi-machine coordination. |

## Config Overrides

Any feature can be overridden via environment variables:

```bash
# Disable a feature
FEATURE_TELEGRAM_BOT=disabled

# Change a feature's maturity
FEATURE_ASYNC_AGENT_JOBS=stable

# Enable/disable explicitly
FEATURE_OPENHANDS_RUNTIME=true
FEATURE_SIDECAE_RUNTIMES=false
```

The environment variable pattern is `FEATURE_<UPPERCASE_FEATURE_ID>`.

## Admin API

The support matrix is exposed at:

- `GET /admin/features` — full matrix with summary
- `GET /admin/features/{feature_id}` — single feature details + warnings
- `POST /admin/features/check` — check if a feature is available

## Gating Behavior

- **disabled** features: code calling `matrix.check_available(feature_id)` receives a `FeatureUnavailableError` with structured `code`, `feature_id`, `maturity`, `reason`, and `fix_hint`.
- **beta/experimental** features: `matrix.maturity_warning(feature_id)` returns a warning string. API responses include a `warning` field.
- **enabled + stable** features: no warnings, normal operation.
