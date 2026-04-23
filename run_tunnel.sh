#!/usr/bin/env bash
# Starts an ngrok tunnel pointing at the proxy port.
# If NGROK_DOMAIN is set, uses it as the static domain (--domain flag).

PROXY_PORT="${PROXY_PORT:-8000}"

# Resolve ngrok binary
if [ -n "$NGROK_EXE" ]; then
    NGROK_BIN="$NGROK_EXE"
elif [ -f "$HOME/.local/share/ngrok/ngrok" ]; then
    NGROK_BIN="$HOME/.local/share/ngrok/ngrok"
else
    NGROK_BIN="ngrok"
fi

if [ -n "$NGROK_DOMAIN" ]; then
    exec "$NGROK_BIN" http "$PROXY_PORT" --url="$NGROK_DOMAIN" --log=stderr
else
    exec "$NGROK_BIN" http "$PROXY_PORT" --log=stderr
fi
