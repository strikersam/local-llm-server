#!/usr/bin/env powershell
<#
.SYNOPSIS
    One-time setup for Claude Code + local proxy.
    
.EXAMPLE
    .\setup-claude-code.ps1
#>

$ErrorActionPreference = "Stop"

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

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
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

Write-Header "Claude Code + Local Proxy Setup"

# Step 1: Python
Write-Host ""
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow

$pythonExe = Find-Python
if ($null -eq $pythonExe) {
    Write-ErrorMsg "Python not found"
    Write-Host "Install from https://www.python.org/downloads/"
    exit 1
}

# Get Python version
$pythonVersion = & $pythonExe --version 2>&1
Write-Success $pythonVersion

# Step 2: Node.js (Optional - used for Claude Code CLI installation)
Write-Host ""
Write-Host "[2/5] Checking Node.js..." -ForegroundColor Yellow

$nodeResults = where.exe node 2>$null
$nodeExe = $null

if ($nodeResults) {
    if ($nodeResults -is [array]) {
        $nodeExe = $nodeResults[0]
    } else {
        $nodeExe = $nodeResults
    }
}

# If not found via where, try direct call
if (-not $nodeExe) {
    try {
        $output = & node.exe --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $nodeExe = "node.exe"
        }
    } catch {}
}

if ($null -eq $nodeExe) {
    Write-Host "[WARNING] Node.js not found (optional)" -ForegroundColor Yellow
    Write-Host "Install from https://nodejs.org/ if you need the CLI" -ForegroundColor Gray
} else {
    $nodeVersion = & $nodeExe --version 2>&1
    Write-Success ("Node.js " + $nodeVersion)
    
    # Check for Claude Code CLI
    $claudeResults = where.exe claude 2>$null
    $claudeExe = $null
    
    if ($claudeResults) {
        if ($claudeResults -is [array]) {
            $claudeExe = $claudeResults[0]
        } else {
            $claudeExe = $claudeResults
        }
    }
    
    if ($null -eq $claudeExe) {
        Write-Host ""
        Write-Host "Claude Code CLI not found" -ForegroundColor Yellow
        $response = Read-Host "Would you like to install it? (y/n)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            & npm install -g "@anthropic-ai/claude-code"
            Write-Success "Claude Code CLI installed"
        } else {
            Write-Host "[WARNING] Claude Code CLI not installed" -ForegroundColor Yellow
        }
    } else {
        Write-Success "Claude Code CLI found"
    }
}

# Step 3: .env
Write-Host ""
Write-Host "[3/5] Checking .env..." -ForegroundColor Yellow

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $scriptDir ".env"

if (-not (Test-Path $envFile)) {
    Write-Info "Creating .env..."
    
    $envContent = @"
KEYS_FILE=keys.json
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
CORS_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b
"@
    
    $envContent | Out-File -Encoding UTF8 $envFile
    Write-Success ".env created"
} else {
    Write-Success ".env already exists"
}

# Step 4: Dependencies
Write-Host ""
Write-Host "[4/5] Installing dependencies..." -ForegroundColor Yellow

$reqFile = Join-Path $scriptDir "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "Running: $pythonExe -m pip install -q -r requirements.txt" -ForegroundColor Gray
    & $pythonExe -m pip install -q -r $reqFile
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Dependencies installed"
    } else {
        Write-ErrorMsg "Dependency installation failed"
        exit 1
    }
} else {
    Write-ErrorMsg "requirements.txt not found"
    exit 1
}

# Step 5: API Keys
Write-Host ""
Write-Host "[5/5] Checking API keys..." -ForegroundColor Yellow

$keysFile = Join-Path $scriptDir "keys.json"

if (-not (Test-Path $keysFile)) {
    Write-Info "Creating keys.json..."
    @{ version = 1; keys = @() } | ConvertTo-Json | Out-File -Encoding UTF8 $keysFile
}

$keysJson = Get-Content $keysFile | ConvertFrom-Json
$keyCount = @($keysJson.keys).Count

if ($keyCount -eq 0) {
    Write-Info "0 API keys (will generate on launch)"
} else {
    Write-Success "$keyCount API key(s) available"
}

# Complete
Write-Header "Setup Complete!"

Write-Host @"

Next steps:

1. Start Ollama with a model:
   ollama run qwen3-coder:30b

2. Launch Claude Code:
   .\launch-claude-code.ps1 -Local

3. Use Claude Code normally!

Documentation:
  - CLAUDE-CODE-QUICKSTART.md
  - CLAUDE-CODE-COMMAND-LINE.md
  - AUTO-LAUNCHER-GUIDE.md

"@
