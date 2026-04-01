# NEXT ACTION — AI Engineering Retrofit

**Session:** `repo-ai-retrofit` (2026-04-01)
**Resume command:** `python scripts/ai_runner.py resume`
**Status file:** `.claude/state/agent-state.json`
**Checkpoint log:** `.claude/state/checkpoint.jsonl`

---

## Current Objective

Retrofit `local-llm-server` into a repo-native AI engineering system with:
durable memory, reusable skills, deterministic hooks, mandatory tests + changelog
enforcement, multi-agent orchestration, OpenClaw integration, and auto-resume.

---

## Completed Steps

- [x] Repo inspection (stack: Python 3.13, FastAPI, pytest, ollama proxy)
- [x] Directory scaffold created
- [x] Bootstrap state files written
- [x] `.gitignore` updated (allow `.claude/` project files)
- [x] Root `CLAUDE.md` created
- [x] Local `CLAUDE.md` for `agent/`, `router/`
- [x] `.claude/skills/` — all 10 required skills
- [x] `.claude/hooks/` — pre-commit, pre-push, commit-msg (blocking)
- [x] `.githooks/` upgraded (soft→hard changelog check)
- [x] GitHub Actions CI workflow
- [x] GitHub Actions changelog-check workflow
- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `.github/CODEOWNERS`
- [x] `.claude/agents/` — planner, implementer, reviewer, judge personas
- [x] `scripts/ai_runner.py` — auto-resume watchdog
- [x] `docs/architecture/` — overview, agent-orchestration
- [x] `docs/runbooks/` — auto-resume, release
- [x] `docs/adrs/` — 3 ADRs
- [x] `docs/admin/github-branch-protection.md`
- [x] Cleanup: reverted web UI work + removed Vercel artifacts/references

## Next Step

- [ ] **Step 17 — Self-test & verification**
  - Run `pytest` to ensure all tests still pass
  - Run hook simulation
  - Verify `scripts/ai_runner.py` checkpoint/resume cycle

## If Interrupted

1. Read `.claude/state/agent-state.json` for full plan state
2. Read `.claude/state/checkpoint.jsonl` for last successful checkpoint
3. Run `python scripts/ai_runner.py status` to see current state
4. Run `python scripts/ai_runner.py resume` to continue from last checkpoint
