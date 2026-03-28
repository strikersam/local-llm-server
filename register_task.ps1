# Register the LLM server as a Windows startup task (run once).
# Uses $PSScriptRoot so it works regardless of where the repo is cloned.

$SRVDIR    = $PSScriptRoot
$TASK_NAME = "LocalLLMServer"

Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$SRVDIR\start_server.ps1`"" `
    -WorkingDirectory $SRVDIR

$trigger  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Auto-starts local LLM server (Ollama + auth proxy + Cloudflare tunnel) at login" | Out-Null

Write-Host "[OK] Task '$TASK_NAME' registered." -ForegroundColor Green
Write-Host "     Server will start automatically on next Windows login." -ForegroundColor Gray
Get-ScheduledTask -TaskName $TASK_NAME | Select-Object TaskName, State
