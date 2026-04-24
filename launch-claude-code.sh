#!/bin/bash
# Launch Claude Code with local Qwen/DeepSeek models via this proxy.
#
# Prerequisites:
# - Proxy dependencies installed: pip install -r requirements.txt
# - Claude Code CLI installed: npm install -g @anthropic-ai/claude-code
# - Ollama model available: ollama run qwen3-coder:30b
#
# Usage:
#   ./launch-claude-code.sh [--local] [--interactive] [--model claude-sonnet-4-6]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
KEYS_FILE="${KEYS_FILE:-$SCRIPT_DIR/keys.json}"
ENV_FILE="$SCRIPT_DIR/.env"

LOCAL=false
INTERACTIVE=false
MODEL="claude-sonnet-4-6"

while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            LOCAL=true
            shift
            ;;
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_header() {
    echo -e "\n${CYAN}━━━ $1 ━━━${NC}"
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

# ============================================================================
# Phase 1: Validate Setup
# ============================================================================

log_header "Validating Setup"

if [ ! -f "$ENV_FILE" ]; then
    log_error ".env not found"
    echo "Please create a .env file with at least: KEYS_FILE=keys.json"
    exit 1
fi
log_success ".env found"

if [ ! -f "$KEYS_FILE" ]; then
    log_error "keys.json not found"
    echo "Generating new keys file..."
    echo '{"version": 1, "keys": []}' > "$KEYS_FILE"
    log_success "Created keys.json (empty)"
fi
log_success "keys.json accessible"

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 not found in PATH"
    exit 1
fi
log_success "Python 3 found: $(which python3)"

if ! command -v claude &> /dev/null; then
    log_error "Claude Code CLI not installed"
    echo "Install with: npm install -g @anthropic-ai/claude-code"
    echo "Then retry this script."
    exit 1
fi
log_success "Claude Code CLI found: $(which claude)"

# ============================================================================
# Phase 2: Generate or Retrieve API Key
# ============================================================================

log_header "API Key Setup"

KEY_COUNT=$(python3 -c "import json; keys = json.load(open('$KEYS_FILE')); print(len(keys.get('keys', [])))" 2>/dev/null || echo "0")

if [ "$KEY_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}No API keys found. Generating one...${NC}"
    
    if [ "$INTERACTIVE" = true ]; then
        read -p "Enter your email: " EMAIL
        read -p "Enter department/seat name: " DEPT
    else
        EMAIL="claude-code@localhost"
        DEPT="local-dev"
    fi
    
    API_KEY=$(python3 scripts/generate_api_key.py \
        --email "$EMAIL" \
        --department "$DEPT" \
        --keys-file "$KEYS_FILE" 2>&1 | sed -n '3p')
    
    if [ -z "$API_KEY" ]; then
        log_error "Failed to generate API key"
        exit 1
    fi
    
    log_success "API key generated"
    echo "Keep this key safe and never commit it to git."
else
    echo "$KEY_COUNT key(s) already exist in keys.json"
    
    # Extract the first API key from keys.json
    API_KEY=$(python3 -c "import json; keys = json.load(open('$KEYS_FILE')); print(keys['keys'][0]['key'])" 2>/dev/null)
    
    if [ -z "$API_KEY" ]; then
        log_error "Failed to read API key from keys.json"
        exit 1
    fi
    
    log_success "Using existing API key from keys.json"
fi

if [ -z "$API_KEY" ]; then
    log_error "No API key available"
    exit 1
fi

log_success "API key ready"

# ============================================================================
# Phase 3: Start Proxy (if not already running)
# ============================================================================

log_header "Proxy Server"

if timeout 1 bash -c "echo >/dev/tcp/localhost/8000" 2>/dev/null; then
    log_success "Proxy already running on localhost:8000"
else
    echo -e "${YELLOW}Starting proxy server...${NC}"
    
    mkdir -p "$LOG_DIR"
    
    # Source .env
    set -a
    source "$ENV_FILE"
    set +a
    
    # Start proxy in background
    nohup python3 -m uvicorn proxy:app --port 8000 > "$LOG_DIR/proxy.log" 2>&1 &
    PROXY_PID=$!
    echo $PROXY_PID > "$LOG_DIR/proxy.pid"
    
    echo -n -e "${YELLOW}Waiting for proxy to start..."
    WAITED=0
    MAX_WAIT=30
    while [ $WAITED -lt $MAX_WAIT ]; do
        if timeout 1 bash -c "echo >/dev/tcp/localhost/8000" 2>/dev/null; then
            break
        fi
        sleep 1
        WAITED=$((WAITED + 1))
        echo -n "."
    done
    echo ""
    
    if timeout 1 bash -c "echo >/dev/tcp/localhost/8000" 2>/dev/null; then
        log_success "Proxy started and responding"
    else
        log_error "Proxy failed to start within $MAX_WAIT seconds"
        echo "Check logs at: $LOG_DIR/proxy.log"
        exit 1
    fi
fi

# ============================================================================
# Phase 4: Verify Models Available
# ============================================================================

log_header "Model Check"

if command -v curl &> /dev/null; then
    HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
    if echo "$HEALTH" | grep -q '"status":"ok"'; then
        log_success "Proxy health check passed"
        echo "Available models:"
        echo "$HEALTH" | python3 -c "import sys, json; h=json.load(sys.stdin); [print(f'  • {m}') for m in h.get('models', [])]" 2>/dev/null || true
    fi
fi

# ============================================================================
# Phase 5: Launch Claude Code
# ============================================================================

log_header "Launching Claude Code"

if [ "$LOCAL" = true ]; then
    export ANTHROPIC_BASE_URL="http://localhost:8000"
else
    export ANTHROPIC_BASE_URL="https://your-tunnel-url.trycloudflare.com"
fi

export ANTHROPIC_API_KEY="$API_KEY"
export ANTHROPIC_MODEL="$MODEL"

log_success "Environment configured"
echo "  ANTHROPIC_BASE_URL = $ANTHROPIC_BASE_URL"
echo "  ANTHROPIC_API_KEY = ${API_KEY:0:8}..."
echo "  Model: $MODEL"

echo -e "\n${CYAN}Launching Claude Code CLI...${NC}"
echo -e "${CYAN}Press Ctrl+C to exit.\n${NC}"

# Launch Claude Code
claude code

echo -e "\n$(printf '─%.0s' {1..50})"
log_success "Claude Code session ended"
echo -e "${CYAN}Proxy is still running at http://localhost:8000${NC}"
echo "Use: pgrep -f uvicorn and kill to stop it, or check logs/proxy.pid" -ForegroundColor Gray
