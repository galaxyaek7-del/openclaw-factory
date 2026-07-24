#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Gumroad Publisher
Uploads digital products to Gumroad via REST API.
Reads GUMROAD_ACCESS_TOKEN from .env. Never logs the token.

Standalone module. Does not import or modify any live factory file.
Loud errors only — nothing here silently falls back or swallows a
failure into a fake success.
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
GUMROAD_API_BASE = "https://api.gumroad.com/v2"

# Retry only idempotent calls (GET/PUT) on transient failures — a dropped
# connection or a 5xx is safe to retry because repeating the same read or
# the same update has no side effect beyond the intended one. create_product
# (POST) is deliberately NEVER retried here: if the first request actually
# succeeded on Gumroad's side but the response was lost, a blind retry
# would create a second, duplicate paid listing. That failure mode is worse
# than surfacing one honest error and letting a human decide.
_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.5


class ConfigError(Exception):
    """A missing/invalid local configuration — never a Gumroad API error."""
    pass


def _request_with_retry(method, url, **kwargs):
    """requests.request() wrapper that retries a transient failure (network
    error or 5xx response) up to _RETRY_ATTEMPTS times with linear backoff.
    A 4xx response is never retried — it is a permanent client/config error
    that will not resolve itself on a second try."""
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


def load_token(env_path=None):
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if token:
        return token
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GUMROAD_ACCESS_TOKEN"):
                    value = line.split("=", 1)[1].strip()
                    if value:
                        return value
    raise ConfigError(
        "GUMROAD_ACCESS_TOKEN not set. Get it from https://gumroad.com/settings/advanced"
    )


def list_products(token):
    try:
        r = _request_with_retry("GET", f"{GUMROAD_API_BASE}/products", params={"access_token": token}, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad list_products request failed: {_safe_err(e)}")
    data = r.json()
    if not data.get("success", False):
        raise RuntimeError(f"Gumroad API returned success=false: {data.get('message', 'unknown error')}")
    return data.get("products", [])


def create_product(token, product_spec):
    file_path = product_spec.get("file_path")
    if not file_path:
        raise ConfigError("product_spec missing 'file_path'")
    file_path = Path(file_path)
    if not file_path.exists():
        raise ConfigError(f"file_path not found: {file_path}")

    price_cents = product_spec.get("price_cents")
    if price_cents is None:
        raise ConfigError("product_spec missing 'price_cents'")

    title = product_spec.get("title")
    if not title:
        raise ConfigError("product_spec missing 'title'")

    data = {
        "access_token": token,
        "name": title,
        "price": price_cents,
        "description": product_spec.get("description", ""),
        "customizable_price": "false",
    }
    try:
        # Deliberately not retried — see _request_with_retry's docstring.
        with open(file_path, "rb") as fh:
            files = {"file": (file_path.name, fh, "application/pdf")}
            r = requests.post(f"{GUMROAD_API_BASE}/products", data=data, files=files, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad create_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad create_product failed: {result.get('message', 'unknown error')}")
    return result.get("product", result)


def update_product(token, product_id, updates):
    if not product_id:
        raise ConfigError("update_product requires a product_id")
    data = dict(updates)
    data["access_token"] = token
    try:
        r = _request_with_retry("PUT", f"{GUMROAD_API_BASE}/products/{product_id}", data=data, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad update_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad update_product failed: {result.get('message', 'unknown error')}")
    return result.get("product", result)


def get_sales(token, product_id=None):
    params = {"access_token": token}
    if product_id:
        params["product_id"] = product_id
    try:
        r = _request_with_retry("GET", f"{GUMROAD_API_BASE}/sales", params=params, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad get_sales request failed: {_safe_err(e)}")
    data = r.json()
    if not data.get("success", False):
        raise RuntimeError(f"Gumroad get_sales failed: {data.get('message', 'unknown error')}")
    return data.get("sales", [])


def _safe_err(exc):
    """Stringify a requests exception WITHOUT ever letting the access_token
    (present in the request URL/params/body) leak into an error message."""
    text = str(exc)
    token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    if token and token in text:
        text = text.replace(token, "***REDACTED***")
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

    parser = argparse.ArgumentParser(description="Gumroad publisher CLI (Galaxy Forge)")
    parser.add_argument("--list", action="store_true", help="List existing Gumroad products")
    parser.add_argument("--create", metavar="SPEC_JSON", help="Create a product from a spec JSON file")
    parser.add_argument("--sales", action="store_true", help="List sales")
    parser.add_argument("--product-id", default=None, help="Optional product_id filter for --sales")
    args = parser.parse_args()

    try:
        token = load_token()

        if args.list:
            products = list_products(token)
            emit({"success": True, "products": products})
            return

        if args.create:
            with open(args.create, "r", encoding="utf-8") as f:
                spec = json.load(f)
            product = create_product(token, spec)
            emit({"success": True, "product": product})
            return

        if args.sales:
            sales = get_sales(token, product_id=args.product_id)
            emit({"success": True, "sales": sales})
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
