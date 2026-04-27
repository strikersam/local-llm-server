# Skill: ticket-to-pr

## Purpose
Transform a GitHub issue (ticket) into a complete, merged pull request. End-to-end automation from reading the issue to pushing working, tested code.

## Trigger
Use when:
- Given an issue number or URL to implement
- Told "implement issue #N"
- A GitHub issue is linked in the task

## Process

### Step 1: Parse the Issue
Read the issue title, body, labels, and comments. Extract:
- **What**: The feature/fix being requested
- **Why**: The motivation or user need
- **Acceptance Criteria**: Explicit or implied success conditions
- **Constraints**: Any technical requirements or limitations mentioned
- **Context**: Related issues, PRs, or discussions referenced

If acceptance criteria are not explicit, derive them from the description and list them out for confirmation.

### Step 2: Context Prime
Run the `context-prime` skill to ensure full codebase understanding before writing code.

Focus particularly on:
- Files most likely affected by this change
- Existing tests for related functionality
- Any TODO comments or known issues in relevant areas

### Step 3: Plan the Implementation
Before writing code, produce a plan:
```
## Implementation Plan for #[N]: [title]

### Files to Create
- path/to/new_file.py — [purpose]

### Files to Modify  
- path/to/existing.py — [what changes and why]

### Tests to Add
- tests/test_feature.py — [what scenarios to cover]

### Acceptance Criteria Checklist
- [ ] [criterion 1]
- [ ] [criterion 2]
```

### Step 4: Test-First Implementation
For each acceptance criterion:
1. Write the test first (failing)
2. Write the minimal implementation to pass it
3. Refactor if needed
4. Confirm test passes

Use `test-first-executor` skill for complex features.

### Step 5: Run Full Validation
```bash
# All of these must pass:
- Unit tests
- Integration tests (if applicable)
- Lint/type checks (use auto-fix skill first)
- Any CI checks that can be run locally
```

### Step 6: Commit with Smart-Commit
Use the `smart-commit` skill to create a well-structured commit:
- Reference the issue number in commit message
- Follow conventional commits format
- Include `Closes #N` in commit body

### Step 7: Self-Review
Before pushing, review your own diff:
- Does it actually solve what the issue asked for?
- Are there any obvious bugs or edge cases missed?
- Is the code consistent with project conventions?
- Are the tests meaningful (not just passing, but actually validating behavior)?

### Step 8: Push and Summarize
Push the branch and output a PR description:
```
## PR: [title]

Closes #[N]

### What Changed
[brief description]

### How to Test
[step-by-step testing instructions]

### Checklist
- [x] Tests added/updated
- [x] Lint passes
- [x] Acceptance criteria met
```

## Rules
- Never skip the planning step — rushing leads to wrong implementations
- Never mark acceptance criteria as met without a test proving it
- If the issue is ambiguous, make explicit assumptions and document them
- If the issue reveals a deeper problem, note it but stay focused on the ticket scope
- Use `scope-guard` skill to avoid over-implementing

## Integration with Other Skills
- → `context-prime`: always run first
- → `test-first-executor`: for the implementation loop  
- → `auto-fix`: before final commit
- → `smart-commit`: for the commit message
- → `scope-guard`: to stay focused
