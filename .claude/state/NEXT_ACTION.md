# NEXT ACTION — GitHub Pages Bug Sweep

**Session:** `github-pages-bug-sweep` (2026-04-25)
**Resume command:** `python scripts/ai_runner.py resume`
**Status file:** `.claude/state/agent-state.json`
**Checkpoint log:** `.claude/state/checkpoint.jsonl`

---

## Current Objective

The deployment/auth bug sweep is complete locally. The next meaningful step is to
deploy the updated frontend/backend and verify the GitHub Pages login/bootstrap
flow against the live site.

---

## Completed Steps

- [x] Reproduced the router baseline failure and GitHub Pages/frontend auth issues locally
- [x] Fixed router alias resolution so explicit `MODEL_MAP` aliases remain deterministic
- [x] Added pre-login bootstrap access for static frontend deployments
- [x] Fixed frontend token refresh and redirect logic to respect the active backend URL and `PUBLIC_URL`
- [x] Fixed GitHub OAuth popup origin checks to use the configured backend origin
- [x] Stabilized router/v3 auth tests against host-specific environment differences
- [x] Updated changelog and added deployment-focused regression coverage
- [x] Ran `./.venv/bin/pytest -x` successfully (`613 passed`)
- [x] Verified `/bootstrap` and `/login` locally in the browser

## Next Step

- [ ] Deploy the updated branch/build to the live environment
- [ ] Verify the live GitHub Pages site:
  - login page still authenticates against the configured backend
  - `/bootstrap` is reachable before auth
  - expired-token redirects stay under `/local-llm-server/...`
  - GitHub OAuth popup/redirect flow still completes with the configured backend
- [ ] Optionally add end-to-end browser coverage for the public deployment path

## If Interrupted

1. Read `.claude/state/agent-state.json` for full plan state
2. Read `.claude/state/checkpoint.jsonl` for last successful checkpoint
3. Run `python scripts/ai_runner.py status` to see current state
4. Run `python scripts/ai_runner.py resume` to continue from last checkpoint
