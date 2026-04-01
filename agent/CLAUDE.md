# CLAUDE.md — agent/

> **RISKY MODULE.** This package orchestrates multi-step AI task execution and
> writes files to the filesystem. Read this entire file before modifying anything here.

---

## What This Package Does

`agent/` implements the three-role orchestration loop:

```
Planner  (deepseek-r1:32b)  → produces AgentPlan with ordered steps
Executor (qwen3-coder:30b)  → applies file changes per step
Verifier (deepseek-r1:32b)  → validates each change before it is written
```

The `AgentRunner.run()` method in `loop.py` drives the whole cycle.
`WorkspaceTools` in `tools.py` is the only place that writes to the filesystem.

---

## Security Surface

### `agent/tools.py` — `apply_diff()`

- This method **writes arbitrary content to disk**.
- It uses `path.resolve()` but does **NOT** enforce a strict root boundary by default.
- **Any change to path handling must be reviewed.** Ensure resolved paths stay within `self.root`.
- Never accept raw file paths from untrusted user input without validation.

### `agent/loop.py` — `_local_safety_check()`

- Scans generated code for hardcoded secrets (JWT secret keys, fake user DBs).
- If you add new risky patterns (e.g., OS command injection, eval), add them here.
- The verifier LLM is a best-effort check — do not rely on it as the sole security layer.

### `agent/loop.py` — `_commit_step()`

- Auto-commits with `git commit` when `auto_commit=True`.
- Only commits the specific `changed_files`, not the whole working tree.
- Never pass unsanitized step descriptions as commit messages without escaping.

---

## Invariants — Do Not Break

1. **Verifier must pass before `apply_diff` is called.** Never skip or bypass the `VerificationResult.status == "pass"` check.
2. **`max_steps` is always respected.** Never allow unbounded iteration.
3. **Retry limit is 3.** `while retries <= 2` — keep this bound.
4. **JSON extraction has a 3-attempt retry.** Beyond that, raise — don't silently swallow.
5. **`_local_syntax_check` runs before verification.** It catches Python parse errors cheaply.

---

## Adding New Tools

Tools available to the executor are defined in `_run_tool()` in `loop.py`.
To add a new tool:
1. Implement the operation in `tools.py`.
2. Add a dispatch case in `_run_tool()`.
3. Document the tool in `agent/models.py` (ToolCall schema).
4. Add tests in `tests/test_agent_tools.py`.

---

## Testing Expectations

- `tests/test_agent_runner.py` — integration tests for `AgentRunner` (uses mocks/monkeypatching).
- `tests/test_agent_tools.py` — unit tests for `WorkspaceTools`.
- Any new tool or loop change **must** include a test.
- Use `pytest -x tests/test_agent_runner.py tests/test_agent_tools.py` to run just agent tests.

---

## Model Env Vars

```
AGENT_PLANNER_MODEL   Default: deepseek-r1:32b
AGENT_EXECUTOR_MODEL  Default: qwen3-coder:30b
AGENT_VERIFIER_MODEL  Default: deepseek-r1:32b
```

Override these in `.env` for testing without large models.

---

## Skills to Use When Modifying This Package

- `risky-module-review` — mandatory for any change to `tools.py` or auth surface
- `test-first-executor` — write tests before implementing new tools
- `implementation-planner` — plan multi-step agent capability additions
