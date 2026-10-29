#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Narrow inbound-only Customer Evidence Gate (POST ARM 8 governance).

Collects genuine inbound product-interest signals with deterministic
provenance + timestamp. Evidence-only: it does NOT feed the production /
payment / distribution pipeline, and never triggers outreach, advertising,
or automated messaging.

Classification discipline (MARKET / PRODUCT / CUSTOMER / TRANSACTION) is
preserved per the Founder Directive:
  - A genuine human inbound interest signal is classified CUSTOMER.
  - MARKET / PRODUCT / TRANSACTION signals are NOT produced by this gate.

Reputation and unit-economics stay UNKNOWN until qualifying real inputs exist.
OpenCode may improve validation / observability / defensive tests, but may NOT
reinterpret evidence to satisfy a gate, declare readiness, or open another ARM.

Concurrency safety: appends are guarded by an advisory file lock so that
concurrent writers — including the separate Python processes the server spawns
per request via execFile — cannot lose or corrupt JSONL records. Validation,
dedup read, and append happen inside one locked critical section, guaranteeing
both lossless writes and correct deduplication across processes.
"""

import hashlib
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from datetime import datetime, timezone

try:
    import msvcrt
    _HAVE_MSVC = True
except ImportError:  # POSIX
    msvcrt = None
    _HAVE_MSVC = False
    try:
        import fcntl
    except ImportError:
        fcntl = None

FACTORY_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = FACTORY_ROOT / "data" / "customer_interest.jsonl"
REJECTED_LEDGER_PATH = FACTORY_ROOT / "data" / "customer_interest_rejected.jsonl"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_FIELD = 2000
MIN_MESSAGE = 10
MAX_MESSAGE = 2000
# Safety stop: automatic halt once this many genuine signals are recorded,
# forcing a founder review before any further ingestion.
LEDGER_CAP = 5000
# Non-deliverable / synthetic email domains rejected at ingestion.
REJECT_EMAIL_DOMAINS = ("@example.com", "@test.com", "@localhost", "@invalid")

# In-process lock registry (keyed by lock-file path) so threads in the same
# process serialize before attempting the inter-process advisory lock.
_global_tlock = threading.Lock()
_thread_locks = {}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _dedup_hash(email, message):
    norm = (email or "").strip().lower() + "|" + (message or "").strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _thread_lock_for(key):
    with _global_tlock:
        return _thread_locks.setdefault(key, threading.Lock())


def _acquire_lock(lock_path):
    """Acquire a process-wide advisory exclusive lock on lock_path.

    Combines an in-process threading.Lock (per path) with an OS-level advisory
    lock (msvcrt on Windows, fcntl.flock on POSIX) so concurrent separate
    processes cannot enter the critical section simultaneously. Blocks with a
    bounded timeout (30s) then raises."""
    key = str(lock_path)
    tlock = _thread_lock_for(key)
    tlock.acquire()
    lf = open(lock_path, "a+")
    lf.seek(0)
    deadline = time.time() + 30
    while True:
        try:
            if _HAVE_MSVC:
                msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)
            elif fcntl is not None:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                break  # no OS lock available; threading-only best effort
            break
        except (OSError, BlockingIOError):
            if time.time() > deadline:
                try:
                    lf.close()
                finally:
                    tlock.release()
                raise RuntimeError("customer_evidence lock timeout")
            time.sleep(0.005)
    return lf, tlock


def _release_lock(lf, tlock):
    try:
        lf.seek(0)
        if _HAVE_MSVC:
            msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
        elif fcntl is not None:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    finally:
        lf.close()
        tlock.release()


def validate_and_classify(payload):
    """Return (ok, classification, reason, enriched)."""
    if not isinstance(payload, dict):
        return False, None, "payload must be an object", None

    # Honeypot: bots auto-fill the hidden field; real users never see it.
    if payload.get("website"):
        return False, None, "honeypot", None

    email = str(payload.get("email") or "").strip()
    message = str(payload.get("interest") or payload.get("message") or "").strip()
    name = str(payload.get("name") or "").strip()
    product_interest = str(payload.get("product_interest") or payload.get("product_id") or "").strip()

    if not email or not EMAIL_RE.match(email):
        return False, None, "valid email required", None
    if len(message) < MIN_MESSAGE:
        return False, None, "interest message too short", None
    if len(message) > MAX_MESSAGE or len(email) > MAX_FIELD or len(name) > MAX_FIELD or len(product_interest) > MAX_FIELD:
        return False, None, "field exceeds maximum length", None
    if email.lower().endswith(REJECT_EMAIL_DOMAINS):
        return False, None, "non-deliverable email domain", None

    classification = "CUSTOMER"
    enriched = {
        "email": email,
        "name": name or None,
        "message": message,
        "product_interest": product_interest or None,
        "classification": classification,
        "dedup_hash": _dedup_hash(email, message),
    }
    return True, classification, "ok", enriched


def _read_ledger(ledger_path):
    ledger = Path(ledger_path) if ledger_path else LEDGER_PATH
    if not ledger.exists():
        return [], 0
    records = []
    count = 0
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        count += 1
        try:
            records.append(json.loads(line))
        except Exception:
            continue
    return records, count


def _persist_rejection(reason, enriched, rejected_ledger, rejected_lock):
    """Write a rejection record to its own ledger (never counted as genuine).
    Safe under concurrency via its own advisory lock."""
    email = (enriched or {}).get("email", "")
    msg = (enriched or {}).get("message") or (enriched or {}).get("interest") or ""
    dh = _dedup_hash(str(email), str(msg))
    lf, tlock = _acquire_lock(rejected_lock)
    try:
        rejected_ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(rejected_ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "received_at": _now_iso(),
                "reason": reason,
                "classification": None,
                "dedup_hash": dh,
            }, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    finally:
        _release_lock(lf, tlock)


def record_interest_signal(payload, ledger_path=None, rejected_ledger_path=None):
    """Validate, dedup, and persist a genuine inbound interest signal.

    The read→dedup→append sequence runs inside one locked critical section so
    concurrent processes/threads cannot lose writes or admit duplicates."""
    ledger = Path(ledger_path) if ledger_path else LEDGER_PATH
    ledger_lock = ledger.parent / (ledger.name + ".lock")
    rejected = Path(rejected_ledger_path) if rejected_ledger_path else REJECTED_LEDGER_PATH
    rejected_lock = rejected.parent / (rejected.name + ".lock")

    ok, classification, reason, enriched = validate_and_classify(payload)
    if not ok:
        _persist_rejection(reason, enriched, rejected, rejected_lock)
        return {"status": "rejected", "classification": None, "reason": reason}

    lf, tlock = _acquire_lock(ledger_lock)
    try:
        records, count = _read_ledger(ledger)
        if count >= LEDGER_CAP:
            _persist_rejection("ledger cap reached", enriched, rejected, rejected_lock)
            return {"status": "stopped", "classification": None, "reason": "ledger cap reached — founder review required"}

        dedup = {r.get("dedup_hash") for r in records if r.get("dedup_hash")}
        if enriched["dedup_hash"] in dedup:
            _persist_rejection("duplicate", enriched, rejected, rejected_lock)
            return {"status": "duplicate", "classification": None, "reason": "duplicate signal"}

        signal_id = "int_" + hashlib.sha256((enriched["dedup_hash"] + _now_iso()).encode()).hexdigest()[:16]
        record = {
            "signal_id": signal_id,
            "received_at": _now_iso(),
            "channel": "customer_site",
            "source": "web_form",
            "classification": classification,
            "provenance_quality": "direct_inbound",
            "email": enriched["email"],
            "name": enriched["name"],
            "message": enriched["message"],
            "product_interest": enriched["product_interest"],
            "dedup_hash": enriched["dedup_hash"],
        }
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return {"status": "accepted", "signal_id": signal_id, "classification": classification, "reason": "ok",
                "product_interest": enriched["product_interest"]}
    finally:
        _release_lock(lf, tlock)


def read_signals(ledger_path=None):
    records, _ = _read_ledger(ledger_path)
    return records


def read_rejections(rejected_ledger_path=None):
    records, _ = _read_ledger(rejected_ledger_path or REJECTED_LEDGER_PATH)
    return records


def generate_evidence_report(ledger_path=None, rejected_ledger_path=None):
    """Return the A-K evidence report per the Founder Directive (controlled
    live evidence window). Reputation and unit-economics are deliberately
    UNKNOWN; the factory does not decide commercial sufficiency."""
    signals = read_signals(ledger_path)
    rejections = read_rejections(rejected_ledger_path)
    counts = {"MARKET": 0, "PRODUCT": 0, "CUSTOMER": 0, "TRANSACTION": 0}
    for s in signals:
        c = s.get("classification")
        if c in counts:
            counts[c] += 1
    provenance_ok = sum(1 for s in signals if s.get("provenance_quality") == "direct_inbound")

    return {
        "A_genuine_inbound_signals": len(signals),
        "B_valid_product_evidence": counts["PRODUCT"],
        "C_valid_customer_evidence": counts["CUSTOMER"],
        "D_valid_transaction_evidence": counts["TRANSACTION"],
        "E_rejected_synthetic_duplicate": len(rejections),
        "F_provenance_quality": (f"{provenance_ok}/{len(signals)} direct_inbound" if signals else "no signals"),
        "G_reputation_status": "UNKNOWN",
        "H_unit_economics_status": "UNKNOWN",
        "I_current_product_status": ("No REAL PRODUCT accepted with ADR-121 Proof-of-Payment; Offers DEFERRED; "
                                     "published_books=[]; revenue=$0 — evidence-only collection window"),
        "J_gate_assessment": ("Controlled live evidence window ACTIVE. NOT sufficient for commercial progression — "
                              f"{len(signals)} genuine CUSTOMER signals recorded; founder must decide sufficiency."),
        "K_exact_founder_decision_required": ("Founder must decide sufficiency and the next gate before any "
                                              "HOLD→PROCEED, outbound, payment, publishing, or ARM 9. "
                                              "PRODUCT/TRANSACTION evidence requires separate authorization."),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "action required"}))
        sys.exit(1)
    action = sys.argv[1]
    if action == "record":
        raw = sys.stdin.read()
        try:
            payload = json.loads(raw)
        except Exception:
            print(json.dumps({"success": False, "error": "invalid json"}))
            sys.exit(1)
        result = record_interest_signal(payload)
        print(json.dumps({"success": True, **result}))
    elif action == "report":
        print(json.dumps({"success": True, "report": generate_evidence_report()}))
    elif action == "bench-append":
        # Usage: bench-append <ledger> <rejected> <n>
        ledger = sys.argv[2]
        rejected = sys.argv[3]
        n = int(sys.argv[4])
        pid = os.getpid()
        for i in range(n):
            record_interest_signal(
                {"email": f"bench{pid}.{i}@example.org", "message": f"bench append message {pid} {i}"},
                ledger_path=ledger, rejected_ledger_path=rejected)
        print(json.dumps({"success": True, "done": n}))
    else:
        print(json.dumps({"success": False, "error": "unknown action"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
