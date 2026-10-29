"""Fail-closed, per-product publication authorization.

A batch-level statement such as "publish the ten products" is not an
authorization for any individual listing. This module only accepts an
explicit, immutable approval record that binds ONE product to:

  * its exact product id,
  * its exact price in cents and its currency,
  * the exact actions granted (upload, publish, or both),
  * the exact product revision (a digest over the title, description,
    price, currency, tags/category and every deliverable's bytes),
  * a real approval reference and a real expiry.

Missing, malformed, ambiguous, expired, revoked, future-dated, or
mismatched records raise. Nothing here mints, edits, or infers an
approval. The approval file is read-only input; it is never written by
this module or by the publisher.

Approval file shape (JSON)::

    {
      "approvals": [
        {
          "approval_id": "GF-B15-001-20261025-01",
          "status": "APPROVED",
          "approved_by": "founder",
          "approval_reference": "founder message/email/issue reference",
          "approved_at": "2026-10-25T09:00:00Z",
          "expires_at": "2026-10-26T09:00:00Z",
          "product_id": "B15-001",
          "price_cents": 1500,
          "currency": "USD",
          "actions": ["upload", "publish"],
          "revision_sha256": "<64 lowercase hex>"
        }
      ]
    }

The revision digest is produced by :func:`product_revision`. An approval
for a different revision, price, currency, action set, or product is
refused rather than repaired.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALLOWED_ACTIONS = ("upload", "publish")
REQUIRED_APPROVAL_FIELDS = (
    "approval_id",
    "status",
    "approved_by",
    "approval_reference",
    "approved_at",
    "expires_at",
    "product_id",
    "price_cents",
    "currency",
    "actions",
    "revision_sha256",
)
MAX_CLOCK_SKEW_SECONDS = 300
DEFAULT_SESSION_MAX_AGE_SECONDS = 3600
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class AuthorizationError(Exception):
    """Base class for every fail-closed authorization refusal."""


class MissingApproval(AuthorizationError):
    pass


class MalformedApproval(AuthorizationError):
    pass


class MissingApprovalRecord(MissingApproval):
    pass


class AmbiguousApproval(AuthorizationError):
    pass


class ProductRevisionError(AuthorizationError):
    pass


class ApprovalRefused(AuthorizationError):
    pass


class StaleSession(AuthorizationError):
    pass


def _reject_duplicate_keys(pairs):
    seen = set()
    for key, _value in pairs:
        if key in seen:
            raise MalformedApproval(f"approval JSON contains duplicate key {key!r}")
        seen.add(key)
    return dict(pairs)


def _strict_json(text):
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                MalformedApproval(f"approval JSON contains non-finite value {value!r}")
            ),
        )
    except MalformedApproval:
        raise
    except Exception as exc:
        raise MalformedApproval(f"approval JSON is not readable ({type(exc).__name__})") from exc


def _parse_timestamp(value, field):
    if not isinstance(value, str) or not value.strip():
        raise MalformedApproval(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except Exception as exc:
        raise MalformedApproval(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _now(now=None):
    if now is None:
        return datetime.now(timezone.utc)
    if isinstance(now, datetime):
        return now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return datetime.fromtimestamp(float(now), tz=timezone.utc)


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _product_file(product, key, root):
    entry = (product.get("files") or {}).get(key)
    if not isinstance(entry, dict) or not entry.get("path"):
        raise ProductRevisionError(f"product has no {key!r} file entry")
    path = Path(entry["path"])
    if not path.is_absolute():
        path = Path(root or ".") / path
    if not path.is_file():
        raise ProductRevisionError(f"product {key!r} file is missing: {path}")
    return path


def _normalise_tags(value):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        raise ProductRevisionError("tags must be a list when present")
    return sorted(str(tag) for tag in value)


def product_currency(product):
    value = product.get("currency") or product.get("price_currency")
    if not isinstance(value, str) or not value.strip():
        return None
    normalised = value.strip().upper()
    return normalised if _CURRENCY.match(normalised) else None


def product_revision(product, *, root=None):
    """Digest the exact product the approval would authorise.

    The digest is over actual file bytes, not the manifest's own claims,
    so replacing a bundle after review changes the revision. It also
    includes title, description, price, currency, tags/category and any
    existing platform id, so a listing edit cannot reuse an old approval.
    """
    if not isinstance(product, dict):
        raise ProductRevisionError("product must be a mapping")
    product_id = product.get("id")
    if not isinstance(product_id, str) or not product_id.strip():
        raise ProductRevisionError("product id is missing")
    title = product.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ProductRevisionError("product title is missing")
    price = product.get("price_cents")
    if not isinstance(price, int) or isinstance(price, bool):
        raise ProductRevisionError("product price_cents must be an integer")
    currency = product_currency(product)
    if currency is None:
        raise ProductRevisionError("product currency is UNKNOWN; refusing to bind an approval to it")
    description = ((product.get("qa") or {}).get("listing") or {}).get("description_html")
    if not isinstance(description, str) or not description.strip():
        raise ProductRevisionError("product listing description is missing")

    payload = {
        "product_id": product_id,
        "slug": product.get("slug"),
        "title": title,
        "price_cents": price,
        "currency": currency,
        "tags": _normalise_tags(product.get("tags")),
        "category": product.get("category"),
        "description_html": description,
        "existing_product_id": product.get("existing_product_id"),
        "bundle_sha256": _sha256_file(_product_file(product, "bundle", root)),
        "workbook_sha256": _sha256_file(_product_file(product, "workbook", root)),
        "guide_sha256": _sha256_file(_product_file(product, "guide", root)),
        "cover_sha256": _sha256_file(_product_file(product, "cover", root)),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def load_approvals(path):
    if not path:
        raise MissingApproval("no publication approval file was supplied")
    approval_path = Path(path)
    if not approval_path.is_file():
        raise MissingApproval(f"publication approval file does not exist: {approval_path}")
    try:
        text = approval_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise MalformedApproval(f"approval file is not readable ({type(exc).__name__})") from exc
    data = _strict_json(text)
    if isinstance(data, dict):
        records = data.get("approvals")
    else:
        records = data
    if not isinstance(records, list):
        raise MalformedApproval("approval file must be a list or an object with an 'approvals' list")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise MalformedApproval(f"approval record {index} is not an object")
    return records


def _normalise_actions(value):
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "both":
            return ["upload", "publish"]
        parts = [lowered] if lowered else []
    elif isinstance(value, (list, tuple)):
        parts = [str(item).strip().lower() for item in value]
    else:
        raise MalformedApproval("actions must be a list or the string 'both'")
    if not parts or any(not part for part in parts):
        raise MalformedApproval("actions must name at least one action")
    if "both" in parts:
        raise MalformedApproval("'both' may only be used alone, not mixed with other actions")
    unknown = sorted(set(parts) - set(ALLOWED_ACTIONS))
    if unknown:
        raise MalformedApproval(f"unknown actions: {unknown}")
    if len(parts) != len(set(parts)):
        raise MalformedApproval("actions contains a duplicate")
    return parts


def _require_text(record, field):
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MalformedApproval(f"{field} must be a non-empty string")
    return value.strip()


def validate_approval(record, product, *, root=None, required_actions=("upload", "publish"),
                      now=None, max_age_seconds=None):
    """Validate one record against one product; raise on any mismatch."""
    if not isinstance(record, dict):
        raise MalformedApproval("approval record must be an object")
    missing = [field for field in REQUIRED_APPROVAL_FIELDS if field not in record]
    if missing:
        raise MalformedApproval(f"approval record is missing fields: {missing}")

    approval_id = _require_text(record, "approval_id")
    if record.get("status") != "APPROVED":
        raise ApprovalRefused(f"approval {approval_id} status is {record.get('status')!r}, not 'APPROVED'")
    if str(record.get("approved_by") or "").strip().lower() != "founder":
        raise ApprovalRefused(f"approval {approval_id} was not issued by the founder")
    reference = _require_text(record, "approval_reference")
    if record.get("revoked_at") or record.get("superseded_by"):
        raise ApprovalRefused(f"approval {approval_id} is revoked or superseded")

    if not isinstance(product, dict):
        raise ProductRevisionError("product must be a mapping")
    product_id = product.get("id")
    if not isinstance(product_id, str) or not product_id.strip():
        raise ProductRevisionError("product id is missing")
    if record.get("product_id") != product_id or product_id in ("*", "all", "batch"):
        raise ApprovalRefused(
            f"approval {approval_id} is bound to product {record.get('product_id')!r}, "
            f"not {product_id!r}"
        )

    price = product.get("price_cents")
    if not isinstance(price, int) or isinstance(price, bool):
        raise ProductRevisionError("product price_cents must be an integer")
    approved_price = record.get("price_cents")
    if not isinstance(approved_price, int) or isinstance(approved_price, bool):
        raise MalformedApproval("approval price_cents must be an integer")
    if approved_price != price:
        raise ApprovalRefused(
            f"approval {approval_id} is bound to price_cents={approved_price}, "
            f"not the product's {price}"
        )

    currency = product_currency(product)
    if currency is None:
        raise ProductRevisionError("product currency is UNKNOWN; cannot validate an approval")
    approved_currency = record.get("currency")
    if not isinstance(approved_currency, str) or not _CURRENCY.match(approved_currency.strip().upper()):
        raise MalformedApproval("approval currency must be a three-letter code")
    if approved_currency.strip().upper() != currency:
        raise ApprovalRefused(
            f"approval {approval_id} is bound to currency {approved_currency!r}, "
            f"not the product's {currency!r}"
        )

    granted = _normalise_actions(record.get("actions"))
    required = _normalise_actions(required_actions)
    absent = [action for action in required if action not in granted]
    if absent:
        raise ApprovalRefused(
            f"approval {approval_id} does not grant required action(s): {absent}"
        )

    revision = record.get("revision_sha256")
    if not isinstance(revision, str) or not _HEX64.match(revision.strip().lower()):
        raise MalformedApproval("approval revision_sha256 must be 64 lowercase hex characters")
    actual_revision = product_revision(product, root=root)
    if revision.strip().lower() != actual_revision:
        raise ApprovalRefused(
            f"approval {approval_id} is bound to revision {revision}, "
            f"but the product's current revision is {actual_revision}"
        )

    approved_at = _parse_timestamp(record.get("approved_at"), "approved_at")
    expires_at = _parse_timestamp(record.get("expires_at"), "expires_at")
    current = _now(now)
    if approved_at > current + timedelta(seconds=MAX_CLOCK_SKEW_SECONDS):
        raise ApprovalRefused(f"approval {approval_id} is dated in the future")
    if expires_at <= approved_at:
        raise ApprovalRefused(f"approval {approval_id} expires before it was approved")
    if current >= expires_at:
        raise ApprovalRefused(f"approval {approval_id} expired at {expires_at.isoformat()}")
    if max_age_seconds is not None:
        if (current - approved_at).total_seconds() > int(max_age_seconds):
            raise ApprovalRefused(f"approval {approval_id} is stale")

    return {
        "approval_id": approval_id,
        "approval_reference": reference,
        "product_id": product_id,
        "price_cents": price,
        "currency": currency,
        "actions": granted,
        "revision_sha256": actual_revision,
        "approved_at": approved_at.isoformat(),
        "expires_at": expires_at.isoformat(),
    }


def select_approval(approvals, product_id):
    matches = [record for record in approvals if record.get("product_id") == product_id]
    if not matches:
        raise MissingApprovalRecord(f"no approval record exists for product {product_id!r}")
    if len(matches) > 1:
        raise AmbiguousApproval(
            f"{len(matches)} approval records exist for product {product_id!r}; refusing to choose one"
        )
    return matches[0]


def require_approval(approvals, product, *, root=None, required_actions=("upload", "publish"),
                     now=None, max_age_seconds=None):
    record = select_approval(approvals, product.get("id"))
    return validate_approval(
        record,
        product,
        root=root,
        required_actions=required_actions,
        now=now,
        max_age_seconds=max_age_seconds,
    )


def inspect_approval(approvals, product, *, root=None, required_actions=("upload", "publish"),
                     now=None, max_age_seconds=None):
    if approvals is None:
        return {"status": "MISSING", "reason": "no approval file was supplied"}
    try:
        return {
            "status": "VALID",
            "reason": "approval matches product id, price, currency, actions and revision",
            **require_approval(
                approvals,
                product,
                root=root,
                required_actions=required_actions,
                now=now,
                max_age_seconds=max_age_seconds,
            ),
        }
    except AmbiguousApproval as exc:
        return {"status": "AMBIGUOUS", "reason": str(exc)}
    except MissingApprovalRecord as exc:
        return {"status": "MISSING", "reason": str(exc)}
    except AuthorizationError as exc:
        return {"status": "INVALID", "reason": str(exc)}


def assert_session_fresh(state, *, now=None, max_age_seconds=DEFAULT_SESSION_MAX_AGE_SECONDS):
    """Refuse a stale or non-verified Gumroad credential state.

    ``write_gate`` performs the same check immediately before a write; this
    pre-flight copy lets a batch stop before any product is touched.
    """
    if not isinstance(state, dict):
        raise StaleSession("no Gumroad auth state was returned")
    if str(state.get("status") or "").strip() != "VERIFIED":
        raise StaleSession(f"Gumroad auth state is {state.get('status')!r}, not VERIFIED")
    stamp = state.get("at")
    if not stamp:
        raise StaleSession("Gumroad auth state has no timestamp")
    at = _parse_timestamp(stamp, "auth state at")
    current = _now(now)
    age = (current - at).total_seconds()
    if age > int(max_age_seconds):
        raise StaleSession(
            f"Gumroad auth state is {int(age)}s old (> {int(max_age_seconds)}s); refusing a live write"
        )
    if age < -MAX_CLOCK_SKEW_SECONDS:
        raise StaleSession("Gumroad auth state timestamp is in the future")
    return {"status": "VERIFIED", "at": at.isoformat(), "age_seconds": int(age)}
