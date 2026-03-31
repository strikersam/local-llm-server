# download_models.ps1 — Pull the coding-optimised model stack to D:\aipc-models
#
# Default stack (2026):
#   - qwen3-coder:30b   executor / IDE coding assistant  (≈ Claude Sonnet 4.6 class, 17 GB)
#   - deepseek-r1:32b   planner / reasoning              (≈ Claude Opus 4.6 class,   18.5 GB)
#   - deepseek-r1:671b  optional flagship                (needs ~404 GB storage)
#
# Extended stack — open-source models with local weights:
#   - frob/minimax-m2.5  MiniMax M2.5 229B MoE (10B active) community GGUF  (138 GB Q4_K_M)
#
# Cloud-proxy models (no local weights — Ollama routes to vendor API, requires vendor key):
#   - deepseek-v3.2:cloud    DeepSeek V3.2 685B (cloud API proxy)
#   - minimax-m2.7:cloud     MiniMax M2.7 (cloud API proxy — open weights not yet released)
#   - glm-5:cloud            GLM-5 744B MoE (cloud API proxy)
#
# NOT available locally (as of 2026-03-31):
#   - MiMo-V2-Pro (Xiaomi)    — proprietary, weights not released
#   - Step 3.5 Flash (stepfun) — open source (Apache 2.0, 111 GB Q4) but not yet in Ollama
#                                  download via: huggingface-cli download stepfun-ai/Step-3.5-Flash-GGUF
#
# Run from the repo root:
#   .\download_models.ps1                    # pulls default coding stack
#   .\download_models.ps1 -IncludeFlagship   # also pulls deepseek-r1:671b (needs 404 GB free)
#   .\download_models.ps1 -Lightweight       # pulls 7B tier only (needs ~10 GB)
#   .\download_models.ps1 -Extended          # adds MiniMax M2.5 local GGUF (138 GB extra)
#   .\download_models.ps1 -CloudProxy        # pulls Ollama cloud-proxy models (needs vendor API keys)
#
# Requires Ollama to be installed and findable on PATH (or set OLLAMA_EXE in .env).

param(
    [switch]$IncludeFlagship,
    [switch]$Lightweight,
    [switch]$Extended,
    [switch]$CloudProxy
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

# Local GGUF weights for new open-source models (community-quantized via Ollama hub)
$extendedStack = @(
    @{ tag = "frob/minimax-m2.5:230b-a10b-q4_K_M"; sizeGb = 138; role = "MiniMax M2.5 229B MoE (10B active) — GPT-4.1 class, 192K ctx (community Q4_K_M)" }
)

# Cloud-proxy models: Ollama routes to vendor API — NO local weights downloaded.
# Requires the vendor API key to be configured in your Ollama environment.
# See: https://ollama.com/blog/openai-compatibility for how to configure vendor keys.
$cloudProxyStack = @(
    @{ tag = "deepseek-v3.2:cloud"; sizeGb = 0;   role = "DeepSeek V3.2 685B (cloud proxy — set DEEPSEEK_API_KEY in Ollama env)" },
    @{ tag = "minimax-m2.7:cloud";  sizeGb = 0;   role = "MiniMax M2.7 (cloud proxy — open weights not yet released, set MINIMAX_API_KEY)" },
    @{ tag = "glm-5:cloud";         sizeGb = 0;   role = "GLM-5 744B MoE (cloud proxy — set GLM_API_KEY / ZAI_API_KEY in Ollama env)" }
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
if ($Extended) {
    $toPull = $toPull + $extendedStack
}
if ($CloudProxy) {
    $toPull = $toPull + $cloudProxyStack
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
Write-Host ""
Write-Host "Extended local models (if pulled with -Extended):"
Write-Host "  # MiniMax M2.5 — route Claude Haiku-class requests to it:"
Write-Host "  # MODEL_MAP=...,*:frob/minimax-m2.5:230b-a10b-q4_K_M"
Write-Host ""
Write-Host "Cloud-proxy models (if pulled with -CloudProxy):"
Write-Host "  # These call vendor APIs — configure vendor API keys in your Ollama environment first."
Write-Host "  # deepseek-v3.2:cloud  minimax-m2.7:cloud  glm-5:cloud"
