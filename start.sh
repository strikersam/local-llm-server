#!/usr/bin/env bash
# Replit startup script for LLM Relay Platform

set -e

PORT=${PORT:-5000}
HOST=0.0.0.0

echo "[INFO] Starting LLM Relay Platform on ${HOST}:${PORT}"

exec python3.12 -m uvicorn backend.server:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level info
