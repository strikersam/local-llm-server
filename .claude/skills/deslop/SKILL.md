---
name: deslop
description: >
  Remove AI code slop before committing. Review AI-generated code for unnecessary
  verbosity, redundant comments, over-engineering, and low-signal patterns that
  degrade codebase quality over time.
triggers:
  - "deslop"
  - "clean up the code"
  - "remove AI slop"
  - "before I commit"
  - "is this over-engineered?"
  - "remove unnecessary comments"
  - after any large AI-generated code block
references:
  - CLAUDE.md
---

# Skill: deslop

## When to Use

Run this skill **before every commit** on AI-generated code. AI tends to:
- Add excessive comments explaining obvious things
- Create unnecessary abstractions "for future extensibility"
- Write verbose variable names that add noise
- Add defensive checks for impossible scenarios
- Generate boilerplate that wasn't asked for

This skill catches and removes that slop before it becomes technical debt.

---

## What "Slop" Looks Like

### Category 1 — Obvious Comments

```python
# BAD: comment restates the code
# Increment the counter by one
counter += 1

# BAD: docstring for a trivial getter
def get_name(self):
    """Returns the name."""  # ← remove this
    return self.name

# GOOD: comment explains the WHY, not the WHAT
# Retry once on 429 — Ollama rate limits burst requests
if response.status == 429:
    await asyncio.sleep(1)
    response = await client.post(...)
```

### Category 2 — Phantom Abstractions

```python
# BAD: helper function used exactly once
def _build_auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

# ... used only here:
headers = _build_auth_header(api_key)

# GOOD: inline it — one use doesn't need extraction
headers = {"Authorization": f"Bearer {api_key}"}
```

### Category 3 — Defensive Checks for Impossible Cases

```python
# BAD: model is typed as str, can't be None here
if model is None:
    model = "default"

# BAD: list was just created, can't be empty by contract
if not items:
    return []
```

### Category 4 — Speculative Generality

```python
# BAD: added for hypothetical future use
class BaseRouter(ABC):
    @abstractmethod
    def route(self): ...

class ModelRouter(BaseRouter):
    def route(self): ...   # only one implementation, ever

# GOOD: just write ModelRouter directly
class ModelRouter:
    def route(self): ...
```

### Category 5 — Verbose Variable Names

```python
# BAD
current_request_model_name_string = request.model

# GOOD
model = request.model
```

### Category 6 — Unasked-For Boilerplate

```python
# BAD: added logging, error handling, and retry for a one-liner
async def get_health():
    log.debug("Starting health check")
    try:
        result = await check_ollama()
        log.debug("Health check completed successfully")
        return result
    except Exception as e:
        log.error(f"Health check failed: {e}")
        raise

# GOOD (if no retry logic was requested):
async def get_health():
    return await check_ollama()
```

---

## Instructions

### Step 1 — Read the diff

```bash
git diff --staged        # staged changes only
# or
git diff HEAD            # all changes since last commit
```

### Step 2 — Apply the deslop checklist

For each changed file, check:

- [ ] No comments that restate what the code does
- [ ] No one-use helper functions (inline them)
- [ ] No defensive None/empty checks for values that can't be None/empty by contract
- [ ] No abstract base classes or interfaces with a single implementation
- [ ] No verbose variable names (if the short name is unambiguous)
- [ ] No unasked-for boilerplate (logging, retry, error handling beyond what was specified)
- [ ] No type: ignore comments that mask real problems
- [ ] No TODO comments added by AI (remove or file as an issue)
- [ ] No backwards-compatibility shims for code that was just written

### Step 3 — Apply fixes

For each slop item found:
1. Remove it entirely (comments, phantom helpers, unnecessary checks)
2. Inline it (one-use helpers)
3. Simplify it (verbose names, over-abstracted interfaces)

Do not refactor beyond removing slop. The goal is cleaner, not different.

### Step 4 — Verify nothing broke

```bash
pytest -x
```

---

## The One Rule

> **If the code would be clearer without it, delete it.**

---

## Acceptance Checks

- [ ] No obvious comments (restating the code)
- [ ] No one-use helper functions
- [ ] No phantom defensive checks
- [ ] No speculative abstractions
- [ ] No verbose names where short ones are unambiguous
- [ ] No unasked-for boilerplate
- [ ] Tests still pass after cleanup
