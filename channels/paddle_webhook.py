"""Galaxy Forge — Paddle inbound webhook verification (Phase 31, ADR-223,
2026-08-08).

The Phase 30.5 forensic audit found no inbound payment-webhook receiver
exists anywhere in this factory -- every prior "webhook" reference is an
outbound n8n notification call. This module closes that specific gap.

Deliberately does NOT duplicate customer_pipeline.py's real, already-
working payment-confirmation mechanism (check_payment_status()/
check_all_awaiting_payments(), a polling call against Paddle's real
/transactions endpoint). A verified webhook event is only ever used
here as a fast TRIGGER for that same existing, already-tested logic --
never a second, competing order/revenue-recording path. This module's
own responsibility stops at: verify signature -> validate event
structure -> validate against the real product catalog -> idempotency
-> append to a real, append-only evidence ledger. It never writes to
finance_data.json, never creates a customer_pipeline.py request, and
never marks a delivery -- those stay exactly as real and founder/
system-gated as they already are.

No PADDLE_WEBHOOK_SECRET has ever been configured in this factory
(confirmed via .env scan, Phase 30.5 audit) -- every function here
handles that as a real, honest MISSING_SECRET / FOUNDER_ACTION_REQUIRED
state, never a fabricated bypass. All test coverage uses locally-
generated, clearly-fake HMAC signatures over synthetic payloads -- never
a real secret, never a real transaction.
"""

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROCESSED_EVENTS_PATH = _FACTORY_ROOT / "data" / "paddle_webhook_events.jsonl"
DEFAULT_CATALOG_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"

# Real, Paddle-documented event types this factory currently cares about.
# An event type not in this set is honestly rejected as UNKNOWN_EVENT_TYPE
# rather than silently accepted.
KNOWN_EVENT_TYPES = {"transaction.completed", "transaction.paid"}

REJECTION_REASONS = (
    "MISSING_SECRET", "INVALID_SIGNATURE", "MALFORMED_PAYLOAD", "UNKNOWN_EVENT_TYPE",
    "DUPLICATE_EVENT", "PRODUCT_MISMATCH", "AMOUNT_MISMATCH", "CURRENCY_MISMATCH",
)

# Paddle amounts are quoted in the smallest currency unit as strings
# (e.g. "38800" for $388.00) -- this tolerance guards only against real
# float-rounding drift between the catalog's float price and Paddle's
# integer-cents amount, never a business-logic fudge factor.
_AMOUNT_TOLERANCE_CENTS = 1


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def load_webhook_secret(env_path=None):
    """Real, honest secret load -- returns None (never a fabricated
    placeholder) when PADDLE_WEBHOOK_SECRET is not configured."""
    return os.environ.get("PADDLE_WEBHOOK_SECRET")


def parse_signature_header(header):
    """Parses Paddle's real 'Paddle-Signature: ts=<unix>;h1=<hex>' format.
    Returns (ts, h1) or (None, None) on any malformed header -- never
    raises, so a malformed header is a normal INVALID_SIGNATURE
    rejection, not a crash."""
    if not header or not isinstance(header, str):
        return None, None
    parts = {}
    for segment in header.split(";"):
        if "=" not in segment:
            continue
        key, _, value = segment.partition("=")
        parts[key.strip()] = value.strip()
    return parts.get("ts"), parts.get("h1")


def verify_signature(raw_body, signature_header, secret):
    """Real Paddle HMAC-SHA256 verification: HMAC(secret, f"{ts}:{raw_body}")
    compared in constant time against the real h1 digest. raw_body must be
    bytes (the exact, unparsed request body Paddle signed) -- verifying a
    re-serialized/re-parsed body would be a real, subtle security bug this
    function deliberately avoids by taking raw_body as its own parameter."""
    if not secret:
        return False
    ts, h1 = parse_signature_header(signature_header)
    if not ts or not h1:
        return False
    if isinstance(raw_body, str):
        raw_body = raw_body.encode("utf-8")
    signed_payload = f"{ts}:".encode("utf-8") + raw_body
    computed = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, h1)


def _load_catalog(catalog_path=None):
    path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def validate_event_against_catalog(transaction_data, catalog=None, catalog_path=None):
    """Real, mechanical validation -- the event's items must reference a
    real, known price_id, and the total amount/currency must match the
    real catalog entry. Never trusts the event's own product/price
    fields without cross-checking the real, independently-maintained
    catalog."""
    catalog = catalog if catalog is not None else _load_catalog(catalog_path)
    catalog_by_price_id = {c["price_id"]: c for c in catalog if isinstance(c, dict) and c.get("price_id")}

    items = transaction_data.get("items") or []
    if not items:
        return {"valid": False, "reason": "MALFORMED_PAYLOAD", "detail": "no line items in transaction"}

    for item in items:
        price = item.get("price") or {}
        price_id = price.get("id") or item.get("price_id")
        if price_id not in catalog_by_price_id:
            return {"valid": False, "reason": "PRODUCT_MISMATCH", "detail": f"price_id {price_id} not in real catalog"}
        catalog_entry = catalog_by_price_id[price_id]

        totals = transaction_data.get("details", {}).get("totals", {})
        grand_total_cents = totals.get("grand_total") or totals.get("total")
        if grand_total_cents is not None:
            try:
                expected_cents = round(catalog_entry["price"] * 100)
                actual_cents = int(grand_total_cents)
                if abs(actual_cents - expected_cents) > _AMOUNT_TOLERANCE_CENTS:
                    return {"valid": False, "reason": "AMOUNT_MISMATCH",
                            "detail": f"expected ~{expected_cents} cents, got {actual_cents}"}
            except (TypeError, ValueError):
                return {"valid": False, "reason": "MALFORMED_PAYLOAD", "detail": "non-numeric total"}

        currency = totals.get("currency_code")
        if currency and currency != "USD":
            return {"valid": False, "reason": "CURRENCY_MISMATCH", "detail": f"expected USD, got {currency}"}

    return {"valid": True, "reason": None, "detail": None}


def _load_processed_event_ids(path):
    if not path.exists():
        return set()
    ids = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            eid = record.get("event_id")
            if eid:
                ids.add(eid)
    return ids


def _append_event_record(record, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_paddle_webhook(raw_body, signature_header, secret=None, processed_events_path=None,
                            catalog_path=None, now=None):
    """The one real orchestrator. Every rejection path is honest and
    logged (accepted and rejected events are both appended to the same
    real evidence ledger, per Section 6's own 'log rejected events, log
    accepted events' requirement) -- never silently dropped.

    Returns {"status": "ACCEPTED"|"REJECTED", "reason": ..., "event_id": ...,
    "detail": ...}. Never creates an order, never writes finance_data.json,
    never marks a delivery -- see this module's own docstring."""
    processed_events_path = Path(processed_events_path) if processed_events_path else DEFAULT_PROCESSED_EVENTS_PATH
    secret = secret if secret is not None else load_webhook_secret()
    generated_at = _now_iso(now)

    def _reject(reason, detail, event_id=None):
        record = {
            "generated_at": generated_at, "status": "REJECTED", "reason": reason, "detail": detail,
            "event_id": event_id,
        }
        _append_event_record(record, processed_events_path)
        return record

    if not secret:
        return _reject("MISSING_SECRET", "PADDLE_WEBHOOK_SECRET is not configured -- FOUNDER_ACTION_REQUIRED: set it in .env once Paddle's real webhook is configured in vendors.paddle.com.")

    if not verify_signature(raw_body, signature_header, secret):
        return _reject("INVALID_SIGNATURE", "HMAC signature did not match -- event rejected without trusting any of its contents.")

    try:
        payload = json.loads(raw_body if isinstance(raw_body, str) else raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _reject("MALFORMED_PAYLOAD", f"body is not valid JSON: {exc}")

    if not isinstance(payload, dict):
        return _reject("MALFORMED_PAYLOAD", "top-level payload is not a JSON object")

    event_type = payload.get("event_type")
    event_id = payload.get("event_id")

    if event_type not in KNOWN_EVENT_TYPES:
        return _reject("UNKNOWN_EVENT_TYPE", f"'{event_type}' is not a recognized/handled event type", event_id=event_id)

    if not event_id:
        return _reject("MALFORMED_PAYLOAD", "missing event_id -- cannot guarantee idempotency without a real event identifier")

    already_processed = _load_processed_event_ids(processed_events_path)
    if event_id in already_processed:
        return _reject("DUPLICATE_EVENT", f"event_id {event_id} was already processed -- replay/retry rejected, never double-counted", event_id=event_id)

    transaction_data = payload.get("data", {})
    validation = validate_event_against_catalog(transaction_data, catalog_path=catalog_path)
    if not validation["valid"]:
        return _reject(validation["reason"], validation["detail"], event_id=event_id)

    record = {
        "generated_at": generated_at, "status": "ACCEPTED", "reason": None,
        "event_id": event_id, "event_type": event_type,
        "transaction_id": transaction_data.get("id"),
        "custom_data": transaction_data.get("custom_data"),
        "note": "Verified, validated, and recorded. This record is evidence only -- order/customer/revenue creation happens exclusively through customer_pipeline.py's existing, already-tested check_payment_status()/check_all_awaiting_payments() polling path, triggered as a fast follow-up to this event, never duplicated here.",
    }
    _append_event_record(record, processed_events_path)
    return record


def _cli_main():
    """CLI entrypoint matching this factory's existing stdin/stdout JSON
    convention (scripts/check_paddle_checkout_status.py --json, etc.).
    Expects {"raw_body_base64": "...", "signature_header": "..."} on
    stdin -- base64 so binary-exactness of the raw body is never at risk
    of encoding drift crossing the Node<->Python process boundary."""
    import argparse
    import base64

    parser = argparse.ArgumentParser(description="Paddle inbound webhook processor (ADR-223)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.json:
        parser.print_help()
        return

    try:
        job = json.loads(sys.stdin.read())
        raw_body = base64.b64decode(job["raw_body_base64"])
        signature_header = job.get("signature_header")
        result = process_paddle_webhook(raw_body, signature_header)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "REJECTED", "reason": "MALFORMED_PAYLOAD", "detail": str(e)}))


if __name__ == "__main__":
    _cli_main()
