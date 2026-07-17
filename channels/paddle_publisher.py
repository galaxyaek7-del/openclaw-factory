#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Paddle Publisher (ADR-065/MASTER_CHARTER.md §2)

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


class ConfigError(Exception):
    """A missing/invalid local configuration — never a Paddle API error."""
    pass


def _request_with_retry(method, url, **kwargs):
    """Same retry discipline as gumroad_publisher.py's own helper: only
    idempotent methods are safe to retry blindly, a 4xx is a permanent
    client error, never retried."""
    last_exc = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            r = requests.request(method, url, **kwargs)
        except requests.RequestException as e:
            last_exc = e
        else:
            if r.status_code < 500:
                return r
            last_exc = requests.RequestException(f"HTTP {r.status_code}: {r.text[:200]}")
        if attempt < _RETRY_ATTEMPTS:
            time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
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


def list_products(api_key):
    try:
        r = _request_with_retry("GET", f"{PADDLE_API_BASE}/products", headers=_headers(api_key), timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle list_products request failed: {_safe_err(e, api_key)}")
    return r.json().get("data", [])


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
        # "digital" is the honest default for this factory's own products;
        # a real SaaS/B2B product might need "software" — left overridable
        # via product_spec rather than guessed silently.
        "tax_category": product_spec.get("tax_category", "digital-goods"),
    }
    try:
        r = requests.post(f"{PADDLE_API_BASE}/products", headers=_headers(api_key), json=body, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle create_product request failed: {_safe_err(e, api_key)}")
    return r.json().get("data", r.json())


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
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle create_price request failed: {_safe_err(e, api_key)}")
    return r.json().get("data", r.json())


def get_transactions(api_key):
    """Paddle's real-sales-data equivalent of gumroad_publisher.get_sales()
    — Paddle calls a completed sale a 'transaction'."""
    try:
        r = _request_with_retry("GET", f"{PADDLE_API_BASE}/transactions", headers=_headers(api_key), timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Paddle get_transactions request failed: {_safe_err(e, api_key)}")
    return r.json().get("data", [])


def _safe_err(exc, api_key=None):
    """Same key-redaction discipline as gumroad_publisher._safe_err()."""
    text = str(exc)
    key = api_key or os.environ.get("PADDLE_API_KEY", "")
    if key and key in text:
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

    parser = argparse.ArgumentParser(description="Paddle publisher CLI (OpenClaw Factory, ADR-065)")
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
