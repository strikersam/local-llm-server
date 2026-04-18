# Skill: resource-panel

## Purpose
Track, display, and summarise all **resources** consumed or produced during an agent session: files read/written, URLs fetched, tools called, tokens used, and external dependencies touched.

Inspired by Copilot's resource panel UI — gives operators a single-pane-of-glass view of what an agent actually touched.

## When to Use
- After any multi-step implementation task
- During code review to understand blast radius
- In CI to surface unexpected file or network access
- As a pre-commit audit

## Output Format

The resource panel is emitted as a fenced Markdown block:

```
╔══════════════════════════════════════════════════════╗
║                   RESOURCE PANEL                     ║
╠══════════════════════════════════════════════════════╣
║ FILES READ        │ 12 files                         ║
║ FILES WRITTEN     │ 5 files                          ║
║ URLS FETCHED      │ 3 URLs                           ║
║ TOOLS CALLED      │ Bash(8) Read(12) Write(5)        ║
║ EXTERNAL DEPS     │ npm:lodash, pip:requests         ║
╠══════════════════════════════════════════════════════╣
║ CHANGED FILES                                        ║
║   src/index.ts          [modified]                   ║
║   src/utils/parser.ts   [created]                    ║
║   tests/parser.test.ts  [created]                    ║
╠══════════════════════════════════════════════════════╣
║ URLS                                                 ║
║   https://example.com/api   [fetched]                ║
╚══════════════════════════════════════════════════════╝
```

## How to Use

### Ask Claude to emit a resource panel

At the end of your task prompt, add:
```
When done, emit a resource-panel summary following .claude/skills/resource-panel/SKILL.md
```

### Automated via shell (git-based)

```bash
bash .claude/skills/resource-panel/summarise.sh
```

This script uses `git diff --name-only` and `git status` to auto-generate the panel for the current working tree.

## Fields

| Field | Source |
|---|---|
| Files Read | Tool calls: `Read`, `Glob`, `Grep` |
| Files Written | Tool calls: `Write`, `Edit`, `MultiEdit` |
| URLs Fetched | Tool calls: `WebFetch`, `WebSearch` |
| Tools Called | All tool invocations, grouped by type |
| External Deps | New entries in `package.json`, `requirements.txt`, `go.mod`, etc. |
| Changed Files | `git diff --name-status HEAD` |

## Integration

Pair with:
- **`dependency-audit`** — for deep analysis of new deps
- **`risky-module-review`** — flag high-risk touched files
- **`changelog-enforcer`** — ensure all written files have changelog entries
- **`task-alive-updates`** — show resource panel at end of long-running task

## Files

- `SKILL.md` — this file
- `summarise.sh` — auto-generate panel from git state
