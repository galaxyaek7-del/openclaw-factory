#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Etsy Publisher (ADR-025)
Reads ETSY_API_KEY, ETSY_ACCESS_TOKEN, ETSY_SHOP_ID from .env. Never logs
any of them.

Verified via a real web search on 2026-07-12 (developer.etsy.com/
documentation): Etsy's Open API v3 DOES support creating listings
programmatically, including digital downloads (listing type "download"),
via `POST /v3/application/shops/{shop_id}/listings` with an
`x-api-key: <keystring>` header and an OAuth2 Bearer token carrying the
`listings_w` scope.

Two real, separate obstacles to ever going live, documented honestly
(ADR-025) rather than glossed over:
  1. Obtaining ETSY_ACCESS_TOKEN requires a full OAuth2 authorization-code
     flow (app registration + a real user consent redirect) — NOT
     implemented here, same as this module never implements "how do I get
     a Gumroad token" for channels/gumroad_publisher.py. A one-time manual/
     human setup step, out of scope for this module.
  2. Etsy is independently documented as restrictive/unreliable about
     approving NEW developer apps in several categories since 2024 — this
     is a business risk independent of code correctness.

The exact required/optional fields for a listing create call are NOT
fully verified against a live call in this session (no token exists to
test against) — confirm the current shape at
https://developers.etsy.com/documentation/reference/ before ever using
this for a real listing.

Standalone module. Does not import or modify any live factory file.
"""

import os
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"
ETSY_API_BASE = "https://openapi.etsy.com/v3/application"


class ConfigError(Exception):
    """A missing/invalid local configuration — never an Etsy API error."""
    pass


def _read_env_var(name, env_path):
    value = os.environ.get(name)
    if value:
        return value
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(name):
                    v = line.split("=", 1)[1].strip()
                    if v:
                        return v
    return None


def load_credentials(env_path=None):
    """Returns (api_key, access_token, shop_id). Raises ConfigError if any
    of the three is missing — a real listing call needs all three, so a
    partial credential set is treated the same as none (fail-safe)."""
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    api_key = _read_env_var("ETSY_API_KEY", env_path)
    access_token = _read_env_var("ETSY_ACCESS_TOKEN", env_path)
    shop_id = _read_env_var("ETSY_SHOP_ID", env_path)
    if not (api_key and access_token and shop_id):
        raise ConfigError(
            "ETSY_API_KEY, ETSY_ACCESS_TOKEN, and ETSY_SHOP_ID must all be set. "
            "Register an app at https://www.etsy.com/developers, then complete "
            "the OAuth2 authorization-code flow to obtain an access token with "
            "the listings_w scope (not implemented by this factory — a one-time "
            "manual setup step)."
        )
    return api_key, access_token, shop_id


def create_product(api_key, access_token, shop_id, product_spec):
    if requests is None:
        raise RuntimeError("requests library not installed")

    file_path = product_spec.get("file_path")
    if not file_path:
        raise ConfigError("product_spec missing 'file_path'")
    if not Path(file_path).exists():
        raise ConfigError(f"file_path not found: {file_path}")

    title = product_spec.get("title")
    if not title:
        raise ConfigError("product_spec missing 'title'")

    price_usd = product_spec.get("price_usd")
    if price_usd is None:
        raise ConfigError("product_spec missing 'price_usd'")

    headers = {
        "x-api-key": api_key,
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "quantity": 999,
        "title": title,
        "description": product_spec.get("description", ""),
        # CODE REVIEW FLAG (unverified, no live token to test against): Etsy's
        # v3 API conventionally expects listing money fields as a structured
        # amount/divisor/currency_code object, not a bare decimal in
        # form-encoded data — this specific field is a likely 400 on first
        # real use, not just a generic "unverified shape" caveat. Confirm
        # against https://developers.etsy.com/documentation/reference/
        # #operation/createDraftListing before ever calling this live.
        "price": price_usd,
        "who_made": "i_did",
        "when_made": "made_to_order",
        "taxonomy_id": 0,  # placeholder — a real listing needs a valid Etsy taxonomy id
        "type": "download",
    }
    try:
        r = requests.post(
            f"{ETSY_API_BASE}/shops/{shop_id}/listings",
            headers=headers, data=data, timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Etsy create listing request failed: {_safe_err(e, access_token)}")
    return r.json()


def _safe_err(exc, access_token):
    """Stringify a requests exception WITHOUT ever letting the access
    token leak into an error message, same discipline as
    gumroad_publisher.py's _safe_err()."""
    text = str(exc)
    if access_token and access_token in text:
        text = text.replace(access_token, "***REDACTED***")
    return text
