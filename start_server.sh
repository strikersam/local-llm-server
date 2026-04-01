#!/usr/bin/env bash
# Local LLM Server - Linux/macOS Startup Script
# Starts: Ollama -> Auth Proxy -> Cloudflare Tunnel

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_DIR="$SCRIPT_DIR/logs"

# -- Load .env ------------------------------------------------------------------
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    echo "[OK] Loaded .env"
else
    echo "[FAIL] .env not found. Copy .env.example to .env and configure it."
    exit 1
fi

mkdir -p "$LOG_DIR"

# -- Resolve executables --------------------------------------------------------
OLLAMA_EXE="${OLLAMA_EXE:-ollama}"
if [[ -n "${PYTHON_EXE// }" ]]; then
    :
elif [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON_EXE="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON_EXE="python3"
fi
CLOUDFLARED_EXE="${CLOUDFLARED_EXE:-cloudflared}"
PROXY_PORT="${PROXY_PORT:-8000}"

if ! command -v "$OLLAMA_EXE" &>/dev/null && [[ ! -x "$OLLAMA_EXE" ]]; then
    echo "[FAIL] Ollama not found. Set OLLAMA_EXE in .env or install from https://ollama.com"
    exit 1
fi

if ! command -v "$PYTHON_EXE" &>/dev/null; then
    echo "[FAIL] Python not found. Set PYTHON_EXE in .env or install Python 3."
    exit 1
fi

# -- Step 1: Start Ollama -------------------------------------------------------
echo ""
echo "[1/3] Starting Ollama..."

pkill -f "ollama serve" 2>/dev/null || true
sleep 1

export OLLAMA_MODELS="${OLLAMA_MODELS:-$HOME/.ollama/models}"
export OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"

"$SCRIPT_DIR/run_ollama.sh" >"$LOG_DIR/ollama.log" 2>"$LOG_DIR/ollama-err.log" &
OLLAMA_PID=$!

for i in $(seq 1 20); do
    sleep 1
    if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "[OK] Ollama ready (PID $OLLAMA_PID)"
        curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    gb = round(m['size']/1e9, 1)
    print(f'     - {m[\"name\"]} ({gb} GB)')
"
        break
    fi
    if [[ $i -eq 20 ]]; then
        echo "[FAIL] Ollama did not start. Check $LOG_DIR/ollama-err.log"
        exit 1
    fi
    echo "  Waiting for Ollama... ($i/20)"
done

# -- Step 2: Start Auth Proxy ---------------------------------------------------
echo ""
echo "[2/3] Starting Auth Proxy..."

pkill -f "uvicorn proxy:app" 2>/dev/null || true
sleep 0.5

"$SCRIPT_DIR/run_proxy.sh" >"$LOG_DIR/proxy.log" 2>"$LOG_DIR/proxy-err.log" &
PROXY_PID=$!

for i in $(seq 1 15); do
    sleep 1
    if curl -sf "http://localhost:$PROXY_PORT/health" >/dev/null 2>&1; then
        echo "[OK] Auth Proxy running on port $PROXY_PORT (PID $PROXY_PID)"
        break
    fi
    if [[ $i -eq 15 ]]; then
        echo "[FAIL] Proxy did not start. Check $LOG_DIR/proxy-err.log"
        exit 1
    fi
    echo "  Waiting for proxy... ($i/15)"
done

# -- Step 3: Start Cloudflare Tunnel --------------------------------------------
echo ""
echo "[3/3] Starting Cloudflare Tunnel..."

TUNNEL_PID=""

if ! command -v "$CLOUDFLARED_EXE" &>/dev/null; then
    echo "[SKIP] cloudflared not found. Run install.sh to set it up."
    echo "       Local only: http://localhost:$PROXY_PORT"
else
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    sleep 0.5

    "$SCRIPT_DIR/run_tunnel.sh" >"$LOG_DIR/tunnel.log" 2>"$LOG_DIR/tunnel-err.log" &
    TUNNEL_PID=$!

    sleep 8
    TUNNEL_URL=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' "$LOG_DIR/tunnel-err.log" 2>/dev/null | head -1)

    echo "[OK] Tunnel started (PID $TUNNEL_PID)"
    if [[ -n "$TUNNEL_URL" ]]; then
        echo ""
        echo "  >>> Public URL: $TUNNEL_URL <<<"
        echo ""
    else
        echo "  Check $LOG_DIR/tunnel-err.log for the public URL."
    fi
fi

# -- Save PIDs ------------------------------------------------------------------
cat > "$SCRIPT_DIR/server.pids" <<EOF
{
  "ollama": $OLLAMA_PID,
  "proxy": $PROXY_PID,
  "tunnel": ${TUNNEL_PID:-null}
}
EOF

# -- Summary --------------------------------------------------------------------
echo ""
echo "======================================================="
echo " Local LLM Server is Running!"
echo "======================================================="
echo " Local:   http://localhost:$PROXY_PORT"
echo " Health:  http://localhost:$PROXY_PORT/health"
echo " Logs:    $LOG_DIR/"
echo " Stop:    ./stop_server.sh"
echo "======================================================="
