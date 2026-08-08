#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Paddle checkout readiness check (ADR-085/ADR-086).

ADR-074 created the first real Paddle product+price (the $388 techdoc,
"AI-Powered Compliance Automation System for Accounting Firms") and found
checkout-link creation blocked by Paddle's own account-onboarding gate
(`transaction_checkout_not_enabled`) — a real, live, account-level block,
not a code defect. That gate is entirely on Paddle's side; nothing here
can clear it, only detect the moment it clears.

ADR-086 (2026-07-22) extended this from one hardcoded product to a real
registry (`data/paddle_products.json`) — 4 more real products were priced
and queued the same night, and checkout will clear for the whole account
at once, not per-product, so all 5 need checking together.

For every product in the registry, re-attempts `create_checkout_transaction()`
for its already-existing price (never creates a new product/price). Two
outcomes per product:

  - Still blocked (`transaction_checkout_not_enabled`): reported quietly,
    no Telegram message. Expected on every run before onboarding clears.
  - Real checkout URL returned: sent directly to the founder's Telegram in
    Arabic (channels/telegram_direct.py — bypasses n8n on purpose, same
    precedent as ADR-072/ADR-074's addendum) and recorded in
    data/paddle_checkout_notifications.json, keyed per price_id, so a
    later run never re-sends the same real link.

This factory deliberately has no scheduler (CLAUDE.md, ADR-035/036) — so
"automatic" here means zero further code changes and one click away, via
the `check-paddle-checkout-status` Mission Control action, not a
background timer. See ADR-085/ADR-086 for the full reasoning.

CLI mirrors scripts/poll_sales.py's stdin/stdout JSON convention:

    echo '{}' | python scripts/check_paddle_checkout_status.py --json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import paddle_publisher
from channels import telegram_direct

DEFAULT_REGISTRY_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "paddle_checkout_notifications.json"


def _load_product_registry(registry_path=None):
    path = Path(registry_path) if registry_path else DEFAULT_REGISTRY_PATH
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


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
    """Atomic write -- same tmp-file-then-os.replace pattern as
    factory_state.py/safe_mode.py. Resilience & Stress Hardening audit
    (2026-08-08) found this real notification-idempotency state was
    also written non-atomically; a crash mid-write here has a lower
    real consequence than the evolution-queue fix (worst case: a
    forgotten notification, at most one duplicate Telegram message,
    not a lost financial record) but the fix is the same well-tested
    4 lines, so it's applied here too."""
    path = Path(state_path) if state_path else DEFAULT_STATE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f"{path.name}.tmp-{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _build_arabic_message(title, price, checkout_url):
    return (
        "\U0001F4B0 رابط الدفع جاهز!\n\n"
        f"المنتج: {title}\n"
        f"السعر: ${price:.2f}\n\n"
        f"رابط الدفع الحقيقي:\n{checkout_url}"
    )


def check_and_notify(product, state_path=None, env_path=None):
    """One product through the readiness check. `product` is a dict with
    at least title/price_id/price. Returns a dict describing exactly what
    happened — never raises. already_notified=True means a real link was
    already sent in a prior run and this call intentionally sent nothing
    new."""
    price_id = product["price_id"]
    title = product.get("title", price_id)
    price = product.get("price", 0.0)

    state = _read_state(state_path)
    existing = state.get(price_id)
    if existing and existing.get("notified"):
        return {
            "title": title, "success": True, "checkout_ready": True, "already_notified": True,
            "checkout_url": existing.get("checkout_url"), "telegram_sent": False,
            "notified_at": existing.get("notified_at"),
        }

    try:
        api_key = paddle_publisher.load_api_key(env_path)
    except paddle_publisher.ConfigError as e:
        return {"title": title, "success": False, "checkout_ready": False, "error": str(e)}

    try:
        _txn, checkout_url = paddle_publisher.create_checkout_transaction(api_key, price_id)
    except RuntimeError as e:
        # ADR-074 found Paddle's real error body puts this reason in
        # `detail`, not the `code` -- and _raise_with_paddle_error() prefers
        # `detail` when both exist, so the code string
        # "transaction_checkout_not_enabled" often never appears in the
        # message text at all. Confirmed live (2026-07-18, 2026-07-19,
        # 2026-07-22) that the real detail text is always some variant of
        # "checkout... [not/aren't] ...enabled ... account" -- match on
        # that combination rather than the code, which this account's real
        # responses don't actually surface.
        msg = str(e).lower()
        if "checkout" in msg and "enabled" in msg and "account" in msg:
            return {
                "title": title, "success": True, "checkout_ready": False, "already_notified": False,
                "reason": "Paddle onboarding still incomplete (checkout not enabled for this account) — expected until the founder finishes it in vendors.paddle.com",
            }
        return {"title": title, "success": False, "checkout_ready": False, "error": str(e)}

    if not checkout_url:
        # Paddle accepted the request but returned no checkout.url — a real,
        # different-shaped problem worth surfacing honestly rather than
        # silently treating as "still blocked".
        return {"title": title, "success": False, "checkout_ready": False, "error": "Paddle returned no checkout.url despite a successful transaction response"}

    telegram_result = telegram_direct.send_telegram_message(_build_arabic_message(title, price, checkout_url), env_path=env_path)

    notified_at = datetime.now(timezone.utc).isoformat()
    state[price_id] = {
        "notified": bool(telegram_result.get("sent")),
        "checkout_url": checkout_url,
        "notified_at": notified_at if telegram_result.get("sent") else None,
        "telegram_error": telegram_result.get("error"),
    }
    _write_state(state, state_path)

    return {
        "title": title, "success": True, "checkout_ready": True, "already_notified": False,
        "checkout_url": checkout_url, "telegram_sent": bool(telegram_result.get("sent")),
        "telegram_error": telegram_result.get("error"),
    }


def check_and_notify_all(registry_path=None, state_path=None, env_path=None):
    """Runs check_and_notify() for every product in the registry. One
    Paddle account has one onboarding gate — the moment it clears, every
    product's first real check afterward will report checkout_ready=True
    and send its own real Telegram message, not just the first one ever
    registered."""
    products = _load_product_registry(registry_path)
    results = [check_and_notify(p, state_path=state_path, env_path=env_path) for p in products]
    return {
        "success": all(r.get("success") for r in results) if results else True,
        "total_products": len(results),
        "newly_ready": sum(1 for r in results if r.get("checkout_ready") and not r.get("already_notified")),
        "results": results,
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

    parser = argparse.ArgumentParser(description="Paddle checkout readiness check (ADR-085/ADR-086)")
    parser.add_argument("--json", action="store_true", help="Read a JSON job from stdin, print a JSON result to stdout")
    args = parser.parse_args()

    if not args.json:
        parser.print_help()
        return

    try:
        sys.stdin.read()  # no job fields used today; kept for convention consistency
        result = check_and_notify_all()
        emit(result)
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
