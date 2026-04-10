# Daily Feature Scout — Autonomous Industry Research & Implementation

You are running inside the `local-llm-server` repository: a self-hosted
OpenAI-compatible proxy with bearer-token auth, dynamic model routing,
multi-agent orchestration, Langfuse observability, Telegram bot control,
and a web admin dashboard.

Execute every numbered step in order.  Do not skip any step.

---

## STEP 1 — Baseline

Run `pytest -x` and confirm tests are green before touching any code.
If the baseline is red, write a log entry to `docs/daily_scout_log.md`
under today's date explaining the failing tests, then stop — do not
attempt feature work on a broken baseline.

---

## STEP 2 — Research (last 7 days)

Use WebSearch to find what shipped or was announced in the past 7 days
across these sources.  For each, extract **concrete, shippable features**
— not vague roadmap items:

1. **Claude Code / Anthropic** — new CLI features, MCP protocol updates,
   agent harness patterns, hooks, context-engineering techniques, new API
   parameters, SDK changes, model capabilities.
2. **OpenAI Codex / ChatGPT** — new agentic modes, tool-use patterns,
   streaming improvements, new model endpoints, function-calling or
   structured-output additions.
3. **Lovable / v0 / Bolt / Replit Agent** — workspace sandboxing, live
   preview approaches, scaffolding or code-generation patterns.
4. **Emergent / Devin / SWE-agent / OpenHands** — multi-agent
   coordination, task-planning, memory architectures, tool-dispatch
   improvements.
5. **Cursor / Continue / Aider / Cline** — context retrieval, diff
   application, background-agent designs, IDE integration protocols.
6. **LLM infrastructure** — Ollama updates, vLLM / llama.cpp serving
   techniques, Langfuse / OpenTelemetry patterns, rate-limit strategies,
   token-budget management.

Produce a ranked candidate list ordered by:
- Relevance to this repo's architecture (proxy, routing, agent harness,
  observability, dashboard)
- Implementation effort (prefer high value / low effort)
- Novelty (not already present in this codebase)

---

## STEP 3 — Relevance Filter

Before selecting features to implement, read these files:

- `CLAUDE.md` — architecture map and coding rules
- `docs/changelog.md` — everything already shipped (do not re-implement)
- `README.md` lines 25-50 — the "What's New" section
- `proxy.py` — current middleware chain and feature singletons
- `router/model_router.py` — routing logic
- `agent/loop.py` — agent harness

From the ranked list, select only features that:
1. Are NOT already in the changelog or source
2. Fit the existing architecture without a large-scale rewrite
3. Can be fully implemented AND tested in this session
4. Are additive and backward-compatible (no breaking API changes)
5. Do not touch `admin_auth.py`, `key_store.py`, or `agent/tools.py`
   unless you invoke the `risky-module-review` skill first

If zero features qualify, write a log entry to `docs/daily_scout_log.md`
and stop.

---

## STEP 4 — Plan

For each selected feature, write an explicit plan before writing code:
- Which files to create or modify
- Public API / interface shape (Pydantic models for all I/O)
- Test file + test function names
- Changelog entry text
- Any new dependencies (run `dependency-audit` skill before adding any)

---

## STEP 5 — Implement (one feature at a time)

For each feature:

1. Write or update tests in `tests/` FIRST.
2. Implement the feature.
3. Run `pytest -x` — must be green before moving to the next feature.
4. If tests still fail after 2 fix attempts, abandon that feature, log it
   in `docs/daily_scout_log.md` under "Failed to land", continue to next.

Coding rules (from CLAUDE.md — must follow):
- `from __future__ import annotations` on all new files
- Type annotations on all public functions
- No secrets in source — all config via environment variables
- Pydantic models for all API I/O
- `async` for all I/O handlers
- `logging`, not `print` — use `log = logging.getLogger("qwen-proxy")`
- No speculative abstractions — implement only what the feature needs

---

## STEP 6 — Quality Gates

After all features are implemented and tests are green:

1. Invoke the `deslop` skill — remove AI code slop.
2. Invoke the `council-review` skill — multi-perspective review.
3. Fix any blocking issues raised, re-run `pytest -x` after fixes.

---

## STEP 7 — Update Changelog

Edit `docs/changelog.md`.  Under `## [Unreleased]`, add:

```markdown
### Added
- **<Feature Name>** (`<file.py>`): What it does and why it matters.
  Source: <tool/company the idea came from>.
```

---

## STEP 8 — Update README "What's New"

Edit `README.md`, section `## What's New` (around line 25):
1. Update the date label to today's date.
2. Prepend a bullet for each new feature (one line, plain English).
3. Do NOT remove existing bullets.

---

## STEP 9 — Final Test Run

Run `pytest -v`.  All tests must pass.  Fix any failures before Step 10.
Never push a red build.

---

## STEP 10 — Commit and Push

Stage only the files you changed (never `git add -A`).

Commit message format:

```
feat(scout): <short summary of features landed>

- <feature 1 one-liner>
- <feature 2 one-liner>

Sources: <comma-separated list of tools/companies>
Researched: <today's date>
Auto-landed by: daily_feature_scout
```

Push to master:

```bash
git push -u origin master
```

If push fails due to a remote conflict, run
`git pull --rebase origin master` then push again.
Retry up to 4 times with exponential backoff (2 s, 4 s, 8 s, 16 s).
If still failing, stop and log the error in `docs/daily_scout_log.md`.

---

## STEP 11 — Session Log

Append to `docs/daily_scout_log.md` (create if missing):

```markdown
## <today's date>

### Researched
- <source>: <summary of what was found>

### Landed
- <feature name> — <one-line description>

### Skipped
- <feature name> — <reason: already exists / too risky / tests failed / out of scope>

### Pushed
- Commit: <hash>
- Branch: master
```

---

## Hard Rules

- Never push a red build.
- Never break existing APIs — features must be additive.
- Never hardcode secrets — all config through environment variables.
- Never re-implement something already in the changelog.
- Never add external packages without running `dependency-audit` first.
- If a feature requires a breaking change to ship correctly, skip it.
- When uncertain about scope, choose the smaller, safer implementation.
