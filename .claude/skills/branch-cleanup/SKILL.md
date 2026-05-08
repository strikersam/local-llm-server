---
name: branch-cleanup
description: >
  Delete remote and local branches that have been merged into master.
  Run after every merge to keep the repo to master-only.
  Supports both git-push deletion and GitHub API deletion (when git push --delete
  returns 403 due to proxy restrictions).
triggers:
  - "delete merged branches"
  - "clean up branches"
  - "remove stale branches"
  - "branch cleanup"
  - "leave only master"
  - "merged, delete the branch"
  - "push to master and clean up"
references:
  - docs/changelog.md
  - CLAUDE.md
---

# Skill: branch-cleanup

## When to Use

Run this skill:
- After merging any feature/fix branch into master
- After a release, when multiple branches have been absorbed
- Any time `git branch -a` shows branches beyond `master` and `gh-pages`

**Protected branches — never delete:**
- `master`
- `gh-pages` (GitHub Pages deployment)

---

## Step 1 — Confirm master is up to date

```bash
git fetch origin
git status
```

Make sure you are on `master` and `Your branch is up to date with 'origin/master'`.
If not, push first before touching branches.

---

## Step 2 — List all remote branches

```bash
git branch -r | grep -v 'origin/master\|origin/gh-pages\|origin/HEAD'
```

For each branch listed, check whether it is fully merged:

```bash
git log origin/master..origin/<branch-name> --oneline
```

- **Empty output** → fully merged, safe to delete.
- **Commits listed** → unmerged work; merge it into master first (see Step 3), then return here.

---

## Step 3 — Merge any unmerged branches (if needed)

For each branch with unmerged commits:

```bash
git merge --no-ff origin/<branch-name> -m "Merge branch '<branch-name>'"
```

Resolve any conflicts (keep HEAD for code files; merge both sides for `docs/changelog.md`).
Run tests before committing the merge:

```bash
pytest -x -q
```

Then push:

```bash
git push origin master
```

---

## Step 4 — Delete merged branches

### Option A — git push (standard)

```bash
git push origin --delete <branch-name>
```

Repeat for every merged branch. If this returns 204 or succeeds, you are done.

### Option B — GitHub API (use when `git push --delete` returns 403)

This happens when the git remote is proxied and lacks delete-refs permission.
Requires a GitHub PAT with `repo` scope (or `delete_head_branch` permission).

```bash
curl -s -o /dev/null -w "%{http_code}" -X DELETE \
  -H "Authorization: token <GITHUB_PAT>" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<owner>/<repo>/git/refs/heads/<branch-name>"
```

Expected response: `204` (success). Any other code means failure — check PAT permissions.

To delete all merged branches in one pass:

```bash
REPO="<owner>/<repo>"
PAT="<GITHUB_PAT>"
for branch in <branch1> <branch2> <branch3>; do
  status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "Authorization: token $PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$REPO/git/refs/heads/$branch")
  [ "$status" = "204" ] && echo "✓ deleted $branch" || echo "✗ failed $branch (HTTP $status)"
done
```

### Option C — Delete local tracking refs after remote deletion

```bash
git fetch --prune
git branch -d <branch-name>   # safe delete (refuses if unmerged)
```

---

## Step 5 — Verify

```bash
git fetch --prune
git branch -a
```

Expected output contains only:
```
* master
  remotes/origin/master
  remotes/origin/gh-pages
```

---

## Step 6 — Security note on PATs

If a GitHub PAT was shared or pasted in plaintext during this session:
**Revoke and regenerate it immediately** at https://github.com/settings/tokens.
Never commit a PAT to the repository.

---

## Automation — post-merge hook (optional)

To trigger this automatically after every successful push to master, add to
`.claude/hooks/post-push.sh` (create if it doesn't exist):

```bash
#!/usr/bin/env bash
# After pushing master, delete the branch we just merged from (if set).
if [ -n "$MERGED_BRANCH" ]; then
  git push origin --delete "$MERGED_BRANCH" 2>/dev/null || \
  curl -s -X DELETE \
    -H "Authorization: token $GITHUB_PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/$GITHUB_REPO/git/refs/heads/$MERGED_BRANCH"
fi
```

Set `MERGED_BRANCH` before pushing:
```bash
MERGED_BRANCH=claude/my-feature git push origin master
```

---

## Acceptance Checks

- [ ] `git branch -a` shows only `master` and `gh-pages` on remote
- [ ] All merged branches confirmed empty (`git log origin/master..origin/<b>` returns nothing)
- [ ] Any PAT used in plaintext has been revoked and regenerated
- [ ] `pytest -x -q` still green after all merges
