#!/usr/bin/env bash
# Stops all LLM server processes.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/server.pids"

echo "Stopping Local LLM Server..."

if [[ -f "$PID_FILE" ]]; then
    for name in tunnel proxy ollama; do
        procid=$(python3 -c "import json,sys; d=json.load(open('$PID_FILE')); print(d.get('$name',''))" 2>/dev/null)
        if [[ -n "$procid" && "$procid" != "null" ]]; then
            if kill -0 "$procid" 2>/dev/null; then
                kill "$procid" && echo "[OK] Stopped $name (PID $procid)"
            else
                echo "[--] $name (PID $procid) already stopped"
            fi
        fi
    done
    rm -f "$PID_FILE"
else
    echo "[!] No PID file found. Killing by process name..."
    pkill -f "cloudflared tunnel" 2>/dev/null && echo "[OK] Stopped cloudflared" || true
    pkill -f "uvicorn proxy:app"   2>/dev/null && echo "[OK] Stopped proxy"       || true
    pkill -f "ollama serve"        2>/dev/null && echo "[OK] Stopped ollama"      || true
fi

echo "Done."
