---
name: changelog-enforcer
description: >
  Ensure every meaningful change has a proper docs/changelog.md entry.
  Use before every commit that changes behaviour, adds features, or fixes bugs.
triggers:
  - before any git commit with code changes
  - "update the changelog"
  - "add a changelog entry"
  - CI changelog-check failing
references:
  - docs/changelog.md
  - https://keepachangelog.com/en/1.0.0/
---

# Skill: changelog-enforcer

## When to Use

Before EVERY commit that is not purely:
- `chore:` — dependency bumps, tooling config
- `docs:` — doc-only changes (unless the doc IS the changelog)
- `style:` — formatting only
- `ci:` — CI/workflow-only changes
- `test:` — test-only additions with no behaviour change

If in doubt, add a changelog entry. Entries are cheap; missing them causes release confusion.

## Changelog Location

`docs/changelog.md` — follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.

## Entry Format

Add under `## [Unreleased]` at the top of the file:

```markdown
## [Unreleased]

### Added
- Brief description of new feature or capability. (#PR or commit reference if known)

### Changed
- What existing behaviour changed and how.

### Fixed
- What bug was fixed and what the symptom was.

### Security
- Any change touching auth, API keys, secrets, or access control.

### Removed
- Features, endpoints, or options that were removed.
```

Only include subsections that are relevant to the commit.

## Instructions

1. Read `docs/changelog.md` to find the `[Unreleased]` block.
2. Add a new entry under the appropriate subsection.
3. Be specific: mention the module, the route, or the behaviour that changed.
4. Include the reason if non-obvious.
5. Stage `docs/changelog.md` alongside the code change.

## Examples

**Good entries:**
```
### Added
- `router/registry.py` — `fast_response` category routes short streaming requests to `qwen3-coder:7b` (lightest model) to reduce latency.

### Fixed
- `agent/loop.py` — `_parse_execution_response` now handles Windows-style CRLF line endings without corrupting file content.

### Security
- `key_store.py` — API keys are now hashed with SHA-256 before storage; plain-text keys are no longer written to `keys.json`.
```

**Bad entries (too vague):**
```
### Changed
- Updated some stuff.
- Fixed bug.
```

## Acceptance Checks

- [ ] `docs/changelog.md` has at least one new entry under `[Unreleased]`
- [ ] Entry uses correct subsection (`Added` / `Changed` / `Fixed` / `Security` / `Removed`)
- [ ] Entry names the specific file or feature that changed
- [ ] `git diff --cached -- docs/changelog.md` shows staged changes
- [ ] CI `changelog-check` job will pass (see `.github/workflows/changelog-check.yml`)

## Hook Behaviour

The `commit-msg` hook in `.Codex/hooks/commit-msg` will reject commits with
code changes but no `docs/changelog.md` staged update, unless the commit
subject starts with `chore:`, `docs:`, `style:`, `ci:`, or `test:`.
