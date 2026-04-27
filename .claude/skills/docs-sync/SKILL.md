---
name: docs-sync
description: >
  Keep documentation in sync after code changes.
  Run after any change that alters module behaviour, APIs, env vars, or architecture.
triggers:
  - "update the docs"
  - "sync documentation"
  - after any new endpoint, model, env var, or agent capability
  - after any removal or deprecation
references:
  - docs/
  - CLAUDE.md
  - README.md
---

# Skill: docs-sync

## When to Use

Run this skill after any change that:
- Adds or removes a FastAPI endpoint
- Adds or removes an environment variable
- Changes agent capabilities or planner/executor/verifier behaviour
- Changes model routing logic or adds a new model
- Adds a new dependency to `requirements.txt`
- Modifies the admin dashboard or Telegram bot

## Docs to Check After Each Change Type

| Change | Docs to update |
|--------|---------------|
| New endpoint | `README.md`, `docs/configuration-reference.md` |
| New env var | `README.md`, `docs/configuration-reference.md`, `.env.example` |
| New model or routing change | `docs/model-routing.md`, `router/CLAUDE.md` |
| New agent capability | `docs/features.md`, `agent/CLAUDE.md` |
| Admin dashboard change | `docs/admin-dashboard.md` |
| Telegram bot change | `docs/telegram-bot.md` |
| Architecture change | `docs/architecture/overview.md`, relevant ADR |
| New ADR decision | `docs/adrs/` — write a new ADR |
| New dependency | `docs/configuration-reference.md` if setup-relevant |
| Breaking change | `docs/changelog.md` `### Changed` or `### Removed` |

## Instructions

1. Identify which doc files need updating (use the table above).
2. Read the current doc file content.
3. Make the minimal accurate update.
4. Use clear present-tense language ("The proxy exposes..." not "The proxy will expose...").
5. Verify all code snippets and example commands still work after your changes.
6. Update `CLAUDE.md` (root or module-level) if the operating instructions changed.

## CLAUDE.md Update Rules

Root `CLAUDE.md` changes when:
- Key commands change
- New risky modules are introduced
- Skill-to-situation mapping changes
- Codebase structure changes significantly

Module `CLAUDE.md` changes when:
- Module invariants change
- New env vars are introduced
- Security surface changes

## ADR Guidelines

Write a new ADR in `docs/adrs/` when:
- A significant architecture decision is made
- A new technology or pattern is adopted
- An existing approach is replaced with something different

ADR filename: `NNN-short-title.md` where NNN is the next sequential number.

ADR template:
```markdown
# ADR NNN: <title>

**Status:** Accepted | Superseded by ADR NNN
**Date:** YYYY-MM-DD

## Context
Why is this decision needed?

## Decision
What was decided?

## Consequences
### Positive
### Negative / Trade-offs
### Neutral
```

## Acceptance Checks

- [ ] All relevant doc files updated
- [ ] No code examples in docs are stale
- [ ] CLAUDE.md updated if operating instructions changed
- [ ] ADR written if architecture decision was made
- [ ] Changelog updated
