#!/usr/bin/env bash
# heartbeat.sh — task-alive-updates skill helper
# Usage: source this file, then call heartbeat_start / heartbeat_stop

HEARTBEAT_PID=""
HEARTBEAT_START_EPOCH=""
HEARTBEAT_STEP="initializing"
HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-30}"

heartbeat_start() {
  local initial_step="${1:-running}"
  HEARTBEAT_STEP="$initial_step"
  HEARTBEAT_START_EPOCH=$(date +%s)

  (
    while true; do
      sleep "$HEARTBEAT_INTERVAL"
      local now
      now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
      local elapsed=$(( $(date +%s) - HEARTBEAT_START_EPOCH ))
      echo "[ALIVE] ${now} | step: ${HEARTBEAT_STEP} | elapsed: ${elapsed}s | status: in progress"
    done
  ) &

  HEARTBEAT_PID=$!
  # Ensure heartbeat is killed if the parent exits unexpectedly
  trap 'heartbeat_stop "interrupted"' EXIT INT TERM
}

heartbeat_set_step() {
  HEARTBEAT_STEP="${1:-unknown}"
}

heartbeat_stop() {
  local result="${1:-success}"
  if [[ -n "$HEARTBEAT_PID" ]]; then
    kill "$HEARTBEAT_PID" 2>/dev/null
    wait "$HEARTBEAT_PID" 2>/dev/null
    HEARTBEAT_PID=""
  fi
  local now
  now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  local elapsed=$(( $(date +%s) - HEARTBEAT_START_EPOCH ))
  echo "[DONE]  ${now} | elapsed: ${elapsed}s | result: ${result}"
  # Remove the EXIT trap so it doesn't double-fire
  trap - EXIT INT TERM
}
