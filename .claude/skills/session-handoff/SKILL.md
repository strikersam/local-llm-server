---
name: session-handoff
description: >
  Write structured resume documentation for the next session. Captures state,
  context, and next actions so any AI or developer can continue without archaeology.
triggers:
  - "write a handoff"
  - "prepare for next session"
  - "I need to stop, document where we are"
  - "handoff doc"
  - end of a long session
  - before switching contexts
references:
  - .claude/state/NEXT_ACTION.md
  - .claude/state/agent-state.json
  - .claude/state/checkpoint.jsonl
  - .claude/state/learnings.md
---

# Skill: session-handoff

## When to Use

Use this skill when:
- Pausing mid-task and planning to resume later
- Handing off to a different AI session or developer
- A task is too large to finish in one session
- You want a clean resume point before a context window reset

This is more detailed than `wrap-up` — it focuses on producing a handoff artifact
that another session can use to continue without asking any questions.

---

## Instructions

### Step 1 — Capture current state

Gather the raw facts:

```bash
git status                          # what's staged / unstaged
git log --oneline -5                # recent commits
git stash list                      # any stashes
cat .claude/state/agent-state.json  # machine state
tail -30 .claude/state/checkpoint.jsonl  # recent steps
```

### Step 2 — Write the handoff document

Update `.claude/state/NEXT_ACTION.md` with the full handoff:

```markdown
# Session Handoff

**Date:** YYYY-MM-DD HH:MM
**Branch:** <current branch>
**Objective:** <one sentence — what is being built?>

---

## What Was Accomplished This Session

- <completed item 1>
- <completed item 2>
- <completed item 3>

## Current State

**Working tree:** <clean | N files modified | N staged>
**Tests:** <passing | failing — see blockers>
**Last commit:** `<hash> <message>`

## Exactly Where We Left Off

<Describe the precise stopping point. Include file name and line number if mid-edit.>

## Next Actions (in order)

1. **First:** `<exact command or action>`
2. **Then:** `<next action>`
3. **Finally:** `<last action to complete the task>`

## Blockers

- <blocker 1 — what is it and why is it blocking?>
- None (if clear)

## Key Decisions Made

- **Decision:** <what was decided>  **Reason:** <why>
- <repeat for each significant decision>

## Files Changed This Session

| File | Change |
|------|--------|
| `path/to/file.py` | Added X, modified Y |

## Do Not Touch

- `<file>` — in progress, half-written
- `<module>` — requires risky-module-review before any changes

## Context for Next Session

<2–3 sentences of context that would take 10 minutes to re-derive.
Include any gotchas, unexpected behaviour, or things that will matter.>
```

### Step 3 — Update machine-readable state

```bash
# Update agent-state.json
```

Set in `.claude/state/agent-state.json`:
- `status`: `"paused"`
- `next_step`: next action (from Step 2 above)
- `last_updated`: current ISO8601 timestamp
- `pending_risks`: any known risks to carry forward

### Step 4 — Confirm the handoff is self-contained

Ask: "Could another session read only `NEXT_ACTION.md` and continue without asking questions?"

If no: add the missing context.

---

## Acceptance Checks

- [ ] `NEXT_ACTION.md` written with all sections complete
- [ ] Next actions are numbered and specific (not vague)
- [ ] Blockers explicitly listed (or "None")
- [ ] Files changed this session listed
- [ ] `agent-state.json` updated with `status: "paused"` and `next_step`
- [ ] Handoff is self-contained — next session needs no archaeology
