#!/usr/bin/env powershell
<#
.SYNOPSIS
    Launch Claude Code with local Ollama models via proxy.
    
.EXAMPLE
    .\launch-claude-code.ps1 -Local
#>

param(
    [switch]$Local = $false,
    [switch]$Interactive = $false,
    [string]$Model = "claude-sonnet-4-6"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $scriptDir "logs"
$keysFile = Join-Path $scriptDir "keys.json"
$envFile = Join-Path $scriptDir ".env"

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Find-Python {
    # Try multiple ways to find Python
    
    # Method 1: Try 'where python' - get first result only
    try {
        $pythonResults = where.exe python 2>$null
        if ($pythonResults) {
            # Handle both single result and multiple results
            if ($pythonResults -is [array]) {
                $pythonExe = $pythonResults[0]
            } else {
                $pythonExe = $pythonResults
            }
            
            if ($pythonExe -and (Test-Path $pythonExe)) {
                return $pythonExe
            }
        }
    } catch {}
    
    # Method 2: Try calling python.exe directly
    try {
        $output = & python.exe --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return "python.exe"
        }
    } catch {}
    
    # Method 3: Check common installation paths
    $commonPaths = @(
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python312\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe",
        "$env:USERPROFILE\AppData\Local\Programs\Python\Python310\python.exe"
    )
    
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            return $path
        }
    }
    
    return $null
}

function Find-Claude {
    # Try multiple ways to find Claude Code CLI
    
    # Method 1: Try 'where claude' - get first result only
    try {
        $claudeResults = where.exe claude 2>$null
        if ($claudeResults) {
            # Handle both single result and multiple results
            if ($claudeResults -is [array]) {
                $claudeExe = $claudeResults[0]
            } else {
                $claudeExe = $claudeResults
            }
            
            if ($claudeExe -and (Test-Path $claudeExe)) {
                return $claudeExe
            }
        }
    } catch {}
    
    # Method 2: Try calling claude directly
    try {
        $output = & claude.exe --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            return "claude.exe"
        }
    } catch {}
    
    return $null
}

# Validate Setup
Write-Header "Validating Setup"

if (-not (Test-Path $envFile)) {
    Write-ErrorMsg ".env not found"
    exit 1
}
Write-Success ".env found"

if (-not (Test-Path $keysFile)) {
    @{ version = 1; keys = @() } | ConvertTo-Json | Out-File $keysFile -Encoding UTF8
}
Write-Success "keys.json accessible"

# Find Python executable
$pythonExe = Find-Python
if ($null -eq $pythonExe) {
    Write-ErrorMsg "Python not found - install from https://www.python.org/downloads/"
    exit 1
}
Write-Success "Python found"

# Find Claude Code CLI executable
$claudeExe = Find-Claude
if ($null -eq $claudeExe) {
    Write-ErrorMsg "Claude Code CLI not installed"
    Write-Host "Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
}
Write-Success "Claude Code CLI found"

# API Key Setup
Write-Header "API Key Setup"

$keysJson = Get-Content $keysFile | ConvertFrom-Json

# Default identity used when generating a key interactively or non-interactively
$email = if ($Interactive) { Read-Host "Email" } else { "claude-code@localhost" }
$dept = if ($Interactive) { Read-Host "Department" } else { "local-dev" }

$apiKey = ""

# Helper to generate via Python script and extract plaintext key from output
function Generate-PlainApiKey {
    param($pyExe, $email, $dept, $keysFile)
    $genOutput = & $pyExe scripts/generate_api_key.py --email $email --department $dept --keys-file $keysFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    $genLines = $genOutput -split "`n"
    $possible = $genLines | Where-Object { $_ -match '^sk-' } | Select-Object -First 1
    if ($possible) { return $possible.Trim() }
    if ($genLines.Length -ge 3) { return $genLines[2].Trim() }
    return $null
}

if (-not $keysJson -or -not $keysJson.keys -or $keysJson.keys.Count -eq 0) {
    Write-Host "No keys present in keys.json — generating new API key..." -ForegroundColor Yellow
    $apiKey = Generate-PlainApiKey -pyExe $pythonExe -email $email -dept $dept -keysFile $keysFile
    if (-not $apiKey) {
        Write-ErrorMsg "Failed to generate API key"
        exit 1
    }
    Write-Success "API key generated"
} else {
    $first = $keysJson.keys[0]
    # If a plaintext 'key' field exists, use it. Otherwise fall back to ANTHROPIC_API_KEY or API_KEYS env vars, or generate.
    if ($first.PSObject.Properties.Name -contains 'key' -and $first.key) {
        $apiKey = $first.key
        Write-Success "Using existing API key from keys.json"
    } elseif ($env:ANTHROPIC_API_KEY -and $env:ANTHROPIC_API_KEY.Trim()) {
        $apiKey = $env:ANTHROPIC_API_KEY.Trim()
        Write-Success "Using ANTHROPIC_API_KEY from environment"
    } elseif ($env:API_KEYS -and $env:API_KEYS.Trim()) {
        $apiKey = ($env:API_KEYS -split ',')[0].Trim()
        Write-Success "Using API_KEYS from environment (legacy)"
    } else {
        Write-Host "No plaintext key found in keys.json — generating a new API key..." -ForegroundColor Yellow
        $apiKey = Generate-PlainApiKey -pyExe $pythonExe -email $email -dept $dept -keysFile $keysFile
        if (-not $apiKey) {
            Write-ErrorMsg "Failed to generate API key"
            exit 1
        }
        Write-Success "API key generated"
    }
}

Write-Success "API key ready"

# Start Proxy
Write-Header "Proxy Server"

# Test if proxy is running using socket connection (compatible with PS 5.1)
$proxyRunning = $false
try {
    $socket = New-Object System.Net.Sockets.TcpClient
    $socket.Connect("localhost", 8000)
    if ($socket.Connected) {
        $proxyRunning = $true
        $socket.Close()
    }
} catch {
    $proxyRunning = $false
}

if (-not $proxyRunning) {
    Write-Host "Starting proxy server..." -ForegroundColor Yellow
    
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    
    Get-Content $envFile | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" } | ForEach-Object {
        $parts = $_ -split "=", 2
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
    
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "run_proxy.bat" -WorkingDirectory $scriptDir -RedirectStandardOutput (Join-Path $logDir "proxy.log") -RedirectStandardError (Join-Path $logDir "proxy-err.log") -WindowStyle Hidden
    
    Write-Host "Waiting for proxy..." -NoNewline -ForegroundColor Yellow
    $waited = 0
    while ($waited -lt 30 -and -not (Test-Connection localhost -Port 8000 -Count 1 -Quiet 2>$null)) {
        Start-Sleep -Seconds 1
        $waited++
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }
    Write-Host ""
    
    if (Test-Connection localhost -Port 8000 -Count 1 -Quiet 2>$null) {
        Write-Success "Proxy started"
    } else {
        Write-ErrorMsg "Proxy failed to start"
        exit 1
    }
} else {
    Write-Success "Proxy already running"
}

# Model Check
Write-Header "Model Check"

try {
    $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue | ConvertFrom-Json
    if ($health.status -eq "ok") {
        Write-Success "Proxy health check passed"
    }
} catch {
    Write-Host "Warning: Could not verify models" -ForegroundColor Yellow
}

# Launch Claude Code
Write-Header "Launching Claude Code"

$env:ANTHROPIC_BASE_URL = if ($Local) { "http://localhost:8000" } else { "https://your-tunnel-url.trycloudflare.com" }
$env:ANTHROPIC_API_KEY = $apiKey
$env:ANTHROPIC_MODEL = $Model

Write-Success "Environment configured"
Write-Host "Base URL: $($env:ANTHROPIC_BASE_URL)"
Write-Host "Model: $Model"
Write-Host ""
Write-Host "Launching Claude Code CLI..." -ForegroundColor Cyan
Write-Host ""

& $claudeExe code

Write-Host ""
Write-Host ("=" * 50)
Write-Success "Claude Code session ended"
