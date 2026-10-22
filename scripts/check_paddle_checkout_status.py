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


def recorded_checkout_status(state_path=None):
    """Read-only view of what earlier real checks recorded. Never calls
    Paddle and never sends Telegram. For status/gate readers, which must not
    trigger check_and_notify_all(): that function POSTs a Paddle transaction
    per product and may send a message."""
    state = _read_state(state_path)
    results = [{"price_id": k, "checkout_ready": True, "checkout_url_recorded": True}
               for k, v in state.items() if isinstance(v, dict) and v.get("checkout_url")]
    return {"results": results, "source": "recorded_state", "read_only": True}


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

    # 2026-10-22: a checkout URL obtained on an earlier run is reused; only
    # the Telegram send is retried. Before this, `notified` was the only
    # stop condition, so with Telegram unconfigured (OPENCLAW_TELEGRAM_CHAT_ID
    # unset) every factory_loop tick would have created a NEW Paddle
    # transaction per product, indefinitely, once checkout started working.
    # Each product now gets at most one transaction from this script.
    if existing and existing.get("checkout_url"):
        checkout_url = existing["checkout_url"]
        telegram_result = telegram_direct.send_telegram_message(
            _build_arabic_message(title, price, checkout_url), env_path=env_path)
        existing["notified"] = bool(telegram_result.get("sent"))
        existing["telegram_error"] = telegram_result.get("error")
        if telegram_result.get("sent"):
            existing["notified_at"] = datetime.now(timezone.utc).isoformat()
        state[price_id] = existing
        _write_state(state, state_path)
        return {
            "title": title, "success": True, "checkout_ready": True, "already_notified": False,
            "checkout_url": checkout_url, "telegram_sent": bool(telegram_result.get("sent")),
            "telegram_error": telegram_result.get("error"), "reused_existing_transaction": True,
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
        # 2026-10-22: the live API key returns 403 "You aren't permitted to
        # perform this request" on every Paddle call, so the key lacks the
        # needed permission. Name that cause instead of a generic error, so
        # factory_loop stops recording it as an "unspecified failure".
        if "403" in msg or "aren't permitted" in msg or "not permitted" in msg:
            return {"title": title, "success": False, "checkout_ready": False,
                    "error_category": "PADDLE_PERMISSION_DENIED", "error": str(e)}
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
        "checkout_obtained_at": notified_at,
        "notified_at": notified_at if telegram_result.get("sent") else None,
        "telegram_error": telegram_result.get("error"),
    }
    _write_state(state, state_path)

    return {
        "title": title, "success": True, "checkout_ready": True, "already_notified": False,
        "checkout_url": checkout_url, "telegram_sent": bool(telegram_result.get("sent")),
        "telegram_error": telegram_result.get("error"),
    }


# The throttle timestamp lives in its OWN file. founder_next_action.py treats
# the mere existence of paddle_checkout_notifications.json as "checkout is
# enabled", so writing bookkeeping into that file would create a false signal.
DEFAULT_ATTEMPT_META_PATH = _FACTORY_ROOT / "data" / "paddle_checkout_check_meta.json"
MIN_INTERVAL_SECONDS = 1800


def _read_meta(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_meta(meta, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def check_and_notify_all(registry_path=None, state_path=None, env_path=None, now=None,
                         min_interval_seconds=MIN_INTERVAL_SECONDS, meta_path=None):
    """Runs check_and_notify() for every product in the registry. One
    Paddle account has one onboarding gate — the moment it clears, every
    product's first real check afterward will report checkout_ready=True
    and send its own real Telegram message, not just the first one ever
    registered."""
    now = now or datetime.now(timezone.utc)
    # 2026-10-22: factory_loop.js runs this on every ~10-minute tick, i.e.
    # one Paddle write attempt per product per tick (728 failed runs since
    # 2026-10-15, alongside Paddle 429 rate-limit refusals in sales_poll).
    # An onboarding/permission gate does not clear within minutes, so a run
    # within min_interval_seconds of the last real attempt is skipped
    # (reported as throttled, 0 products checked). Pass 0 to disable.
    if meta_path:
        meta_path = Path(meta_path)
    elif state_path:
        # A caller-supplied state file (tests, tools) keeps its meta beside it,
        # so it never touches the real data/ file.
        meta_path = Path(state_path).with_name(Path(state_path).stem + "_check_meta.json")
    else:
        meta_path = DEFAULT_ATTEMPT_META_PATH
    meta = _read_meta(meta_path)
    last = meta.get("last_paddle_attempt_at")
    if min_interval_seconds and last:
        try:
            elapsed = (now - datetime.fromisoformat(last)).total_seconds()
        except (TypeError, ValueError):
            elapsed = None
        if elapsed is not None and 0 <= elapsed < min_interval_seconds:
            return {"success": True, "throttled": True, "total_products": 0, "newly_ready": 0,
                    "results": [], "last_attempt_at": last}

    products = _load_product_registry(registry_path)
    results = [check_and_notify(p, state_path=state_path, env_path=env_path) for p in products]
    _write_meta({"last_paddle_attempt_at": now.isoformat()}, meta_path)

    out = {
        "success": all(r.get("success") for r in results) if results else True,
        "total_products": len(results),
        "newly_ready": sum(1 for r in results if r.get("checkout_ready") and not r.get("already_notified")),
        "results": results,
    }
    # factory_loop.js reads a top-level `error`; without it every failure
    # was logged as "فشل غير محدَّد" (unspecified failure).
    failed = [r for r in results if not r.get("success")]
    if failed:
        cats = sorted({r.get("error_category") or "ERROR" for r in failed})
        out["error"] = (f"{'/'.join(cats)}: {len(failed)}/{len(results)} products -- "
                        f"{str(failed[0].get('error', ''))[:160]}")
    return out


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
