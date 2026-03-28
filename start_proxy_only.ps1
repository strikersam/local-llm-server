$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $scriptDir ".env"
$logDir = Join-Path $scriptDir "logs"

if (-not (Test-Path $envFile)) {
    throw ".env not found at $envFile"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Get-Content $envFile | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "=" } | ForEach-Object {
    $parts = $_ -split "=", 2
    [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
}

Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*uvicorn proxy:app*" -or $_.CommandLine -like "*run_proxy.bat*"
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Start-Sleep -Seconds 1

Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "run_proxy.bat" `
    -WorkingDirectory $scriptDir `
    -RedirectStandardOutput (Join-Path $logDir "proxy.log") `
    -RedirectStandardError (Join-Path $logDir "proxy-err.log") `
    -WindowStyle Hidden
