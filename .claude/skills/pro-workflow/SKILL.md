---
name: pro-workflow
description: >
  Core AI coding workflow. Orchestrates 8 patterns: Scout → Plan → Implement → Review,
  with smart commits, session rituals, and continuous learning capture.
  This is the master skill — invoke it at the start of any non-trivial task.
triggers:
  - "start working on"
  - "implement this feature"
  - "let's build"
  - "help me with this task"
  - any task touching more than 1 file
  - any task with unclear scope
references:
  - CLAUDE.md
  - .claude/agents/scout.md
  - .claude/agents/planner.md
  - .claude/agents/reviewer.md
  - .claude/state/
---

# Skill: pro-workflow

## The 8 Core Patterns

| # | Pattern | Skill |
|---|---------|-------|
| 1 | Scout before you implement | `scout` agent |
| 2 | Plan before you code | `implementation-planner` |
| 3 | Test first | `test-first-executor` |
| 4 | Review before merge | `council-review` |
| 5 | Commit with quality gates | `smart-commit` |
| 6 | Persist corrections | `learn-rule` |
| 7 | Surface past patterns | `replay-learnings` |
| 8 | Hand off cleanly | `wrap-up` + `session-handoff` |

---

## Workflow: Research → Plan → Implement

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│  RESEARCH   │────▶│    PLAN     │────▶│   IMPLEMENT     │
│             │     │             │     │                 │
│ Scout scores│     │ Planner     │     │ Phased execution│
│ readiness.  │     │ breaks down │     │ Reviewer gates  │
│ GO / HOLD   │     │ steps.      │     │ each checkpoint │
└─────────────┘     └─────────────┘     └─────────────────┘
       │                   │                     │
  Validation          Validation            Validation
  gate: must          gate: must            gate: must
  pass before         pass before           pass before
  proceeding          proceeding            merge
```

**Validation gate between each phase — must pass before proceeding.**

---

## Instructions

### Phase 1 — Research (Scout)

1. Invoke the Scout agent with the task description.
2. If Scout returns **HOLD**: resolve each gap, then re-score.
3. If Scout returns **GO**: proceed to Phase 2.

```
Scout checklist:
- [ ] Score ≥ 70 (GO verdict)
- [ ] Context mode selected (DEV / REVIEW / RESEARCH)
- [ ] No unresolved gaps
```

### Phase 2 — Plan

1. Run the `implementation-planner` skill (or `/plan` command).
2. Review the plan for risky modules — invoke `risky-module-review` if flagged.
3. Check `replay-learnings` for relevant past patterns before accepting the plan.

```
Plan checklist:
- [ ] Plan produced with ordered steps
- [ ] Risky modules flagged and reviewed
- [ ] Past learnings consulted
- [ ] Max 10 steps (split if more)
```

### Phase 3 — Implement

1. Execute plan steps one at a time.
2. After each file change, Reviewer agent validates before writing.
3. Run `pytest -x` after each logical group of changes.
4. Run `deslop` skill before final commit to remove AI code slop.
5. Run `smart-commit` to gate and commit.

```
Implement checklist:
- [ ] Reviewer passed each file change
- [ ] pytest -x green after each step
- [ ] docs/changelog.md updated
- [ ] deslop run before commit
- [ ] smart-commit used for final commit
```

### Phase 4 — Wrap Up

1. Run `council-review` if changes are > 50 lines or touch risky modules.
2. Run `wrap-up` skill to close the session.
3. Run `learn-rule` to persist any corrections from this session.
4. Run `session-handoff` to write resume docs for the next session.

---

## Model Selection Guide

Use the right Claude model for the task type:

| Task | Model |
|------|-------|
| Quick fixes, typos, config changes | Haiku 4.5 |
| New features, standard implementations | Sonnet 4.6 (adaptive thinking) |
| Refactors, structural changes | Opus 4.6 (adaptive thinking) |
| Architecture decisions, ADR writing | Opus 4.6 (1M context) |
| Hard bugs, deep debugging | Opus 4.6 (1M context) |

---

## Acceptance Checks

- [ ] Scout scored ≥ 70 before implementation started
- [ ] Plan was produced and reviewed
- [ ] All tests pass
- [ ] Changelog updated
- [ ] Commit made with `smart-commit`
- [ ] Session closed with `wrap-up`
