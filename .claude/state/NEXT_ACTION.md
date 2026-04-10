# NEXT ACTION — Hugging Face + Ollama Providers (Dashboard + Proxy)

**Session:** `hf-ollama-providers` (2026-04-10)
**Checkpoint log:** `.claude/state/checkpoint.jsonl`

---

## Current Objective

Ship first-class provider support for **Hugging Face serverless** and **Ollama** so the dashboard
(`http://localhost:3000`) can select providers/models without manual setup.

---

## Completed Steps

- [x] Fixed Playwright shutdown hang by default-disabling browser automation unless `BROWSER_AUTOMATION_ENABLED=true`
- [x] Added dashboard provider client helpers (`backend/llm_providers.py`) + unit tests
- [x] Wired dashboard chat UI to select provider + model (`frontend/src/pages/ChatPage.js`)
- [x] Added Docker profile for dashboard stack (Mongo + API + Web UI)
- [x] Updated `.env.example`, docs, and changelog
- [x] `pytest -x` green
- [x] Manual sanity-check: login + chat via Ollama (`tinyllama:latest`) through the dashboard API

## Next Step

- [ ] Stop local dev processes started for sanity-check (Ollama, dashboard backend, dashboard frontend)
- [ ] Commit changes in logical chunks, merge to `master`, and push (only if tests still pass)
