#!/usr/bin/env powershell
<#
.SYNOPSIS
    Stop the local proxy server and optionally kill Ollama.
    
.DESCRIPTION
    Kills the FastAPI proxy process and optionally Ollama, cleaning up
    background resources started by launch-claude-code.ps1
    
.EXAMPLE
    .\stop-proxy.ps1
    
    Stops just the proxy.
    
.EXAMPLE
    .\stop-proxy.ps1 -KillOllama
    
    Stops both proxy and Ollama.
#>

param(
    [switch]$KillOllama = $false
)

$ErrorActionPreference = "Stop"

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

Write-Host "`n" -NoNewline
Write-Host "━━━ Stopping Proxy ━━━" -ForegroundColor Cyan

# Kill proxy processes
$proxyProcs = Get-Process | Where-Object {
    $_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn proxy:app*"
} -ErrorAction SilentlyContinue

if ($proxyProcs) {
    $proxyProcs | Stop-Process -Force
    Write-Success "Proxy process stopped"
} else {
    Write-Host "No proxy process found running" -ForegroundColor Yellow
}

if ($KillOllama) {
    Write-Host "`n━━━ Stopping Ollama ━━━" -ForegroundColor Cyan
    
    $ollamaProcs = Get-Process | Where-Object {
        $_.ProcessName -like "*ollama*"
    } -ErrorAction SilentlyContinue
    
    if ($ollamaProcs) {
        $ollamaProcs | Stop-Process -Force
        Write-Success "Ollama process stopped"
    } else {
        Write-Host "No Ollama process found running" -ForegroundColor Yellow
    }
}

Write-Host "`n" + ("─" * 50) + "`n"
Write-Success "Cleanup complete"
