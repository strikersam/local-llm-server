# Telegram Bot Setup

The Telegram bot gives you a secure remote command-and-control interface for your local LLM server from any device that has Telegram installed.

---

## What It Does

- Check service health (Ollama, proxy, tunnel) from your phone
- Start/stop/restart individual services or the whole stack
- View currently loaded models and current tunnel URL
- See live infrastructure cost projections
- Create and list API keys
- Trigger one-off agent runs
- All commands are auth-gated by Telegram user ID

The bot is a standalone process (`telegram_bot.py`) that runs alongside the proxy and communicates with it over localhost.

---

## Prerequisites

- Python dependencies installed: `pip install -r requirements.txt`
  (Requires: `python-telegram-bot`, `httpx`, `python-dotenv`)
- The proxy is running on `http://localhost:8000` (or `PROXY_BASE_URL` configured)
- An `ADMIN_SECRET` is set in `.env` (the bot uses this to call admin endpoints)

---

## Step 1 — Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send the command: `/newbot`
3. Follow the prompts:
   - Choose a display name (e.g. `My LLM Server`)
   - Choose a username (must end in `bot`, e.g. `my_llm_server_bot`)
4. BotFather replies with a token like: `PLACEHOLDER_TELEGRAM_TOKEN`
5. Copy this token — you will need it for `TELEGRAM_BOT_TOKEN`

---

## Step 2 — Find Your Telegram User ID

1. Open Telegram and search for **@userinfobot**
2. Send `/start`
3. It replies with your numeric user ID, e.g. `12345678`

Repeat this for any other users you want to grant access.

> User IDs are stable and do not change even if a username changes.

---

## Step 3 — Configure `.env`

Add these values to your `.env` file:

```env
# Bot token from @BotFather (required)
TELEGRAM_BOT_TOKEN=PLACEHOLDER_TELEGRAM_TOKEN

# Comma-separated Telegram user IDs allowed to use the bot (read-only commands)
TELEGRAM_ALLOWED_USER_IDS=12345678,87654321

# Subset of ALLOWED that can run admin/mutating commands
# These users can start/stop services and create keys
TELEGRAM_ADMIN_USER_IDS=12345678

# API key the bot uses to call /admin/* endpoints on the proxy
# Use your ADMIN_SECRET value here
TELEGRAM_PROXY_API_KEY=your-admin-secret-here

# Proxy URL the bot connects to (default: local port 8000)
# Change to tunnel URL if running the bot on a different machine
PROXY_BASE_URL=http://localhost:8000
```

**Minimal setup (just health checks):**

```env
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_ALLOWED_USER_IDS=your-user-id
TELEGRAM_ADMIN_USER_IDS=your-user-id
TELEGRAM_PROXY_API_KEY=your-admin-secret
```

---

## Step 4 — Start the Bot

```bash
# Linux / macOS
python telegram_bot.py

# Windows PowerShell
python telegram_bot.py

# Run in background (Linux)
nohup python telegram_bot.py >> logs/telegram.log 2>&1 &

# Run in background (Windows PowerShell)
Start-Process python -ArgumentList "telegram_bot.py" -RedirectStandardOutput "logs\telegram.log" -NoNewWindow
```

You should see:

```
[INFO] telegram-bot Starting...
[INFO] telegram-bot Bot username: @my_llm_server_bot
[INFO] telegram-bot Polling for updates...
```

---

## Authorization Model

The bot has two access tiers:

| Tier | Who | What they can do |
|------|-----|------------------|
| **Allowed** | `TELEGRAM_ALLOWED_USER_IDS` | `/status`, `/models`, `/cost`, `/help` |
| **Admin** | `TELEGRAM_ADMIN_USER_IDS` | Everything above + service control + key management + agent runs |

Messages from any user ID **not in `TELEGRAM_ALLOWED_USER_IDS`** are silently dropped — the bot does not reply at all. This prevents enumeration attacks.

Admin IDs must be a subset of allowed IDs (if a user is in `ADMIN_USER_IDS` but not in `ALLOWED_USER_IDS`, their messages are still dropped).

---

## Command Reference

### Read-only commands (any allowed user)

**`/status`** — Check service health

```
🖥 Server Status
• Ollama:  ✅ Running (PID 12345)
• Proxy:   ✅ Running (PID 12346)
• Tunnel:  ✅ Running
• URL:     https://example-words.trycloudflare.com
```

**`/models`** — List currently loaded models

```
🤖 Loaded models:
• qwen3-coder:30b  (17.3 GB)
• deepseek-r1:32b  (18.5 GB)
```

**`/cost`** — Infrastructure cost projection

```
💸 Infra cost estimate
• GPU active: 150W  |  Idle: 20W  |  System: 50W
• Electricity: $0.12/kWh
• Projected daily (8h active): $0.052
• Hardware amortization: $1.85/day (over 36 months)
• Total projected: ~$2.00/day
```

**`/help`** — Show all available commands

---

### Admin commands (immediate, no confirmation)

**`/start <service>`** — Start a service

```
/start ollama
/start proxy
/start tunnel
/start stack      ← starts everything
```

**`/stop <service>`** — Stop a service

```
/stop ollama
/stop proxy
/stop tunnel
/stop stack       ← stops everything
```

> Warning: stopping the proxy or tunnel ends all active remote sessions.

**`/restart <service>`** — Restart a service

```
/restart ollama
/restart proxy
/restart tunnel
/restart stack
```

---

### Admin commands with approval required

These commands require you to **reply "yes" within 30 seconds** to confirm:

**`/agent <task>`** — Run an agent task

```
You: /agent Add a docstring to the main() function in proxy.py
Bot: About to run agent task: "Add a docstring to the main() function in proxy.py"
     Reply 'yes' within 30s to confirm, or wait to cancel.
You: yes
Bot: ▶ Running agent...
     ✅ Done. Changed: proxy.py
```

**`/keylist`** — List API key records (first 10)

```
You: /keylist
Bot: About to list API keys. Reply 'yes' within 30s to confirm.
You: yes
Bot: 🔑 API Keys (10 shown):
     • alice@company.com  |  engineering  |  kid_abc123
     • bob@company.com    |  research     |  kid_def456
```

**`/keycreate <email> <dept>`** — Create a new API key

```
You: /keycreate alice@company.com engineering
Bot: About to create key for alice@company.com (engineering). Reply 'yes' to confirm.
You: yes
Bot: ✅ Key created for alice@company.com
     Token (shown once): sk-qwen-xxxxxxxxxx
     key_id: kid_abc123def456
```

> The bot intentionally shows only a truncated token in Telegram. For full tokens, use the browser admin UI or CLI.

---

## Approval Workflow

For sensitive admin commands, the bot implements a two-step confirmation:

1. You issue the command
2. The bot echoes back what it will do and asks you to reply "yes" within 30 seconds
3. If you reply "yes", the action executes
4. If you don't reply within 30 seconds, the pending action is discarded

This prevents accidental trigger from typos or forwarded messages.

The 30-second window is hard-coded in `APPROVAL_TIMEOUT_SECONDS`. The pending state is in-memory only — restarting the bot clears all pending approvals.

---

## Rate Limiting

Each user is limited to **5 commands per minute** (in-memory, resets after 60 seconds). If exceeded:

```
⚠️ Slow down — you've sent too many commands. Try again in a moment.
```

This is a soft protection against accidental rapid-fire commands. It is not a security boundary.

---

## Security Considerations

- **User ID allow-list is the primary auth gate.** Telegram user IDs are stable numeric identifiers that cannot be spoofed by changing a username.
- The bot **never exposes full API keys or `ADMIN_SECRET`** in Telegram messages. Key creation returns only a truncated prefix.
- All communication between the bot and proxy happens over localhost — Telegram traffic does not pass through the proxy.
- The `TELEGRAM_PROXY_API_KEY` (or `ADMIN_SECRET` fallback) is used only for admin API calls; it is never forwarded in bot replies.
- Telegram itself encrypts traffic between your app and Telegram servers (MTProto). The bot-to-Telegram server link uses HTTPS long-polling.
- For higher security, use `TELEGRAM_ADMIN_USER_IDS` to restrict destructive commands to specific users even within your allowed list.

---

## Testing the Bot Locally

1. Start the proxy: `.\start_server.ps1`
2. Start the bot: `python telegram_bot.py`
3. Open Telegram and message your bot
4. Send `/status`

If the bot does not respond within a few seconds:
- Check the bot token is correct
- Check your user ID is in `TELEGRAM_ALLOWED_USER_IDS`
- Check the bot process logs for errors

### Debugging message delivery

Enable verbose logging:

```bash
LOG_LEVEL=DEBUG python telegram_bot.py
```

Look for:

```
[DEBUG] Received update from user_id=12345678
[DEBUG] User 12345678 is allowed: True
[DEBUG] Command: /status
[DEBUG] Calling proxy GET /admin/api/status
```

If you see "User not in allowed list" in logs: your user ID in `TELEGRAM_ALLOWED_USER_IDS` does not match the actual ID from Telegram. Verify via @userinfobot.

### Debugging proxy connection failures

If commands time out:

```bash
curl http://localhost:8000/admin/api/status \
  -H "Authorization: Bearer your-admin-secret"
```

If this fails, the proxy is not running or `ADMIN_SECRET` is not configured.

---

## Running the Bot as a Service

### Windows (Task Scheduler)

```powershell
$action = New-ScheduledTaskAction -Execute "python" `
    -Argument "C:\path\to\qwen-server\telegram_bot.py" `
    -WorkingDirectory "C:\path\to\qwen-server"
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "QwenTelegramBot" -Action $action -Trigger $trigger -RunLevel Highest
```

### Linux (systemd)

```ini
[Unit]
Description=Qwen Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/qwen-server
ExecStart=/path/to/python telegram_bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now qwen-telegram
```

---

## Screenshots and Expected Behavior

### What to expect in Telegram

![Telegram bot command exchange](screenshots/telegram-bot-commands.png)

The screenshot above shows a full command exchange:

1. **`/status`** — green dot for running services, red for stopped, with loaded model names
2. **`/cost`** — displays configured wattage values and projected daily cost (electricity + hardware amortization)
3. **`/models`** — lists all models currently loaded in Ollama with their sizes
4. **`/restart tunnel`** — restarts the tunnel service and reports the new URL
5. **`/agent` + approval** — the two-step confirmation flow: bot echoes the task and waits for "yes"

> **Note:** The BotFather bot creation flow and @userinfobot ID lookup are Telegram-native interactions that cannot be screenshotted here. Follow the steps in [Step 1](#step-1--create-a-telegram-bot) and [Step 2](#step-2--find-your-telegram-user-id) above.
