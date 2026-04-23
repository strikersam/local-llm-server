#!/bin/bash
# One-time setup helper for Claude Code + local proxy.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo ""
    printf '%*s\n' 60 | tr ' ' '━'
    echo -e "${CYAN}$1${NC}"
    printf '%*s\n' 60 | tr ' ' '━'
}

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

log_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

print_header "Claude Code + Local Proxy Setup"

# ============================================================================
# Step 1: Check Python
# ============================================================================
echo -e "\n${YELLOW}[1/5] Checking Python...${NC}"

if ! command -v python3 &> /dev/null; then
    log_error "Python 3 not found in PATH"
    echo "Install from https://www.python.org/downloads/ or use your package manager"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
log_success "$PYTHON_VERSION"

# ============================================================================
# Step 2: Check Node.js (for Claude Code CLI)
# ============================================================================
echo -e "\n${YELLOW}[2/5] Checking Node.js...${NC}"

if ! command -v node &> /dev/null; then
    log_error "Node.js not found in PATH"
    echo "Install from https://nodejs.org/ (LTS recommended)"
    echo "Then install Claude Code CLI: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
NODE_VERSION=$(node --version)
log_success "Node.js $NODE_VERSION"

if ! command -v claude &> /dev/null; then
    echo ""
    read -p "Claude Code CLI not found. Install it now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install -g "@anthropic-ai/claude-code"
        log_success "Claude Code CLI installed"
    else
        log_error "Claude Code CLI required. Install with: npm install -g @anthropic-ai/claude-code"
        exit 1
    fi
else
    log_success "Claude Code CLI found"
fi

# ============================================================================
# Step 3: Setup .env file
# ============================================================================
echo -e "\n${YELLOW}[3/5] Checking .env configuration...${NC}"

if [ ! -f ".env" ]; then
    log_info ".env not found, creating one..."
    
    cat > .env << 'EOF'
# Proxy Configuration
KEYS_FILE=keys.json
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
CORS_ENABLED=true

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Model Routing (maps Claude model names to Ollama models)
# Format: anthropic_name:ollama_name,another_claude_name:another_ollama_name,*:default_model
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,claude-opus-4-6:deepseek-r1:32b,*:qwen3-coder:30b

# Optional: Langfuse observability
# LANGFUSE_SECRET_KEY=sk_...
# LANGFUSE_PUBLIC_KEY=pk_...

# Optional: Telegram bot
# TELEGRAM_BOT_TOKEN=...
EOF
    
    log_success ".env created with defaults"
else
    log_success ".env already exists"
fi

# ============================================================================
# Step 4: Install proxy dependencies
# ============================================================================
echo -e "\n${YELLOW}[4/5] Installing proxy dependencies...${NC}"

if [ -f "requirements.txt" ]; then
    echo "Running: pip3 install -q -r requirements.txt"
    python3 -m pip install -q -r requirements.txt
    if [ $? -eq 0 ]; then
        log_success "Dependencies installed"
    else
        log_error "Dependency installation failed"
        echo "Try manually: python3 -m pip install -r requirements.txt"
        exit 1
    fi
else
    log_error "requirements.txt not found"
    exit 1
fi

# ============================================================================
# Step 5: API Key Setup
# ============================================================================
echo -e "\n${YELLOW}[5/5] Checking API keys...${NC}"

if [ ! -f "keys.json" ]; then
    log_info "Creating empty keys.json (will generate keys on first launch)..."
    echo '{"version": 1, "keys": []}' > keys.json
fi

KEY_COUNT=$(python3 -c "import json; keys = json.load(open('keys.json')); print(len(keys.get('keys', [])))" 2>/dev/null || echo "0")

if [ "$KEY_COUNT" -eq 0 ]; then
    log_info "$KEY_COUNT API keys stored (will generate on first launch)"
else
    log_success "$KEY_COUNT API key(s) available"
fi

# ============================================================================
# Done!
# ============================================================================
print_header "✓ Setup Complete!"

cat << 'EOF'

Next steps:

1. Make sure Ollama is running with a model:
   ollama run qwen3-coder:30b

2. Launch Claude Code:
   ./launch-claude-code.sh --local

3. (Optional) Make scripts executable globally:
   chmod +x launch-claude-code.sh stop-proxy.sh
   sudo ln -s "$(pwd)/launch-claude-code.sh" /usr/local/bin/claude-code

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Documentation:
  • Quick Start:     ./CLAUDE-CODE-QUICKSTART.md
  • Full Guide:      ./docs/claude-code-setup.md
  • Architecture:    ./docs/architecture/overview.md
  • Troubleshooting: ./CLAUDE-CODE-QUICKSTART.md#troubleshooting
EOF
