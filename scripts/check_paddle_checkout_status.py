#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Paddle checkout readiness check (ADR-085).

ADR-074 created the first real Paddle product+price (the $388 techdoc,
"AI-Powered Compliance Automation System for Accounting Firms") and found
checkout-link creation blocked by Paddle's own account-onboarding gate
(`transaction_checkout_not_enabled`) — a real, live, account-level block,
not a code defect. That gate is entirely on Paddle's side; nothing here
can clear it, only detect the moment it clears.

This script re-attempts `create_checkout_transaction()` for that exact,
already-existing price (never creates a new product/price — that would
mean a second real Paddle product for the same techdoc). Two outcomes:

  - Still blocked (`transaction_checkout_not_enabled`): reported quietly,
    no Telegram message. Onboarding isn't done yet; this is the expected,
    ordinary case every time this runs before that.
  - Real checkout URL returned: sent directly to the founder's Telegram in
    Arabic (channels/telegram_direct.py — bypasses n8n on purpose, same
    precedent as ADR-072/ADR-074's addendum for critical one-off
    messages) and recorded in data/paddle_checkout_notifications.json so
    a second run never re-sends the same real link.

This factory deliberately has no scheduler (CLAUDE.md, ADR-035/036) — so
"automatic" here means zero further code changes and one click away, via
the `check-paddle-checkout-status` Mission Control action, not a
background timer. See ADR-085 for the full reasoning.

CLI mirrors scripts/poll_sales.py's stdin/stdout JSON convention:

    echo '{}' | python scripts/check_paddle_checkout_status.py --json
"""

import argparse
import json
import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import paddle_publisher
from channels import telegram_direct

# ADR-074: the exact, already-created $388 techdoc product/price. Hardcoded
# deliberately — re-deriving this from a live list_products() search on
# every check would risk silently matching a different product if
# custom_data ever drifts; the known-good IDs from the ADR are the ground
# truth here, and a mismatch should surface as a clear Paddle error, not a
# guessed substitute.
KNOWN_PRODUCT_ID = "pro_01kxtd3xzaz0nmfgphk55brhn7"
KNOWN_PRICE_ID = "pri_01kxtd4p62t4m7ezap61k5ree0"
KNOWN_PRODUCT_TITLE = "AI-Powered Compliance Automation System for Accounting Firms"
KNOWN_PRICE_USD = 388.00

DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "paddle_checkout_notifications.json"


def _read_state(state_path=None):
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(state, state_path=None):
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _build_arabic_message(checkout_url):
    return (
        "\U0001F4B0 رابط الدفع جاهز!\n\n"
        f"المنتج: نظام أتمتة الامتثال بالذكاء الاصطناعي لمكاتب المحاسبة\n"
        f"السعر: ${KNOWN_PRICE_USD:.2f}\n\n"
        f"رابط الدفع الحقيقي:\n{checkout_url}"
    )


def check_and_notify(state_path=None, env_path=None):
    """Returns a dict describing exactly what happened — never raises.
    already_notified=True means a real link was already sent in a prior
    run and this call intentionally sent nothing new."""
    state = _read_state(state_path)
    existing = state.get(KNOWN_PRICE_ID)
    if existing and existing.get("notified"):
        return {
            "success": True, "checkout_ready": True, "already_notified": True,
            "checkout_url": existing.get("checkout_url"), "telegram_sent": False,
            "notified_at": existing.get("notified_at"),
        }

    try:
        api_key = paddle_publisher.load_api_key(env_path)
    except paddle_publisher.ConfigError as e:
        return {"success": False, "checkout_ready": False, "error": str(e)}

    try:
        _txn, checkout_url = paddle_publisher.create_checkout_transaction(api_key, KNOWN_PRICE_ID)
    except RuntimeError as e:
        # ADR-074 found Paddle's real error body puts this reason in
        # `detail`, not the `code` -- and _raise_with_paddle_error() prefers
        # `detail` when both exist, so the code string
        # "transaction_checkout_not_enabled" often never appears in the
        # message text at all. Confirmed live (2026-07-18, 2026-07-19, and
        # again here) that the real detail text is always some variant of
        # "checkout... [not/aren't] ...enabled ... account" -- match on
        # that combination rather than the code, which this account's real
        # responses don't actually surface.
        msg = str(e).lower()
        if "checkout" in msg and "enabled" in msg and "account" in msg:
            return {
                "success": True, "checkout_ready": False, "already_notified": False,
                "reason": "Paddle onboarding still incomplete (checkout not enabled for this account) — expected until the founder finishes it in vendors.paddle.com",
            }
        return {"success": False, "checkout_ready": False, "error": str(e)}

    if not checkout_url:
        # Paddle accepted the request but returned no checkout.url — a real,
        # different-shaped problem worth surfacing honestly rather than
        # silently treating as "still blocked".
        return {"success": False, "checkout_ready": False, "error": "Paddle returned no checkout.url despite a successful transaction response"}

    telegram_result = telegram_direct.send_telegram_message(_build_arabic_message(checkout_url), env_path=env_path)

    from datetime import datetime, timezone
    notified_at = datetime.now(timezone.utc).isoformat()
    state[KNOWN_PRICE_ID] = {
        "notified": bool(telegram_result.get("sent")),
        "checkout_url": checkout_url,
        "notified_at": notified_at if telegram_result.get("sent") else None,
        "telegram_error": telegram_result.get("error"),
    }
    _write_state(state, state_path)

    return {
        "success": True, "checkout_ready": True, "already_notified": False,
        "checkout_url": checkout_url, "telegram_sent": bool(telegram_result.get("sent")),
        "telegram_error": telegram_result.get("error"),
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Paddle checkout readiness check (ADR-085)")
    parser.add_argument("--json", action="store_true", help="Read a JSON job from stdin, print a JSON result to stdout")
    args = parser.parse_args()

    if not args.json:
        parser.print_help()
        return

    try:
        sys.stdin.read()  # no job fields used today; kept for convention consistency
        result = check_and_notify()
        emit(result)
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
