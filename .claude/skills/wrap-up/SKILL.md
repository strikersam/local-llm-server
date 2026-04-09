---
name: wrap-up
description: >
  Session closing ritual with learning capture. Run at the end of every coding session.
  5 steps: changes audit, quality check, learning capture, next session planning, summary.
triggers:
  - "wrap up"
  - "end of session"
  - "I'm done for now"
  - "let's wrap"
  - session is ending
  - "summarize what we did"
references:
  - .claude/state/agent-state.json
  - .claude/state/NEXT_ACTION.md
  - .claude/state/checkpoint.jsonl
  - .claude/state/learnings.md
---

# Skill: wrap-up

## When to Use

Run at the end of every coding session — whether work is complete or paused.
This ritual ensures nothing is lost, lessons are captured, and the next session
can start immediately without archaeology.

---

## The 5-Step Wrap-Up Ritual

### Step 1 — Changes Audit

Review everything that happened this session:

```bash
git status                      # uncommitted changes
git diff --stat HEAD            # what changed vs last commit
git log --oneline -10           # commits made this session
```

**Check for:**
- Uncommitted changes that should be committed (use `smart-commit`)
- Uncommitted changes that should be discarded
- TODOs left in code (`grep -r "TODO\|FIXME\|HACK" --include="*.py" .`)
- Any `.claude/state/` files that need updating

---

### Step 2 — Quality Check

```bash
pytest -x                       # tests must pass
python -m py_compile proxy.py   # syntax check main file
```

If tests fail: either fix now or document the failure in NEXT_ACTION.md as a blocker.

**Do not leave the session with silently broken tests.**

---

### Step 3 — Learning Capture

For each meaningful correction, mistake, or discovery this session, append to
`.claude/state/learnings.md`:

```markdown
## <date> — <short title>

**Context:** What was being worked on.
**Mistake / Discovery:** What went wrong or what was learned.
**Correction:** What the right approach is.
**Pattern:** One-line rule to remember (e.g., "Always read router/CLAUDE.md before touching model_router.py").
```

Create the file if it doesn't exist. Even 1 learning per session compounds over time.

---

### Step 4 — Next Session Planning

Update `.claude/state/NEXT_ACTION.md` with a clear resume guide:

```markdown
# Next Action

**Objective:** <what are we building?>
**Status:** <COMPLETE | IN PROGRESS | BLOCKED>
**Last completed:** <step or task just finished>

## If Resuming: Start Here

1. Read: <file to read first>
2. Run: `pytest -x` to confirm baseline
3. Then: <exact next action>

## Blockers

- <any known blockers or dependencies>

## Optional Next Steps

- <lower priority work to do after the main task>
```

Also update `.claude/state/agent-state.json`:
- Set `next_step` to the next action
- Set `last_updated` to current ISO8601 timestamp

---

### Step 5 — One-Paragraph Summary

Write a single paragraph that any developer (or AI) could read to instantly
understand what happened this session. Output it to the user as the final
message of the session.

**Include:**
- What was the goal
- What was accomplished
- What was skipped or deferred
- Any important decisions made
- What comes next

**Example:**
> Added Scout agent and 9 missing skills (pro-workflow, smart-commit, wrap-up, learn-rule,
> parallel-worktrees, replay-learnings, session-handoff, insights, deslop) to the .claude/
> system. Updated CLAUDE.md with the new skill table and model selection guide. All tests
> pass. Next: push to `claude/improve-repo-docs-9Q3eO` and verify CI is green.

---

## Acceptance Checks

- [ ] `git status` reviewed — no unintended uncommitted changes
- [ ] `pytest -x` green (or failure documented as blocker)
- [ ] At least one learning captured in `.claude/state/learnings.md`
- [ ] `NEXT_ACTION.md` updated with clear resume instructions
- [ ] `agent-state.json` `next_step` and `last_updated` updated
- [ ] One-paragraph summary written
