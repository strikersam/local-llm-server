# Troubleshooting

Common problems and how to fix them. For configuration details, see [docs/configuration-reference.md](configuration-reference.md).

---

## Quick Diagnostics

Run these first before diving into specific issues:

```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# Is the proxy running?
curl http://localhost:8000/health

# What models are loaded?
ollama ps

# What's in the logs?
tail -50 logs/proxy.log
tail -50 logs/ollama-err.log
tail -50 logs/tunnel.log
```

On Windows (PowerShell):
```powershell
Get-Content logs\proxy.log -Tail 50
```

---

## Startup Issues

### Proxy fails to start

**Symptom:** `.\start_server.ps1` completes but `curl http://localhost:8000/health` returns "connection refused"

**Check proxy log:**
```bash
tail -30 logs/proxy-err.log
```

**Common causes:**

| Error in log | Fix |
|-------------|-----|
| `Port 8000 already in use` | Another process has port 8000. Change `PROXY_PORT` in `.env` or kill the conflicting process. |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again. |
| `KEYS_FILE set but file not found` | Create `keys.json` or run `python generate_api_key.py --email ...` first. |
| `API_KEYS and KEYS_FILE are both empty` | At least one key source must be configured. Add `API_KEYS=your-key` to `.env`. |
| `PROXY_DEFAULT_MAX_TOKENS must be at least 1` | Check `.env` for a typo in `PROXY_DEFAULT_MAX_TOKENS`. |

### Ollama fails to start

```bash
tail -30 logs/ollama-err.log
```

**Common causes:**

| Error | Fix |
|-------|-----|
| `listen tcp 127.0.0.1:11434: bind: address already in use` | Ollama is already running. Check Task Manager (Windows) or `ps aux | grep ollama`. |
| `OLLAMA_MODELS: no space left on device` | The model storage path is full. Free space or point to a different drive. |
| `no GPU found` | Normal on CPU-only machines — Ollama falls back to CPU. Slow but functional. |

### Cloudflare tunnel fails to start

```bash
tail -30 logs/tunnel.log
```

**Common causes:**

| Error | Fix |
|-------|-----|
| `cloudflared: command not found` | Set `CLOUDFLARED_EXE` in `.env` to the full path. |
| `error connecting to local service` | Proxy is not running on port 8000. Start proxy first. |
| `connection refused` | Firewall blocking the Cloudflare connection. Check outbound port 7844. |

---

## Authentication Issues

### 401 Unauthorized

**Claude Code / API clients:**
- Confirm `ANTHROPIC_API_KEY` (or `Authorization: Bearer` header) matches a key in `API_KEYS` or `KEYS_FILE`
- Keys are case-sensitive
- Check with: `curl http://localhost:8000/health -H "Authorization: Bearer your-key"` (health doesn't require auth but shows the proxy is up)

**Admin UI / API:**
- If using Windows auth: ensure `ADMIN_WINDOWS_AUTH=true` and you're entering Windows credentials
- If using `ADMIN_SECRET`: the password field on the login form must match `ADMIN_SECRET` exactly
- If `ADMIN_WINDOWS_ALLOWED_USERS` is set, your username must be in the list

### 403 Forbidden from remote machine

- The API key provided doesn't match what's in `.env`
- Check for trailing spaces or newlines in the key
- Try copying the key fresh from `keys.json` (the `key_id` field helps identify the record)

### 429 Too Many Requests

- Rate limit exceeded (default: 60 req/min per key)
- Wait 60 seconds and retry, or increase `RATE_LIMIT_RPM` in `.env`

---

## Model and Response Issues

### "Model not found" or 404 on model requests

```bash
ollama list          # Show pulled models
ollama pull qwen3-coder:30b   # Pull if missing
```

Check that `OLLAMA_MODELS` in `.env` points to where models are stored and that the Ollama process inherits this env var. The start scripts load `.env` automatically — if you started Ollama manually without sourcing `.env`, models may not be found.

### Responses get cut off mid-sentence

`PROXY_DEFAULT_MAX_TOKENS` is too low. Claude Code needs at least 4096; 8192 is recommended.

```env
PROXY_DEFAULT_MAX_TOKENS=8192
```

Check the live `.env` (not just `.env.example`).

### `<think>...</think>` appears in responses

DeepSeek-R1 and other reasoning models emit think blocks by default. Enable stripping:

```env
PROXY_STRIP_THINK_TAGS=true
```

### Responses are empty or very short

- Check `PROXY_DEFAULT_MAX_TOKENS` (see above)
- Check Ollama isn't running out of context: `ollama ps` shows the context window in use
- Try a direct Ollama call to confirm the issue is in Ollama, not the proxy:
  ```bash
  curl http://localhost:11434/api/chat \
    -d '{"model":"qwen3-coder:30b","messages":[{"role":"user","content":"hello"}]}'
  ```

### Very slow first response (30–90 seconds)

Expected behavior when the model doesn't fit fully in RAM and is being memory-mapped from NVMe.

- `ollama ps` shows which models are loaded
- Response time improves dramatically on subsequent requests once the model is warm
- The 32B model runs faster than 671B — use 32B for interactive use

If responses are consistently slow (not just first request), the model may be paging:
- Check available RAM: `Get-Process -Name "ollama" | Select-Object WorkingSet` (Windows)
- Consider using a lighter model tier

### Model eviction between requests

Ollama unloads models after 5 minutes of inactivity by default. Every cold-start request will be slow.

**Keep models warm:**
```bash
# Reload every 4 minutes (Linux cron / Windows Task Scheduler)
curl -s -o /dev/null http://localhost:11434/api/generate \
  -d '{"model":"qwen3-coder:30b","prompt":"ping","stream":false}'
```

---

## Claude Code Specific Issues

### Claude Code sends requests but gets no useful response

1. Confirm the proxy is routing to the right model:
   ```bash
   tail -f logs/proxy.log  # watch for "POST /v1/messages model=qwen3-coder:30b"
   ```
2. Confirm `PROXY_DEFAULT_MAX_TOKENS=8192` (was 1200 in old configs — truncates everything)
3. Confirm `PROXY_DEFAULT_SYSTEM_PROMPT_ENABLED=false` (double-prompting confuses the model)

### "Context length exceeded" in Claude Code

Claude Code's system prompt uses ~15–20K tokens. With a 32K model, only ~12K remain for conversation.

- Clear the Claude Code session: run `/clear` in the Claude Code prompt
- Start fresh conversations for large tasks instead of continuing long sessions
- Consider models with 128K context windows when available via Ollama

### Claude Code shows model as "claude-sonnet-4-6" but proxy logs show wrong model

Check `MODEL_MAP` in `.env`:
```env
MODEL_MAP=claude-sonnet-4-6:qwen3-coder:30b,...
```

If `MODEL_MAP` is not set, built-in defaults apply. If the model name isn't in the map and no `*` wildcard is set, the request may fall through to an unmapped model. Check `handlers/anthropic_compat.py` for the built-in defaults.

---

## Admin Dashboard Issues

### Dashboard shows "KEYS_FILE not configured"

Set `KEYS_FILE=keys.json` in `.env` and restart the proxy.

### New key flash banner not appearing after key creation

The flash banner appears once immediately after creation and is cleared on the next page load. If you refreshed before copying it, use the **Rotate** action on the key to generate a new token.

### "Stop stack" disconnects me from the dashboard

Expected behavior — stopping the proxy terminates the connection. Access the dashboard via `localhost:8000` from the server machine itself, or use a named tunnel with a permanent URL.

### Windows auth login fails

- Confirm you're using the Windows username (not email) and password for this machine
- Try `HOSTNAME\username` format if plain `username` doesn't work
- Check `ADMIN_WINDOWS_ALLOWED_USERS` — if set, your username must be listed
- Enable debug logging: `LOG_LEVEL=DEBUG` and restart proxy, then check logs on login attempt

---

## Langfuse Issues

### No traces appearing in Langfuse

1. Run the connection test in the admin dashboard
2. Check `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are both set and correct
3. Confirm `LANGFUSE_BASE_URL` matches your Langfuse instance
4. Try `LANGFUSE_USE_HTTP_ONLY=true` if the SDK is failing silently
5. Look for Langfuse errors in the proxy log: `tail logs/proxy.log | grep -i langfuse`

### Traces appear but metadata is missing

- Legacy `API_KEYS` requests will have `user=unknown` and no `key_id` — switch to `KEYS_FILE`
- Infrastructure cost fields only appear if `INFRA_*` variables are configured
- Commercial equivalent fields only appear if the model is in the pricing map

### Langfuse shows "cost" as $0

`COMMERCIAL_EQUIVALENT_PRICES_JSON` or `COMMERCIAL_EQUIVALENT_PRICES_FILE` may not be configured, or the model name in your requests doesn't match any entry in the pricing map.

Check: `python -c "from commercial_equivalent import get_prices; print(list(get_prices().keys()))"`

---

## Telegram Bot Issues

### Bot doesn't respond to messages

1. Confirm the bot is running: `python telegram_bot.py` (check for startup log)
2. Confirm your user ID is in `TELEGRAM_ALLOWED_USER_IDS`
3. Confirm `TELEGRAM_BOT_TOKEN` is correct (try creating a new token via @BotFather if unsure)
4. Get your actual ID via @userinfobot and compare to what's in `.env`

### "Permission denied" from admin commands

Your user ID is in `TELEGRAM_ALLOWED_USER_IDS` but not in `TELEGRAM_ADMIN_USER_IDS`. Add it to the admin list.

### Bot runs but service control commands fail

The bot calls the proxy's admin API. Check:
- `PROXY_BASE_URL` is correct (default: `http://localhost:8000`)
- `TELEGRAM_PROXY_API_KEY` matches `ADMIN_SECRET` in `.env`
- The proxy is running: `curl http://localhost:8000/health`

---

## Agent API Issues

### Agent returns empty or incomplete plan

The planner model (default: `deepseek-r1:32b`) needs to be pulled and running. Check:
```bash
ollama list   # deepseek-r1:32b should be present
ollama ps     # check if it's loaded
```

### Agent makes a change but doesn't verify correctly

The verifier (`deepseek-r1:32b`) may be returning inconsistent JSON. Enable debug logging and check the verifier's raw output in the proxy logs.

### Agent workspace errors ("file not found")

`AGENT_WORKSPACE_ROOT` defaults to the directory containing `proxy.py`. If you're running the agent against a different repo, set:
```env
AGENT_WORKSPACE_ROOT=C:\path\to\your\project
```

### Rollback command fails

The rollback endpoint (`POST /agent/sessions/{id}/rollback-last-commit`) requires:
- The session used `auto_commit: true` when running the task
- The workspace is a git repository
- The last commit was made by the agent (it checks the commit message prefix)

---

## Network and Tunnel Issues

### Tunnel URL changes on every restart

Normal behavior for quick-tunnel (no Cloudflare account). Set up a named tunnel for a permanent URL — see the README's [Permanent URL section](../README.md#permanent-url-optional).

### Can't find current tunnel URL

```bash
./get_tunnel_url.sh        # Linux/macOS
.\get_tunnel_url.ps1       # Windows
```

Or check the admin dashboard — the URL appears in the Service Controls section when the tunnel is running.

### Remote client gets "SSL certificate error"

Quick-tunnel uses Cloudflare's wildcard certificate on `*.trycloudflare.com`. This should be trusted by all modern OS/browsers. If you see this error:
- Update your OS CA certificates
- Try `curl -k` to bypass (debugging only, not for production)

### High latency from remote clients

The tunnel adds ~20–50ms overhead on top of model inference time. For interactive use, the model inference time (1–30 seconds) dominates. The tunnel latency is not significant in practice.

---

## Performance Issues

### Tokens-per-second is low

Compare `tokens_per_sec` in Langfuse traces:

| Tokens/sec | Likely cause |
|------------|-------------|
| < 5 | Model is memory-mapped from NVMe (not enough RAM) |
| 5–15 | Partial GPU offload or CPU inference |
| 15–40 | Good GPU inference (30B model on mid-range GPU) |
| > 40 | High-end GPU or very fast inference setup |

To improve: ensure the model fits in RAM/VRAM. Use `ollama ps` to see if layers are being offloaded to CPU.

### Multiple simultaneous users cause slowdowns

Ollama processes one request at a time by default. Queue depth increases with concurrent users.

- Consider running separate Ollama instances for different model tiers
- Use smaller models for high-concurrency use cases
- The proxy's rate limiting (`RATE_LIMIT_RPM`) helps prevent queue pile-up
