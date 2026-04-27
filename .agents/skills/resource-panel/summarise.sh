#!/usr/bin/env bash
# summarise.sh — resource-panel skill
# Generates a resource panel from current git working tree state
# Usage: bash .claude/skills/resource-panel/summarise.sh [base_ref]

BASE_REF="${1:-HEAD}"

# ── Gather data ──────────────────────────────────────────────────────────────

# Changed files
MODIFIED=$(git diff --name-status "$BASE_REF" 2>/dev/null | grep '^M' | awk '{print $2}')
CREATED=$(git diff --name-status "$BASE_REF" 2>/dev/null | grep '^A' | awk '{print $2}')
DELETED=$(git diff --name-status "$BASE_REF" 2>/dev/null | grep '^D' | awk '{print $2}')
UNTRACKED=$(git ls-files --others --exclude-standard 2>/dev/null)

# New dependencies
NEW_DEPS=""
if git diff "$BASE_REF" -- package.json 2>/dev/null | grep -q '^+'; then
  PKG_DEPS=$(git diff "$BASE_REF" -- package.json 2>/dev/null \
    | grep '^+' | grep -v '^+++' | grep '"' | grep -v 'version\|name\|description' \
    | sed 's/.*"\([^"]*\)".*/npm:\1/' | head -10)
  NEW_DEPS="$NEW_DEPS $PKG_DEPS"
fi
if git diff "$BASE_REF" -- requirements.txt 2>/dev/null | grep -q '^+'; then
  PY_DEPS=$(git diff "$BASE_REF" -- requirements.txt 2>/dev/null \
    | grep '^+' | grep -v '^+++' | sed 's/^+/pip:/' | head -10)
  NEW_DEPS="$NEW_DEPS $PY_DEPS"
fi
if git diff "$BASE_REF" -- go.mod 2>/dev/null | grep -q '^+'; then
  GO_DEPS=$(git diff "$BASE_REF" -- go.mod 2>/dev/null \
    | grep '^+' | grep -v '^+++' | grep 'require' | sed 's/.*require /go:/' | head -10)
  NEW_DEPS="$NEW_DEPS $GO_DEPS"
fi
NEW_DEPS=$(echo "$NEW_DEPS" | xargs)  # trim

# Counts
MOD_COUNT=$(echo "$MODIFIED" | grep -c . || true)
CRE_COUNT=$(echo "$CREATED" | grep -c . || true)
DEL_COUNT=$(echo "$DELETED" | grep -c . || true)
UNT_COUNT=$(echo "$UNTRACKED" | grep -c . || true)
TOTAL_WRITTEN=$(( CRE_COUNT + MOD_COUNT ))
TOTAL_CHANGED=$(( MOD_COUNT + CRE_COUNT + DEL_COUNT + UNT_COUNT ))

# ── Render panel ─────────────────────────────────────────────────────────────

W=56  # panel width

pad_right() {
  local text="$1"
  local width="$2"
  printf "%-${width}s" "$text"
}

divider() { printf '╠%s╣\n' "$(printf '═%.0s' $(seq 1 $W))"; }
top()     { printf '╔%s╗\n' "$(printf '═%.0s' $(seq 1 $W))"; }
bottom()  { printf '╚%s╝\n' "$(printf '═%.0s' $(seq 1 $W))"; }
row()     { printf '║ %-*s ║\n' $(( W - 2 )) "$1"; }

top
row "$(pad_right '                  RESOURCE PANEL' $(( W - 2 )))"
divider
row "$(pad_right "FILES MODIFIED     │ ${MOD_COUNT} files" $(( W - 2 )))"
row "$(pad_right "FILES CREATED      │ ${CRE_COUNT} files" $(( W - 2 )))"
row "$(pad_right "FILES DELETED      │ ${DEL_COUNT} files" $(( W - 2 )))"
row "$(pad_right "UNTRACKED NEW      │ ${UNT_COUNT} files" $(( W - 2 )))"
if [[ -n "$NEW_DEPS" ]]; then
  row "$(pad_right "NEW DEPS           │ ${NEW_DEPS}" $(( W - 2 )))"
fi

if [[ $TOTAL_CHANGED -gt 0 ]]; then
  divider
  row "CHANGED FILES"
  for f in $MODIFIED; do
    row "  $(pad_right "$f" 30) [modified]"
  done
  for f in $CREATED; do
    row "  $(pad_right "$f" 30) [created]"
  done
  for f in $DELETED; do
    row "  $(pad_right "$f" 30) [deleted]"
  done
  for f in $UNTRACKED; do
    row "  $(pad_right "$f" 30) [untracked]"
  done
fi

bottom
