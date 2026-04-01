# Release Procedure

See also: `.claude/skills/release-readiness/SKILL.md`

## Pre-Flight

1. Run `pytest -v` — all tests must pass
2. Confirm `docs/changelog.md` has content under `## [Unreleased]`
3. Run `make audit` — no hardcoded secrets, no obvious security issues
4. Run `make changelog-check` — confirms non-empty [Unreleased]

## Version Bump

Determine the version bump type:
- `MAJOR` (X+1.0.0) — breaking API change, endpoint removal, incompatible behaviour
- `MINOR` (X.Y+1.0) — new feature, new endpoint, backwards-compatible
- `PATCH` (X.Y.Z+1) — bug fix, dependency update, backwards-compatible

## Changelog Update

In `docs/changelog.md`:

1. Rename `## [Unreleased]` to `## [X.Y.Z] — YYYY-MM-DD`
2. Add new `## [Unreleased]` section at top with `_(nothing pending)_`

## Commit and Tag

```bash
git add docs/changelog.md
git commit -m "chore: release vX.Y.Z"
git tag vX.Y.Z
git push origin HEAD
git push origin vX.Y.Z
```

## Verify CI

Check that the CI workflow passes on the tagged commit.
Go to: GitHub Actions → CI → latest run on the tag.

## Post-Release Checklist

- [ ] Tests green on CI
- [ ] Changelog merged to main
- [ ] Tag pushed
- [ ] `.env.example` updated if new env vars were added
- [ ] `README.md` updated if setup instructions changed
- [ ] Telegram bot notified (if configured)

## Rollback

```bash
# Delete tag
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z

# Revert release commit
git revert HEAD
git push origin HEAD

# Fix issue, then re-release
```
