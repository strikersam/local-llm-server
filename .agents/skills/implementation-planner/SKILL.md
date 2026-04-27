---
name: implementation-planner
description: >
  Plan a multi-file or multi-step implementation before writing any code.
  Use before any change touching more than two files, adding a new feature,
  or changing a module interface.
triggers:
  - "implement X"
  - "add feature"
  - "refactor Y"
  - "design the approach for"
  - any change to proxy.py, agent/loop.py, router/model_router.py, or chat_handlers.py
references:
  - AGENTS.md
  - docs/architecture/overview.md
  - docs/adrs/
---

# Skill: implementation-planner

## When to Use

Use this skill **before writing any code** when:
- The change touches more than 2 files
- A new endpoint, agent capability, or routing behaviour is being added
- The approach is not obvious from the existing code structure
- You are unsure whether a change will break existing tests

## Instructions

### Step 1 — Understand the current state
1. Read the relevant module `AGENTS.md` if one exists.
2. Run `pytest -x` to confirm the baseline is green.
3. Read the key files you expect to touch.

### Step 2 — Write the plan
Produce a plan in this structure:

```
## Goal
One sentence: what does this change accomplish?

## Approach
2-3 sentences: the technical approach chosen and why.

## Files to change
- `path/to/file.py` — what changes and why
- `tests/test_something.py` — new or updated tests

## Files to read first
- `path/to/related.py` — to understand the interface

## Risks
- Any behaviour that might regress
- Any risky module being touched (triggers risky-module-review skill)

## Acceptance checks
- [ ] pytest -x passes
- [ ] changelog entry added
- [ ] no hardcoded secrets
- [ ] new tests cover the new behaviour
```

### Step 3 — Get implicit approval before coding
If the plan involves a risky module (auth, key store, agent tools), invoke the
`risky-module-review` skill before proceeding.

### Step 4 — Implement
Follow the plan step by step. Update the plan if reality diverges from the
written plan (annotate with `# REVISED:` comments).

### Step 5 — Verify
After implementing:
1. Run `pytest -x`.
2. If tests fail, fix and re-run before reporting done.
3. Update `docs/changelog.md`.
4. Update `.Codex/state/agent-state.json` with completed steps.

## Acceptance Checks

- [ ] Plan was written before implementation
- [ ] All listed files were changed
- [ ] All tests pass
- [ ] Changelog updated
- [ ] No risky module changed without risky-module-review

## Failure / Retry Behaviour

If a step fails (syntax error, test failure, unexpected interface):
1. Do NOT silently swallow the failure.
2. Annotate the plan with the failure.
3. Diagnose before retrying — read the error carefully.
4. If blocked, write the blocker to `.Codex/state/NEXT_ACTION.md` and stop cleanly.
