---
name: insights
description: >
  Analytics, heatmaps, and trends from session history. Analyze checkpoint logs,
  learnings, and git history to surface patterns: which files change most, which
  steps fail most often, and where to invest in tooling or tests.
triggers:
  - "show me insights"
  - "what are the patterns"
  - "which files break most"
  - "session analytics"
  - "what should I automate"
  - "heatmap"
  - "trends"
references:
  - .claude/state/checkpoint.jsonl
  - .claude/state/learnings.md
  - .claude/state/agent-state.json
---

# Skill: insights

## When to Use

Run this skill:
- After 5+ sessions to surface meaningful patterns
- When deciding where to invest in tests or tooling
- When repeating errors and wanting a data-driven view of why
- As part of a planning session to understand the codebase's hot spots

---

## Instructions

### Step 1 — File change heatmap (which files change most)

```bash
# Top 20 most-changed files in git history
git log --name-only --format="" | grep '\.py$' | sort | uniq -c | sort -rn | head -20
```

**Interpret:** High-churn files are either:
- Core abstractions that evolve frequently (expected)
- Files with unclear responsibility (refactor candidate)
- Risky files where instability = risk (add tests)

### Step 2 — Failure pattern analysis

```bash
# Extract failed steps from checkpoint log
grep '"status":"failed"' .claude/state/checkpoint.jsonl | \
  python3 -c "import sys,json; [print(json.loads(l).get('step','?')) for l in sys.stdin]" | \
  sort | uniq -c | sort -rn
```

**Interpret:** Steps that fail repeatedly indicate:
- Unclear acceptance criteria in the plan
- A dependency that needs better documentation
- A missing test that should catch the failure earlier

### Step 3 — Retry analysis

```bash
# Steps that appeared more than once (retried)
grep '"status"' .claude/state/checkpoint.jsonl | \
  python3 -c "
import sys, json, collections
steps = []
for line in sys.stdin:
    try:
        d = json.loads(line)
        steps.append(d.get('step', '?'))
    except:
        pass
counts = collections.Counter(steps)
for step, count in counts.most_common():
    if count > 1:
        print(f'{count}x  {step}')
"
```

### Step 4 — Learnings frequency analysis

```bash
# Count learnings by module/topic
grep -c "##" .claude/state/learnings.md 2>/dev/null || echo "0 learnings recorded."
grep "^## " .claude/state/learnings.md 2>/dev/null || echo "No learnings file."
```

**Interpret:** Clusters of learnings around the same module suggest:
- The module needs clearer documentation
- CLAUDE.md for that module is missing or outdated
- The module should be refactored for clarity

### Step 5 — Produce a summary report

Output a structured summary:

```
## Insights Report — YYYY-MM-DD

### File Heatmap (top 5 most-changed)
1. proxy.py            — 47 changes  [CORE — expected]
2. router/model_router.py — 31 changes  [HIGH CHURN — add tests]
3. agent/tools.py      — 28 changes  [RISKY — review coverage]
4. tests/test_router.py — 22 changes  [HEALTHY — test evolution]
5. admin_auth.py       — 19 changes  [RISKY — security surface]

### Failure Patterns
- "apply-diff on tools.py" failed 4 times → Add input validation test
- "pytest after router change" failed 3 times → Router tests may be brittle

### Retry Hot Spots
- 3x "generate planner output" → Planner prompt may need clarification

### Learning Clusters
- 5 learnings about git commit practices → Consider a pre-commit hook
- 3 learnings about router/CLAUDE.md → Update router/CLAUDE.md to be clearer

### Recommendations

| Priority | Action | Rationale |
|----------|--------|-----------|
| HIGH | Add tests for model_router.py | 31 changes, 3 test failures |
| HIGH | Review agent/tools.py coverage | 28 changes, risky module |
| MED | Update router/CLAUDE.md | 3 learnings cluster there |
| LOW | Pre-commit hook for commit style | 5 learnings, repetitive pattern |
```

---

## Acceptance Checks

- [ ] File heatmap produced (top 10+ files)
- [ ] Failed steps and retry patterns analyzed
- [ ] Learnings clustered by topic
- [ ] Recommendations ranked by priority
- [ ] At least 1 actionable recommendation made
