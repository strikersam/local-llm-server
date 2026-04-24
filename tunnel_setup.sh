#!/bin/bash
# Tunnel setup script for local-llm-server

set -e

echo "=========================================="
echo "🚀 Local LLM Server Tunnel Setup"
echo "=========================================="
echo

# Check if services are running
echo "✅ Checking local services..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "   ✓ Proxy running on localhost:8000"
else
    echo "   ✗ Proxy NOT running"
    echo "   Start with: .venv/bin/python -m uvicorn proxy:app --port 8000"
    exit 1
fi

if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "   ✓ Ollama running on localhost:11434"
else
    echo "   ✗ Ollama NOT running"
    exit 1
fi

echo
echo "=========================================="
echo "📡 Tunnel Options"
echo "=========================================="
echo

if command -v ngrok &> /dev/null; then
    echo "Option 1: ngrok (Installed)"
    echo "  ngrok http 8000 --domain=your-ngrok-domain"
    echo
fi

if command -v cloudflared &> /dev/null; then
    echo "Option 2: Cloudflare Tunnel (Installed)"
    echo "  1. Authenticate: cloudflared tunnel login"
    echo "  2. Create tunnel: cloudflared tunnel create local-llm"
    echo "  3. Route DNS: cloudflared tunnel route dns local-llm yourdomain.com"
    echo "  4. Run tunnel: cloudflared tunnel run --url http://localhost:8000 local-llm"
    echo
fi

echo "Option 3: Python pyngrok tunnel (Easy)"
echo "  pip install pyngrok"
echo "  python start_tunnel.py"
echo

echo "=========================================="
echo "✅ Testing Public Access"
echo "=========================================="
echo

if [ -z "$NGROK_URL" ]; then
    read -p "Enter your tunnel public URL (e.g., https://...): " NGROK_URL
fi

if [ ! -z "$NGROK_URL" ]; then
    echo "Testing: $NGROK_URL/health"
    curl -s "$NGROK_URL/health" | python3 -m json.tool 2>/dev/null && \
        echo "✅ Tunnel is working!" || \
        echo "⚠️  Could not reach tunnel URL"
fi
