# Deployment Guide — Expose local-llm-server to the Internet

Your local services are running and ready. Now let's make them publicly accessible.

## Quick Start (30 seconds)

You have 3 ways to deploy:

### ✅ Option 1: Use Your Existing ngrok Tunnel (Recommended)

You already have: `https://incalculably-unswaggering-kora.ngrok-free.dev`

**Step 1: Get your ngrok auth token**
1. Visit https://dashboard.ngrok.com/
2. Sign in to your ngrok account
3. Go to "Auth" section
4. Copy your "Authtoken"

**Step 2: Start the tunnel**
```bash
export NGROK_AUTH_TOKEN=your_auth_token_here
.venv/bin/python start_tunnel_simple.py
```

The script will output your public URL. It should match your existing domain.

**Step 3: Test it**
```bash
curl https://incalculably-unswaggering-kora.ngrok-free.dev/health
```

---

### Option 2: Use Cloudflare Tunnel (More Reliable)

Cloudflare is already installed on your system.

```bash
# 1. Authenticate (opens browser)
cloudflared tunnel login

# 2. Create a tunnel
cloudflared tunnel create local-llm-server

# 3. Route to your domain
cloudflared tunnel route dns local-llm-server yourdomain.com

# 4. Run the tunnel
cloudflared tunnel run --url http://localhost:8000 local-llm-server
```

Your service will be at: `https://local-llm-server.yourdomain.com`

---

### Option 3: Quick ngrok (No auth token needed, URL changes on restart)

```bash
brew install ngrok  # if not installed
ngrok http 8000
```

URL will be something like: `https://random-string.ngrok-free.dev`

---

## Verify Your Deployment

Once tunnel is running, test from anywhere:

```bash
# Health check
curl https://your-tunnel-url/health

# Chat API test
curl -X POST https://your-tunnel-url/v1/chat/completions \
  -H "Authorization: Bearer sk-qwen-9Ob7nJSX4vxkr4AbYlXNB0Z-FVO6MitnOZGLZwRhGps" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma4:latest",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 100
  }'
```

---

## Using with Claude Code

Once public, use with Claude Code CLI:

```bash
export ANTHROPIC_BASE_URL=https://your-tunnel-url
claude code
```

Or in VS Code extension settings:
```json
{
  "anthropic.customEndpoint": "https://your-tunnel-url"
}
```

---

## Troubleshooting

### Tunnel URL is not working
- ✓ Confirm proxy is running: `curl http://localhost:8000/health`
- ✓ Confirm Ollama is running: `curl http://localhost:11434/api/tags`
- ✓ Check tunnel status at `http://localhost:4040` (ngrok dashboard)
- ✓ Check CloudFlare dashboard if using Cloudflare tunnel

### Getting 401 Unauthorized
- ✓ Include your API key: `Authorization: Bearer sk-qwen-9Ob7nJSX4vxkr4AbYlXNB0Z-FVO6MitnOZGLZwRhGps`
- ✓ Check that the local proxy is responding properly

### Tunnel keeps disconnecting
- Use Cloudflare tunnel instead (more stable)
- Set ngrok auth token for persistent URLs
- Check your internet connection

---

## Current Status

- ✅ Proxy: Running on `http://localhost:8000`
- ✅ Ollama: Running on `http://localhost:11434`
- ✅ Models: `gemma4:latest`, `tinyllama:latest`
- ⏳ Public tunnel: *Ready to configure above*

---

## Next Steps

1. Choose your deployment method above
2. Start the tunnel
3. Test from the public URL
4. Use with Claude Code or API clients

Questions? Check:
- `QUICK_START.md` — Local usage
- `setup_local_models.py` — Configure services
- `task_runner.py` — Submit tasks
