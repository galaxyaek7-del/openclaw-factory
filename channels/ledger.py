"""OpenClaw Factory — unified sales ledger writer (OCTOPUS_ARCHITECTURE.md §10.4).

Single append-only source of truth for distribution events, replacing the
"published: true" claim that OCTOPUS_ARCHITECTURE.md §7 identified as a
lie. One file, two event types — not a separate published_events.jsonl
plus a separate sales file:

  publish_attempt  — an arm's publish() call returned, success or failure.
                      Recorded from a PublishResult (channels/base_arm.py).
  sale             — a real sale as reported by a platform's get_sales().

Each line is one JSON object. Never overwrites, never rewrites history —
append only, so a corrupt write can't destroy prior events (unlike the
data/finance.json incident this project already hit once).

This module does not wire itself into reality.py or any arm automatically
— that integration is a deliberate follow-up, not done here, so existing
reads of config/reality.json / finance_data.json are untouched.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER_PATH = _FACTORY_ROOT / "data" / "sales_ledger.jsonl"

_VALID_EVENT_TYPES = {"publish_attempt", "sale"}


def append_event(event: dict, ledger_path=None) -> dict:
    """Append one validated event as a single JSON line. Returns the event
    actually written (with a timestamp filled in if missing)."""
    if event.get("event_type") not in _VALID_EVENT_TYPES:
        raise ValueError(
            f"event_type must be one of {_VALID_EVENT_TYPES}, got {event.get('event_type')!r}"
        )

    record = dict(event)
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return record


def record_publish_attempt(product, result, ledger_path=None) -> dict:
    """Build a publish_attempt event from a Product + PublishResult and
    append it. Never raises on a failed publish — a failure is exactly what
    this ledger exists to record honestly."""
    event = {
        "event_type": "publish_attempt",
        "platform": result.platform,
        "ok": result.ok,
        "dry_run": result.dry_run,
        "product_id": result.product_id,
        "url": result.url,
        "error": result.error,
        "product_title": getattr(product, "title", None),
        "product_source_id": getattr(product, "source_id", None),
        "product_type": getattr(product, "product_type", None),
    }
    return append_event(event, ledger_path=ledger_path)


def record_sale(platform: str, sale: dict, ledger_path=None) -> dict:
    """Append one real sale as reported by a platform's get_sales(). The raw
    sale dict is kept under "raw" verbatim — never reshaped/guessed, since a
    ledger meant to replace a lie must not introduce a new one."""
    event = {
        "event_type": "sale",
        "platform": platform,
        "raw": sale,
    }
    return append_event(event, ledger_path=ledger_path)


def read_events(event_type=None, ledger_path=None):
    """Yield every event in the ledger, optionally filtered by event_type.
    Missing ledger file yields nothing (a ledger with zero events yet is not
    an error)."""
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type is not None and record.get("event_type") != event_type:
                continue
            yield record
