#!/usr/bin/env bash
# Starts the FastAPI auth proxy.
# Source .env before running, or set variables in your environment.

set -e

export API_KEYS="${API_KEYS:-change-me}"
export OLLAMA_BASE="${OLLAMA_BASE:-http://localhost:11434}"
export PROXY_PORT="${PROXY_PORT:-8000}"
export RATE_LIMIT_RPM="${RATE_LIMIT_RPM:-60}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXE="${PYTHON_EXE:-python3}"

cd "$SCRIPT_DIR"
exec "$PYTHON_EXE" -m uvicorn proxy:app --host 0.0.0.0 --port "$PROXY_PORT"
