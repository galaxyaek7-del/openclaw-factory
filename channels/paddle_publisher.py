#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Paddle Publisher (ADR-065/MASTER_CHARTER.md §2)

Skeleton client for Paddle's real Billing API (https://api.paddle.com) —
the merchant-of-record platform this factory's new AI SaaS/B2B ladder ranks
are priced for (recurring subscriptions, license-key software, invoiced B2B
— none of which Gumroad's one-time-download model fits well, hence
channels/gumroad_arm.py being archived rather than extended for this).

Reads PADDLE_API_KEY from .env. Never logs the key. Mirrors
gumroad_publisher.py's shape deliberately (ConfigError, _request_with_retry,
_safe_err key-redaction) — same contract, different platform, per the
"every new engine follows the same interface" principle (MASTER_CHARTER.md
§4.2) applied one level down to publishers.

Standalone module. Does not import or modify any live factory file. Loud
errors only — nothing here silently falls back or swallows a failure into a
fake success. Graceful "not configured" state: a missing PADDLE_API_KEY
raises ConfigError, which channels/paddle_arm.py's status() turns into
ArmStatus.UNAVAILABLE — never a crash, same as every other arm.

Honesty note: unlike gumroad_publisher.py, none of the functions below have
ever been called against a real Paddle account (no PADDLE_API_KEY has ever
existed in this factory) — this is a skeleton built from Paddle's public
API documentation shape (Products/Prices/Transactions resources, Bearer
auth), not something verified against a live response. Treat any real
response-shape assumption here as unverified until a real key is added and
this is actually exercised once.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"
PADDLE_API_BASE = "https://api.paddle.com"  # sandbox: https://sandbox-api.paddle.com

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.5

# Production Hardening (ADR-204, Phase 14, 2026-08-08): a real, confirmed
# gap found in Phase 13's reality test (FAILURE_REGISTER.md F6) --
# _request_with_retry() treated a 429 (rate limit) as an immediate,
# never-retried return (status_code < 500), unlike book_generator.py::
# groq_chat()'s own real Retry-After-aware retry (fixed 2026-08-06 after
# a real 429 was observed live). Same discipline, mirrored here: when a
# 429/503 response carries a real Retry-After header, it is respected
# (capped at 30s so a misbehaving header can never hang a caller
# indefinitely); every other case falls back to the original fixed
# backoff, byte-for-byte -- a genuine 400/401/403/404 is still never
# retried (a permanent client error, not a rate limit).
_MAX_RETRY_AFTER_SECONDS = 30


def _retry_delay_seconds(attempt, response=None):
    default = _RETRY_BACKOFF_SECONDS * attempt
    if response is not None and response.status_code in (429, 503):
        header = response.headers.get("Retry-After")
        if header:
            try:
                seconds = float(header)
                if seconds >= 0:
                    return min(seconds, _MAX_RETRY_AFTER_SECONDS)
            except (TypeError, ValueError):
                pass  # not a numeric Retry-After (e.g. an HTTP-date) -- fall back below
    return default


class ConfigError(Exception):
    """A missing/invalid local configuration — never a Paddle API error."""
    pass


def _request_with_retry(method, url, **kwargs):
    """Same retry discipline as gumroad_publisher.py's own helper: a real
    4xx client error (400/401/403/404/...) is permanent, never retried.
    429 (rate limit) and 503 (service unavailable) are the one real
    exception -- both are genuinely transient and are retried with a
    real Retry-After-aware delay (see _retry_delay_seconds() above,
    ADR-204 fix for FAILURE_REGISTER.md F6)."""
    last_exc = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            r = requests.request(method, url, **kwargs)
        except requests.RequestException as e:
            last_exc = e
            response = None
        else:
            if r.status_code not in (429, 503) and r.status_code < 500:
                return r
            last_exc = requests.RequestException(f"HTTP {r.status_code}: {r.text[:200]}")
            response = r
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_retry_delay_seconds(attempt, response))
    raise last_exc


def load_api_key(env_path=None):
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    key = os.environ.get("PADDLE_API_KEY")
    if key:
        return key
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("PADDLE_API_KEY"):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
    raise ConfigError(
        "PADDLE_API_KEY not set. Get it from https://vendors.paddle.com/authentication-v2"
    )


def _headers(api_key):
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _safe_json(r, action, api_key=None):
    """Production Hardening (ADR-204, Phase 14, 2026-08-08): closes
    FAILURE_REGISTER.md F8 -- a malformed JSON response used to raise a
    raw, unwrapped ValueError from every `.json()` call site below.
    PaddleArm's own layer already caught this correctly (confirmed live
    during Phase 13), but the publisher layer itself did not -- this is
    the real fix at the actual source, for defense in depth and a
    clearer error message at either layer."""
    try:
        return r.json()
    except ValueError as e:
        raise RuntimeError(f"Paddle {action} returned a malformed response: {_safe_err(e, api_key)}")


def list_products(api_key):
    try:
        r = _request_with_retry("GET", f"{PADDLE_API_BASE}/products", headers=_headers(api_key), timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle list_products request failed: {_safe_err(e, api_key)}")
    return _safe_json(r, "list_products", api_key).get("data", [])


def _raise_with_paddle_error(r, action, api_key):
    """Paddle's error responses carry a real, specific reason in the JSON
    body ({"error": {"code", "detail"}}) that requests.raise_for_status()'s
    generic HTTPError discards — surfacing it directly saved real diagnosis
    time once a live account was actually available to test against (a
    product_tax_category_not_approved / transaction_checkout_not_enabled
    error is meaningless as a bare 'HTTP 400 Client Error')."""
    try:
        body = r.json()
        detail = body.get("error", {}).get("detail") or body.get("error", {}).get("code") or r.text[:300]
    except Exception:
        detail = r.text[:300]
    raise RuntimeError(f"Paddle {action} failed: HTTP {r.status_code}: {_safe_err(detail, api_key)}")


def create_product(api_key, product_spec):
    """Creates a Paddle Product — the recurring-revenue/reusable-asset
    equivalent of gumroad_publisher.create_product(), but Paddle products
    don't carry a file upload or a price directly (see create_price()
    below); this only registers the sellable item's identity."""
    title = product_spec.get("title")
    if not title:
        raise ConfigError("product_spec missing 'title'")

    body = {
        "name": title,
        "description": product_spec.get("description", ""),
        # "standard" confirmed live against a real Paddle account
        # (2026-07-18) as the tax category actually approved for a
        # freshly-onboarded seller — "digital-goods"/"ebooks" both came
        # back product_tax_category_not_approved on the same real account.
        # Paddle approves categories per-account, so this default is a
        # real, confirmed starting point, not a guess — still overridable
        # via product_spec for an account with different approvals.
        "tax_category": product_spec.get("tax_category", "standard"),
    }
    # Unified Recovery System §5 (2026-07-18): a real, structured
    # custom_data key (Paddle's own supported field for exactly this)
    # lets paddle_arm.py's publish() find this product again via
    # list_products() before ever creating a second one for the same
    # production_id — turns "retry-safe by luck" into "retry-safe by
    # construction." Omitted (every caller before this existed) leaves
    # the request body exactly as before.
    if product_spec.get("custom_data"):
        body["custom_data"] = product_spec["custom_data"]
    try:
        r = requests.post(f"{PADDLE_API_BASE}/products", headers=_headers(api_key), json=body, timeout=60)
        if not r.ok:
            _raise_with_paddle_error(r, "create_product", api_key)
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle create_product request failed: {_safe_err(e, api_key)}")
    body = _safe_json(r, "create_product", api_key)
    return body.get("data", body)


def update_product(api_key, product_id, updates):
    """PATCH an existing product — used to fill in real title/description
    on a product created with placeholder values, rather than creating a
    duplicate every time a caller wants to change one field."""
    if not product_id:
        raise ConfigError("update_product requires a product_id")
    try:
        r = requests.patch(f"{PADDLE_API_BASE}/products/{product_id}", headers=_headers(api_key), json=updates, timeout=60)
        if not r.ok:
            _raise_with_paddle_error(r, "update_product", api_key)
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle update_product request failed: {_safe_err(e, api_key)}")
    body = _safe_json(r, "update_product", api_key)
    return body.get("data", body)


def create_price(api_key, product_id, price_spec):
    """A Paddle Price is a separate resource attached to a Product — where
    the actual sellable amount and billing cycle (one-time vs recurring)
    live. Required before a product can actually be sold."""
    if not product_id:
        raise ConfigError("create_price requires a product_id")
    unit_price_cents = price_spec.get("unit_price_cents")
    if unit_price_cents is None:
        raise ConfigError("price_spec missing 'unit_price_cents'")

    body = {
        "product_id": product_id,
        "description": price_spec.get("description", "Standard price"),
        "unit_price": {"amount": str(unit_price_cents), "currency_code": price_spec.get("currency", "USD")},
    }
    billing_cycle = price_spec.get("billing_cycle")  # e.g. {"interval": "month", "frequency": 1}
    if billing_cycle:
        body["billing_cycle"] = billing_cycle
    try:
        r = requests.post(f"{PADDLE_API_BASE}/prices", headers=_headers(api_key), json=body, timeout=60)
        if not r.ok:
            _raise_with_paddle_error(r, "create_price", api_key)
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle create_price request failed: {_safe_err(e, api_key)}")
    body = _safe_json(r, "create_price", api_key)
    return body.get("data", body)


def create_checkout_transaction(api_key, price_id, quantity=1):
    """Creates a Paddle Transaction for a given price — the real mechanism
    that produces a shareable checkout URL (`data.checkout.url` in the
    response). Confirmed live (2026-07-18) that a freshly-approved account
    can still be blocked here with `transaction_checkout_not_enabled`
    ("Checkouts aren't enabled for this account... you haven't fully
    completed the Paddle onboarding process") even after products/prices
    already work — a real, distinct account-level gate, not a bug in this
    function. Callers must handle that RuntimeError as "founder needs to
    finish onboarding in the Paddle dashboard," not a code defect."""
    if not price_id:
        raise ConfigError("create_checkout_transaction requires a price_id")
    body = {"items": [{"price_id": price_id, "quantity": quantity}]}
    try:
        r = requests.post(f"{PADDLE_API_BASE}/transactions", headers=_headers(api_key), json=body, timeout=60)
        if not r.ok:
            _raise_with_paddle_error(r, "create_checkout_transaction", api_key)
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle create_checkout_transaction request failed: {_safe_err(e, api_key)}")
    body = _safe_json(r, "create_checkout_transaction", api_key)
    data = body.get("data", body)
    checkout_url = (data.get("checkout") or {}).get("url")
    return data, checkout_url


def get_transactions(api_key):
    """Paddle's real-sales-data equivalent of gumroad_publisher.get_sales()
    — Paddle calls a completed sale a 'transaction'."""
    try:
        r = _request_with_retry("GET", f"{PADDLE_API_BASE}/transactions", headers=_headers(api_key), timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle get_transactions request failed: {_safe_err(e, api_key)}")
    return _safe_json(r, "get_transactions", api_key).get("data", [])


def _safe_err(exc, api_key=None):
    """Same key-redaction discipline as gumroad_publisher._safe_err().

    Real Paddle keys are always long (`pdl_live_apikey_...`, 46+ chars),
    but a blind substring replace has no such guarantee — found live
    (2026-07-18) via a test using a short placeholder key ("k") that
    happened to collide with a letter inside a real, unrelated Paddle
    error message ("Checkouts" -> "Chec***REDACTED***outs"). Guarding
    against anything short enough to plausibly appear as an ordinary
    substring keeps this safe without weakening real-key redaction."""
    text = str(exc)
    key = api_key or os.environ.get("PADDLE_API_KEY", "")
    if key and len(key) >= 16 and key in text:
        text = text.replace(key, "***REDACTED***")
    return text


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Paddle publisher CLI (Galaxy Forge, ADR-065)")
    parser.add_argument("--list", action="store_true", help="List existing Paddle products")
    parser.add_argument("--create", metavar="SPEC_JSON", help="Create a product from a spec JSON file")
    parser.add_argument("--transactions", action="store_true", help="List transactions (Paddle's 'sales')")
    args = parser.parse_args()

    try:
        api_key = load_api_key()

        if args.list:
            emit({"success": True, "products": list_products(api_key)})
            return

        if args.create:
            with open(args.create, "r", encoding="utf-8") as f:
                spec = json.load(f)
            product = create_product(api_key, spec)
            emit({"success": True, "product": product})
            return

        if args.transactions:
            emit({"success": True, "transactions": get_transactions(api_key)})
            return

        parser.print_help()

    except ConfigError as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
