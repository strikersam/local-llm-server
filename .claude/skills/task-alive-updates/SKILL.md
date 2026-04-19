# Skill: task-alive-updates

## Purpose
Keep long-running agent tasks visibly alive by emitting periodic heartbeat status updates to stdout. Prevents silent timeouts and gives the operator confidence the task is still progressing.

## When to Use
- Any task expected to run longer than 2 minutes
- Background agent loops (e.g., `parallel-agents`, `agent-harness`)
- CI-style workflows where no output = assumed dead

## How It Works

1. **Heartbeat interval**: Every 30 seconds of inactivity, emit a status line.
2. **Status line format**:
   ```
   [ALIVE] <timestamp> | step: <current_step> | elapsed: <Xs> | status: <message>
   ```
3. **Completion signal**: On finish, emit:
   ```
   [DONE] <timestamp> | elapsed: <Xs> | result: <success|failure>
   ```

## Usage

### In a shell script / agent harness

```bash
# Source the heartbeat helper
source .claude/skills/task-alive-updates/heartbeat.sh

# Start heartbeat (fires every 30s in background)
heartbeat_start "running implementation plan"

# ... do your work ...

heartbeat_stop "success"
```

### In Claude task descriptions

Prepend your task prompt with:
```
<task-alive-updates interval="30" />
Emit [ALIVE] lines every 30 seconds while working on: ...
```

## Implementation Rules

- NEVER suppress stdout during long operations
- Always call `heartbeat_stop` in a trap/finally pattern
- The heartbeat message should reflect the **current step name**, not a generic string
- Timestamps must be ISO-8601

## Integration with parallel-agents

When used inside `parallel-agents`, each worker emits its own heartbeat prefixed with its worker ID:
```
[ALIVE][worker-2] 2025-01-15T10:23:45Z | step: test-suite | elapsed: 47s
```

## Files

- `SKILL.md` — this file
- `heartbeat.sh` — bash helper (source this in shell-based agents)

## Example Output

```
[ALIVE] 2025-01-15T10:21:00Z | step: installing-deps | elapsed: 30s | status: npm install running
[ALIVE] 2025-01-15T10:21:30Z | step: running-tests   | elapsed: 60s | status: 142/300 tests passed
[DONE]  2025-01-15T10:22:15Z | elapsed: 105s          | result: success
```
