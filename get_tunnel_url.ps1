# Show the current public tunnel URL.
# Run this any time after start_server.ps1 to get the current public URL.

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$LOG_FILE = Join-Path $SCRIPT_DIR "logs\tunnel-err.log"

if (-not (Test-Path $LOG_FILE)) {
    Write-Host "[!] Tunnel log not found. Is the server running?" -ForegroundColor Yellow
    exit 1
}

$content = Get-Content $LOG_FILE -Raw
if ($content -match 'https://[a-z0-9\-]+\.trycloudflare\.com') {
    $allMatches = [regex]::Matches($content, 'https://[a-z0-9\-]+\.trycloudflare\.com')
    $url = $allMatches[$allMatches.Count - 1].Value
    Write-Host ""
    Write-Host " Public URL: $url" -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host " Use this in your client configs:" -ForegroundColor Cyan
    Write-Host "   API Base:  $url/v1" -ForegroundColor White
    Write-Host "   API Key:   (use API_KEYS from your .env - not printed here)" -ForegroundColor White
    $url | Set-Clipboard
    Write-Host " (URL copied to clipboard)" -ForegroundColor Gray
} elseif ($content -match 'https://[a-z0-9\-\.]+') {
    Write-Host " Tunnel URL: $($matches[0])" -ForegroundColor Green
} else {
    Write-Host "[!] Could not find tunnel URL in log. Check logs\tunnel-err.log" -ForegroundColor Yellow
    Write-Host "    Last 10 lines:" -ForegroundColor Gray
    Get-Content $LOG_FILE | Select-Object -Last 10
}
