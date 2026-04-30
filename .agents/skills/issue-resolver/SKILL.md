# Skill: Issue Resolver

## Purpose
Provides a structured, repeatable process for resolving GitHub issues from start to finish — reading the issue, planning a solution, implementing it, testing it, and closing it with a proper commit and changelog entry.

## When to Use
- When assigned a GitHub issue to implement or fix
- When an issue number is referenced in a task prompt
- When a bug report, feature request, or task needs to be converted into working code

## Process

### 1. Read and Understand the Issue
- Fetch and read the full issue text, including all comments
- Identify: issue type (bug / feature / task / question), acceptance criteria, constraints
- Note any linked issues, PRs, or external references

### 2. Explore the Codebase
- Identify files relevant to the issue
- Understand existing patterns, conventions, and architecture
- Check if any existing skill applies (e.g., `auto-fix`, `implementation-planner`, `debug-tracer`)

### 3. Plan the Solution
- Write a short implementation plan (can be inline reasoning, not a file)
- Identify edge cases and risks
- Determine what tests are needed

### 4. Implement
- Make the minimum changes necessary to resolve the issue
- Follow existing code style and conventions
- Do not introduce unrelated changes

### 5. Test
- Run existing tests; confirm they pass
- Write new tests if the change introduces new behavior
- Manually verify the fix or feature works as intended

### 6. Document
- Add an entry to `docs/changelog.md` under `[Unreleased]`
- Update any relevant docs if the issue touched documented behavior

### 7. Commit and Push
- Write a clear commit message referencing the issue: `fix: resolve #<n> - <short description>`
- Push to the appropriate branch (master unless otherwise specified)

## Output
- Working code changes that resolve the issue
- Passing tests
- Changelog entry
- Clean commit pushed to repository

## Notes
- If the issue is ambiguous, implement the most reasonable interpretation and note assumptions in the commit message
- If the issue is out of scope or already resolved, leave a comment explaining why and close it
- Prefer surgical fixes over refactors unless the issue explicitly requests cleanup
