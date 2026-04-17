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

# NGROK_EXE: explicit path in .env, or search default pyngrok install location + PATH
$ngrokExe = $env:NGROK_EXE
if (-not $ngrokExe) {
    $candidates = @(
        "$env:LOCALAPPDATA\ngrok\ngrok.exe",
        "ngrok"
    )
    foreach ($c in $candidates) {
        try {
            & $c version 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { $ngrokExe = $c; break }
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
        $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/version" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-Host "[OK] Ollama ready (PID $($ollamaProc.Id))" -ForegroundColor Green
            try {
                $tagsResp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
                $models = ($tagsResp.Content | ConvertFrom-Json).models
                $models | ForEach-Object { Write-Host "     - $($_.name) ($([math]::Round($_.size/1GB,1)) GB)" }
            } catch {
                Write-Host "     - Model list not ready yet" -ForegroundColor Gray
            }
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
        $listener = Get-NetTCPConnection -LocalPort $env:PROXY_PORT -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($listener) {
            Write-Host "[OK] Auth Proxy running on port $($env:PROXY_PORT) (PID $($proxyProc.Id))" -ForegroundColor Green
            try {
                $resp = Invoke-WebRequest -Uri "http://localhost:$($env:PROXY_PORT)/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
                if ($resp.StatusCode -eq 200) {
                    Write-Host "     - Health endpoint responded" -ForegroundColor Gray
                }
            } catch {
                Write-Host "     - Health endpoint not ready yet, but the port is listening" -ForegroundColor Gray
            }
            break
        }
    } catch {}
    if ($i -eq 15) {
        Write-Host "[FAIL] Proxy did not start. Check $LOG_DIR\proxy-err.log" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Waiting for proxy... ($i/15)"
}

# -- Step 3: Start ngrok Tunnel ------------------------------------------------
Write-Host ""
Write-Host "[3/3] Starting ngrok Tunnel..." -ForegroundColor Cyan

$ngrokProc = $null

if (-not $ngrokExe) {
    Write-Host "[SKIP] ngrok not found. Install via: pip install pyngrok" -ForegroundColor Yellow
    Write-Host "       Local only: http://localhost:$($env:PROXY_PORT)" -ForegroundColor Yellow
} else {
    Get-Process -Name "ngrok" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500

    $ngrokArgs = @("http", "$($env:PROXY_PORT)", "--log=stderr")
    if ($env:NGROK_DOMAIN) {
        $ngrokArgs += "--url=$($env:NGROK_DOMAIN)"
    }

    $ngrokProc = Start-Process -FilePath $ngrokExe `
        -ArgumentList $ngrokArgs `
        -WorkingDirectory $SCRIPT_DIR `
        -RedirectStandardOutput "$LOG_DIR\tunnel.log" `
        -RedirectStandardError  "$LOG_DIR\tunnel-err.log" `
        -WindowStyle Hidden -PassThru

    # Wait for ngrok local API to become ready (up to 15s)
    $tunnelUrl = ""
    for ($i = 1; $i -le 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $listener = Get-NetTCPConnection -LocalPort 4040 -State Listen -ErrorAction Stop | Select-Object -First 1
            if ($listener) {
                try {
                    $apiResp = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -TimeoutSec 3 -ErrorAction Stop
                    $https = $apiResp.tunnels | Where-Object { $_.public_url -like "https://*" } | Select-Object -First 1
                    if ($https) {
                        $tunnelUrl = $https.public_url
                        # Persist as PUBLIC_URL so admin UI and proxy reflect it immediately
                        [System.Environment]::SetEnvironmentVariable("PUBLIC_URL", $tunnelUrl, "Process")
                    }
                } catch {}
                break
            }
        } catch {}
    }

    if (-not (Get-NetTCPConnection -LocalPort 4040 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1)) {
        Write-Host "[FAIL] Tunnel did not become ready. Check $LOG_DIR\tunnel-err.log" -ForegroundColor Red
        exit 1
    }

    Write-Host "[OK] Tunnel started (PID $($ngrokProc.Id))" -ForegroundColor Green
    if ($tunnelUrl) {
        Write-Host ""
        Write-Host "  >>> Public URL: $tunnelUrl <<<" -ForegroundColor Yellow
        try {
            $tunnelUrl | Set-Clipboard
            Write-Host "  (URL copied to clipboard)" -ForegroundColor Gray
        } catch {
            Write-Host "  (Could not copy URL to clipboard in this session)" -ForegroundColor Gray
        }
        Write-Host ""
    } else {
        Write-Host "  (Tunnel API listener is up; public URL not fetched yet)" -ForegroundColor Gray
    }
}

# -- Save PIDs ------------------------------------------------------------------
@{
    ollama = $ollamaProc.Id
    proxy  = $proxyProc.Id
    tunnel = if ($ngrokProc) { $ngrokProc.Id } else { $null }
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
