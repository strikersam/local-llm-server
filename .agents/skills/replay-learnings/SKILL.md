---
name: replay-learnings
description: >
  Surface relevant past patterns before starting work. Read the learnings file and
  extract rules that apply to the current task. Prevents repeating past mistakes.
triggers:
  - "what have we learned about"
  - "replay learnings"
  - "what mistakes did we make before"
  - "remind me of past patterns"
  - at the start of a new session
  - before starting any task in a familiar area
references:
  - .claude/state/learnings.md
  - .claude/state/checkpoint.jsonl
  - .claude/state/agent-state.json
---

# Skill: replay-learnings

## When to Use

Run this skill:
- At the **start of a new session** before touching any code
- Before working on a module you've touched before
- After `cooldown-resume` loads the checkpoint (learnings provide extra context)
- When the user asks "what did we learn about X?"

---

## Instructions

### Step 1 — Read the learnings file

```bash
cat .claude/state/learnings.md
```

If the file doesn't exist, skip to Step 3 (no learnings yet).

### Step 2 — Filter relevant learnings

From all entries, extract those relevant to the current task. Match by:
- **Module name** — does the learning mention a file you're about to touch?
- **Operation type** — does the learning apply to commits, auth, routing, tests?
- **Keyword overlap** — does the learning's situation match the current context?

Present the relevant learnings as a short list:

```
Relevant learnings for this task:
- [2026-03-15] Never use git add -A — stage specific files only.
- [2026-03-22] Always read router/CLAUDE.md before touching model_router.py.
- [2026-04-01] risky-module-review is required for admin_auth.py even for 1-line changes.
```

### Step 3 — Check recent checkpoint history

```bash
tail -20 .claude/state/checkpoint.jsonl 2>/dev/null || echo "No checkpoint history."
```

Look for patterns:
- Steps that were retried (same step_id appearing twice)
- Steps that failed
- Any "partial" status entries

### Step 4 — Surface blockers from previous session

```bash
cat .claude/state/NEXT_ACTION.md 2>/dev/null || echo "No next action file."
```

Check for documented blockers that are still unresolved.

### Step 5 — Apply relevant rules

Before starting work, briefly confirm which rules apply:

```
Applying rules from learnings:
✓ Will stage specific files (not git add -A)
✓ Will read router/CLAUDE.md before touching routing code
✓ Will invoke risky-module-review for auth module
```

---

## Learnings File Doesn't Exist?

This is expected on a fresh clone. The file is created by `learn-rule` and `wrap-up`.
Start working, and the learnings will accumulate over time.

---

## Acceptance Checks

- [ ] `.claude/state/learnings.md` read (or confirmed absent)
- [ ] Relevant rules identified for the current task
- [ ] Recent checkpoint history reviewed
- [ ] Any previous blockers from `NEXT_ACTION.md` noted
- [ ] Rules applied (stated explicitly before starting work)
