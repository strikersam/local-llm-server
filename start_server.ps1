# Local LLM Server - Windows Startup Script
# Starts: Ollama -> Auth Proxy -> Cloudflare Tunnel
# All paths resolved from .env or auto-detected from PATH.

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$ENV_FILE   = "$SCRIPT_DIR\.env"
$LOG_DIR    = "$SCRIPT_DIR\logs"

# -- Load .env ------------------------------------------------------------------
if (Test-Path $ENV_FILE) {
    Get-Content $ENV_FILE | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" } | ForEach-Object {
        $parts = $_ -split "=", 2
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
    Write-Host "[OK] Loaded .env" -ForegroundColor Green
} else {
    Write-Host "[FAIL] .env not found. Copy .env.example to .env and configure it." -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $LOG_DIR | Out-Null

# -- Resolve executables --------------------------------------------------------
# OLLAMA_EXE: explicit path in .env, or search PATH
$ollamaExe = $env:OLLAMA_EXE
if (-not $ollamaExe) {
    $found = Get-Command ollama -ErrorAction SilentlyContinue
    if ($found) { $ollamaExe = $found.Source }
}
if (-not $ollamaExe -or -not (Test-Path $ollamaExe)) {
    Write-Host "[FAIL] Ollama not found. Set OLLAMA_EXE in .env or install Ollama." -ForegroundColor Red
    exit 1
}

# PYTHON_EXE: explicit path in .env, or search PATH
$pythonExe = $env:PYTHON_EXE
if (-not $pythonExe) {
    foreach ($cmd in @("python", "python3")) {
        try {
            $null = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0) { $pythonExe = $cmd; break }
        } catch {}
    }
}
if (-not $pythonExe) {
    Write-Host "[FAIL] Python not found. Set PYTHON_EXE in .env or install Python 3." -ForegroundColor Red
    exit 1
}

# CLOUDFLARED_EXE: explicit path in .env, or search PATH + common install locations
$cfExe = $env:CLOUDFLARED_EXE
if (-not $cfExe) {
    $candidates = @(
        "cloudflared",
        "C:\Program Files (x86)\cloudflared\cloudflared.exe",
        "C:\Program Files\cloudflared\cloudflared.exe",
        "$env:LOCALAPPDATA\cloudflared\cloudflared.exe"
    )
    foreach ($c in $candidates) {
        try {
            & $c --version 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { $cfExe = $c; break }
        } catch {}
    }
}

# -- Step 1: Start Ollama -------------------------------------------------------
Write-Host ""
Write-Host "[1/3] Starting Ollama..." -ForegroundColor Cyan

Get-Process -Name "ollama" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$ollamaProc = Start-Process -FilePath "$SCRIPT_DIR\run_ollama.bat" `
    -RedirectStandardOutput "$LOG_DIR\ollama.log" `
    -RedirectStandardError  "$LOG_DIR\ollama-err.log" `
    -WindowStyle Hidden -PassThru

for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Host "[OK] Ollama ready (PID $($ollamaProc.Id))" -ForegroundColor Green
            $models = ($resp.Content | ConvertFrom-Json).models
            $models | ForEach-Object { Write-Host "     - $($_.name) ($([math]::Round($_.size/1GB,1)) GB)" }
            break
        }
    } catch {}
    if ($i -eq 20) {
        Write-Host "[FAIL] Ollama did not start. Check $LOG_DIR\ollama-err.log" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Waiting for Ollama... ($i/20)"
}

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

for ($i = 1; $i -le 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:$($env:PROXY_PORT)/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Host "[OK] Auth Proxy running on port $($env:PROXY_PORT) (PID $($proxyProc.Id))" -ForegroundColor Green
            break
        }
    } catch {}
    if ($i -eq 15) {
        Write-Host "[FAIL] Proxy did not start. Check $LOG_DIR\proxy-err.log" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Waiting for proxy... ($i/15)"
}

# -- Step 3: Start Cloudflare Tunnel --------------------------------------------
Write-Host ""
Write-Host "[3/3] Starting Cloudflare Tunnel..." -ForegroundColor Cyan

$cfProc = $null

if (-not $cfExe) {
    Write-Host "[SKIP] cloudflared not found. Run install.ps1 to set it up." -ForegroundColor Yellow
    Write-Host "       Local only: http://localhost:$($env:PROXY_PORT)" -ForegroundColor Yellow
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
        $tunnelUrl | Set-Clipboard
        Write-Host "  (URL copied to clipboard)" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "  Run .\get_tunnel_url.ps1 to see the public URL." -ForegroundColor Yellow
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
Write-Host " Local LLM Server is Running!" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Local:   http://localhost:$($env:PROXY_PORT)"
Write-Host " Health:  http://localhost:$($env:PROXY_PORT)/health"
Write-Host " Logs:    $LOG_DIR\"
Write-Host " Stop:    .\stop_server.ps1"
Write-Host "=======================================================" -ForegroundColor Cyan
