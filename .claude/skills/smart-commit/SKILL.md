---
name: smart-commit
description: >
  Quality gates + conventional commits. Run tests, lint, and typecheck before
  committing. Format the commit message as a conventional commit. Blocks on failure.
triggers:
  - "commit this"
  - "make a commit"
  - "save my progress"
  - before any git commit
  - "smart commit"
references:
  - docs/changelog.md
  - .claude/hooks/commit-msg
  - .claude/hooks/pre-push
---

# Skill: smart-commit

## When to Use

Use this skill every time you are ready to commit code. It replaces ad-hoc
`git add && git commit` with a structured quality gate sequence.

---

## Instructions

### Step 1 — Confirm changelog is updated

```bash
git diff docs/changelog.md
```

If the diff is empty and this is a code change (not chore/test/docs), update
`docs/changelog.md` under `## [Unreleased]` before continuing.

### Step 2 — Run tests

```bash
pytest -x
```

**Block on failure.** Do not commit with failing tests. Fix the failure first.

### Step 3 — Check for obvious issues

```bash
# Syntax check staged Python files
git diff --staged --name-only | grep '\.py$' | xargs python -m py_compile

# Confirm no secrets in staged files
git diff --staged | grep -iE '(SECRET_KEY\s*=\s*["\x27][^"\x27]{8}|password\s*=\s*["\x27][^"\x27]{4}|api_key\s*=\s*["\x27]sk-)'
```

If any secrets are detected: **stop immediately**, do not commit.

### Step 4 — Stage your changes

```bash
git status                          # review what changed
git diff --staged                   # confirm what's staged
git add <specific files>            # stage by name, not -A
```

### Step 5 — Write a conventional commit message

Format: `<type>(<scope>): <short description>`

| Type | When to Use |
|------|-------------|
| `feat` | New feature visible to users |
| `fix` | Bug fix |
| `refactor` | Code change with no behaviour change |
| `test` | Adding or updating tests |
| `docs` | Documentation only |
| `chore` | Tooling, config, dependencies |
| `ci` | CI/CD changes |
| `style` | Formatting, whitespace (no logic change) |
| `perf` | Performance improvement |
| `security` | Security fix or hardening |

**Examples:**
```
feat(router): add task classification for long-context requests
fix(auth): reject tokens with empty bearer string
refactor(agent): extract planner prompt into prompts.py
security(key_store): hash keys before comparison
```

### Step 6 — Commit

```bash
git commit -m "$(cat <<'EOF'
feat(scope): description here

- Additional context if needed
- Reference issue if applicable

https://claude.ai/code/session_<id>
EOF
)"
```

### Step 7 — Verify

```bash
git log --oneline -3    # confirm commit appeared
git status              # confirm working tree is clean
```

---

## Acceptance Checks

- [ ] `docs/changelog.md` updated (or commit is chore/test/docs/ci/style exempt)
- [ ] `pytest -x` passed
- [ ] No secrets in staged diff
- [ ] Specific files staged (not `git add -A`)
- [ ] Conventional commit message used
- [ ] `git log` confirms commit
