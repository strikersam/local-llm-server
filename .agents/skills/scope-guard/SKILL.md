# Skill: scope-guard

## Purpose
Detect and prevent scope creep during implementation. Keeps Claude focused on the original task and flags when it's about to do more than asked.

## Trigger
Use:
- At the start of any implementation task (define scope)
- During implementation when you notice you're about to change something unrelated
- When a fix "requires" refactoring something else
- When you feel the urge to "clean up while you're in here"

## Process

### Step 1: Define the Scope Contract
At task start, write an explicit scope contract:
```
## Scope Contract

### In Scope
- [specific change 1]
- [specific change 2]

### Out of Scope (explicitly)
- Refactoring existing working code
- Improving unrelated tests
- Updating unrelated documentation
- Performance improvements not requested
- Style changes in files not being touched

### Allowed Side Effects
- Fixing a bug directly caused by the change
- Updating tests for code being modified
- Updating docs directly describing the feature being added
```

### Step 2: Pre-Implementation Check
Before touching any file, ask:
1. Is this file directly related to the requested change?
2. Would the change work without modifying this file?
3. Is this a "nice to have" or a "need to have"?

If the answer to #2 is "yes" or #3 is "nice to have" — do NOT touch the file.

### Step 3: During Implementation — The Scope Test
When you notice any of these urges, apply the scope test:

**Red Flags (stop and evaluate):**
- "While I'm here, I should also..."
- "This would be cleaner if I refactored..."
- "I noticed this other bug..."
- "The tests could be improved..."
- "This naming is inconsistent across the codebase..."

**The Scope Test:**
1. Was this mentioned in the original task? → If no, stop.
2. Does the original task FAIL without this change? → If no, stop.
3. Is this a security or data-integrity issue? → If yes, flag it separately.

### Step 4: Parking Lot
When you catch scope creep, don't ignore it — park it:
```
## Parking Lot (Out of Scope - Future Issues)
- [ ] `src/utils.py` line 45: inconsistent error handling pattern — could be standardized
- [ ] `tests/test_api.py`: test coverage gaps in edge cases
- [ ] Performance: N+1 query detected in unrelated endpoint
```

These become suggestions for future issues, not additions to the current task.

### Step 5: Final Scope Audit
Before committing, audit the diff:
- List every file changed
- For each file, confirm it was in scope
- If any file changed was NOT in scope, revert those changes and add them to the parking lot

## Rules
- Scope creep feels productive but creates noise in reviews and risks regressions
- A focused PR is better than a "while I was there" PR
- Out-of-scope bugs should be filed as new issues, not fixed silently
- The parking lot is not a trash bin — items there should be filed as real issues

## Anti-Patterns to Avoid
- "Drive-by refactoring" — touching code just because it could be better
- "Yak shaving" — fixing prerequisites to fix prerequisites
- "Boyscout overload" — leaving every file you touch cleaner than you found it (good in principle, bad in PRs)
- "Feature creep" — adding related-but-not-requested functionality

## Output Format
When flagging scope creep:
```
⚠️ SCOPE GUARD: About to modify [file] because [reason].
This is [in scope / out of scope] because [explanation].
[Proceeding / Stopping and parking this for later.]
```
