# Command: /resume

**Trigger:** `/resume`

Resume an interrupted AI coding session from the last checkpoint.

## What It Does

1. Reads `.claude/state/agent-state.json` to find the last saved state
2. Reads `.claude/state/checkpoint.jsonl` to confirm completed steps
3. Verifies changed files are intact (not partially written)
4. Runs `pytest -x` to confirm baseline
5. Continues from the recorded `next_step`

## Usage

```
/resume                          # Resume from .claude/state/NEXT_ACTION.md
```

## References

- `.claude/agents/` — all agent definitions
- `.claude/skills/cooldown-resume/SKILL.md`
- `docs/runbooks/auto-resume.md`
- `scripts/ai_runner.py resume`
