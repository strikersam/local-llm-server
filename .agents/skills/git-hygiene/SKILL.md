# Skill: Git Hygiene

## Purpose
Ensures the repository's git history, branch state, and commit messages are clean, meaningful, and follow project conventions before pushing or merging.

## When to Use
- Before pushing commits to master or opening a PR
- When git history has become messy (fixup commits, WIP messages, etc.)
- As a final step in any implementation workflow
- When the `changelog-enforcer` or `release-readiness` skills are applied

## Process

### 1. Review Staged and Unstaged Changes
- Run `git status` to see what's changed
- Confirm no unintended files are staged (build artifacts, secrets, editor files)
- Check `.gitignore` is catching what it should

### 2. Review Commit History
- Run `git log --oneline -20` to inspect recent commits
- Flag commits with vague messages: "fix", "wip", "test", "asdf", etc.
- Note commits that could be squashed without losing meaning

### 3. Validate Commit Messages
- Ensure messages follow the pattern: `<type>: <short description> [#issue]`
- Valid types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`
- Subject line should be ≤72 characters
- No trailing periods in subject line

### 4. Clean Up if Needed
- Squash fixup commits with `git rebase -i` if appropriate
- Amend the most recent commit message with `git commit --amend` if needed
- Do not rewrite history on shared branches unless explicitly authorized

### 5. Confirm Branch State
- Ensure the working branch is up to date with its upstream
- Resolve any merge conflicts before pushing
- Confirm you are on the intended branch

### 6. Push
- Push with `git push origin <branch>`
- Use `--force-with-lease` only if a rebase was performed, never `--force`

## Output
- Clean git history with meaningful commit messages
- No unintended files committed
- Successful push to the correct branch

## Notes
- Never commit secrets, credentials, or API keys
- Binary files and generated files should generally not be committed
- If in doubt about a commit, use `git diff HEAD~1` to review what it contains
