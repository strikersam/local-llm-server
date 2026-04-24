#!/usr/bin/env bash
# Starts the FastAPI auth proxy.
# Source .env before running, or set variables in your environment.

set -e

if [[ -z "${API_KEYS// }" && -z "${KEYS_FILE// }" ]]; then
  echo "[FAIL] Set API_KEYS and/or KEYS_FILE. Source .env or export before running." >&2
  exit 1
fi
export OLLAMA_BASE="${OLLAMA_BASE:-http://localhost:11434}"
export PROXY_PORT="${PROXY_PORT:-8000}"
export RATE_LIMIT_RPM="${RATE_LIMIT_RPM:-60}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export REGISTER_RUNTIMES="${REGISTER_RUNTIMES:-1}"
# Configure runtime adapters (Docker container URLs)
export HERMES_BASE_URL="${HERMES_BASE_URL:-http://localhost:8002}"
export OPENCODE_BASE_URL="${OPENCODE_BASE_URL:-http://localhost:8003}"
export GOOSE_BASE_URL="${GOOSE_BASE_URL:-http://localhost:8004}"
export AIDER_BASE_URL="${AIDER_BASE_URL:-http://localhost:8005}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -n "${PYTHON_EXE// }" ]]; then
  :
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
  PYTHON_EXE="$SCRIPT_DIR/.venv/bin/python"
else
  PYTHON_EXE="python3"
fi

cd "$SCRIPT_DIR"
exec "$PYTHON_EXE" -m uvicorn proxy:app --host 0.0.0.0 --port "$PROXY_PORT"
