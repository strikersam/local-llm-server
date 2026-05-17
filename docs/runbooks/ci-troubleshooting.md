# CI Troubleshooting Runbook

Hard-won knowledge about GitHub Actions failures in this repo. Read this before
spending time re-diagnosing a CI failure you've seen before.

---

## Python test job fails — "Process completed with exit code 1", no .pytest_cache found

**What it means:** pytest did not run at all. A step *before* "Run tests" failed
(syntax check, pip install, MongoDB wait), which caused all subsequent steps to
be skipped. The "Upload test results" artifact step then fails because
`.pytest_cache/` was never created.

**Diagnosis checklist:**
1. Look at the *step* that failed, not just the job. The failing step is shown
   in red in the GitHub Actions UI — it is almost never "Run tests" when
   `.pytest_cache/` is absent.
2. If "Syntax check" failed: a `.py` file has a syntax error. Run
   `python -m py_compile` on the changed files locally.
3. If "Install dependencies" failed: a package version conflict or network error
   during `pip install -r requirements.txt`. Re-run the job; if it persists,
   check requirements.txt for conflicts.
4. If "Wait for MongoDB" failed: the MongoDB service container did not become
   healthy within 60 s. This is usually a transient runner issue — re-run.

---

## All three CI jobs fail with "git exit code 128" in Post Checkout

**What it means:** The `actions/checkout` post-cleanup step fails to remove git
credentials from the runner. This is a **runner-level transient issue**, not a
code problem.

**Fix (already applied):** All checkout steps in `ci.yml` and `codeql.yml` use
`persist-credentials: false`. This tells the action never to store git
credentials, so there is no credential cleanup step to fail.

```yaml
- uses: actions/checkout@v6
  with:
    persist-credentials: false
```

If the error recurs despite this setting, re-run the failed jobs — it is
almost always a transient runner issue.

---

## A test hangs in CI but passes locally

**Detection:** Without `pytest-timeout`, a hanging test occupies the full
6-hour GitHub Actions job limit with no output. With `--timeout=120` (now
configured), the test fails after 120 s with a clear `TIMEOUT` error that names
the test.

**Common causes:**

| Cause | Fix |
|-------|-----|
| Real HTTP call to Ollama (localhost:11434 not running in CI) | Mock the HTTP client — use `httpx.MockTransport` or `monkeypatch` on the httpx module |
| Real MongoDB call bypassing the motor mock | Confirm `sys.modules['motor']` mock is set in `conftest.py` before the import |
| `asyncio.sleep` with a large value in a test | Monkeypatch `asyncio.sleep` to a no-op in CI, or use a smaller value |
| `socket.create_connection` timeout (e.g. server-reachability check) | Ensure the check has a short timeout (≤ 1 s) |

**How to find the hanging test locally:**

```bash
pytest -x -v --timeout=30 2>&1 | tee /tmp/pytest-timeout.log
# Look for the last PASSED line before the process hangs
```

---

## GitHub Actions YAML block scalar — bash heredoc content at column 0

**Problem:** Bash heredocs require the closing delimiter at the **start of a
line** (column 0). YAML block scalars (`run: |`) require all non-blank content
to be **indented** at the block scalar level (typically 10 spaces). These two
constraints conflict.

**Broken pattern:**
```yaml
      - name: Create PR
        run: |
          PR_BODY="$(cat <<PRBODY
## Summary                    # ← column 0 breaks YAML block scalar
Closes #123
PRBODY                        # ← column 0 breaks YAML block scalar
          )"
```

**Correct pattern:** indent the heredoc content and delimiter to the block
scalar level (10 spaces). YAML strips those spaces before passing the script
to bash, so bash sees the delimiter at column 0 as required.

```yaml
      - name: Create PR
        run: |
          PR_BODY="$(cat <<PRBODY
          ## Summary           # ← indented; YAML strips to col 0 for bash
          Closes #123
          PRBODY               # ← indented; bash sees it at col 0 ✓
          )"
```

**Validation:** Always run `python3 -c "import yaml; yaml.safe_load(open('file.yml'))"` on any edited workflow file before committing.

```bash
for f in .github/workflows/*.yml; do
  python3 -c "import yaml; yaml.safe_load(open('$f'))" \
    && echo "OK: $f" || echo "INVALID: $f"
done
```

---

## Frontend tests fail in parallel / async timer leaks

**Symptom:** Tests pass individually (`npm test -- --testPathPattern=foo`) but
fail when the full suite runs in parallel.

**Cause:** `react-scripts@5` bundles Jest 27, which runs test files in parallel
worker processes by default. Async timers or pending promises from one test file
leak into the next.

**Fix (already applied in `ci.yml`):**

```yaml
run: npm test -- --watchAll=false --forceExit --runInBand
```

- `--runInBand` runs all test files serially in a single process — eliminates
  worker-to-worker leaks.
- `--forceExit` force-quits Jest after all tests finish, even if dangling async
  handles remain.
- `--watchAll=false` disables watch mode (required in CI).

---

## react-router-dom v7 + Jest 27 (react-scripts@5)

**Symptom:** `Cannot find module 'react-router-dom'` or
`Cannot find module 'react-router/dom'` during Jest test collection.

**Cause:** `react-router-dom@7` uses ESM sub-path exports (e.g.
`"react-router/dom"`) that Jest 27 — bundled with `react-scripts@5` — cannot
resolve. Jest 27 predates the Node.js sub-path exports spec adoption in Jest.

**Fix (already applied):** Pin `react-router-dom` to `^6.x` in
`frontend/package.json`. react-router-dom v6 has a CommonJS entry point that
Jest 27 resolves correctly.

```json
"dependencies": {
  "react-router-dom": "^6.28.2"
}
```

Do not upgrade to v7 until `react-scripts` is replaced with a Vite/Webpack 5
setup that supports the modern module resolution spec.

---

## @testing-library/dom peer dependency not installed

**Symptom:** `Cannot find module '@testing-library/dom'` when running frontend
tests.

**Cause:** `@testing-library/react@16` declares `@testing-library/dom` as a
*peer* dependency. `npm install --legacy-peer-deps` does not auto-install peer
dependencies declared this way.

**Fix (already applied):** explicitly add it to `devDependencies`:

```json
"devDependencies": {
  "@testing-library/dom": "^10.4.0"
}
```

---

## Python 3.13 compatibility status

All 1342 tests pass on Python 3.13 (confirmed May 2026 with `pytest-asyncio
1.3.0`, `asyncio_mode = auto`, `anyio 4.13.0`). Key notes:

- `asyncio_default_test_loop_scope = session` in `pytest.ini` is recognised by
  pytest-asyncio 1.3.0.
- `@pytest.mark.anyio` tests work via the `anyio` package's built-in pytest
  plugin (no separate `pytest-anyio` needed).
- Motor is fully mocked in `conftest.py` at module level — no real MongoDB
  connections are made during tests.

---

## CodeQL action version

`codeql.yml` uses `github/codeql-action@v4`. v3 was deprecated and fails.
Always use the latest major version; check
[github/codeql-action releases](https://github.com/github/codeql-action/releases)
when upgrading.
