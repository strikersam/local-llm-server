---
name: cooldown-resume
description: >
  Resume an interrupted AI coding session after token exhaustion, rate limiting,
  or process restart. Use when a session was interrupted mid-task.
triggers:
  - session was interrupted
  - token limit hit
  - rate limit / quota exhaustion
  - "resume from where we left off"
  - process restart during an AI coding session
  - "what was I doing?"
references:
  - .claude/state/agent-state.json
  - .claude/state/NEXT_ACTION.md
  - .claude/state/checkpoint.jsonl
  - docs/runbooks/auto-resume.md
  - scripts/ai_runner.py
---

# Skill: cooldown-resume

## When to Use

Use this skill immediately after:
- A coding session was interrupted by token exhaustion
- Rate limiting or quota exhaustion stopped a task
- A process restart wiped in-memory state
- You are starting a new session and need to continue previous work

## Instructions

### Step 1 — Read the checkpoint files

```bash
# Human-readable next action
cat .claude/state/NEXT_ACTION.md

# Machine-readable full state
cat .claude/state/agent-state.json

# Ordered log of completed steps
cat .claude/state/checkpoint.jsonl
```

Or use the AI runner:

```bash
python scripts/ai_runner.py status
```

### Step 2 — Assess the state

From `agent-state.json`, determine:
- `completed_steps` — what is already done (do NOT redo these)
- `next_step` — what to do next
- `changed_files` — what files were modified (check their current state)
- `pending_risks` — any known issues or blockers

### Step 3 — Verify changed files are correct

For each file in `changed_files`, read the current content to confirm
the change was fully applied (not half-written due to interruption).

If a file appears partially written:
1. Read the file fully.
2. Compare with what the step description says it should contain.
3. Complete or revert the partial change before continuing.

### Step 4 — Run tests to confirm baseline

```bash
pytest -x
```

If tests fail after resuming:
1. Read the test error carefully.
2. Check if it is related to a partial change from the interrupted session.
3. Fix the partial change, then re-run tests.

### Step 5 — Continue from `next_step`

Execute only the steps that are NOT in `completed_steps`.
After each sub-step completes, append to `.claude/state/checkpoint.jsonl`:

```json
{"ts":"<ISO8601>","step":"<step-id>","status":"done","detail":"<what was done>"}
```

And update `.claude/state/agent-state.json`:
- Move the step from plan to `completed_steps`
- Update `next_step` to the following step
- Update `last_updated`

### Step 6 — Use the watchdog for future sessions

For long tasks, start with the AI runner watchdog to get automatic resume:

```bash
python scripts/ai_runner.py start --session my-task "instruction here"
```

The watchdog monitors for interruptions and resumes automatically.
See `docs/runbooks/auto-resume.md` for full documentation.

## Idempotency Rules

- Never re-apply a step that is already in `completed_steps`.
- If a file already has the expected content, skip the write — do not overwrite.
- Use `git diff` to confirm a change was actually needed before applying.

## Acceptance Checks

- [ ] `agent-state.json` was read and current state understood
- [ ] `checkpoint.jsonl` reviewed to confirm which steps are truly done
- [ ] No completed step was repeated
- [ ] Tests pass after resuming
- [ ] `agent-state.json` updated with resumed progress
- [ ] `NEXT_ACTION.md` updated to reflect current next step
