# Runtime model

`local-llm-server` now treats agent execution as an explicit runtime concern.

## Runtime types

- **`internal_agent`** — built-in planner → executor → verifier → judge loop
- **CLI/sidecar runtimes** — OpenCode, Goose, Aider, Hermes, OpenHands
- **Future remote runtimes** — keep the same readiness contract

## Readiness contract

Before any runtime task starts, the server runs preflight validation for:

- required binaries
- required environment variables
- workspace existence + write access
- git availability for git-backed tasks
- runtime health

Failures return a structured readiness report instead of a raw PATH or subprocess error.

## P0 behavior change

- `/runtimes/{id}/run` now returns **412** when preflight fails.
- direct chat agent mode validates the selected runtime before queueing work.
