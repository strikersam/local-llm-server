---
name: council-review
description: >
  Multi-perspective code review before merging. Simulates a council of reviewers
  (security, correctness, performance, maintainability) independently evaluating a change.
  Use before any PR merge or for significant changes.
triggers:
  - "review this PR"
  - "is this ready to merge?"
  - "review before I merge"
  - any change larger than 50 lines
  - any change to auth, routing, or agent execution
references:
  - AGENTS.md
  - agent/AGENTS.md
  - router/AGENTS.md
  - docs/adrs/
---

# Skill: council-review

## When to Use

Use this skill:
- Before merging any PR that changes production code
- When asked "is this safe?" or "can this go out?"
- After a self-review that feels uncertain
- For any change to risky modules (auth, keys, agent tools, routing)

## Instructions

### Step 1 — Gather the diff

```bash
git diff main...HEAD                    # all changes vs main
git diff --stat main...HEAD             # file summary
```

### Step 2 — Run each reviewer role independently

For each role below, read the diff and answer the questions for that role.
Record findings in a structured review comment.

---

#### Role 1: Security Reviewer

Questions to answer:
- Does this change introduce or weaken an auth check?
- Are any secrets, tokens, or API keys potentially exposed?
- Does any new code accept untrusted input without validation?
- Are file paths sanitized? (especially in `agent/tools.py`)
- Does any new dependency introduce a known CVE?

---

#### Role 2: Correctness Reviewer

Questions to answer:
- Does the implementation match the stated goal?
- Are edge cases handled (empty input, None, zero, very long strings)?
- Are error conditions propagated correctly?
- Would any existing test fail after this change?
- Are there any off-by-one errors, race conditions, or type mismatches?

---

#### Role 3: Performance Reviewer

Questions to answer:
- Does this change add any blocking I/O on the async path?
- Are there any N+1 query or repeated expensive computation patterns?
- Does any new loop run on every request?
- Is caching appropriate? (especially for health checks, model registry)

---

#### Role 4: Maintainability Reviewer

Questions to answer:
- Is the code readable without inline explanation?
- Are variable names clear?
- Are new abstractions justified or is this over-engineering?
- Does this add duplication that should be shared?
- Is the module boundary respected? (don't let routing logic leak into proxy.py)

---

### Step 3 — Produce a council verdict

```
## Council Verdict

### Approved / Blocked / Approved with conditions

**Security:** PASS / FAIL / WARN — <one line>
**Correctness:** PASS / FAIL / WARN — <one line>
**Performance:** PASS / FAIL / WARN — <one line>
**Maintainability:** PASS / FAIL / WARN — <one line>

### Required changes before merge
- (list any FAIL or WARN items that must be addressed)

### Optional improvements
- (list any suggestions that are not blockers)
```

### Step 4 — Gate on verdict

- If any reviewer returns FAIL: do not merge. Address and re-run.
- If any reviewer returns WARN: document the known risk in a code comment or ADR.
- If all PASS: merge is safe.

## Acceptance Checks

- [ ] All four reviewer roles evaluated
- [ ] No FAIL verdicts outstanding
- [ ] Required changes (if any) addressed
- [ ] Verdict recorded (in PR description or review comment)
- [ ] Tests pass after any required changes
