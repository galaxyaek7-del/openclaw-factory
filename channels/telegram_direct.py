#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — direct Telegram send (bypasses n8n entirely).

Every existing Telegram notification in this factory (ADR-073's Golden
Hunter Bridge message) goes browser->n8n->Telegram, and depends on n8n
being both running and its `04_Telegram_Notify` workflow toggled Active
(ADR-072: a real, confirmed one-click platform requirement n8n itself
enforces, not something this factory's code controls). ADR-072's and
ADR-074's addenda already sent two real, critical one-off messages by
calling Telegram's Bot API directly instead — this module is that same
proven pattern turned into a reusable function, rather than a third
one-off hand-written call.

Reads TELEGRAM_BOT_TOKEN / OPENCLAW_TELEGRAM_CHAT_ID from .env, same
lookup order as paddle_publisher.load_api_key(). Never raises to the
caller — a failed send is reported, not thrown, matching
lib/n8n_notify.js's notifyN8nProductionEvent() fail-safe philosophy: a
real, already-true event (money is real, a checkout link exists) must
never be lost or crash a caller just because Telegram is unreachable.
"""

import os
from pathlib import Path

import requests

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"
TELEGRAM_API_BASE = "https://api.telegram.org"


def _load_env_value(name, env_path=None):
    value = os.environ.get(name)
    if value:
        return value
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(name):
                    parsed = line.split("=", 1)[1].strip()
                    if parsed:
                        return parsed
    return None


def send_telegram_message(text, env_path=None, timeout=15):
    """Sends `text` to the founder's real Telegram chat. Returns
    {"sent": bool, "message_id": int|None, "error": str|None} — never
    raises. Missing config is reported as an error, not a crash, same
    honesty-over-silence discipline as every other channel adapter."""
    token = _load_env_value("TELEGRAM_BOT_TOKEN", env_path)
    chat_id = _load_env_value("OPENCLAW_TELEGRAM_CHAT_ID", env_path)
    if not token or not chat_id:
        return {"sent": False, "message_id": None, "error": "TELEGRAM_BOT_TOKEN or OPENCLAW_TELEGRAM_CHAT_ID not configured"}

    try:
        r = requests.post(
            f"{TELEGRAM_API_BASE}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=timeout,
        )
        body = r.json() if r.content else {}
    except requests.RequestException as e:
        return {"sent": False, "message_id": None, "error": f"Telegram request failed: {e}"}

    if not r.ok or not body.get("ok"):
        return {"sent": False, "message_id": None, "error": body.get("description") or f"HTTP {r.status_code}"}

    return {"sent": True, "message_id": (body.get("result") or {}).get("message_id"), "error": None}
