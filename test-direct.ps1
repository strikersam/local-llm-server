$body = @{
    model = "claude-sonnet-4-6"
    messages = @(
        @{
            role = "user"
            content = "Say hello in one sentence"
        }
    )
    max_tokens = 500
} | ConvertTo-Json -Depth 10

Write-Host "Testing /v1/messages endpoint with localhost..." -ForegroundColor Cyan
Write-Host "Request body:" -ForegroundColor Yellow
$body | Write-Host

$url = "http://localhost:8000/v1/messages"
$response = Invoke-WebRequest $url `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -UseBasicParsing

Write-Host "`nResponse Status: $($response.StatusCode)" -ForegroundColor Green

$result = $response.Content | ConvertFrom-Json
Write-Host "`nResponse from model:" -ForegroundColor Green
$result | ConvertTo-Json | Write-Host

if ($result.content -and $result.content.Length -gt 0) {
    Write-Host "`n✅ Model responded with:" -ForegroundColor Green
    $result.content[0].text | Write-Host
}
