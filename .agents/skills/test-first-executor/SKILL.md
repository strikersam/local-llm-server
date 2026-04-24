---
name: test-first-executor
description: >
  Write or update tests before (or alongside) implementation.
  Ensures every code change is verifiably correct before merging.
triggers:
  - "add tests for"
  - "write a test"
  - "fix the bug in"
  - any new function, class, or endpoint
  - any bug fix
references:
  - tests/
  - AGENTS.md (Testing Expectations section)
---

# Skill: test-first-executor

## When to Use

Use this skill whenever:
- Adding a new function, class, or FastAPI endpoint
- Fixing a bug (regression test required)
- Adding a new agent tool or router capability
- A reviewer asks "where are the tests?"

## Instructions

### Step 1 — Identify what needs testing
- What is the expected input/output?
- What are the failure modes?
- Is there a risky edge case (empty input, auth bypass, model unavailability)?

### Step 2 — Write the test first

For this repo, tests live in `tests/`. Match the pattern:

```
tests/test_<module>.py     # mirrors src module name
```

Test structure template:
```python
"""Tests for <module>.<Class>."""
from __future__ import annotations

import pytest
# imports

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def some_fixture():
    ...

# ── Happy path ────────────────────────────────────────────────────────────────

def test_<function>_<expected_outcome>():
    ...

# ── Edge cases ────────────────────────────────────────────────────────────────

def test_<function>_raises_on_<bad_input>():
    with pytest.raises(SomeError):
        ...

# ── Regression ────────────────────────────────────────────────────────────────

def test_regression_<issue_description>():
    # Previously this caused <symptom>. Fixed in <commit/version>.
    ...
```

### Step 3 — Confirm the test FAILS before implementation

Run `pytest -x tests/test_<module>.py::test_<name>`.
A test that passes immediately (before implementation) is not testing the right thing.

### Step 4 — Implement until the test passes

### Step 5 — Run the full suite

```bash
pytest -x
```

All pre-existing tests must still pass.

### Step 6 — Check coverage of risky paths

For any change to `admin_auth.py`, `key_store.py`, `agent/tools.py`:
- Write a test that specifically exercises the security boundary.
- Confirm the test would catch a regression if the boundary were removed.

## Acceptance Checks

- [ ] Test file exists for the changed module
- [ ] New test covers the new behaviour
- [ ] Test was run and passed
- [ ] No pre-existing test was broken
- [ ] Regression test added for any bug fix
- [ ] `pytest -x` exits 0

## Test File Map

| Module | Test file |
|--------|-----------|
| `proxy.py` | `tests/test_agent_api.py` |
| `agent/loop.py` | `tests/test_agent_runner.py` |
| `agent/tools.py` | `tests/test_agent_tools.py` |
| `router/` | `tests/test_model_router.py` |
| new modules | `tests/test_<module_name>.py` |
