---
name: parallel-worktrees
description: >
  Git worktree setup for zero dead time. Work on multiple branches simultaneously
  without switching branches or stashing. Ideal for running tests on main while
  implementing on a feature branch.
triggers:
  - "set up parallel worktrees"
  - "I need to work on multiple branches"
  - "worktree"
  - "zero dead time"
  - "run tests on main while I work"
references:
  - CLAUDE.md
---

# Skill: parallel-worktrees

## When to Use

Use this skill when you need to:
- Run the test suite on `main` while implementing on a feature branch
- Keep a clean reference copy of the code for comparison during refactors
- Work on a hotfix without disturbing in-progress feature work
- Avoid `git stash` / `git checkout` cycles that interrupt flow

---

## Concept

Git worktrees let you check out multiple branches of the same repo into different
directories simultaneously. Each worktree shares the `.git` database but has its
own working tree and index.

```
/home/user/local-llm-server/          ← main worktree (your current branch)
/home/user/local-llm-server-main/     ← linked worktree (main branch, read reference)
/home/user/local-llm-server-hotfix/   ← linked worktree (hotfix branch)
```

---

## Instructions

### Step 1 — Create a worktree for reference/parallel work

```bash
# Create a linked worktree for the main branch (read reference)
git worktree add ../local-llm-server-main main

# Create a linked worktree for a new feature branch
git worktree add ../local-llm-server-feature -b feature/my-feature

# Create a linked worktree for an existing remote branch
git worktree add ../local-llm-server-hotfix origin/hotfix/issue-42
```

### Step 2 — List active worktrees

```bash
git worktree list
```

Output shows each worktree's path, HEAD commit, and branch.

### Step 3 — Work across worktrees

Each worktree is an independent directory. You can:

```bash
# Run tests on main without switching branches
cd ../local-llm-server-main && pytest -x

# Edit files in the feature worktree
cd ../local-llm-server-feature && $EDITOR proxy.py

# Compare files across worktrees
diff ../local-llm-server-main/proxy.py ./proxy.py
```

### Step 4 — Remove a worktree when done

```bash
# Remove the linked worktree (does not delete the branch)
git worktree remove ../local-llm-server-main

# Force remove if worktree has uncommitted changes
git worktree remove --force ../local-llm-server-main

# Prune stale worktree references
git worktree prune
```

---

## Common Patterns

### Pattern A — Test main while you implement

```bash
# Terminal 1: implement on feature branch
cd /home/user/local-llm-server
git checkout -b feature/scout-agent

# Terminal 2: run tests continuously on main
git worktree add ../llm-server-main main
cd ../llm-server-main
pytest --watch   # or: watch -n 5 pytest -x
```

### Pattern B — Review reference during refactor

```bash
# Keep a clean reference copy while refactoring
git worktree add ../llm-server-ref HEAD

# Compare your changes against the original
diff -r ../llm-server-ref/router/ ./router/
```

### Pattern C — Hotfix without disturbing feature work

```bash
# You're mid-feature on main worktree
# Create a hotfix worktree without stashing anything
git worktree add ../llm-server-hotfix -b hotfix/auth-bypass

# Work in the hotfix worktree, merge, then remove
cd ../llm-server-hotfix
# ... fix, test, commit ...
git worktree remove ../llm-server-hotfix
```

---

## Constraints

- You cannot check out the same branch in two worktrees simultaneously.
- Worktrees share the `.git` database — commits in one are visible in all.
- The `.venv` virtual environment is not shared automatically. Each worktree
  needs its own activated environment or you can symlink: `ln -s /home/user/local-llm-server/.venv ../llm-server-main/.venv`

---

## Acceptance Checks

- [ ] `git worktree list` shows the expected worktrees
- [ ] Each worktree is on the intended branch
- [ ] Work completed in worktrees is committed before removal
- [ ] `git worktree prune` run after removing worktrees
