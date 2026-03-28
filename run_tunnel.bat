@echo off
:: Starts a Cloudflare quick tunnel pointing at the proxy port.
:: Uses cloudflared from PATH, or CLOUDFLARED_EXE if set.

if "%PROXY_PORT%"=="" set PROXY_PORT=8000

if "%CLOUDFLARED_EXE%"=="" (
    cloudflared tunnel --url http://localhost:%PROXY_PORT%
) else (
    "%CLOUDFLARED_EXE%" tunnel --url http://localhost:%PROXY_PORT%
)
