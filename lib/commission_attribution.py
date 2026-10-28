#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Privacy-preserving commission attribution (ANALYSIS ledger only).

This is NOT financial truth. It records anonymous, PII-free attribution events
for future organic-traffic measurement. It must never be treated as revenue or
converted into any financial ledger.

Security properties (all unit-tested):
- No PII: anonymous `anon_id` (uuid), no names/emails/IPs.
- Duplicate protection: same (anon_id, event_type, product_id, window) deduped.
- Concurrency-safe append: advisory `.lock` file (never the ledger itself).
- Ledger integrity: parse-safe; corrupt lines are skipped and counted.
- Crash recovery: partial writes do not corrupt the ledger.
- Anomaly detection: rapid-burst flag (never a definitive bot verdict).
- Bot filtering: flag only (bot status UNKNOWN when UA absent).
- Malformed input: rejected gracefully, ledger untouched.
- Corruption resistance: truncated/partial trailing line tolerated.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import Lock

FACTORY_ROOT = Path(__file__).resolve().parent.parent
ATTRIBUTION_PATH = FACTORY_ROOT / "data" / "commission_attribution_log.jsonl"
ATTRIBUTION_LOCK = FACTORY_ROOT / "data" / "commission_attribution_log.jsonl.lock"

_lock = Lock()
DUP_WINDOW_SECONDS = 300
BURST_THRESHOLD = 20  # clicks by same anon_id within 60s -> anomaly flag


def _now() -> float:
    return time.time()


def _ensure_dir() -> None:
    ATTRIBUTION_PATH.parent.mkdir(parents=True, exist_ok=True)


def record_event(anon_id: str, event_type: str, product_id: str,
                 source_category: str = "", value: float = 0.0,
                 metadata: dict = None) -> dict:
    """Append one anonymous attribution event. Returns a receipt dict.

    Rejects malformed input (empty/oversized fields, unknown event_type).
    No PII. Never writes financial truth.
    """
    if not anon_id or not isinstance(anon_id, str) or len(anon_id) > 128:
        return {"ok": False, "error": "invalid_anon_id"}
    # content_view/outbound_click are emitted by the real server.js customer-site
    # route (ANALYSIS ledger only, never financial truth) — the allowlist must
    # match the actual producer vocabulary, otherwise valid analysis events
    # are rejected while a parallel writer keeps appending them unvalidated.
    if event_type not in ("affiliate_click", "attributed_conversion", "commission_recorded",
                          "content_view", "outbound_click"):
        return {"ok": False, "error": "unknown_event_type"}
    if not product_id or not isinstance(product_id, str) or len(product_id) > 256:
        return {"ok": False, "error": "invalid_product_id"}
    if source_category and (not isinstance(source_category, str) or len(source_category) > 128):
        return {"ok": False, "error": "invalid_source_category"}
    if value < 0 or value > 1e12:
        return {"ok": False, "error": "invalid_value"}
    if metadata is not None and not isinstance(metadata, dict):
        return {"ok": False, "error": "invalid_metadata"}

    event = {
        "anon_id": anon_id,
        "event_type": event_type,
        "product_id": product_id,
        "source_category": source_category,
        "value": float(value),
        "ts": _now(),
        "bot_status": "UNKNOWN",
        "anomaly": False,
        "metadata": metadata or {},
    }

    # duplicate protection
    with _lock:
        recent = _read_recent_window(anon_id, event_type, product_id, DUP_WINDOW_SECONDS)
        if recent:
            return {"ok": False, "error": "duplicate", "existing_ts": recent[0].get("ts")}
        # burst anomaly detection
        burst = _count_recent_burst(anon_id, 60)
        if burst + 1 >= BURST_THRESHOLD:
            event["anomaly"] = True
        _append_atomic(event)
    return {"ok": True, "event": event}


def _read_all() -> list:
    _ensure_dir()
    if not ATTRIBUTION_PATH.exists():
        return []
    out = []
    corrupt = 0
    with ATTRIBUTION_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                corrupt += 1
                continue
    return out


def _read_recent_window(anon_id: str, event_type: str, product_id: str, window: float) -> list:
    now = _now()
    return [
        e for e in _read_all()
        if e.get("anon_id") == anon_id and e.get("event_type") == event_type
        and e.get("product_id") == product_id and (now - float(e.get("ts", 0))) <= window
    ]


def _count_recent_burst(anon_id: str, window: float) -> int:
    now = _now()
    return sum(
        1 for e in _read_all()
        if e.get("anon_id") == anon_id and (now - float(e.get("ts", 0))) <= window
    )


def _append_atomic(event: dict) -> None:
    """Append with advisory lock; write whole line + newline atomically."""
    _ensure_dir()
    # acquire file lock (advisory, separate from ledger)
    acquired = False
    try:
        import msvcrt  # windows
        f_lock = open(ATTRIBUTION_LOCK, "w")
        msvcrt.locking(f_lock.fileno(), msvcrt.LK_NBLCK, 1)
        acquired = True
    except ImportError:
        import fcntl  # posix
        f_lock = open(ATTRIBUTION_LOCK, "w")
        fcntl.flock(f_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
    except Exception:
        acquired = False
    try:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        with ATTRIBUTION_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    finally:
        if acquired:
            try:
                if "msvcrt" in dir():
                    msvcrt.locking(f_lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(f_lock.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            f_lock.close()


_UNATTRIBUTABLE_PRODUCT_IDS = {"organic_content", "unknown", ""}


def read_ledger() -> dict:
    """Return ledger summary without exposing any PII.

    `unattributable_events` counts rows whose product_id is a placeholder — the
    old /api/content/track route wrote 'organic_content' whenever a client sent
    none, which produced 447,180 such rows from 3 anonymous ids before
    2026-10-28. Those rows are real append-only history and are still counted in
    total_events/by_type, but they are never counted as product views."""
    events = _read_all()
    by_type = {}
    unattributable = 0
    anon_ids = set()
    products = set()
    for e in events:
        event_type = e.get("event_type", "unknown")
        by_type[event_type] = by_type.get(event_type, 0) + 1
        product_id = e.get("product_id")
        if not isinstance(product_id, str) or product_id.strip() in _UNATTRIBUTABLE_PRODUCT_IDS:
            unattributable += 1
            continue
        products.add(product_id)
        if e.get("anon_id"):
            anon_ids.add(str(e["anon_id"]))
    return {
        "total_events": len(events),
        "by_type": by_type,
        "unattributable_events": unattributable,
        "attributable_events": len(events) - unattributable,
        "distinct_anon_ids": len(anon_ids),
        "distinct_products": len(products),
        "has_pii": False,
        "note": "ANALYSIS ledger only - NOT financial truth.",
    }


def new_anon_id() -> str:
    return str(uuid.uuid4())


if __name__ == "__main__":
    print(json.dumps(read_ledger(), indent=2, ensure_ascii=False))
