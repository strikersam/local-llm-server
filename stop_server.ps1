# Qwen3-Coder Server Stop

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PID_FILE   = "$SCRIPT_DIR\server.pids"

Write-Host "Stopping Qwen3-Coder server..." -ForegroundColor Yellow

if (Test-Path $PID_FILE) {
    $pids = Get-Content $PID_FILE | ConvertFrom-Json
    foreach ($name in @("tunnel", "proxy", "ollama")) {
        $procId = $pids.$name
        if ($procId) {
            try {
                Stop-Process -Id $procId -Force -ErrorAction Stop
                Write-Host "[OK] Stopped $name (PID $procId)" -ForegroundColor Green
            } catch {
                Write-Host "[--] $name (PID $procId) was already stopped" -ForegroundColor Gray
            }
        }
    }
    Remove-Item $PID_FILE -Force
} else {
    Write-Host "[!] No PID file found. Killing by process name / command line..." -ForegroundColor Yellow
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-Process -Name "ollama"      -ErrorAction SilentlyContinue | Stop-Process -Force
    Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*proxy:app*" } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Done." -ForegroundColor Green
