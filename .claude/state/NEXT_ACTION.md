# NEXT ACTION — Hosted Control Plane Regression Follow-up

**Session:** `hosted-control-plane-regressions` (2026-05-02)
**Resume command:** `python scripts/ai_runner.py resume`
**Status file:** `.claude/state/agent-state.json`
**Checkpoint log:** `.claude/state/checkpoint.jsonl`

---

## Current Objective

The hosted Control Plane regressions are fixed locally. The next meaningful step is to
merge the branch, let Render/GitHub Pages deploy, and re-run hosted browser QA
including direct-chat code-edit scenarios.

---

## Completed Steps

- [x] Reproduced hosted schedule creation 404s, missing observability endpoints, and agent profile schema drift
- [x] Added backend schedule + observability coverage for `backend.server:app`
- [x] Restored frontend build/test tooling by re-adding `react-scripts`
- [x] Fixed frontend schedules/logs data handling and removed fake recent-run samples
- [x] Added regression coverage for hosted schedules, observability, and agent profile persistence
- [x] Ran `python3 -m pytest -x` successfully (`729 passed, 15 skipped`)
- [x] Ran frontend test suite successfully (`46 passed`)
- [x] Verified `npm run build` succeeds for the GitHub Pages frontend

## Next Step

- [ ] Push the branch and merge it to `master`
- [ ] Wait for Render + GitHub Pages to finish deploying
- [ ] Verify the live hosted site:
  - schedules can be created from the UI without 404s
  - logs/activity/metrics tabs show real data instead of empty or fake states
  - Engineer agent profiles retain role/runtime/task metadata
  - direct chat handles complex code-edit / commit-oriented prompts acceptably

## If Interrupted

1. Read `.claude/state/agent-state.json` for full plan state
2. Read `.claude/state/checkpoint.jsonl` for last successful checkpoint
3. Run `python scripts/ai_runner.py status` to see current state
4. Run `python scripts/ai_runner.py resume` to continue from last checkpoint
