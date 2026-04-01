# Runbook: Auto-Resume After Cooldown / Interruption

## Overview

AI coding sessions in this repo are designed to survive interruption. When a session is
interrupted by token exhaustion, rate limiting, quota errors, or process restart, it can
be resumed automatically from the exact next unfinished step.

## How It Works

### State Persistence

Every meaningful step writes to two files:

1. **`.claude/state/agent-state.json`** — Full session state including:
   - `session_id`, `objective`, `status`
   - `plan` (list of all steps with status)
   - `completed_steps` (list of done step IDs)
   - `next_step` (the exact step to execute on resume)
   - `changed_files` (all files modified so far)
   - `cooldown_until` (ISO8601 if rate-limited)

2. **`.claude/state/checkpoint.jsonl`** — Append-only log of completed steps.
   Each line: `{"ts":"...", "step":"<id>", "status":"done|failed", "detail":"..."}`
   This log is the source of truth for what has actually been completed.

### Cooldown Detection

The AI runner (`scripts/ai_runner.py`) monitors for these signals:
- Exit codes 1 or 2 from the claude CLI
- Patterns in output: `rate.?limit`, `429`, `529`, `overloaded`, `quota.?exceeded`, etc.

When a cooldown is detected, the runner:
1. Writes `status: "cooldown"` and `cooldown_until` to `agent-state.json`
2. Waits using exponential backoff: 60s → 120s → 240s → 480s → 960s
3. Retries the session up to 5 times

### Resume Logic

On resume:
1. Reads `agent-state.json` for the `next_step`
2. Reads `checkpoint.jsonl` to find all `status: "done"` step IDs
3. Skips any step whose ID is already in the checkpoint log
4. Continues from the first step NOT in the completed set

This ensures **idempotency**: resuming twice doesn't corrupt the repo.

## Commands

```bash
# Check current state
python scripts/ai_runner.py status

# Resume interrupted session
python scripts/ai_runner.py resume

# Start a new session
python scripts/ai_runner.py start --session my-task "implement X"

# Stop current session
python scripts/ai_runner.py stop

# Tail session logs
python scripts/ai_runner.py logs --tail 100

# Run simulation proof
python scripts/ai_runner.py test-resume
```

Or via Makefile:

```bash
make ai-status
make ai-resume
make ai-start
make ai-stop
make ai-logs
```

## Inspecting a Stuck Run

If a run appears stuck:

1. Check the lock file: `cat .claude/state/runner.lock`
   - If it exists and the PID is not running, the lock is stale.
   - Remove with: `rm .claude/state/runner.lock`

2. Check the state: `python scripts/ai_runner.py status`

3. Check logs: `python scripts/ai_runner.py logs --tail 50`

4. Check the checkpoint log: `cat .claude/state/checkpoint.jsonl`

## Force-Resume After Stale Lock

```bash
rm .claude/state/runner.lock
python scripts/ai_runner.py resume
```

## Forcing an Abort

```bash
python scripts/ai_runner.py stop
# Or manually:
rm .claude/state/runner.lock
# Update state manually if needed:
python3 -c "
import json
state = json.load(open('.claude/state/agent-state.json'))
state['status'] = 'aborted'
json.dump(state, open('.claude/state/agent-state.json', 'w'), indent=2)
print('Aborted.')
"
```

## Cooldown Detection Logic

The runner checks for these patterns (case-insensitive regex) in session output:
```
rate.?limit
quota.?exceeded
token.?limit
overloaded
529
429
context.?window
max.?tokens
cooldown
```

If any match → exponential backoff → retry.

## What Requires Human Intervention

Some failures cannot be auto-resumed:
- `PLAN_BLOCKED` — planner couldn't understand the instruction
- `max_retries_exceeded` — cooldown retries exhausted (check API quota)
- `failed` steps that need human diagnosis
- Partial file writes detected on resume (read the file, assess manually)

In these cases, `python scripts/ai_runner.py status` will show the `status` field.
Fix the underlying issue, update the state manually, then run `resume`.

## Simulation Proof

Run this to verify the resume system works end-to-end:

```bash
python scripts/ai_runner.py test-resume
```

Expected output:
```
SIMULATION RESULT: PASS
Checkpoint persisted → cooldown waited → state reloaded → correct step resumed
No duplicate edits: step-one was skipped (already in checkpoint log)
```
