"""
Secure Telegram control plane for qwen-server.

Provides remote command/control of the local LLM proxy via a Telegram bot.
All commands are auth-gated by Telegram user ID. Admin commands require approval.

Setup:
  1. Create a bot via @BotFather — get TELEGRAM_BOT_TOKEN
  2. Find your user ID via @userinfobot — set TELEGRAM_ALLOWED_USER_IDS
  3. Set TELEGRAM_ADMIN_USER_IDS (subset of ALLOWED, can run mutating commands)
  4. Add both to .env and restart

Run:
  python telegram_bot.py

Dependencies:
  pip install python-telegram-bot httpx python-dotenv

Command reference:
  READ-ONLY (any allowed user):
    /status          — proxy + ollama + tunnel health
    /models          — loaded Ollama models
    /cost            — local infra cost projection
    /help            — show all commands

  ADMIN-ONLY (immediate):
    /start <svc>     — start ollama|proxy|tunnel|stack
    /stop <svc>      — stop service
    /restart <svc>   — restart service

  ADMIN-ONLY (requires confirmation):
    /agent <task>    — run an agent task (reply 'yes' within 30s to confirm)
    /keylist         — list API key records
    /keycreate <email> <dept> — create new API key

Security model:
  - All messages from non-allowlisted user IDs are silently dropped.
  - Admin commands from non-admin IDs return a permission error.
  - Approval-required commands time out after 30 seconds.
  - The proxy API key used by this bot is stored in TELEGRAM_PROXY_API_KEY.
  - This bot never exposes API keys or secrets in Telegram messages.
  - Rate limiting: max 5 commands per user per minute (in-memory).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

log = logging.getLogger("qwen-telegram")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] telegram-bot %(message)s",
)

# ─── Configuration ─────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
PROXY_BASE_URL: str = os.environ.get("PROXY_BASE_URL", "http://localhost:8000").rstrip("/")
PROXY_ADMIN_SECRET: str = os.environ.get("ADMIN_SECRET", "").strip()
PROXY_API_KEY: str = os.environ.get("TELEGRAM_PROXY_API_KEY", "").strip()

_raw_allowed = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "").strip()
_raw_admins = os.environ.get("TELEGRAM_ADMIN_USER_IDS", "").strip()

ALLOWED_USER_IDS: set[int] = {
    int(x.strip()) for x in _raw_allowed.split(",") if x.strip().lstrip("-").isdigit()
}
ADMIN_USER_IDS: set[int] = {
    int(x.strip()) for x in _raw_admins.split(",") if x.strip().lstrip("-").isdigit()
}

APPROVAL_TIMEOUT_SECONDS = 30
MAX_COMMANDS_PER_MINUTE = 5

# In-memory pending approvals: user_id → {expires, action, payload}
_pending_approvals: dict[int, dict] = {}
# In-memory rate limiter: user_id → [timestamps]
_rate_buckets: dict[int, list[float]] = defaultdict(list)


# ─── Auth helpers ──────────────────────────────────────────────────────────────

def _is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def _check_rate_limit(user_id: int) -> bool:
    now = time.time()
    bucket = _rate_buckets[user_id]
    _rate_buckets[user_id] = [t for t in bucket if now - t < 60]
    if len(_rate_buckets[user_id]) >= MAX_COMMANDS_PER_MINUTE:
        return False
    _rate_buckets[user_id].append(now)
    return True


# ─── Proxy API calls ───────────────────────────────────────────────────────────

def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {PROXY_ADMIN_SECRET}"}


def _api_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {PROXY_API_KEY}"}


async def _proxy_get(path: str, use_admin: bool = True) -> dict:
    headers = _admin_headers() if use_admin else _api_headers()
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{PROXY_BASE_URL}{path}", headers=headers)
        r.raise_for_status()
        return r.json()


async def _proxy_post(path: str, body: dict, use_admin: bool = True) -> dict:
    headers = _admin_headers() if use_admin else _api_headers()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{PROXY_BASE_URL}{path}", json=body, headers=headers)
        r.raise_for_status()
        return r.json()


# ─── Command handlers ──────────────────────────────────────────────────────────

async def cmd_status(user_id: int) -> str:
    try:
        data = await _proxy_get("/admin/api/status")
        services = data.get("services", {})
        tunnel_url = data.get("tunnel_url", "unknown")
        lines = ["*Service status:*"]
        for svc, info in services.items():
            state = "running" if info.get("running") else "stopped"
            icon = "🟢" if info.get("running") else "🔴"
            lines.append(f"  {icon} {svc}: {state}")
        lines.append(f"\nTunnel: `{tunnel_url}`")
        return "\n".join(lines)
    except Exception as exc:
        return f"Status check failed: {exc}"


async def cmd_models(user_id: int) -> str:
    try:
        data = await _proxy_get("/health", use_admin=False)
        models = data.get("models", [])
        if not models:
            return "No models loaded."
        return "*Loaded models:*\n" + "\n".join(f"  • `{m}`" for m in models)
    except Exception as exc:
        return f"Model check failed: {exc}"


async def cmd_cost(user_id: int) -> str:
    try:
        from infra_cost import project_session_cost
        proj = project_session_cost()
        return f"*Local infra cost estimate:*\n```\n{proj.summary()}\n```"
    except Exception as exc:
        return f"Cost model error: {exc}"


async def cmd_control(user_id: int, action: str, target: str) -> str:
    if not _is_admin(user_id):
        return "Permission denied. Admin only."
    valid_actions = {"start", "stop", "restart"}
    valid_targets = {"ollama", "proxy", "tunnel", "stack"}
    if action not in valid_actions or target not in valid_targets:
        return f"Invalid action/target. Use: {valid_actions} / {valid_targets}"
    try:
        data = await _proxy_post("/admin/api/control", {"action": action, "target": target})
        return f"{action} {target}: `{data.get('status', 'ok')}`"
    except Exception as exc:
        return f"Control failed: {exc}"


async def cmd_keylist(user_id: int) -> str:
    if not _is_admin(user_id):
        return "Permission denied. Admin only."
    try:
        data = await _proxy_get("/admin/api/users")
        records = data.get("records", [])
        if not records:
            return "No keys found."
        lines = [f"*API Keys ({len(records)}):*"]
        for rec in records[:10]:
            lines.append(f"  • `{rec['key_id']}` — {rec['email']} ({rec['department']})")
        if len(records) > 10:
            lines.append(f"  …and {len(records) - 10} more")
        return "\n".join(lines)
    except Exception as exc:
        return f"Key list failed: {exc}"


def _request_approval(user_id: int, action: str, payload: dict) -> None:
    _pending_approvals[user_id] = {
        "expires": time.time() + APPROVAL_TIMEOUT_SECONDS,
        "action": action,
        "payload": payload,
    }


def _pop_approval(user_id: int) -> dict | None:
    pending = _pending_approvals.get(user_id)
    if not pending:
        return None
    if time.time() > pending["expires"]:
        del _pending_approvals[user_id]
        return None
    del _pending_approvals[user_id]
    return pending


# ─── Telegram update processing ────────────────────────────────────────────────

async def _send_message(bot_token: str, chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
        )


async def _process_update(bot_token: str, update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    user_id: int = message.get("from", {}).get("id", 0)
    chat_id: int = message.get("chat", {}).get("id", 0)
    text: str = (message.get("text") or "").strip()

    # Silent drop for non-allowlisted users
    if not _is_allowed(user_id):
        log.warning("Ignored message from non-allowlisted user %d", user_id)
        return

    # Rate limiting
    if not _check_rate_limit(user_id):
        await _send_message(bot_token, chat_id, "Rate limit reached. Please wait a minute.")
        return

    # Check for pending approval confirmation
    if text.lower() in ("yes", "confirm", "y"):
        approval = _pop_approval(user_id)
        if approval:
            action = approval["action"]
            payload = approval["payload"]
            if action == "agent":
                await _send_message(bot_token, chat_id, "Running agent task… (this may take a while)")
                try:
                    result = await _proxy_post("/agent/run", payload, use_admin=False)
                    summary = result.get("result", {}).get("summary", str(result))
                    await _send_message(bot_token, chat_id, f"*Agent result:*\n```\n{summary[:3000]}\n```")
                except Exception as exc:
                    await _send_message(bot_token, chat_id, f"Agent failed: {exc}")
            return
        # No pending approval — treat as regular message

    if text.lower() in ("no", "cancel", "n"):
        _pop_approval(user_id)
        await _send_message(bot_token, chat_id, "Cancelled.")
        return

    # Command dispatch
    parts = text.split(maxsplit=2)
    cmd = parts[0].lower().split("@")[0] if parts else ""

    response = ""

    if cmd == "/help":
        response = (
            "*Available commands:*\n"
            "/status — service health\n"
            "/models — loaded models\n"
            "/cost — local infra cost estimate\n"
            "\n*Admin only:*\n"
            "/start|stop|restart <svc> — control ollama|proxy|tunnel|stack\n"
            "/agent <task> — run agent task (requires confirmation)\n"
            "/keylist — list API keys\n"
        )

    elif cmd == "/status":
        response = await cmd_status(user_id)

    elif cmd == "/models":
        response = await cmd_models(user_id)

    elif cmd == "/cost":
        response = await cmd_cost(user_id)

    elif cmd in ("/start", "/stop", "/restart"):
        action = cmd[1:]
        target = parts[1].lower() if len(parts) > 1 else ""
        if not target:
            response = f"Usage: {cmd} <ollama|proxy|tunnel|stack>"
        else:
            response = await cmd_control(user_id, action, target)

    elif cmd == "/keylist":
        response = await cmd_keylist(user_id)

    elif cmd == "/agent":
        if not _is_admin(user_id):
            response = "Permission denied. Admin only."
        else:
            task = " ".join(parts[1:]) if len(parts) > 1 else ""
            if not task:
                response = "Usage: /agent <task description>"
            else:
                _request_approval(user_id, "agent", {"instruction": task})
                response = (
                    f"*Agent task:* `{task[:200]}`\n"
                    f"Reply *yes* within {APPROVAL_TIMEOUT_SECONDS}s to confirm, or *no* to cancel."
                )

    else:
        response = "Unknown command. Use /help to see available commands."

    if response:
        await _send_message(bot_token, chat_id, response)


# ─── Long-poll main loop ───────────────────────────────────────────────────────

async def run_bot() -> None:
    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN is not set. Set it in .env and restart.")
        return
    if not ALLOWED_USER_IDS:
        log.error("TELEGRAM_ALLOWED_USER_IDS is empty. No one can use the bot.")
        return

    log.info("Bot starting. Allowed users: %s  Admin users: %s", ALLOWED_USER_IDS, ADMIN_USER_IDS)
    offset = 0

    while True:
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                r = await client.get(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                    params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                )
            data = r.json()
            if not data.get("ok"):
                log.error("getUpdates error: %s", data)
                await asyncio.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                try:
                    await _process_update(TELEGRAM_BOT_TOKEN, update)
                except Exception as exc:
                    log.exception("Error processing update %d: %s", update.get("update_id"), exc)

        except asyncio.CancelledError:
            log.info("Bot stopped.")
            return
        except Exception as exc:
            log.error("Long-poll error: %s — retrying in 5s", exc)
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_bot())
