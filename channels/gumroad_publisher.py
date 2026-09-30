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

# Gumroad presigns one S3 part per 100 MB chunk (see the official /api
# "Files" documentation). The client must slice the local file to exactly
# the same boundaries S3 enforces, or the uploaded parts will not reassemble.
_PART_SIZE = 100 * 1024 * 1024


class ConfigError(Exception):
    """A missing/invalid local configuration — never a Gumroad API error."""
    pass


# Last token successfully loaded via load_token() (env or .env file).
# Used ONLY for error-message redaction — never logged.
_LAST_LOADED_TOKEN = ""


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
    global _LAST_LOADED_TOKEN
    env_path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    token = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if token:
        token = token.strip().strip("'\"")
        if token:
            _LAST_LOADED_TOKEN = token
            return token
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[len("export "):].strip()
                if not line.startswith("GUMROAD_ACCESS_TOKEN"):
                    continue
                _, _, value = line.partition("=")
                value = value.strip().strip("'\"")
                # Strip trailing inline comment ("token # comment").
                if " #" in value:
                    value = value.split(" #", 1)[0].strip().strip("'\"")
                if value:
                    _LAST_LOADED_TOKEN = value
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
        raise RuntimeError(f"Gumroad API returned success=false: {_gumroad_error(data)}")
    return data.get("products", [])


def _gumroad_error(data):
    """Extract a truthful human-readable error string from a Gumroad response
    body. Gumroad's v2 API reports failures under the `error` key on most
    endpoints (and `message` on some legacy paths) — reading only `message`
    produced the "presign failed: None" / "complete failed: None" messages in
    the sales ledger. Prefer `error`, fall back to `message`, never fabricate."""
    if not isinstance(data, dict):
        return str(data)[:500]
    error = data.get("error")
    if error:
        return str(error)
    message = data.get("message")
    if message:
        return str(message)
    return "unknown error"


def _abort_upload(token, upload_id):
    """Cancel an interrupted presigned upload (POST /v2/files/abort) so the
    dangling S3 multipart session is released. Gumroad's contract: responses
    carry a `status` of `accepted` (S3 took the cancellation but parts in
    flight may finish seconds later) or `already_gone` (no session left).
    Call again while `accepted`; stop on `already_gone`. Never raises — a
    failed abort must never mask the original upload error."""
    for _ in range(5):
        try:
            r = requests.post(
                f"{GUMROAD_API_BASE}/files/abort",
                data={"access_token": token, "upload_id": upload_id},
                timeout=30,
            )
            data = r.json()
        except requests.RequestException:
            return
        if not data.get("success"):
            return
        status = data.get("status")
        if status in ("already_gone", None):
            return
        if status != "accepted":
            return
        time.sleep(2)


def _upload_file(token, file_path):
    file_path = Path(file_path)
    if not file_path.exists() or not file_path.is_file():
        raise ConfigError(f"product file not found: {file_path}")
    try:
        file_size = os.path.getsize(file_path)
    except OSError as e:
        raise ConfigError(f"cannot read product file size: {file_path} ({e})")
    if file_size <= 0:
        raise ConfigError(f"product file is empty (0 bytes): {file_path}")

    # 1. Presign
    r = _request_with_retry("POST", f"{GUMROAD_API_BASE}/files/presign",
                            data={"access_token": token, "filename": file_path.name, "file_size": file_size}, timeout=30)
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"Gumroad presign failed: {_gumroad_error(data)}")

    upload_id = data.get("upload_id")
    key = data.get("key")
    parts = data.get("parts", [])
    if not upload_id or not key or not parts:
        raise RuntimeError(f"Gumroad presign incomplete: missing fields (upload_id: {bool(upload_id)}, key: {bool(key)}, parts: {bool(parts)})")

    # 2. Upload each part's exact byte range to S3, capturing the ETag S3
    # returns per part. S3 requires every non-last part to be >= 5 MB, which
    # the 100 MB presigned boundaries satisfy by construction. Each part PUT
    # is idempotent (same bytes, same presigned URL) so transient failures
    # are safe to retry via _request_with_retry.
    completed_parts = []
    try:
        with open(file_path, "rb") as fh:
            for part in parts:
                part_number = part.get("part_number")
                part_url = part.get("presigned_url")
                if not part_number or not part_url:
                    raise RuntimeError(f"Gumroad presign part missing fields (part_number: {bool(part_number)}, presigned_url: {bool(part_url)})")
                start = (int(part_number) - 1) * _PART_SIZE
                fh.seek(start)
                chunk = fh.read(min(_PART_SIZE, file_size - start))
                put = _request_with_retry("PUT", part_url, data=chunk, timeout=300)
                put.raise_for_status()
                etag = put.headers.get("ETag")
                if not etag:
                    raise RuntimeError(f"Gumroad S3 part {part_number} upload returned no ETag header")
                completed_parts.append({"part_number": int(part_number), "etag": etag})
    except Exception:
        # Any interrupted upload must be aborted so it does not linger in S3.
        _abort_upload(token, upload_id)
        raise

    # 3. Complete. NEVER retried: the upload_id is single-use. If the first
    # request succeeded on Gumroad's side but the response was lost, a blind
    # retry would be rejected (the upload_id no longer exists) — start a
    # fresh presign instead, exactly as Gumroad's docs instruct.
    complete_data = [
        ("access_token", token),
        ("upload_id", upload_id),
        ("key", key),
    ]
    for cp in completed_parts:
        complete_data.append(("parts[][part_number]", cp["part_number"]))
        complete_data.append(("parts[][etag]", cp["etag"]))
    r = requests.post(f"{GUMROAD_API_BASE}/files/complete", data=complete_data, timeout=120)
    data = r.json()
    if not data.get("success"):
        _abort_upload(token, upload_id)
        raise RuntimeError(f"Gumroad complete failed: {_gumroad_error(data)}")

    return data.get("file_url") or key

def create_product(token, product_spec):
    if not token or not str(token).strip():
        raise ConfigError("create_product requires a non-empty token")
    file_path = product_spec.get("file_path")
    if not file_path:
        raise ConfigError("product_spec missing 'file_path'")

    price_cents = product_spec.get("price_cents")
    if price_cents is None:
        raise ConfigError("product_spec missing 'price_cents'")
    try:
        price_cents = int(price_cents)
    except (TypeError, ValueError):
        raise ConfigError(f"product_spec 'price_cents' must be an integer, got {price_cents!r}")
    if price_cents <= 0:
        raise ConfigError(f"product_spec 'price_cents' must be > 0, got {price_cents}")

    title = (product_spec.get("title") or "").strip() if isinstance(product_spec.get("title"), str) else product_spec.get("title")
    if not title:
        raise ConfigError("product_spec missing 'title'")

    # Presign -> Upload -> Complete -> Get URL, then attach files[][url].
    # File existence is validated inside _upload_file(); price/title are
    # validated BEFORE any network call so a bad spec never starts an S3
    # multipart session on Gumroad's side.
    file_url = _upload_file(token, file_path)

    data = {
        "access_token": token,
        "name": title,
        "price": price_cents,
        "description": product_spec.get("description", ""),
        "customizable_price": "false",
        "files[][url]": file_url
    }
    try:
        r = requests.post(f"{GUMROAD_API_BASE}/products", data=data, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad create_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad create_product failed: {_gumroad_error(result)}")
    return result.get("product", result)


def update_product(token, product_id, updates):
    if not product_id:
        raise ConfigError("update_product requires a product_id")
    # Form-encoding cannot carry arrays natively: Gumroad's API expects
    # list fields as repeated `key[]` params (verified live: plain lists
    # are rejected with "tags must be an array of strings"). Translate here
    # so callers pass natural Python lists.
    data = {}
    for key, value in dict(updates).items():
        if isinstance(value, list):
            data[key + "[]"] = value
        else:
            data[key] = value
    data["access_token"] = token
    try:
        r = _request_with_retry("PUT", f"{GUMROAD_API_BASE}/products/{product_id}", data=data, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad update_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad update_product failed: {_gumroad_error(result)}")
    return result.get("product", result)


def enable_product(token, product_id):
    """Publish a draft product so it becomes purchasable (PUT
    /v2/products/:id/enable -- the real publish endpoint; the 'publish'
    field on PUT /v2/products/:id does NOT publish, it stays a draft).

    CORRECTION (2026-09-17, observed): do NOT assume creates arrive as
    hidden drafts. A live POST /v2/products creation returned
    published:true with a publicly rendering page, so treat every created
    product as publicly visible until proven otherwise. There is NO
    delete/archive endpoint wired anywhere in this integration -- a
    created product persists (dashboard-manual removal only).

    Gumroad's publishing requirements (official docs, verified 2026-08-14):
    user's email confirmed, at least one payment method connected, and
    valid pricing. Any unmet requirement is surfaced honestly via
    _gumroad_error() -- never faked into a success."""
    if not product_id:
        raise ConfigError("enable_product requires a product_id")
    try:
        r = _request_with_retry("PUT", f"{GUMROAD_API_BASE}/products/{product_id}/enable",
                                data={"access_token": token}, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad enable_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad enable_product failed: {_gumroad_error(result)}")
    return result.get("product", result)


def get_product(token, product_id):
    """Retrieve a single real product's current state (GET
    /v2/products/:id) -- used to verify price/published/url after
    create/enable without trusting the caller's own assumptions."""
    if not product_id:
        raise ConfigError("get_product requires a product_id")
    try:
        r = _request_with_retry("GET", f"{GUMROAD_API_BASE}/products/{product_id}",
                                params={"access_token": token}, timeout=30)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad get_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad get_product failed: {_gumroad_error(result)}")
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
        raise RuntimeError(f"Gumroad get_sales failed: {_gumroad_error(data)}")
    return data.get("sales", [])


def _safe_err(exc):
    """Stringify a requests exception WITHOUT ever letting the access_token
    (present in the request URL/params/body) leak into an error message."""
    text = str(exc)
    candidates = set()
    env_token = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
    if env_token:
        candidates.add(env_token.strip().strip("'\""))
    if _LAST_LOADED_TOKEN:
        candidates.add(_LAST_LOADED_TOKEN)
    for token in candidates:
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
    parser.add_argument("--enable", metavar="PRODUCT_ID", help="Publish a draft product so it becomes purchasable (PUT /products/:id/enable)")
    parser.add_argument("--get", metavar="PRODUCT_ID", help="Retrieve one product's current real state")
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

        if args.enable:
            product = enable_product(token, args.enable)
            emit({"success": True, "product": product})
            return

        if args.get:
            product = get_product(token, args.get)
            emit({"success": True, "product": product})
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
