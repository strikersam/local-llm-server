#!/usr/bin/env bash
# duplicate.sh — duplicate-thread skill
# Usage: bash .claude/skills/duplicate-thread/duplicate.sh <source-thread-id> <reason>
# Creates a fork of the source thread under .claude/threads/

set -euo pipefail

SOURCE_ID="${1:?Usage: duplicate.sh <source-thread-id> <reason>}"
REASON="${2:?Provide a reason/label for the fork (no spaces, use dashes)}"
THREADS_DIR=".claude/threads"
SOURCE_DIR="${THREADS_DIR}/${SOURCE_ID}"

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: Source thread directory not found: $SOURCE_DIR"
  echo "Available threads:"
  ls "$THREADS_DIR" 2>/dev/null || echo "  (none)"
  exit 1
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE_SLUG=$(date -u +"%Y%m%d-%H%M%S")
FORK_ID="${SOURCE_ID}--fork-${REASON}"
FORK_DIR="${THREADS_DIR}/${FORK_ID}"

if [[ -d "$FORK_DIR" ]]; then
  echo "ERROR: Fork already exists: $FORK_DIR"
  echo "Choose a different reason label or remove the existing fork."
  exit 1
fi

echo "Duplicating thread: $SOURCE_ID → $FORK_ID"
cp -r "$SOURCE_DIR" "$FORK_DIR"

# Write meta.json
cat > "${FORK_DIR}/meta.json" <<EOF
{
  "thread_id": "${FORK_ID}",
  "forked_from": "${SOURCE_ID}",
  "fork_reason": "${REASON}",
  "forked_at": "${TIMESTAMP}",
  "status": "active"
}
EOF

# Stamp the fork notice at the top of PLAN.md if it exists
if [[ -f "${FORK_DIR}/PLAN.md" ]]; then
  FORK_NOTICE="<!-- FORKED from ${SOURCE_ID} at ${TIMESTAMP} | reason: ${REASON} -->\n\n"
  TMP=$(mktemp)
  printf '%b' "$FORK_NOTICE" | cat - "${FORK_DIR}/PLAN.md" > "$TMP"
  mv "$TMP" "${FORK_DIR}/PLAN.md"
fi

echo ""
echo "✅ Fork created: ${FORK_DIR}"
echo "   Source:  ${SOURCE_DIR}"
echo "   Fork ID: ${FORK_ID}"
echo "   Reason:  ${REASON}"
echo "   Time:    ${TIMESTAMP}"
echo ""
echo "Next steps:"
echo "  • Edit ${FORK_DIR}/PLAN.md to adjust the forked plan"
echo "  • Run agents against the fork independently"
echo "  • On success: set status=merged in ${FORK_DIR}/meta.json"
echo "  • On failure: set status=abandoned and return to ${SOURCE_DIR}"
