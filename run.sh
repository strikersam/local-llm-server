#!/bin/bash
# Cross-platform Claude Code launcher (Unix entry point)
# Auto-detects OS and executes with proper error handling

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found in PATH"
    echo "Please install Python 3"
    exit 1
fi

# Execute the Python launcher, passing through all arguments
python3 run-claude-code.py "$@"
exit $?
