# Aider — connect to your home PC models (Windows PowerShell)
# Usage:
#   . .\aider_config.ps1
#   aider --model openai/deepseek-r1:671b

$env:OPENAI_API_BASE = "https://YOUR_TUNNEL_URL/v1"
$env:OPENAI_API_KEY  = "YOUR_API_KEY"

Write-Host "Aider configured to use home PC models." -ForegroundColor Green
Write-Host "Available models:"
Write-Host "  aider --model openai/deepseek-r1:671b"
Write-Host "  aider --model openai/deepseek-r1:32b"
Write-Host "  aider --model openai/qwen3-coder:30b"
