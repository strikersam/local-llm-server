# Qwen3-Coder Server Startup
# Starts: Ollama -> Auth Proxy -> Cloudflare Tunnel
# Uses .bat launchers which correctly pass env vars to child processes.

$ErrorActionPreference = "Stop"

$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ENV_FILE    = "$SCRIPT_DIR\.env"
$LOG_DIR     = "$SCRIPT_DIR\logs"
$CF_EXE      = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$MODELS_DIR  = "D:\aipc-models"

# -- Load .env ------------------------------------------------------------------
if (Test-Path $ENV_FILE) {
    Get-Content $ENV_FILE | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" } | ForEach-Object {
        $parts = $_ -split "=", 2
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
    Write-Host "[OK] Loaded .env" -ForegroundColor Green
} else {
    Write-Host "[FAIL] .env not found at $ENV_FILE" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

# -- Step 1: Start Ollama -------------------------------------------------------
Write-Host ""
Write-Host "[1/3] Starting Ollama..." -ForegroundColor Cyan

Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$ollamaProc = Start-Process -FilePath "$SCRIPT_DIR\run_ollama.bat" `
    -RedirectStandardOutput "$LOG_DIR\ollama.log" `
    -RedirectStandardError  "$LOG_DIR\ollama-err.log" `
    -WindowStyle Hidden -PassThru

$ollamaReady = $false
for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ollamaReady = $true; break }
    } catch {}
    Write-Host "  Waiting for Ollama... ($i/20)"
}

if (-not $ollamaReady) {
    Write-Host "[FAIL] Ollama did not start. Check $LOG_DIR\ollama-err.log" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Ollama running (PID $($ollamaProc.Id))" -ForegroundColor Green

# -- Step 2: Start Auth Proxy ---------------------------------------------------
Write-Host ""
Write-Host "[2/3] Starting Auth Proxy..." -ForegroundColor Cyan

Get-WmiObject Win32_Process | Where-Object {
    $_.CommandLine -like "*proxy:app*"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 500

$proxyProc = Start-Process -FilePath "$SCRIPT_DIR\run_proxy.bat" `
    -WorkingDirectory $SCRIPT_DIR `
    -RedirectStandardOutput "$LOG_DIR\proxy.log" `
    -RedirectStandardError  "$LOG_DIR\proxy-err.log" `
    -WindowStyle Hidden -PassThru

$proxyReady = $false
for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $proxyReady = $true; break }
    } catch {}
    Write-Host "  Waiting for proxy... ($i/15)"
}

if (-not $proxyReady) {
    Write-Host "[FAIL] Proxy did not start. Check $LOG_DIR\proxy-err.log" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Auth Proxy running on port 8000 (PID $($proxyProc.Id))" -ForegroundColor Green

# -- Step 3: Start Cloudflare Tunnel --------------------------------------------
Write-Host ""
Write-Host "[3/3] Starting Cloudflare Tunnel..." -ForegroundColor Cyan

$cfProc = $null

if (-not (Test-Path $CF_EXE)) {
    Write-Host "[SKIP] cloudflared not found. Local only: http://localhost:8000" -ForegroundColor Yellow
} else {
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500

    $cfProc = Start-Process -FilePath "$SCRIPT_DIR\run_tunnel.bat" `
        -WorkingDirectory $SCRIPT_DIR `
        -RedirectStandardOutput "$LOG_DIR\tunnel.log" `
        -RedirectStandardError  "$LOG_DIR\tunnel-err.log" `
        -WindowStyle Hidden -PassThru

    Start-Sleep -Seconds 8
    $tunnelUrl = ""
    if (Test-Path "$LOG_DIR\tunnel-err.log") {
        $raw = Get-Content "$LOG_DIR\tunnel-err.log" -Raw -ErrorAction SilentlyContinue
        if ($raw -match "https://[a-z0-9\-]+\.trycloudflare\.com") {
            $tunnelUrl = $matches[0]
        }
    }
    Write-Host "[OK] Tunnel started (PID $($cfProc.Id))" -ForegroundColor Green
    if ($tunnelUrl) {
        Write-Host ""
        Write-Host "  >>> Public URL: $tunnelUrl <<<" -ForegroundColor Yellow
        Write-Host ""
        $tunnelUrl | Set-Clipboard
        Write-Host "  (URL copied to clipboard)" -ForegroundColor Gray
    } else {
        Write-Host "  Run .\get_tunnel_url.ps1 to get the public URL." -ForegroundColor Yellow
    }
}

# -- Save PIDs ------------------------------------------------------------------
@{
    ollama = $ollamaProc.Id
    proxy  = $proxyProc.Id
    tunnel = if ($cfProc) { $cfProc.Id } else { $null }
} | ConvertTo-Json | Set-Content "$SCRIPT_DIR\server.pids"

# -- Summary --------------------------------------------------------------------
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Qwen3-Coder Server is Running!" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Local:   http://localhost:8000"
Write-Host " Health:  http://localhost:8000/health"
Write-Host " Model:   qwen3-coder:30b"
Write-Host " Logs:    $LOG_DIR\"
Write-Host " Stop:    .\stop_server.ps1"
Write-Host "-------------------------------------------------------" -ForegroundColor Cyan
Write-Host " API Key:" -ForegroundColor Yellow
Write-Host " $($env:API_KEYS.Split(',')[0])"
Write-Host "=======================================================" -ForegroundColor Cyan
