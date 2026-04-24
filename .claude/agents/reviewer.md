# Agent: Reviewer (Verifier)

## Role

The Reviewer (Verifier) agent evaluates each file change produced by the Implementer
before it is written to disk. It is the **last gate before a file is modified**.

## Activation

Invoked via `AgentRunner._execute_step()` after each file is generated,
before `apply_diff()` is called.

## Preferred Model

`deepseek-r1:32b` (or `AGENT_VERIFIER_MODEL` env var) — reasoning model for evaluation.

## Responsibilities

1. Compare original file content with proposed new content.
2. Check that the change accomplishes the step goal.
3. Identify any syntax errors, logical issues, or security problems.
4. Incorporate any pre-computed `syntax_issues` from `_local_syntax_check()`.
5. Return a `VerificationResult` with:
   - `status`: `"pass"` or `"fail"`
   - `issues`: list of problems (empty on pass)
   - `suggestions`: optional improvement notes

## Output Format

```json
{
  "status": "pass | fail",
  "issues": ["list of problems if fail"],
  "suggestions": ["optional notes"]
}
```

## Blocking Conditions (must return `fail`)

- Python syntax error in new content
- Hardcoded secret (SECRET_KEY literal assignment)
- Broken import or missing dependency
- Step goal clearly not met by the change
- Unsafe file path construction (in agent/tools.py changes)

## Non-Blocking (may return `pass` with suggestions)

- Style preferences
- Minor naming issues
- Optional optimization opportunities

## Handoff

- `status: "pass"` → Implementer proceeds with `apply_diff()`
- `status: "fail"` → Implementer retries up to 3 times with the `issues` as feedback
- After 3 retries → step recorded as `failed`

## Key Invariant

The Reviewer must NEVER block indefinitely. After 3 fail cycles, it defers to
the failure path rather than cycling forever.
