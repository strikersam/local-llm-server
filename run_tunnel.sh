#!/usr/bin/env bash
# Starts a Cloudflare quick tunnel pointing at the proxy port.

PROXY_PORT="${PROXY_PORT:-8000}"
CLOUDFLARED_EXE="${CLOUDFLARED_EXE:-cloudflared}"

exec "$CLOUDFLARED_EXE" tunnel --url "http://localhost:$PROXY_PORT"
