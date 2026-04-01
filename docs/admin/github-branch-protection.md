# GitHub Branch Protection Settings

## Purpose

This document lists the exact GitHub repository settings required to make the CI and
changelog checks **mandatory gates** for merging to `main` / `master`.

Without these settings, the checks run but can be bypassed. With them, no PR can
merge without all checks passing.

## Required Settings

Go to: **GitHub → Settings → Branches → Add branch protection rule**

### Branch name pattern: `main` (or `master`)

Enable the following:

| Setting | Value | Notes |
|---------|-------|-------|
| Require a pull request before merging | ✅ ON | |
| Required approvals | 1 (or more) | Adjust for team size |
| Dismiss stale PR approvals when new commits pushed | ✅ ON | Prevents approving then force-pushing |
| Require review from Code Owners | ✅ ON | Uses `.github/CODEOWNERS` |
| Require status checks to pass before merging | ✅ ON | |
| **Required status checks:** | | |
| → `test` (from `ci.yml`) | ✅ REQUIRED | Runs pytest |
| → `lint` (from `ci.yml`) | ✅ REQUIRED | Secret scan + syntax |
| → `changelog` (from `changelog-check.yml`) | ✅ REQUIRED | Blocks if no entry |
| Require branches to be up to date before merging | ✅ ON | No stale PRs |
| Require conversation resolution before merging | ✅ ON | |
| Restrict pushes that create matching branches | Optional | |
| Do not allow bypassing the above settings | ✅ ON | Admins also blocked |

## CODEOWNERS Setup

Update `.github/CODEOWNERS` to replace `@your-github-username` with actual GitHub usernames:

```
# Example:
*                          @swami
admin_auth.py              @swami
key_store.py               @swami
agent/tools.py             @swami
```

## Enabling via GitHub CLI

```bash
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  -f required_status_checks='{"strict":true,"contexts":["test","lint","changelog"]}' \
  -f enforce_admins=true \
  -f required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  -f restrictions=null
```

Adjust `{owner}/{repo}` to your actual repo path.

## Why This Can't Be Fully Repo-Enforced

GitHub branch protection is a server-side setting. The repo can contain all the CI
workflow files and hooks, but a repository admin can still push directly to `main`
unless branch protection is configured in the GitHub UI or via the API.

The local `.claude/hooks/pre-push` hook prevents accidental direct pushes from
developer machines, but does not prevent force-pushes or server-side API pushes.

**Always configure branch protection for production/shared repos.**
