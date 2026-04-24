---
name: repo-memory-updater
description: >
  Keep CLAUDE.md files and .claude/state/ in sync with the current repo reality.
  Use after significant structural changes, after adding risky modules,
  or when CLAUDE.md feels stale.
triggers:
  - "update CLAUDE.md"
  - "the docs are stale"
  - "what does CLAUDE.md say about X?"
  - after any module restructure or new module addition
  - after a new env var or command is added
  - periodically (after 5+ meaningful commits without a CLAUDE.md update)
references:
  - CLAUDE.md
  - agent/CLAUDE.md
  - router/CLAUDE.md
  - .claude/state/agent-state.json
---

# Skill: repo-memory-updater

## When to Use

- After adding a new module, endpoint, or significant capability
- After adding risky code (auth, file I/O, external service)
- After any change to key commands, env vars, or test commands
- When starting a new session and CLAUDE.md feels outdated
- After merging a PR that significantly changes structure

## Instructions

### Step 1 — Inventory what changed

```bash
git log --oneline -20                     # recent commits
git diff HEAD~5 --stat                    # files changed in last 5 commits
```

Look for: new files, renamed modules, new env vars in `.env.example`, new commands in README.

### Step 2 — Check root CLAUDE.md

Read `CLAUDE.md` and answer:
- Is the **Codebase Map** section still accurate? (new files, changed structure)
- Are the **Key Commands** still correct? (nothing renamed or removed)
- Are the **Coding Rules** still appropriate? (no new risky patterns uncovered)
- Is the **skill-to-situation mapping table** still complete?
- Is the **Where Deeper Truth Lives** table up to date?

### Step 3 — Check module CLAUDE.md files

For any module that changed significantly:
- Does the module `CLAUDE.md` reflect current invariants?
- Are the env var lists accurate?
- Are the test file references correct?

### Step 4 — Update .claude/state/

Update `.claude/state/agent-state.json`:
- `last_updated` timestamp
- `completed_steps` if new milestones were reached
- `changed_files` list if new files were added by recent work

Append to `.claude/state/checkpoint.jsonl` with a note like:
```json
{"ts":"<ISO>","step":"repo-memory-update","status":"done","detail":"Updated CLAUDE.md for <what changed>"}
```

### Step 5 — Commit the update

```bash
git add CLAUDE.md agent/CLAUDE.md router/CLAUDE.md .claude/state/
git commit -m "docs: sync CLAUDE.md with current repo state"
```

## What NOT to Change

- Do not expand CLAUDE.md into a full reference manual. Keep it scannable.
- Do not duplicate information already in `docs/` — link to it instead.
- Do not add implementation details that belong in module docstrings.

## Acceptance Checks

- [ ] Root CLAUDE.md codebase map reflects current files
- [ ] Key commands in CLAUDE.md work as written
- [ ] Skill-to-situation table is complete
- [ ] Module CLAUDE.md files updated if those modules changed
- [ ] `agent-state.json` last_updated timestamp refreshed
- [ ] Committed with `docs:` prefix (exempt from changelog requirement)
