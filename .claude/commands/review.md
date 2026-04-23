# Command: /review

**Trigger:** `/review` or `/review <file-or-diff>`

Invoke the council-review skill against the current staged changes or a specified file.

## What It Does

1. Reads the current diff (`git diff --cached` or `git diff HEAD`)
2. Runs all four reviewer roles: Security, Correctness, Performance, Maintainability
3. Produces a council verdict
4. Writes verdict to `.claude/state/last-review.json`

## Usage

```
/review                          # Review all staged changes
/review agent/tools.py           # Review a specific file
/review HEAD~3                   # Review last 3 commits
```

## References

- `.claude/agents/reviewer.md`
- `.claude/skills/council-review/SKILL.md`
