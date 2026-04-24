---
name: risky-module-review
description: >
  Mandatory deep review for changes to security-sensitive modules:
  admin_auth.py, key_store.py, agent/tools.py, and any auth/session/key path.
  Do not skip this for any change to these files.
triggers:
  - any edit to admin_auth.py
  - any edit to key_store.py
  - any edit to agent/tools.py (file write surface)
  - any edit adding or changing auth middleware in proxy.py
  - any change involving JWT, sessions, cookies, API keys, or file system writes
references:
  - agent/CLAUDE.md
  - admin_auth.py
  - key_store.py
---

# Skill: risky-module-review

## Risky Modules in This Repo

| File | Risk | What to check |
|------|------|---------------|
| `admin_auth.py` | Session auth, admin identity | No secret leaks, session fixation prevention, proper expiry |
| `key_store.py` | API key persistence | Keys hashed before storage, no plaintext in logs, file permissions |
| `agent/tools.py` | Filesystem write surface | Path traversal prevention, content sanitization |
| `proxy.py` (auth middleware) | Bearer token validation | No bypass paths, rate limit correctness |
| `agent/loop.py` (`_local_safety_check`) | Security guardrail | Not weakened or removed |

## Instructions

### Step 1 — Read the module's CLAUDE.md

- `agent/` → `agent/CLAUDE.md`
- `router/` → `router/CLAUDE.md`
- No module CLAUDE.md? Read the file header docstring carefully.

### Step 2 — Checklist by module

#### `admin_auth.py` checklist
- [ ] Admin password is read from environment — never hardcoded
- [ ] Sessions expire (check `max_age` or `SESSION_MAX_AGE`)
- [ ] `AdminIdentity` is validated before any state-mutating action
- [ ] No `print()` or `log.debug()` exposes the admin password or session token
- [ ] CSRF protection present for state-mutating routes

#### `key_store.py` checklist
- [ ] API keys are stored hashed (SHA-256 or stronger) — never plaintext
- [ ] `keys.json` is never committed (it is in `.gitignore`)
- [ ] Key comparison uses constant-time comparison (`hmac.compare_digest`)
- [ ] No key value appears in any log line
- [ ] `issue_new_api_key` returns the plaintext key exactly once, immediately

#### `agent/tools.py` checklist
- [ ] `apply_diff` resolves paths with `Path.resolve()` and validates they stay within `self.root`
- [ ] No `..` traversal path accepted without rejection
- [ ] File content is not `eval()`-ed or `exec()`-ed
- [ ] `search_code` does not expose `.env` or `keys.json` content

#### `proxy.py` auth middleware checklist
- [ ] `verify_api_key()` cannot be bypassed by setting a header to empty string
- [ ] Rate limit is per-key, not per-IP (IP can be spoofed)
- [ ] `VALID_API_KEYS` from env is populated — empty set should reject all requests

### Step 3 — Run targeted tests

```bash
pytest -x tests/test_agent_api.py tests/test_agent_tools.py
```

### Step 4 — Write a security note in the PR description

```
## Security note
- Changed: <what changed>
- Risk: <what could go wrong>
- Mitigation: <how it is addressed>
- Verified by: risky-module-review skill
```

## Acceptance Checks

- [ ] All relevant checklist items above checked
- [ ] No secrets in source
- [ ] Path traversal not possible in file-write code
- [ ] Tests pass for affected module
- [ ] Security note included in PR description or commit message
- [ ] Changelog entry under `### Security` added if applicable

## Escalation

If a change would weaken an existing security check (e.g., remove path validation,
make auth optional), **stop and document the risk explicitly** before proceeding.
Prefer to add a feature flag rather than weaken a hard check.
