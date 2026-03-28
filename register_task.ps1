# Register Qwen3-Coder as a Windows startup task (run once)
$SRVDIR    = "C:\Users\swami\qwen-server"
$TASK_NAME = "Qwen3-Coder-Server"

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
    -Description "Auto-starts Qwen3-Coder server at login" | Out-Null

Write-Host "[OK] Task registered: $TASK_NAME" -ForegroundColor Green
Get-ScheduledTask -TaskName $TASK_NAME | Select-Object TaskName, State
