# Feature Maturity Matrix

> **Single source of truth:** `features/matrix.py`
>
> The tables below reflect the registry in that file.  For the full API
> representation, call `GET /admin/api/features` (admin auth required).

See [docs/support-matrix.md](../support-matrix.md) for the full human-readable
support matrix including recommended production configuration and operator
override instructions.

---

## Tiers

| Tier | Enforcement |
|------|------------|
| `stable` | No warnings; gated only by config |
| `beta` | WARNING log on first use; available by default |
| `experimental` | WARNING log; disabled by default; opt-in via `FEATURE_ENABLE` |
| `disabled` | Cannot be enabled at all |

---

## Quick reference

### Stable core

- proxy endpoints, auth, rate limiting, provider routing, model routing,
  key management, direct chat, local runtime, Langfuse observability

### Beta

- async agent jobs, planner/verifier/judge pipeline, workspace isolation,
  runtime preflight, task-harness runtime, aider, hermes, per-job progress,
  Telegram bot, tunnel, admin command runner

### Experimental

- jcode, OpenHands, OpenCode, Goose, social auth, multi-agent swarm,
  CRISPY workflow engine

---

## Rule

Unstable integrations must fail in preflight or stay behind explicit
runtime selection rather than failing late during execution.
