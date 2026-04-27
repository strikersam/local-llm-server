---
name: dependency-audit
description: >
  Review, validate, and update Python dependencies safely.
  Use when adding a new package, upgrading an existing one, or reviewing the dependency surface.
triggers:
  - "add dependency X"
  - "upgrade package Y"
  - "is this package safe?"
  - "dependency audit"
  - any edit to requirements.txt
references:
  - requirements.txt
  - docs/changelog.md
---

# Skill: dependency-audit

## When to Use

- Before adding any new package to `requirements.txt`
- Before upgrading a package to a new major version
- Periodically (quarterly) to audit for known CVEs

## Instructions

### Step 1 — Evaluate the new dependency

Answer these questions:
1. **Is it necessary?** Can this be done with the stdlib or an already-imported package?
2. **Is it maintained?** Check the GitHub repo — recent commits, open issues, last release.
3. **Is the license compatible?** This project appears MIT/Apache-compatible. Avoid GPL dependencies unless isolated.
4. **What is the download / adoption level?** Low-adoption packages carry higher supply chain risk.
5. **Does it have known CVEs?** Check https://pypi.org/project/<name>/ and https://osv.dev.

### Step 2 — Pin appropriately

This repo uses `>=` version lower bounds in `requirements.txt`.
- Use `>=X.Y.Z` with a known-working version.
- For security-sensitive packages (auth, crypto), prefer `>=X.Y.Z,<X+1` (major-pinned).

### Step 3 — Install and verify

```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -x
```

All existing tests must still pass after the dependency change.

### Step 4 — Check for conflicts

```bash
pip check
```

No dependency conflicts should be reported.

### Step 5 — Update changelog

Add an entry to `docs/changelog.md`:

```markdown
### Changed
- `requirements.txt` — added `<package>>=X.Y.Z` for <reason>.
```

or

```markdown
### Changed
- `requirements.txt` — upgraded `<package>` from `>=X.Y` to `>=Z.W` for <reason>.
```

### Step 6 — Update `.env.example` if needed

If the new package requires configuration (API keys, URLs), add example env vars to `.env.example`.

## Acceptance Checks

- [ ] Necessity evaluated — stdlib/existing package could not do the job
- [ ] License checked — compatible with project
- [ ] No known CVE at time of addition (note if CVE exists and is accepted)
- [ ] `requirements.txt` updated with appropriate version bound
- [ ] `pytest -x` passes after adding package
- [ ] `pip check` shows no conflicts
- [ ] `docs/changelog.md` updated
- [ ] `.env.example` updated if new config required

## Current Dependencies (quick reference)

| Package | Purpose | Risk Level |
|---------|---------|------------|
| fastapi | Web framework | Low |
| uvicorn | ASGI server | Low |
| httpx | HTTP client (async) | Low |
| python-dotenv | Env loading | Low |
| langfuse | Observability | Medium (external API) |
| jinja2 | Templating | Low |
| python-multipart | File uploads | Low |
| itsdangerous | Session signing | Medium (crypto) |
| pytest | Testing | Dev only |
| pyngrok | Tunnel | Medium (external service) |
