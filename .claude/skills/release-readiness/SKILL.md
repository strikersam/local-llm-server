---
name: release-readiness
description: >
  Gate check before tagging and releasing a new version.
  Run this skill before any `git tag vX.Y.Z` operation.
triggers:
  - "release version X"
  - "tag a release"
  - "prepare for release"
  - "is this ready to release?"
references:
  - docs/runbooks/release.md
  - docs/changelog.md
  - .github/workflows/ci.yml
---

# Skill: release-readiness

## When to Use

Before any version tag or deployment to a production/shared instance.

## Instructions

Work through this checklist in order. Do not proceed to the next step if any item fails.

### 1 — Tests green

```bash
pytest -v
```

All tests must pass. Zero failures, zero errors.

### 2 — Changelog updated

```bash
grep -n "Unreleased" docs/changelog.md
```

There must be at least one entry under `## [Unreleased]`.
If the section says `_(nothing pending)_`, the changelog has NOT been updated — stop here.

### 3 — Determine the version bump

Using [Semantic Versioning](https://semver.org/):
- `MAJOR` — breaking API or behaviour change (existing clients must change)
- `MINOR` — new feature, backwards-compatible
- `PATCH` — bug fix, backwards-compatible

Check `docs/changelog.md` for the current version to determine the next version.

### 4 — Update changelog

In `docs/changelog.md`:
1. Change `## [Unreleased]` to `## [X.Y.Z] — YYYY-MM-DD`
2. Add a new empty `## [Unreleased]` section at the top with `_(nothing pending)_`

### 5 — Commit the changelog update

```bash
git add docs/changelog.md
git commit -m "chore: release vX.Y.Z"
```

### 6 — Tag the release

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

### 7 — Verify CI on the tag

Check that the CI workflow passes on the tagged commit.
See `.github/workflows/ci.yml`.

### 8 — Post-release

- Update `.env.example` if any new environment variables were introduced.
- Update `README.md` if setup instructions changed.
- Notify via Telegram bot if the server is running: `python telegram_bot.py` (if configured).

## Acceptance Checks

- [ ] `pytest -v` exits 0
- [ ] `docs/changelog.md` `[Unreleased]` section had entries
- [ ] Changelog moved to versioned section with date
- [ ] `git tag vX.Y.Z` created
- [ ] CI passes on the tag
- [ ] `.env.example` updated if needed
- [ ] `README.md` updated if needed

## Rollback Plan

If a release is found to be broken after tagging:
1. Delete the tag: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`
2. Revert the release commit: `git revert HEAD`
3. Fix the issue in a new commit
4. Re-run this release-readiness checklist
