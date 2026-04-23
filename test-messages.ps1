$body = @{
    model = "claude-sonnet-4-6"
    messages = @(
        @{
            role = "user"
            content = "hello"
        }
    )
} | ConvertTo-Json

$response = Invoke-WebRequest "http://localhost:8000/v1/messages" `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -UseBasicParsing `
    -ErrorAction SilentlyContinue

Write-Host "Status: $($response.StatusCode)"
