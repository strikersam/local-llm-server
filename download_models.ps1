# download_models.ps1 — Pull the coding-optimised model stack to D:\aipc-models
#
# Default stack (2026):
#   - qwen3-coder:30b   executor / IDE coding assistant  (≈ Claude Sonnet 4.6 class, 17 GB)
#   - deepseek-r1:32b   planner / reasoning              (≈ Claude Opus 4.6 class,   18.5 GB)
#   - deepseek-r1:671b  optional flagship                (needs ~404 GB storage)
#
# Run from the repo root:
#   .\download_models.ps1                    # pulls default coding stack
#   .\download_models.ps1 -IncludeFlagship   # also pulls 671B (needs 404 GB free)
#   .\download_models.ps1 -Lightweight       # pulls 7B tier only (needs ~10 GB)
#
# Requires Ollama to be installed and findable on PATH (or set OLLAMA_EXE in .env).

param(
    [switch]$IncludeFlagship,
    [switch]$Lightweight
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Resolve Ollama binary ──────────────────────────────────────────────────────
$ollamaExe = "ollama"
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*OLLAMA_EXE\s*=\s*(.+)$') {
            $candidate = $Matches[1].Trim()
            if ($candidate -and (Test-Path $candidate)) {
                $ollamaExe = $candidate
            }
        }
    }
}

try {
    & $ollamaExe --version | Out-Null
} catch {
    Write-Error "Ollama not found. Install from https://ollama.com or set OLLAMA_EXE in .env"
    exit 1
}

# ── Set model storage path ─────────────────────────────────────────────────────
$modelDir = "D:\aipc-models"
if (-not (Test-Path $modelDir)) {
    Write-Host "Creating model directory: $modelDir"
    New-Item -ItemType Directory -Path $modelDir -Force | Out-Null
}
$env:OLLAMA_MODELS = $modelDir
Write-Host ""
Write-Host "Model storage: $modelDir"
$free = (Get-PSDrive -Name D).Free
Write-Host ("Free on D:    {0:N1} GB" -f ($free / 1GB))
Write-Host ""

# ── Model definitions ──────────────────────────────────────────────────────────
$defaultStack = @(
    @{ tag = "qwen3-coder:30b";  sizeGb = 17;   role = "Executor / IDE coding assistant (Claude Sonnet 4.6 class)" },
    @{ tag = "deepseek-r1:32b";  sizeGb = 18.5; role = "Planner / Verifier (Claude Opus 4.6 class)" }
)

$lightweightStack = @(
    @{ tag = "qwen3-coder:7b";   sizeGb = 4.7;  role = "Lightweight executor (Claude Haiku class)" },
    @{ tag = "deepseek-r1:7b";   sizeGb = 4.7;  role = "Lightweight reasoning (Haiku class)" }
)

$flagshipStack = @(
    @{ tag = "deepseek-r1:671b"; sizeGb = 404;  role = "Flagship reasoning — needs ~404 GB free" }
)

# ── Choose which models to pull ────────────────────────────────────────────────
if ($Lightweight) {
    $toPull = $lightweightStack
} else {
    $toPull = $defaultStack
}
if ($IncludeFlagship) {
    $toPull = $toPull + $flagshipStack
}

$totalGb = ($toPull | Measure-Object -Property sizeGb -Sum).Sum
Write-Host ("Models to pull: {0} ({1:N0} GB estimated)" -f $toPull.Count, $totalGb)
Write-Host ""

if ($free / 1GB -lt $totalGb * 1.05) {
    Write-Warning ("D: has {0:N1} GB free but selected models need ~{1:N0} GB. Pull may fail." -f ($free / 1GB), $totalGb)
    Write-Host ""
}

# ── Pull each model ────────────────────────────────────────────────────────────
foreach ($m in $toPull) {
    Write-Host ("─── Pulling {0}" -f $m.tag)
    Write-Host ("    {0}" -f $m.role)
    Write-Host ("    ~{0} GB" -f $m.sizeGb)
    Write-Host ""
    & $ollamaExe pull $m.tag
    if ($LASTEXITCODE -ne 0) {
        Write-Warning ("Pull failed for {0} (exit {1}). Skipping." -f $m.tag, $LASTEXITCODE)
    } else {
        Write-Host ("    [OK] {0}" -f $m.tag)
    }
    Write-Host ""
}

# ── Summary ────────────────────────────────────────────────────────────────────
Write-Host "All pulls complete. Listing loaded models:"
Write-Host ""
& $ollamaExe list

Write-Host ""
Write-Host "Set these in .env to activate the coding stack:"
Write-Host "  OLLAMA_MODELS=$modelDir"
Write-Host "  AGENT_EXECUTOR_MODEL=qwen3-coder:30b"
Write-Host "  AGENT_PLANNER_MODEL=deepseek-r1:32b"
Write-Host "  AGENT_VERIFIER_MODEL=deepseek-r1:32b"
