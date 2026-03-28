# Qwen3-Coder One-Time Setup
# Run this ONCE before first use.
# What it does:
#   1. Installs Python pip dependencies
#   2. Installs cloudflared (Cloudflare Tunnel)
#   3. Optionally creates a named Cloudflare tunnel (persistent URL)

$ErrorActionPreference = "Continue"
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Qwen3-Coder Server -- One-Time Setup" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# -- Step 1: Find Python --------------------------------------------------------
Write-Host ""
Write-Host "[1/3] Checking Python..." -ForegroundColor Cyan

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0 -and "$ver" -match "Python 3") {
            $pythonCmd = $cmd
            Write-Host "[OK] Found: $ver ($cmd)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "[FAIL] Python 3 not found!" -ForegroundColor Red
    Write-Host "    Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "    Or via winget: winget install Python.Python.3.12" -ForegroundColor Yellow
    exit 1
}

# Install pip dependencies
Write-Host "    Installing Python dependencies..." -ForegroundColor Gray
& $pythonCmd -m pip install -r "$SCRIPT_DIR\requirements.txt" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] pip install failed. Check your Python installation." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python dependencies installed" -ForegroundColor Green

# -- Step 2: Install cloudflared ------------------------------------------------
Write-Host ""
Write-Host "[2/3] Checking cloudflared..." -ForegroundColor Cyan

$cfInstalled = $false
$cfCmd = "cloudflared"

try {
    $cfVer = & cloudflared --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $cfInstalled = $true
        Write-Host "[OK] Already installed: $cfVer" -ForegroundColor Green
    }
} catch {}

if (-not $cfInstalled) {
    Write-Host "    Installing cloudflared via winget..." -ForegroundColor Gray
    try {
        winget install Cloudflare.cloudflared --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] cloudflared installed via winget" -ForegroundColor Green
            $cfInstalled = $true
        } else {
            throw "winget failed"
        }
    } catch {
        Write-Host "[!] winget install failed. Downloading manually..." -ForegroundColor Yellow
        $cfDir = "$env:LOCALAPPDATA\cloudflared"
        New-Item -ItemType Directory -Force -Path $cfDir | Out-Null
        $cfUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        Write-Host "    Downloading from GitHub..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $cfUrl -OutFile "$cfDir\cloudflared.exe"
        $cfCmd = "$cfDir\cloudflared.exe"
        # Add to user PATH permanently
        $currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
        if ($currentPath -notlike "*$cfDir*") {
            [System.Environment]::SetEnvironmentVariable("PATH", "$currentPath;$cfDir", "User")
        }
        $env:PATH = "$cfDir;$env:PATH"
        Write-Host "[OK] cloudflared downloaded to $cfDir" -ForegroundColor Green
        $cfInstalled = $true
    }
}

# -- Step 3: Cloudflare Tunnel Setup --------------------------------------------
Write-Host ""
Write-Host "[3/3] Cloudflare Tunnel Setup..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Choose tunnel type:" -ForegroundColor Yellow
Write-Host "  [1] Quick Tunnel  -- No account needed. URL changes every restart." -ForegroundColor White
Write-Host "  [2] Named Tunnel  -- Requires free Cloudflare account. Permanent URL." -ForegroundColor White
Write-Host ""
$choice = Read-Host "Enter 1 or 2 (default: 1)"

if ($choice -eq "2") {
    Write-Host ""
    Write-Host "  Named tunnel setup:" -ForegroundColor Cyan
    Write-Host "  This will open a browser for Cloudflare login." -ForegroundColor Gray

    Write-Host "  Step 1: Login to Cloudflare..."
    & $cfCmd tunnel login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Login failed or skipped. Falling back to quick tunnel." -ForegroundColor Yellow
    } else {
        $tunnelName = "qwen-coder"
        Write-Host "  Step 2: Creating named tunnel '$tunnelName'..."
        & $cfCmd tunnel create $tunnelName

        Write-Host ""
        Write-Host "  Step 3: Configure a domain (optional)." -ForegroundColor Cyan
        Write-Host "  If you have a domain on Cloudflare, enter it (e.g. qwen.yourdomain.com)." -ForegroundColor Gray
        Write-Host "  Press Enter to skip." -ForegroundColor Gray
        $domain = Read-Host "  Domain (or Enter to skip)"

        if ($domain) {
            & $cfCmd tunnel route dns $tunnelName $domain
            Write-Host "[OK] DNS route set: $domain -> tunnel" -ForegroundColor Green
            Add-Content "$SCRIPT_DIR\.env" "`nTUNNEL_DOMAIN=$domain"
        }

        Write-Host "[OK] Named tunnel '$tunnelName' created." -ForegroundColor Green
        Write-Host "    start_server.ps1 will use this tunnel automatically." -ForegroundColor Gray
    }
} else {
    Write-Host "[OK] Quick tunnel selected. URL will be shown when server starts." -ForegroundColor Green
    Write-Host "    Note: URL changes every restart. Use named tunnel for a permanent URL." -ForegroundColor Gray
}

# -- Done -----------------------------------------------------------------------
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host " Setup Complete!" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host " Start server:  .\start_server.ps1"
Write-Host " Stop server:   .\stop_server.ps1"
Write-Host " Edit API keys: .\.env  (add/remove keys in API_KEYS)"
Write-Host "=======================================================" -ForegroundColor Green
