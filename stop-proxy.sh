#!/bin/bash
# Stop the local proxy server and optionally kill Ollama.

KILL_OLLAMA=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --kill-ollama)
            KILL_OLLAMA=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${CYAN}━━━ Stopping Proxy ━━━${NC}"

# Kill proxy processes
if pgrep -f "uvicorn proxy:app" > /dev/null; then
    pkill -f "uvicorn proxy:app"
    echo -e "${GREEN}✓ Proxy process stopped${NC}"
else
    echo -e "${YELLOW}No proxy process found running${NC}"
fi

if [ "$KILL_OLLAMA" = true ]; then
    echo -e "\n${CYAN}━━━ Stopping Ollama ━━━${NC}"
    
    if pgrep -i "ollama" > /dev/null; then
        pkill -i "ollama"
        echo -e "${GREEN}✓ Ollama process stopped${NC}"
    else
        echo -e "${YELLOW}No Ollama process found running${NC}"
    fi
fi

echo -e "\n$(printf '─%.0s' {1..50})\n"
echo -e "${GREEN}✓ Cleanup complete${NC}"
