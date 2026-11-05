#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bind the founder's Telegram chat with a one-time pairing code (2026-11-05).

Why a code: whoever writes to the bot first is not necessarily the founder, so the chat id is never taken from "the
latest message". The founder is given a random code; only a private-chat message that contains exactly that code binds
its chat. The code expires after 24 hours and is consumed on use.

    python scripts/telegram_bind.py --issue     # prints the code to give the founder (stored hashed)
    python scripts/telegram_bind.py --once      # loop step: looks for the code, binds, confirms, consumes it

The result is data/telegram_binding.json (a chat id is not a secret; the bot token is never written anywhere here).
channels/telegram_direct.py and lib/telegram_direct.js read it only when OPENCLAW_TELEGRAM_CHAT_ID is not set in .env.
The .env file is never modified.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PAIRING = ROOT / "data" / "telegram_pairing.json"
BINDING = ROOT / "data" / "telegram_binding.json"
TTL = timedelta(hours=24)


def _hash(code):
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def issue(path=PAIRING, now=None):
    now = now or _now()
    code = "GF-" + secrets.token_hex(4).upper()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps({"hash": _hash(code), "expires": (now + TTL).isoformat()}), encoding="utf-8")
    return code


def match(updates, code_hash):
    """chat id of the first PRIVATE-chat message whose text contains the code, else None."""
    for u in updates or []:
        m = u.get("message") or {}
        chat = m.get("chat") or {}
        if chat.get("type") != "private":
            continue
        for word in str(m.get("text") or "").replace("/start", " ").split():
            if hmac.compare_digest(_hash(word.strip().upper()), code_hash):
                return chat.get("id")
    return None


def _token():
    from channels.telegram_direct import _load_env_value
    return _load_env_value("TELEGRAM_BOT_TOKEN")


def fetch_updates(token, timeout=15):
    import requests
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"limit": 100}, timeout=timeout)
    body = r.json() if r.content else {}
    return body.get("result") or []


def run_once(pairing=PAIRING, binding=BINDING, fetch=None, notify=None, now=None):
    now = now or _now()
    if Path(binding).exists():
        return {"action": "none", "detail": "already bound"}
    try:
        p = json.loads(Path(pairing).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"action": "none", "detail": "no pairing code issued"}
    if now > datetime.fromisoformat(p["expires"]):
        Path(pairing).unlink(missing_ok=True)
        return {"action": "expired", "detail": "pairing code expired; issue a new one"}
    if fetch is None:
        token = _token()
        if not token:
            return {"action": "failed", "detail": "TELEGRAM_BOT_TOKEN not set"}
        fetch = lambda: fetch_updates(token)  # noqa: E731
    chat_id = match(fetch(), p["hash"])
    if chat_id is None:
        return {"action": "waiting", "detail": "code not received yet"}
    tmp = Path(str(binding) + ".tmp")
    tmp.write_text(json.dumps({"chat_id": str(chat_id), "bound_at": now.isoformat(timespec="seconds")}), encoding="utf-8")
    os.replace(tmp, binding)
    Path(pairing).unlink(missing_ok=True)
    if notify is None:
        from channels.telegram_direct import send_telegram_message as notify
    sent = notify("Galaxy Forge: this chat is now linked for factory alerts.")
    return {"action": "bound", "detail": "chat bound; confirmation " + ("sent" if (sent or {}).get("sent") else "not sent")}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--issue" in argv:
        sys.stdout.write(issue() + "\n")
        return
    try:
        r = run_once()
    except Exception as e:  # reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
