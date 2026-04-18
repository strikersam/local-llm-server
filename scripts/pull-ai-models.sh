#!/usr/bin/env bash
# pull-ai-models.sh
# Pulls a curated set of Ollama models for the local AI stack
# Usage: ./scripts/pull-ai-models.sh [--minimal|--full]

set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
MODE="${1:---minimal}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pull_model() {
  local model="$1"
  echo -e "${YELLOW}⬇ Pulling:${NC} $model"
  docker exec ollama ollama pull "$model"
  echo -e "${GREEN}✓${NC} $model ready"
  echo ""
}

echo ""
echo "🤖 Pulling Ollama Models"
echo "========================"
echo "Mode: $MODE"
echo ""

# Verify ollama container is running
if ! docker ps --filter "name=ollama" --filter "status=running" | grep -q ollama; then
  echo "❌ Ollama container not running. Start the stack first:"
  echo "   cd docker/local-ai-stack && docker compose up -d"
  exit 1
fi

# Always pull these
pull_model "llama3.2:latest"
pull_model "nomic-embed-text:latest"

if [ "$MODE" = "--full" ]; then
  echo "Pulling full model set..."
  pull_model "deepseek-coder-v2:latest"
  pull_model "phi3:mini"
  pull_model "mistral:latest"
fi

echo "✅ Models ready. List with: docker exec ollama ollama list"
