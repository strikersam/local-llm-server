#!/usr/bin/env bash
# Show the current public Cloudflare tunnel URL (Linux/macOS).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/tunnel-err.log"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "[!] Tunnel log not found. Is the server running?"
    exit 1
fi

URL=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' "$LOG_FILE" | head -1)

if [[ -n "$URL" ]]; then
    echo ""
    echo " Public URL: $URL"
    echo ""
    echo " API Base:  $URL/v1"
    # Copy to clipboard if available
    if command -v pbcopy &>/dev/null; then
        echo "$URL" | pbcopy && echo " (URL copied to clipboard)"
    elif command -v xclip &>/dev/null; then
        echo "$URL" | xclip -selection clipboard && echo " (URL copied to clipboard)"
    fi
else
    echo "[!] Could not find tunnel URL. Check logs/tunnel-err.log"
    tail -10 "$LOG_FILE"
fi
