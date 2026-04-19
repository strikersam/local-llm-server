# Skill: prompt-library

## Purpose
Maintain a structured, versioned library of the prompts and behavioral templates
used by agents in this repository. Inspired by CL4R1T4S's approach of collecting
and publishing AI system prompts for community benefit.

This skill creates a `prompts/` directory that serves as a transparent, browsable
record of every behavioral instruction set active in the project.

## When to Use
- When adding a new agent or skill (to register it in the library)
- When updating existing agent behavior (to snapshot the change)
- When generating documentation for external contributors
- As part of `wrap-up` to ensure library stays current

## Directory Structure Created

```
prompts/
  README.md                    ← Library index and guide
  agents/
    implementer.md             ← Snapshot of implementer agent prompt
    judge.md
    planner.md
    reviewer.md
    scout.md
  skills/
    <skill-name>.md            ← Snapshot of each skill's behavioral spec
  commands/
    plan.md
    resume.md
    review.md
  CHANGELOG.md                 ← History of prompt changes
  TRANSPARENCY.md              ← Plain-language explanation of all active behaviors
```

## Steps

### 1. Sync Snapshots
Copy current content from `.claude/agents/`, `.claude/skills/*/SKILL.md`,
and `.claude/commands/` into the `prompts/` mirror directory.

Add a header to each snapshot:
```markdown
---
source: .claude/agents/implementer.md
synced: <ISO timestamp>
version: <git short SHA>
---
```

### 2. Generate Library Index
Write `prompts/README.md` with:
- Table of all agents (name, role summary, last updated)
- Table of all skills (name, purpose, trigger conditions)
- Table of all commands (name, what it does)
- Link to TRANSPARENCY.md for plain-language summary

### 3. Generate TRANSPARENCY.md
Write a plain-English document explaining:
- "When you interact with an AI in this repo, here is what it has been told..."
- Per-agent: what it does, what it won't do, how it makes decisions
- Overall: what guardrails exist, what human oversight points exist

### 4. Update CHANGELOG.md in prompts/
Record what changed since last sync using git diff on `.claude/` directory.

### 5. Commit
Commit the `prompts/` directory with message:
`docs(prompts): sync prompt library snapshot [<short-sha>]`

## Output
- `prompts/` directory (full library)
- `prompts/README.md` (index)
- `prompts/TRANSPARENCY.md` (plain-language)
- `prompts/CHANGELOG.md` (history)

## Related Skills
- `prompt-transparency` — generates the transparency report
- `system-prompt-audit` — audits for consistency and safety
- `repo-memory-updater` — keeps other repo docs current
- `docs-sync` — general documentation sync
