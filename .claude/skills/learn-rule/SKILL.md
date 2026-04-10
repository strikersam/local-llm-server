---
name: learn-rule
description: >
  Persist corrections and patterns to long-term memory. When a mistake is made
  or a rule is learned, write it to .claude/state/learnings.md so it's never repeated.
triggers:
  - "remember this"
  - "don't do that again"
  - "that was wrong, the correct way is"
  - "note this for future"
  - "add this to memory"
  - after any correction from the user
references:
  - .claude/state/learnings.md
  - CLAUDE.md
---

# Skill: learn-rule

## When to Use

Use this skill whenever:
- The user corrects a mistake you made
- You discover a repo-specific rule that isn't in CLAUDE.md
- A pattern works unexpectedly (positively or negatively)
- You want to persist a decision for future sessions

This is how Claude gets smarter at this specific repo over time.

---

## Instructions

### Step 1 — Identify the rule

Extract the core rule from the correction or discovery. A good rule is:
- **Specific** — refers to a concrete situation
- **Actionable** — tells you what to do or not do
- **Memorable** — can be read in under 10 seconds

**Bad rule:** "Be careful with auth code."
**Good rule:** "Always call `risky-module-review` before touching `admin_auth.py` — even for 1-line changes."

### Step 2 — Append to learnings file

File: `.claude/state/learnings.md`

Create it if it doesn't exist. Always append — never overwrite.

```markdown
## YYYY-MM-DD — <short title>

**Situation:** What was being worked on when this was learned.
**Mistake/Discovery:** What went wrong or what was surprising.
**Rule:** <One clear, actionable sentence starting with a verb.>
**Source:** user-correction | self-discovery | docs
```

**Example entry:**

```markdown
## 2026-04-09 — Don't use git add -A

**Situation:** Committing the router refactor.
**Mistake:** Used `git add -A` which staged keys.json accidentally.
**Rule:** Always stage specific files by name; never use `git add -A` or `git add .`.
**Source:** user-correction
```

### Step 3 — Check if CLAUDE.md should be updated

If the rule is general enough to apply to every future session:
1. Read CLAUDE.md
2. Add it to the "Coding Rules" section (numbered, concise)
3. Use `repo-memory-updater` skill if multiple rules need updating

---

## Learnings File Format

`.claude/state/learnings.md`:

```markdown
# Session Learnings

Rules and corrections learned from working in this repo.
Read this at the start of sessions via the `replay-learnings` skill.

---

## YYYY-MM-DD — title

**Situation:** ...
**Mistake/Discovery:** ...
**Rule:** ...
**Source:** ...

---
```

---

## Acceptance Checks

- [ ] Rule is specific and actionable (not vague advice)
- [ ] Entry appended to `.claude/state/learnings.md`
- [ ] CLAUDE.md updated if rule is broadly applicable
- [ ] Rule phrased as an imperative: "Always X", "Never Y", "Before Z, do W"
