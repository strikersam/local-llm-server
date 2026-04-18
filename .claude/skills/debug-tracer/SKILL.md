# Skill: debug-tracer

## Purpose
Systematically trace and resolve bugs using hypothesis-driven debugging. Prevents random trial-and-error and ensures the root cause is found, not just the symptom.

## Trigger
Use when:
- A bug report needs investigation
- Tests are failing unexpectedly
- Behavior is wrong but the cause is unknown
- "It worked before" situations

## Process

### Step 1: Reproduce First
Before any investigation, reproduce the bug:
```bash
# Document exact reproduction steps:
1. [exact command or action]
2. [expected behavior]
3. [actual behavior]
4. [error message or output]
```

If you cannot reproduce it, stop. A bug you can't reproduce cannot be safely fixed.

### Step 2: Gather Evidence
Collect all available information:
- Full error message and stack trace
- Relevant log output
- When it started occurring (if known)
- What changed recently (`git log --oneline -20`)
- Environment details if relevant

### Step 3: Form Hypotheses
Based on the evidence, list 2-5 hypotheses ranked by likelihood:
```
## Hypotheses
1. [Most likely] The input validation in X is not handling Y case
2. [Likely] Race condition in async handler Z
3. [Possible] Dependency version mismatch after recent update
4. [Unlikely] Infrastructure/environment issue
```

### Step 4: Test Hypotheses (Cheapest First)
For each hypothesis, starting with the easiest to test:
1. What evidence would confirm or deny this hypothesis?
2. What is the minimal test to check it?
3. Run the test
4. Update hypothesis list based on results

**Never fix before confirming hypothesis.**

### Step 5: Identify Root Cause
Once a hypothesis is confirmed:
- Find the exact line(s) causing the issue
- Understand WHY it causes the issue (not just that it does)
- Check if the same pattern exists elsewhere in the codebase

### Step 6: Fix
Apply the minimal fix that addresses the root cause:
- Do not "fix" symptoms
- Do not add defensive code around the bug without fixing it
- The fix should make the reproduction steps work correctly

### Step 7: Add Regression Test
Write a test that:
- Reproduces the exact bug scenario
- Fails before the fix
- Passes after the fix
- Will catch any future regression

### Step 8: Post-Mortem (for significant bugs)
```
## Bug Post-Mortem

### Root Cause
[What caused the bug]

### Why It Wasn't Caught
[Why tests/review didn't catch this]

### Fix Applied
[What was changed]

### Prevention
[What could prevent this class of bug in future]
```

## Rules
- Never commit a fix without a regression test
- If the root cause is "unclear", keep investigating — don't guess-fix
- A fix that introduces a new bug is worse than the original bug
- Document the reasoning, not just the change

## Anti-Patterns
- **Shotgun debugging**: changing multiple things at once and seeing if it works
- **Symptomatic fixes**: adding `try/except` around broken code
- **Cargo-cult fixes**: copying a similar fix without understanding why
- **Optimistic fixing**: assuming the fix works without verifying
