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
import re
import sys
import time
from pathlib import Path

import requests

FACTORY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = FACTORY_DIR / ".env"
GUMROAD_API_BASE = "https://api.gumroad.com/v2"
# Cycle 85: sentinel for a product that does not exist yet (a create). Still
# part of the upload binding, so one creation authorization cannot be replayed
# for another.
NEW_PRODUCT = "NEW_PRODUCT"

# Cycle 85 Phase 3: abort capabilities, derived from a spent upload grant.
#
# A multipart upload id is assigned by the server AT PRESIGN TIME, so it
# cannot be named in a scope before the upload begins. Requiring a second,
# separately minted abort scope would therefore make cleanup impossible -- and
# would break the contract that a failed abort must never mask the original
# upload error.
#
# Instead, when _upload_file consumes a valid authorization it registers the
# upload id it just created as a capability belonging to that product. Only
# such an id may be aborted without an explicit abort scope. An id this
# process never created -- someone else's session -- is not in this table and
# can never be released through this code path.
_ABORT_CAPABILITIES: "dict[str, str]" = {}


def _grant_abort_capability(upload_id, product_id):
    _ABORT_CAPABILITIES[str(upload_id)] = str(product_id or NEW_PRODUCT)


def _is_own_upload_session(upload_id, product_id):
    return _ABORT_CAPABILITIES.get(str(upload_id)) == str(
        product_id or NEW_PRODUCT)

# PHASE 5 (2026-10-14): every mutation function below begins with
# _require_write_authorization(). The import is deliberately made at MODULE
# level and the helper aliased at import time, so the check cannot be shadowed
# by a later local definition, and so any alternate call path that reaches
# these functions -- direct call, alias, partial import -- goes through the
# same gate. If this import ever fails, module import fails loudly rather than
# silently shipping write functions with no authorization at all.
from channels.write_gate import (
    require_write_authorization as _require_write_authorization,
    WriteNotAuthorized,
)
# list_products()'s pagination safety backstop -- module level (not a local)
# so a test can patch it to a small number instead of looping 50 real times.
_MAX_PAGES = 50

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


class DuplicateListing(Exception):
    """A non-deleted listing with the same title already exists (Cycle 91)."""


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
    """Returns the REAL, COMPLETE product catalog.

    REAL BUG, found and fixed 2026-10-13: GET /v2/products is paginated by
    Gumroad at 10 items per page (next_page_key/next_page_url in the raw
    response) and this function returned only that first page, silently.
    Live-verified against the real account: list_products() reported 10
    products while the account genuinely holds 77 across 8 pages. Every
    caller of this function across this factory (channels/gumroad_arm.py's
    verify_product(), autonomous_commerce_ops.py, commercial_activation.py,
    commercial_operations.py, scripts/p1_autonomous_loop.py and others) has
    therefore been auditing/verifying against at most the 10 most-recently-
    created products and silently missing the rest for as long as this
    function has existed -- never a fabricated result, but an incomplete
    one presented as complete.

    Fix: follow next_page_key until the API stops supplying one, exactly
    the mechanism Gumroad's own response already exposes. Three real
    safety guards, not just one, so a partial/broken inventory is never
    silently reported as complete:
      - a repeated page_key is refused immediately (a real pagination
        cycle, not an expected page count);
      - products are de-duplicated by id across pages (a legitimate
        real-world case if the catalog mutates mid-walk, e.g. a product
        created between two page fetches shifting the cursor window --
        never silently double-counted);
      - a hard page cap (50 pages = 500 products) is the final backstop
        against a key that never terminates at all; this account's real
        77 products fit in 8 pages today, so the cap is a backstop, not
        an expected limit.
    A mid-walk failure (HTTP error, success:false, or the cap) raises
    with the real partial progress (pages fetched so far, product count
    so far) in the message -- a caller must never be able to mistake a
    stopped-partway inventory for a complete one.
    """
    all_products = []
    seen_ids = set()
    seen_page_keys = set()
    page_key = None
    pages_fetched = 0
    while True:
        params = {"access_token": token}
        if page_key:
            params["page_key"] = page_key
        try:
            r = _request_with_retry("GET", f"{GUMROAD_API_BASE}/products", params=params, timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(
                f"Gumroad list_products request failed after {pages_fetched} page(s) "
                f"({len(all_products)} product(s) fetched so far -- inventory INCOMPLETE, "
                f"never report this as a full catalog): {_safe_err(e)}"
            )
        data = r.json()
        if not data.get("success", False):
            raise RuntimeError(
                f"Gumroad API returned success=false after {pages_fetched} page(s) "
                f"({len(all_products)} product(s) fetched so far -- inventory INCOMPLETE): "
                f"{_gumroad_error(data)}"
            )
        for product in data.get("products", []):
            pid = product.get("id") if isinstance(product, dict) else None
            if pid is not None:
                if pid in seen_ids:
                    continue  # real-world overlap between pages -- skip, never double-count
                seen_ids.add(pid)
            all_products.append(product)
        pages_fetched += 1
        page_key = data.get("next_page_key")
        if not page_key:
            break
        if page_key in seen_page_keys:
            raise RuntimeError(
                f"Gumroad list_products: next_page_key repeated after {pages_fetched} page(s) "
                f"({len(all_products)} product(s) fetched so far -- inventory INCOMPLETE) -- "
                "pagination is cycling, not progressing; refusing to loop forever."
            )
        seen_page_keys.add(page_key)
        if pages_fetched >= _MAX_PAGES:
            raise RuntimeError(
                f"Gumroad list_products: stopped after {_MAX_PAGES} pages "
                f"({len(all_products)} products) with next_page_key still present -- "
                "refusing to loop forever rather than silently truncating again."
            )
    return all_products


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


def _require_scoped_upload_authorization(operation, *, product_id, value,
                                        token, scope_id=None):
    """
    Cycle 85 Phase 3. Central gate for the two helpers that hold their own
    requests.post and previously had NO gate of their own.

    FAIL CLOSED: no scope_id means no upload and no abort, ever. The check
    runs before any network call, so a denial cannot leave a dangling S3
    multipart session on the platform side -- which is precisely the state
    this pair of helpers exists to clean up.

    product_id may be the NEW_PRODUCT sentinel for a create, where the
    product does not exist yet. It is still part of the binding, so an
    authorization minted for one creation cannot be replayed for another.
    """
    if not scope_id:
        # For an abort, `value` is the upload_id this call would cancel.
        if operation == "abort_upload" and _is_own_upload_session(value,
                                                                  product_id):
            return  # cleanup of a session this process just created
        raise WriteNotAuthorized(
            f"BLOCKED {operation}: no scoped authorization supplied. An upload "
            f"or an abort requires a single-use authorization bound to this "
            f"exact {operation.replace('_', ' ')}.")
    field = "file_path" if operation == "upload_file" else "upload_id"
    from channels.write_scope import consume_scope
    d = consume_scope(scope_id=scope_id,
                      product_id=product_id or NEW_PRODUCT,
                      payload={field: value},
                      operation=operation)
    if not d.allowed:
        raise WriteNotAuthorized(f"BLOCKED {operation}: {d.reason}")


def _abort_upload(token, upload_id, *, scope_id=None, product_id=None):
    """Cancel an interrupted presigned upload (POST /v2/files/abort) so the
    dangling S3 multipart session is released. Gumroad's contract: responses
    carry a `status` of `accepted` (S3 took the cancellation but parts in
    flight may finish seconds later) or `already_gone` (no session left).
    Call again while `accepted`; stop on `already_gone`. Never raises - a
    failed abort must never mask the original upload error.

    Cycle 85 Phase 3: this posts to the network and previously had no gate of
    its own. It now REQUIRES a scoped authorization bound to this exact upload
    session id, so an abort can never be aimed at a session the caller does
    not own. Releasing your OWN dangling session is the safe act; releasing
    someone else's is not reachable through this code path at all.
    """
    _require_scoped_upload_authorization(
        "abort_upload", product_id=product_id, value=str(upload_id),
        token=token, scope_id=scope_id)
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


def _upload_file(token, file_path, *, scope_id=None, product_id=None):
    _require_scoped_upload_authorization(
        "upload_file", product_id=product_id, value=str(file_path),
        token=token, scope_id=scope_id)
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

    # The upload id is assigned by the server. From this moment on, THIS
    # process may release exactly this one session and no other.
    _grant_abort_capability(upload_id, product_id)

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
        _abort_upload(token, upload_id, product_id=product_id)
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
        _abort_upload(token, upload_id, product_id=product_id)
        raise RuntimeError(f"Gumroad complete failed: {_gumroad_error(data)}")

    return data.get("file_url") or key

def _norm_title(t):
    return re.sub(r"\s+", " ", str(t or "")).strip().casefold()


def _check_attachment(file_path, expected_sha256=None):
    """Cycle 91: the attachment must be a readable, non-empty file and, when
    the caller names it, exactly the expected file (sha256). Runs before any
    network call or scope consumption."""
    import hashlib
    fp = Path(file_path)
    if not fp.exists() or not fp.is_file():
        raise ConfigError(f"product file not found: {fp}")
    try:
        data = fp.read_bytes()
    except OSError as e:
        raise ConfigError(f"product file unreadable: {fp} ({e})")
    if not data:
        raise ConfigError(f"product file is empty (0 bytes): {fp}")
    if expected_sha256 is not None:
        got = hashlib.sha256(data).hexdigest()
        if got != str(expected_sha256).strip().lower():
            raise ConfigError(f"product file identity mismatch: {fp.name} sha256 {got[:12]}… "
                              f"!= expected {str(expected_sha256)[:12]}…")


def _find_duplicate_listing(token, title):
    """Cycle 91: a non-deleted listing whose title matches, or None. Reads the
    live catalog (GET only). If the catalog cannot be read, uniqueness cannot
    be proven, so this raises instead of returning None (fail closed)."""
    want = _norm_title(title)
    try:
        existing = list_products(token)
    except Exception as e:  # noqa: BLE001
        raise DuplicateListing(f"cannot verify uniqueness, catalog unreadable: {_safe_err(e)}")
    for p in existing or []:
        if not p.get("deleted") and _norm_title(p.get("name")) == want:
            return p
    return None


def create_product(token, product_spec, *, upload_scope_id=None):
    # PHASE 5 (2026-10-14): mandatory, centralized write authorization.
    # This is the FIRST statement on purpose -- a denied write must not be
    # able to start an S3 multipart session on Gumroad's side via
    # _upload_file() further down. Previously this function performed NO auth
    # check at all; the "writes blocked" posture reported across several
    # cycles was a convention, not a control. See channels/write_gate.py.
    _require_write_authorization("create_product")
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

    # Cycle 91, before any upload or scope consumption: the attachment must be
    # readable (and the expected file, when named), and no live listing may
    # already carry this title -- re-running a batch must never create a
    # second paid listing. No override argument.
    _check_attachment(file_path, product_spec.get("expected_sha256"))
    dup = _find_duplicate_listing(token, title)
    if dup is not None:
        raise DuplicateListing(f"a listing titled {title!r} already exists "
                               f"({dup.get('short_url') or dup.get('id')}); not creating another")

    # Presign -> Upload -> Complete -> Get URL, then attach files[][url].
    # File existence is validated inside _upload_file(); price/title are
    # validated BEFORE any network call so a bad spec never starts an S3
    # multipart session on Gumroad's side.
    # Cycle 85 Phase 3: the upload is its own mutation with its own gate. A
    # product does not exist yet, so it binds to the NEW_PRODUCT sentinel.
    file_url = _upload_file(token, file_path, scope_id=upload_scope_id,
                           product_id=NEW_PRODUCT)

    data = {
        "access_token": token,
        "name": title,
        "price": price_cents,
        "description": product_spec.get("description", ""),
        "customizable_price": "false",
        "files[][url]": file_url
    }
    # 2026-10-30: tags/taxonomy were previously accepted in a spec and silently
    # dropped, so every listing created through this path landed with zero tags
    # while the publisher's audit reported "tags present" (it reads the
    # manifest, not the created listing). Forward them when supplied; callers
    # still verify persistence after the create.
    tags = product_spec.get("tags")
    if tags:
        cleaned = [str(t).strip() for t in tags if str(t).strip()]
        if cleaned:
            data["tags[]"] = cleaned
    if product_spec.get("taxonomy_id") is not None:
        data["taxonomy_id"] = product_spec["taxonomy_id"]
    try:
        r = requests.post(f"{GUMROAD_API_BASE}/products", data=data, timeout=120)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad create_product request failed: {_safe_err(e)}")
    result = r.json()
    if not result.get("success", False):
        raise RuntimeError(f"Gumroad create_product failed: {_gumroad_error(result)}")
    return result.get("product", result)


def _fields_match(sent, got):
    """True iff a field we WROTE matches what a fresh re-read returned.

    List-typed fields (today, `tags`) compare as SETS. Two live observations,
    the second superseding the first:
      * 2026-10-13: one written tag list round-tripped in the exact order sent,
        which is why this used to compare lists order-sensitively.
      * 2026-10-18: a real write of the same 8 tags came back in a DIFFERENT
        order, so update_product() raised VERIFICATION_FAILED for a write that
        had in fact persisted. Order is therefore NOT part of the contract.
    Set comparison still detects every real defect: a missing tag, an
    unexpected tag, or a platform-side dedupe of a tag sent twice. It only
    stops treating element order (which Gumroad does not promise) as a
    failure. Every other type compares by plain equality -- no fuzzy or
    normalized comparison for any field this function has not been
    live-verified against, so an unverified transformation reads as a
    mismatch (FAIL), never a silent pass."""
    if isinstance(sent, list) or isinstance(got, list):
        return set(sent or []) == set(got or [])
    return sent == got


def _html_text(value):
    """Visible text of an HTML fragment: tags removed, entities decoded,
    whitespace collapsed. Exact on the text -- not fuzzy."""
    import html as _html
    import re as _re
    text = _re.sub(r"<[^>]+>", " ", _html.unescape(value or ""))
    return _re.sub(r"\s+", " ", text).strip()


def _description_matches(sent, got):
    """`description` is the one field live-verified (2026-10-14) to be
    REFORMATTED on persist: Gumroad rewrites the HTML markup, so the raw
    string never equals what was sent even when the write fully succeeded.
    Two listings rewritten that day read back with byte-identical visible
    text and different markup. Comparing the visible text exactly keeps the
    Cycle 106 guarantee: a silently dropped write leaves the OLD text in
    place, which still fails this check."""
    return sent == got or _html_text(sent) == _html_text(got)


def update_product_description_scoped(token, product_id, description, *,
                                     scope_id, verify_delay_seconds=1.0,
                                     get_product_fn=None):
    """Cycle 85: the ONLY sanctioned way to write a product description.

    Why this function has to exist:

    channels/write_scope.py can mint a single-use authorization bound to
    (product, operation=update_description, field=description, sha256 of the
    exact text), but nothing connected that authorization to a reachable write.
    update_product() calls the unscoped gate with the literal operation
    "update_product", which no scope can ever satisfy, so the scoped mechanism
    was real machinery behind an unusable door.

    The constraints this enforces, none of which update_product() can express:

      * exactly ONE field may be written -- description. A caller that also
        passes price, name, published, files, or tags is refused before any
        network call, because a description repair must never be able to move
        price, title, attachments, or publication state.
      * the authorization is consumed BEFORE the write, and its payload digest
        is checked against the text actually about to be sent, so a scope
        minted for one description cannot be pointed at a different one.
      * the write is verified by re-read, exactly like update_product(), so a
        200 that silently fails to persist is reported as FAIL rather than
        success.

    Returns the freshly re-read product dict on verified success.
    """
    if not product_id:
        raise ConfigError("update_product_description_scoped requires a product_id")
    if not scope_id:
        raise WriteNotAuthorized(
            "BLOCKED update_description: a scoped authorization is required. "
            "There is no unscoped path to a description write, by design.")
    if not isinstance(description, str) or not description:
        raise ConfigError("description must be a non-empty string")

    # Consume and verify the authorization BEFORE handing anything to the
    # network layer. _payload_digest is the same canonicalization
    # write_scope used when the scope was issued; consume_scope already
    # re-derived it from the scope's own allowed_fields, so this second
    # comparison is a redundant-but-cheap defence against the field set
    # itself ever drifting.
    from channels.write_scope import consume_scope, operation_fields
    d = consume_scope(scope_id=scope_id, product_id=product_id,
                      payload={"description": description},
                      operation="update_description")
    if not d.allowed:
        raise WriteNotAuthorized(f"BLOCKED update_description: {d.reason}")
    if operation_fields("update_description") != ("description",):
        raise WriteNotAuthorized(
            "BLOCKED update_description: the operation's field set changed; "
            "refusing to act on an authorization issued under different rules")

    # Single-field enforcement, last gate before the write.
    return _update_product_write_and_verify(
        token, product_id, {"description": description},
        verify_delay_seconds=verify_delay_seconds,
        get_product_fn=get_product_fn)


def update_product(token, product_id, updates, verify_delay_seconds=1.0,
                   get_product_fn=None):
    """Write real product fields, then PROVE the write persisted before
    ever returning as if it succeeded.

    REAL BUG this closes (found 2026-10-11, Cycle 106): Gumroad's PUT
    /v2/products/:id can return HTTP 200 and success:true while NOT
    persisting the written fields -- live-reproduced then: a probe string
    written to description/name was absent on re-read and on the public
    page. This function never again trusts that response alone: every
    write is followed by a real GET /v2/products/:id (the same official
    read endpoint get_product() uses) and the EXACT fields this call asked
    to change are compared against what actually comes back. Untouched
    fields are never compared -- a legitimate platform-side change to some
    other field is not this function's concern and must never fail a
    write it didn't ask for.

    Return/raise contract (PASS/BLOCKED/FAIL/UNKNOWN, honestly distinct,
    matching this factory's own real/estimated/unknown discipline):
      - PASS:    the write API call succeeded AND the re-read matches
                 every requested field -- returns the fresh, re-read
                 product dict (never the unverified PUT response).
      - BLOCKED: Gumroad's own PUT response reported success:false (an
                 explicit platform-side rejection, e.g. the real,
                 live-discovered 'tag too long' constraint) -- raises
                 RuntimeError prefixed "Gumroad update_product failed:",
                 unchanged from before this fix.
      - FAIL:    the PUT reported success, but the re-read PROVES at
                 least one requested field never actually changed --
                 raises RuntimeError prefixed "VERIFICATION_FAILED:",
                 naming exactly which field(s) and the sent-vs-got values.
                 This is the Cycle 106 defect made loud instead of silent.
      - UNKNOWN: the PUT reported success, but the post-write re-read
                 itself could not be completed (network/timeout/malformed
                 response) -- raises RuntimeError prefixed
                 "VERIFICATION_UNKNOWN:". The write MAY have persisted;
                 this function refuses to claim either PASS or FAIL
                 without having actually looked.

    No update requested (`updates` empty/falsy) is refused before any
    network call -- there is nothing to verify, and sending a vacuous PUT
    just to get a success:true would be exactly the kind of unproven claim
    this function exists to prevent.

    verify_delay_seconds (default 1.0, tests pass 0): a small, fixed,
    disclosed wait before the verification re-read -- not evidence of a
    real measured propagation lag (live testing found none; re-reads
    matched immediately), kept only as a cheap safety margin. HTTP-level
    transient failures (5xx/timeouts) are retried independently and
    already, inside _request_with_retry()/get_product() -- this parameter
    is not a substitute for that and does not retry the write.

    get_product_fn is injectable purely so tests can simulate a re-read
    failure/mismatch without a real network call; real callers never
    pass it (defaults to the real get_product())."""
    # PHASE 5 (2026-10-14): mandatory, centralized write authorization --
    # first statement, before any validation or network call, so a denied
    # write cannot leave a partial effect (or an S3 multipart session)
    # behind on Gumroad's side. See channels/write_gate.py.
    _require_write_authorization("update_product")
    return _update_product_write_and_verify(
        token, product_id, updates,
        verify_delay_seconds=verify_delay_seconds,
        get_product_fn=get_product_fn)


def _update_product_write_and_verify(token, product_id, updates,
                                     verify_delay_seconds=1.0,
                                     get_product_fn=None):
    """The write-and-prove body of update_product, with NO gate of its own.

    Split out in Cycle 85 so that update_product_description_scoped() can
    reach it after consuming a single-use, payload-bound authorization. The
    split deliberately does NOT add a `pre_authorized` bypass flag to
    update_product(): a conditional gate would have meant the unscoped entry
    point no longer had the gate as its first executable statement, which is
    a real invariant this factory tests for. Instead update_product() keeps an
    unconditional gate as its first statement, and only the scoped wrapper --
    which enforces exactly one field -- calls this private body.
    """
    if not product_id:
        raise ConfigError("update_product requires a product_id")
    if not updates:
        raise ConfigError("update_product requires at least one field to update")
    read_product = get_product_fn or get_product

    # Form-encoding cannot carry arrays natively: Gumroad's API expects
    # list fields as repeated `key[]` params (verified live: plain lists
    # are rejected with "tags must be an array of strings"). Translate here
    # so callers pass natural Python lists.
    updates = dict(updates)
    data = {}
    for key, value in updates.items():
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
    try:
        result = r.json()
    except ValueError as e:
        raise RuntimeError(f"Gumroad update_product returned invalid JSON: {_safe_err(e)}")
    if not isinstance(result, dict) or not result.get("success", False):
        raise RuntimeError(f"Gumroad update_product failed: {_gumroad_error(result if isinstance(result, dict) else {})}")

    if verify_delay_seconds:
        time.sleep(verify_delay_seconds)
    try:
        reread = read_product(token, product_id)
    except Exception as e:
        raise RuntimeError(
            f"VERIFICATION_UNKNOWN: update_product's write call for {product_id} reported "
            f"success, but the post-write re-read failed, so persistence could not be proven: {_safe_err(e)}"
        )
    if not isinstance(reread, dict):
        raise RuntimeError(
            f"VERIFICATION_UNKNOWN: update_product's post-write re-read for {product_id} "
            f"returned a non-product response ({type(reread).__name__}); persistence could not be proven."
        )

    mismatches = {}
    for key, sent_value in updates.items():
        got_value = reread.get(key)
        same = (_description_matches(sent_value, got_value) if key == "description"
                else _fields_match(sent_value, got_value))
        if not same:
            mismatches[key] = {"sent": sent_value, "got": got_value}
    if mismatches:
        raise RuntimeError(
            f"VERIFICATION_FAILED: update_product's write for {product_id} reported success, "
            f"but a fresh re-read proves {len(mismatches)} field(s) did not persist: {mismatches}"
        )
    return reread


def update_product_file(token, product_id, file_path, verify_delay_seconds=1.0,
                         verify_attempts=3, upload_fn=None, get_product_fn=None,
                         upload_scope_id=None):
    """Replace a product's attached deliverable with a real local file, then
    PROVE it actually attached before returning as if it succeeded.

    Why this is a SEPARATE function from update_product(), not another key
    in its generic `updates` dict: the write and the read use genuinely
    different shapes for a file. The write sends a single string,
    "files[][url]" -> a fresh, signed upload URL from _upload_file(). The
    re-read returns a `files` LIST of dicts, each with its own `size` /
    `filetype` -- and that URL is re-signed by Gumroad on every read
    (different query string each time), so comparing the sent URL against
    the re-read URL would NEVER match even on a fully successful attach.
    update_product()'s generic _fields_match() has no way to know this --
    reusing it here would either always false-FAIL or (worse) silently
    skip real verification. The one real, stable property both sides can
    agree on is the file's own byte size, known locally before upload and
    present in Gumroad's own re-read -- that is what this function proves.

    REAL FINDING (2026-10-13, live): a multi-file zip attach can take
    longer than a simple text-field update to finish processing --
    observed live, the first re-read (after a 3s delay) returned a real
    `files` entry already present but with `size: None` (still being
    processed server-side); a fresh re-read moments later showed the
    correct, matching size. One fixed delay is therefore not enough on
    its own; the verification re-read is retried up to `verify_attempts`
    times with linear backoff before a FAIL is declared, distinguishing
    "still processing" from "genuinely never attached."

    Same honest PASS/BLOCKED/FAIL/UNKNOWN discipline as update_product():
      - PASS:    upload + attach succeeded AND a re-read (possibly after
                 a few retried attempts) proves the `files` list contains
                 an entry whose size matches the real local file exactly
                 -- returns that fresh re-read product.
      - BLOCKED: the attach PUT itself reported success:false.
      - FAIL:    the PUT reported success, but no file of the correct
                 size ever appeared across every verification attempt.
      - UNKNOWN: every post-attach re-read attempt itself failed outright
                 (e.g. network/timeout) -- never a size-mismatch.

    upload_fn/get_product_fn are injectable purely so tests can simulate
    the upload and re-read without a real network call or a real local
    file; real callers never pass them."""
    # PHASE 5 (2026-10-14): mandatory, centralized write authorization --
    # first statement, before any validation or network call, so a denied
    # write cannot leave a partial effect (or an S3 multipart session)
    # behind on Gumroad's side. See channels/write_gate.py.
    _require_write_authorization("update_product_file")
    if not product_id:
        raise ConfigError("update_product_file requires a product_id")
    if not file_path:
        raise ConfigError("update_product_file requires a file_path")
    do_upload = upload_fn or (
        # Cycle 85 Phase 3: when the real uploader runs, it must carry its own
        # scoped authorization bound to this product and this exact file path.
        lambda t, f: _upload_file(t, f, scope_id=upload_scope_id,
                                  product_id=product_id))
    read_product = get_product_fn or get_product

    file_path = Path(file_path)
    try:
        expected_size = os.path.getsize(file_path)
    except OSError as e:
        raise ConfigError(f"cannot read local file size for {file_path}: {e}")
    if expected_size <= 0:
        raise ConfigError(f"local file is empty (0 bytes): {file_path}")

    file_url = do_upload(token, file_path)

    data = {"access_token": token, "files[][url]": file_url}
    try:
        r = _request_with_retry("PUT", f"{GUMROAD_API_BASE}/products/{product_id}", data=data, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad update_product_file request failed: {_safe_err(e)}")
    try:
        result = r.json()
    except ValueError as e:
        raise RuntimeError(f"Gumroad update_product_file returned invalid JSON: {_safe_err(e)}")
    if not isinstance(result, dict) or not result.get("success", False):
        raise RuntimeError(f"Gumroad update_product_file failed: {_gumroad_error(result if isinstance(result, dict) else {})}")

    reread = None
    sizes_seen = []
    for attempt in range(1, verify_attempts + 1):
        if verify_delay_seconds:
            time.sleep(verify_delay_seconds * attempt)
        try:
            reread = read_product(token, product_id)
        except Exception as e:
            raise RuntimeError(
                f"VERIFICATION_UNKNOWN: update_product_file's attach for {product_id} reported "
                f"success, but the post-write re-read failed, so persistence could not be proven: {_safe_err(e)}"
            )
        if not isinstance(reread, dict):
            raise RuntimeError(
                f"VERIFICATION_UNKNOWN: update_product_file's post-write re-read for {product_id} "
                f"returned a non-product response ({type(reread).__name__}); persistence could not be proven."
            )
        reread_files = reread.get("files") or []
        sizes_this_attempt = [f.get("size") for f in reread_files if isinstance(f, dict)]
        sizes_seen.append(sizes_this_attempt)
        if expected_size in sizes_this_attempt:
            return reread

    raise RuntimeError(
        f"VERIFICATION_FAILED: update_product_file's attach for {product_id} reported success, "
        f"but the expected {expected_size}-byte file never appeared across {verify_attempts} "
        f"re-read attempt(s) (sizes seen per attempt: {sizes_seen})"
    )


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
    # PHASE 5 (2026-10-14): mandatory, centralized write authorization --
    # first statement, before any validation or network call, so a denied
    # write cannot leave a partial effect (or an S3 multipart session)
    # behind on Gumroad's side. See channels/write_gate.py.
    _require_write_authorization("enable_product")
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


def add_product_cover(token, product_id, image_url, *, verify_delay_seconds=1.0,
                      get_product_fn=None, expected_cover_count=None):
    """Attach a cover image to a product from a PUBLICLY ACCESSIBLE http(s) URL
    (POST /v2/products/:id/covers -- the real cover endpoint).

    Documented contract (Gumroad API docs, verified 2026-08-05; endpoint added
    by antiwork/gumroad PR #4311): the server FETCHES the URL and stores its own
    copy, so the URL must be reachable over plain HTTP(S) and must NOT be a
    private or pre-signed upload URL. Requires the `edit_products` scope, or the
    `account` scope when authenticating with an API key. Accepts images
    (JPEG/PNG/GIF) and video URLs; WebP is NOT supported.

    Why this function exists: previous rounds recorded "Gumroad's API has no
    cover upload" and pushed the cover to a manual dashboard step. That reading
    was wrong for cover *images*: the endpoint exists. Covers are distinct from
    the product THUMBNAIL (POST /v2/products/:id/thumbnail), which needs an
    ActiveStorage signed blob; the product page renders the first cover as its
    main image, so a cover is sufficient for a professional listing.

    Never trusts the POST response alone: only touches the cover list, then
    PROVES the attach with a fresh GET /v2/products/:id whose `covers` must be
    non-empty and (when Gumroad returns an `original_url`) must contain the URL
    that was sent. It changes no other field -- price, files, name and
    publication state are not part of the request, by the endpoint's contract.

    Return/raise contract, matching update_product()'s honest PASS/BLOCKED/
    FAIL/UNKNOWN discipline:
      - PASS:    POST succeeded and the re-read proves a cover persisted --
                 returns the fresh, re-read product dict.
      - BLOCKED: Gumroad's own response reported success:false (e.g. an
                 unsupported file type or an unreachable URL) -- raises
                 RuntimeError prefixed "Gumroad add_product_cover failed:".
      - FAIL:    POST reported success but the re-read proves no matching
                 cover persisted -- raises RuntimeError prefixed
                 "VERIFICATION_FAILED:". When expected_cover_count is given,
                 a re-read cover count that did not grow is also a FAIL.
      - UNKNOWN: POST reported success but the re-read could not be completed
                 -- raises RuntimeError prefixed "VERIFICATION_UNKNOWN:".
    """
    # Same mandatory, centralized write authorization as every other write in
    # this module: first statement, before any validation or network call.
    _require_write_authorization("update_product")
    if not product_id:
        raise ConfigError("add_product_cover requires a product_id")
    if not isinstance(image_url, str) or not image_url.lower().startswith(("http://", "https://")):
        raise ConfigError(
            "add_product_cover requires a publicly accessible http(s) image URL "
            "(Gumroad fetches it server-side; a local path or pre-signed URL cannot work)")
    try:
        r = _request_with_retry("POST", f"{GUMROAD_API_BASE}/products/{product_id}/covers",
                                data={"access_token": token, "url": image_url}, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Gumroad add_product_cover request failed: {_safe_err(e)}")
    try:
        result = r.json()
    except ValueError as e:
        raise RuntimeError(f"Gumroad add_product_cover returned invalid JSON: {_safe_err(e)}")
    if not isinstance(result, dict) or not result.get("success", False):
        raise RuntimeError(
            f"Gumroad add_product_cover failed: {_gumroad_error(result if isinstance(result, dict) else {})}")

    if verify_delay_seconds:
        time.sleep(verify_delay_seconds)
    read_product = get_product_fn or get_product
    try:
        reread = read_product(token, product_id)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            f"VERIFICATION_UNKNOWN: add_product_cover's POST for {product_id} reported "
            f"success, but the post-write re-read failed, so the attach could not be "
            f"proven: {_safe_err(e)}")
    if not isinstance(reread, dict):
        raise RuntimeError(
            f"VERIFICATION_UNKNOWN: add_product_cover's post-write re-read for {product_id} "
            f"returned a non-product response ({type(reread).__name__}).")

    covers = reread.get("covers")
    if not isinstance(covers, list) or not covers:
        raise RuntimeError(
            f"VERIFICATION_FAILED: add_product_cover's POST for {product_id} reported success, "
            f"but a fresh re-read shows no covers attached (covers={covers!r}).")
    if expected_cover_count is not None and len(covers) <= int(expected_cover_count):
        raise RuntimeError(
            f"VERIFICATION_FAILED: add_product_cover's re-read for {product_id} shows "
            f"{len(covers)} cover(s), which did not grow past the expected {expected_cover_count}.")
    # NOTE (live, 2026-10-18): Gumroad stores its own copy and reports THAT copy
    # as `original_url` (e.g. https://public-files.gumroad.com/...), NOT the URL
    # that was sent -- the docs' oEmbed example is misleading on this point.
    # Comparing the sent URL against original_url therefore produced a false
    # VERIFICATION_FAILED for an attach that had in fact succeeded. Identity is
    # instead established by: a cover exists, it carries a display URL, and the
    # cover count grew when a prior count was supplied.
    if not any(isinstance(c, dict) and c.get("url") for c in covers):
        raise RuntimeError(
            f"VERIFICATION_FAILED: add_product_cover's re-read for {product_id} returned "
            f"cover entries with no display url: {covers!r}")
    return reread


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
    (present in the request URL/params/body) leak into an error message.

    Two layers, deliberately:
      1. known-value redaction - replace the actual token(s) we loaded.
      2. pattern redaction - blank any `access_token=<value>` in a URL,
         even when that value was never loaded into this process. Layer 2
         is what makes the guarantee hold for an exception raised before
         load_token() ran, or with a token from another source."""
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
    text = re.sub(r"(access_token=)[^&\s'\"\\]+", r"\1***REDACTED***", text)
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
        # C100: this handler used str(e) directly. An unexpected exception
        # raised inside requests (rather than one wrapped by a RuntimeError
        # via _safe_err) carries the full request URL, and the access_token
        # travels in the query string - so the raw text printed the live
        # secret to stdout/logs. Route every catch-all through _safe_err so
        # there is exactly one redaction choke point.
        emit({"success": False, "error": _safe_err(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
