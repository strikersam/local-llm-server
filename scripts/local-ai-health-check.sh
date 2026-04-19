#!/usr/bin/env bash
# local-ai-health-check.sh
# Checks the health of the local AI Docker stack
# Usage: ./scripts/local-ai-health-check.sh

set -euo pipefail

OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
CHROMA_URL="${CHROMA_URL:-http://localhost:8000}"
WEBUI_URL="${WEBUI_URL:-http://localhost:3000}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check() {
  local name="$1"
  local url="$2"
  local expected_status="${3:-200}"

  http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")

  if [ "$http_code" = "$expected_status" ] || [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓${NC} $name is healthy (HTTP $http_code)"
    return 0
  else
    echo -e "${RED}✗${NC} $name is NOT healthy (HTTP $http_code) — $url"
    return 1
  fi
}

echo ""
echo "🔍 Local AI Stack Health Check"
echo "================================"

FAILURES=0

# Ollama
check "Ollama API" "$OLLAMA_URL/api/tags" || FAILURES=$((FAILURES + 1))

# List loaded models
if curl -s --max-time 3 "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  MODELS=$(curl -s "$OLLAMA_URL/api/tags" | python3 -c "import sys,json; data=json.load(sys.stdin); print(', '.join([m['name'] for m in data.get('models', [])]))" 2>/dev/null || echo "none")
  echo -e "   ${YELLOW}Models available:${NC} ${MODELS:-none}"
fi

# ChromaDB
check "ChromaDB" "$CHROMA_URL/api/v1/heartbeat" || FAILURES=$((FAILURES + 1))

# Open WebUI
check "Open WebUI" "$WEBUI_URL" || FAILURES=$((FAILURES + 1))

echo ""

if [ "$FAILURES" -eq 0 ]; then
  echo -e "${GREEN}✅ All services healthy!${NC}"
  exit 0
else
  echo -e "${RED}❌ $FAILURES service(s) unhealthy.${NC}"
  echo ""
  echo "To start the stack:"
  echo "  cd docker/local-ai-stack && docker compose up -d"
  exit 1
fi
