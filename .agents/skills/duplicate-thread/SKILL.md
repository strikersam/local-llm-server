# Skill: duplicate-thread

## Purpose
Clone an existing plan, task thread, or agent session so you can explore an **alternative approach** without losing the original. Analogous to "duplicate thread" in Copilot's mission control.

## When to Use
- You want to try a risky refactor without throwing away the current plan
- A/B testing two implementation strategies in parallel
- Resuming a stalled task from a known-good checkpoint with different parameters
- Forking a plan for a different target environment (e.g., prod vs. staging)

## How It Works

1. **Identify the source thread** — a `.claude/threads/<id>/` directory, a plan file, or a PLAN.md
2. **Copy it** to a new thread ID with a meaningful suffix
3. **Stamp it** with metadata (source thread, fork reason, timestamp)
4. **Continue** in the new thread independently

## Thread Directory Convention

```
.claude/threads/
  <thread-id>/
    PLAN.md          # the plan or task description
    CONTEXT.md       # accumulated context
    CHECKPOINT.md    # last known-good state (from checkpoint-strategy skill)
    meta.json        # thread metadata
```

## Usage

### Manual duplication

```bash
bash .claude/skills/duplicate-thread/duplicate.sh <source-thread-id> <reason>
```

**Example:**
```bash
bash .claude/skills/duplicate-thread/duplicate.sh plan-2025-01-15 "try-async-approach"
# Creates: .claude/threads/plan-2025-01-15--fork-try-async-approach/
```

### In a Claude prompt

```
Duplicate the current thread as "alternative-auth-strategy" and in the fork,
replace the JWT approach with session cookies. Keep the original intact.
```

Claude will:
1. Copy the current `PLAN.md` / `CONTEXT.md` to a new thread folder
2. Apply the requested change only in the fork
3. Proceed with the forked version, noting the original thread ID in `meta.json`

## meta.json Schema

```json
{
  "thread_id": "plan-2025-01-15--fork-try-async-approach",
  "forked_from": "plan-2025-01-15",
  "fork_reason": "try-async-approach",
  "forked_at": "2025-01-15T10:30:00Z",
  "status": "active"
}
```

## Merging Back

If the fork succeeds and you want to merge learnings back:
1. Compare `PLAN.md` diffs between fork and original
2. Update the original `CONTEXT.md` with lessons learned
3. Archive the fork: set `"status": "merged"` in `meta.json`

If the fork fails:
1. Set `"status": "abandoned"` in `meta.json`
2. Return to the original thread — it is untouched

## Integration

Pairs well with:
- **`checkpoint-strategy`** — always checkpoint before duplicating
- **`parallel-agents`** — run both threads simultaneously and compare
- **`council-review`** — have the council evaluate both approaches and pick the winner
- **`cooldown-resume`** — resume a forked thread after a pause

## Files

- `SKILL.md` — this file
- `duplicate.sh` — shell helper to copy a thread
