# ─── Register Qwen3-Coder Server as a Windows Task Scheduler job ─────────────────
# This makes the server start automatically when you log in to Windows.
# Run this script ONCE (as your normal user, no admin needed for user tasks).
# ────────────────────────────────────────────────────────────────────────────────

$SCRIPT_DIR  = Split-Path -Parent $MyInvocation.MyCommand.Path
$TASK_NAME   = "Qwen3-Coder-Server"
$START_SCRIPT = "$SCRIPT_DIR\start_server.ps1"

# ── Remove existing task if present ────────────────────────────────────────────
$existingTask = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Write-Host "[~] Removed existing task '$TASK_NAME'" -ForegroundColor Yellow
}

# ── Create the task ─────────────────────────────────────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$START_SCRIPT`"" `
    -WorkingDirectory $SCRIPT_DIR

# Trigger: at user logon (current user only)
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

# Settings: run whether on battery or AC, don't stop if on battery
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -RunOnlyIfNetworkAvailable

# Principal: run as current user
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TASK_NAME `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Auto-starts Qwen3-Coder Ollama server + auth proxy + Cloudflare tunnel at login"

if ($LASTEXITCODE -eq 0 -or $?) {
    Write-Host "[✓] Task '$TASK_NAME' registered successfully." -ForegroundColor Green
    Write-Host "    The server will start automatically on next login." -ForegroundColor Gray
} else {
    Write-Host "[✗] Failed to register task." -ForegroundColor Red
}

# ── Optionally start it right now ──────────────────────────────────────────────
Write-Host ""
$startNow = Read-Host "Start the server now? [Y/n]"
if ($startNow -ne "n" -and $startNow -ne "N") {
    Write-Host "Starting..." -ForegroundColor Cyan
    & $START_SCRIPT
}
