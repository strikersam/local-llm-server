#!/usr/bin/env bash
# setup-autostart.sh — Install the LLM Relay systemd service so the entire
# docker-compose stack (proxy, MCP server, runtimes, Ollama, MongoDB) starts
# automatically on boot with no manual intervention.
#
# Run once as root on the host machine:
#   sudo bash scripts/setup-autostart.sh
#
# After installation:
#   systemctl status llm-relay    — check service status
#   journalctl -u llm-relay -f    — tail logs
#   systemctl stop llm-relay      — stop everything
#   systemctl disable llm-relay   — remove from boot

set -euo pipefail

SERVICE_NAME="llm-relay"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_SRC="$SCRIPT_DIR/llm-relay.service"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}.service"

# ── Checks ────────────────────────────────────────────────────────────────────
if [[ "$(id -u)" != "0" ]]; then
  echo "Error: run as root — sudo bash $0" >&2
  exit 1
fi

if ! command -v docker &>/dev/null; then
  echo "Error: docker is not installed. Install Docker Engine first:" >&2
  echo "  https://docs.docker.com/engine/install/" >&2
  exit 1
fi

if ! docker compose version &>/dev/null 2>&1; then
  echo "Error: 'docker compose' (v2 plugin) is not available." >&2
  echo "Install Docker Compose v2: https://docs.docker.com/compose/install/" >&2
  exit 1
fi

if ! command -v systemctl &>/dev/null; then
  echo "Error: systemd not found. This script requires a systemd-based Linux distro." >&2
  exit 1
fi

if [[ ! -f "$REPO_DIR/docker-compose.yml" ]]; then
  echo "Error: docker-compose.yml not found at $REPO_DIR" >&2
  exit 1
fi

# ── Copy service file, patching WorkingDirectory to the real repo path ────────
if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "Error: service file not found at $SERVICE_SRC" >&2
  exit 1
fi
echo "Installing $SERVICE_DST…"
sed "s#/opt/local-llm-server#$REPO_DIR#g" "$SERVICE_SRC" > "$SERVICE_DST"
chmod 644 "$SERVICE_DST"

# ── Enable and start ──────────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
echo "Starting $SERVICE_NAME (this may take a few minutes on first run)…"
systemctl start "$SERVICE_NAME"

echo ""
echo "✓ LLM Relay auto-start installed and running"
echo ""
echo "  Status:  systemctl status $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo "  Stop:    systemctl stop $SERVICE_NAME"
echo "  Disable: systemctl disable $SERVICE_NAME"
