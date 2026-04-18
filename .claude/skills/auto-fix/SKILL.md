# Skill: auto-fix

## Purpose
Automatically detect and fix linting, formatting, and type errors across the codebase. Acts as a one-shot "clean up everything" command before committing or opening a PR.

## Trigger
Use when:
- Pre-commit cleanup is needed
- CI is failing due to lint/type errors
- Code was written quickly and needs polish
- You want to ensure the codebase is green before review

## Process

### Step 1: Discover Fix Commands
Read `CLAUDE.md`, `package.json`, `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml` to find:
- Lint fix commands (eslint --fix, ruff check --fix, black, prettier)
- Type check commands (mypy, tsc --noEmit, pyright)
- Format commands (isort, autopep8, gofmt)

### Step 2: Run Fixers (Auto-fixable)
Execute all auto-fixable tools in order:
1. Formatters first (black, prettier, gofmt)
2. Import sorters (isort, organize-imports)
3. Lint fixers (eslint --fix, ruff --fix)

Capture output for each. Note what was changed.

### Step 3: Run Checkers (Non-auto-fixable)
Run tools that report but cannot auto-fix:
1. Type checkers (mypy, tsc, pyright)
2. Strict lint rules that require manual intervention

Collect all errors with file:line references.

### Step 4: Manual Fix Loop
For each remaining error:
1. Read the file at the error location
2. Understand the error message
3. Apply the minimal correct fix
4. Re-run the checker to confirm resolved
5. Never suppress errors with `# type: ignore` or `// eslint-disable` unless it's genuinely unfixable and documented why

### Step 5: Final Verification
Run the full check suite one more time. All checks must pass before declaring done.

### Step 6: Report
Summarize:
- Files auto-formatted: N
- Lint issues auto-fixed: N  
- Type errors manually fixed: N
- Remaining issues (if any): list them with explanations

## Rules
- Never introduce `any` types to silence TypeScript errors
- Never use `# noqa` or `# type: ignore` without a comment explaining why
- Prefer fixing root causes over suppressing symptoms
- If a fix requires understanding business logic, flag it rather than guess
- Run tests after fixing to ensure no regressions

## Output Format
```
## Auto-Fix Report

### Auto-formatted
- src/utils.py (black)
- src/models.py (isort + black)

### Lint Fixed
- src/api.py: removed unused import `os`
- src/routes.py: fixed f-string formatting

### Type Errors Fixed
- src/service.py:45 — Added `Optional[str]` return type
- src/models.py:12 — Fixed dict type annotation

### Still Failing
- None ✅
```
