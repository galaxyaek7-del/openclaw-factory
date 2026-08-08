"""Galaxy Forge — Commission Ledger (Phase 33, ADR-226, 2026-08-08).

Sections 10-11 of the Commission Commerce Engine directive: a dedicated,
append-only commission ledger with a hard anti-fabrication guard. Kept
as its own module, separate from commission_engine.py, because it is
this factory's closest analog to a real financial record for commission
income -- the same reasoning channels/ledger.py (real sales events) and
finance_data.json (real revenue) are kept as focused, single-purpose
real ledgers rather than folded into a general-purpose module.

The one hard rule this entire module exists to enforce: a REAL
commission record cannot be created without real evidence. This is not
a convention -- record_commission() raises ValueError if environment=
"REAL" and evidence is falsy. Verified by a dedicated regression test
that this raise actually fires and that no record is written to disk
when it does.
"""

import json
import platform
import threading
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_LEDGER_PATH = _FACTORY_ROOT / "data" / "commission_ledger.jsonl"

COMMISSION_STATUSES = (
    "EXPECTED", "PENDING", "CONFIRMED", "PAID", "REVERSED", "REFUNDED", "DISPUTED", "UNKNOWN",
)
LEDGER_ENVIRONMENTS = ("REAL", "TEST", "SIMULATION")


class AntiFabricationError(ValueError):
    """Raised when a caller attempts to create a REAL commission record
    without real evidence. Never caught and silently downgraded --
    the caller must supply real evidence or use TEST/SIMULATION."""


class DuplicateCommissionError(ValueError):
    """Phase 38b ('Chief Commercial Engineer' directive, ADR-234,
    2026-08-08), Section 13's named 'duplicate commission' adversarial
    case. Raised when a REAL commission with a given
    external_transaction_id is recorded a second time -- the same real
    transaction must never double-count as two separate real
    commission events. Scoped to REAL only: TEST/SIMULATION records
    carry no real financial claim, so a repeated test transaction_id
    is harmless and never blocked."""


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


_MIN_MEANINGFUL_LENGTH = 4


# ---------------------------------------------------------------------------
# Phase 39 (ADR-236), Section 9 -- real cross-process advisory file lock.
#
# Found while stress-testing the actual expected workload (10 real,
# genuinely concurrent threads racing to record the same real
# external_transaction_id): the duplicate-check above is a
# check-then-write race -- load_ledger() reads, then a separate append
# writes, with no lock between them. Under true concurrency (a real,
# expected scenario: Paddle and most webhook providers document
# at-least-once delivery, so two near-simultaneous deliveries of the
# same event are a real, not hypothetical, occurrence) 3 of 10
# concurrent calls for the identical transaction_id were each recorded
# as separate REAL commission records before this fix -- a genuine,
# serious gap in exactly the guarantee Section 7 of this same
# directive names ("prove the same ... commission event cannot be
# counted twice"). The sequential 10x retry-storm test this factory
# already had (tests/test_resilience_idempotency.py) only proved
# safety for sequential retries, never genuine concurrency -- a real,
# previously-uncaught blind spot in that test's own coverage.
#
# Fixed with a minimal, real, disclosed advisory lock file
# (data/commission_ledger.jsonl.lock) held only around the duplicate-
# check + write critical section, REAL environment only (TEST/
# SIMULATION records carry no real financial claim and are
# unaffected). Windows-native msvcrt.locking() on this platform; a
# real fcntl.flock() branch for POSIX, since this same module may run
# in either environment. No behavior change for any existing caller
# outside of true concurrent REAL writes -- the lock is acquired and
# released within the same function call, transparently.
# ---------------------------------------------------------------------------

class _LedgerLock:
    """A real, minimal, cross-process advisory lock -- blocks until
    acquired, released even on exception via context-manager __exit__.

    Real production topology (per CLAUDE.md) spawns a separate Python
    subprocess per Mission Control action, so genuinely concurrent
    commission writes are almost always separate OS processes -- the
    real case this lock exists for, handled by msvcrt.locking()
    (Windows) / fcntl.flock() (POSIX). A dedicated intra-process
    threading.Lock() is held first: Windows' msvcrt.locking(LK_LOCK)
    was found, while writing this round's own concurrency stress test
    (Section 9), to raise a real 'Resource deadlock avoided' OSError
    when multiple THREADS in the same process race for the same
    byte-range lock via separate handles -- a genuine Windows same-
    process locking quirk, not a hypothetical. The threading.Lock()
    serializes same-process callers before they ever reach msvcrt,
    while the file lock still protects the real cross-process case."""

    _thread_lock = threading.Lock()

    def __init__(self, ledger_path):
        self._lock_path = str(ledger_path) + ".lock"
        self._fh = None

    def __enter__(self):
        self._thread_lock.acquire()
        self._fh = open(self._lock_path, "a+")
        if platform.system() == "Windows":
            import msvcrt
            self._fh.seek(0)
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if platform.system() == "Windows":
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._thread_lock.release()
        return False


def _is_meaningful(value):
    """Real, minimal content check -- closes a real firewall gap found
    in Phase 35 (ADR-228): a non-empty-but-whitespace-only or trivially
    short string (e.g. "   ", "x") previously passed the bare `not
    value` check and could fabricate a REAL commission record with no
    actual evidence content. This is deliberately NOT a claim that any
    string of sufficient length is genuinely real evidence -- it only
    closes the specific, cheap bypass; real evidentiary weight is still
    the caller's responsibility."""
    if value is None:
        return False
    if not isinstance(value, str):
        return bool(value)
    return len(value.strip()) >= _MIN_MEANINGFUL_LENGTH


def record_commission(partner_id, opportunity_id, commission_status, gross_commission,
                       environment, customer_id=None, lead_id=None, deal_id=None,
                       external_transaction_id=None, fees=0.0, currency="USD", evidence=None,
                       source=None, ledger_path=None, now=None):
    """The one real write path into the commission ledger. Hard rule:
    environment="REAL" requires real, non-empty evidence (e.g. a real
    external_transaction_id plus a real evidence citation) -- raises
    AntiFabricationError otherwise, before anything is written to disk.
    TEST/SIMULATION records never require evidence, since they carry no
    real financial claim."""
    if environment not in LEDGER_ENVIRONMENTS:
        raise ValueError(f"environment must be one of {LEDGER_ENVIRONMENTS}, got {environment!r}")
    if commission_status not in COMMISSION_STATUSES:
        raise ValueError(f"commission_status must be one of {COMMISSION_STATUSES}, got {commission_status!r}")

    if environment == "REAL" and not _is_meaningful(evidence):
        raise AntiFabricationError(
            "Cannot record a REAL commission without real evidence. "
            "Provide evidence= (e.g. a real webhook event_id, a real transaction confirmation) -- "
            "a whitespace-only or trivially short string does not count -- "
            "or use environment='TEST'/'SIMULATION' instead."
        )
    if environment == "REAL" and commission_status in ("CONFIRMED", "PAID") and not _is_meaningful(external_transaction_id):
        raise AntiFabricationError(
            "A REAL commission cannot be CONFIRMED or PAID without a real, meaningful external_transaction_id "
            "(whitespace-only or trivially short values are rejected)."
        )

    net_commission = gross_commission - fees
    record = {
        "commission_id": f"COM-{partner_id}-{opportunity_id}-{_now_iso(now)}",
        "partner_id": partner_id, "opportunity_id": opportunity_id,
        "customer_id": customer_id, "lead_id": lead_id, "deal_id": deal_id,
        "external_transaction_id": external_transaction_id,
        "commission_status": commission_status,
        "gross_commission": gross_commission, "fees": fees, "net_commission": net_commission,
        "currency": currency,
        "created_at": _now_iso(now), "confirmed_at": None, "paid_at": None, "reversed_at": None,
        "evidence": evidence, "source": source, "environment": environment,
    }
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    if environment == "REAL" and _is_meaningful(external_transaction_id):
        # Section 9 fix: the duplicate-check + write must happen as one
        # atomic critical section under a real cross-process lock --
        # doing the check and the write as two separate, unlocked
        # operations (the pre-Phase-39 behavior) is a genuine
        # check-then-write race under true concurrency.
        with _LedgerLock(path):
            existing = [r for r in load_ledger(ledger_path) if r.get("environment") == "REAL" and r.get("external_transaction_id") == external_transaction_id]
            if existing:
                raise DuplicateCommissionError(
                    f"A REAL commission with external_transaction_id={external_transaction_id!r} already exists "
                    f"(commission_id={existing[0]['commission_id']}) -- the same real transaction must never be "
                    f"recorded twice. If this is a real, separate refund/reversal/correction, use the appropriate "
                    f"commission_status on the existing record's own follow-up event instead of a new record."
                )
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_ledger(ledger_path=None):
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def real_commission_summary(ledger_path=None):
    """The one real, authoritative summary -- filters strictly on
    environment='REAL'. TEST/SIMULATION records are counted separately
    and never blended into these totals, per the directive's own
    explicit rule (Section 9's REAL/TEST/SIMULATION separation, applied
    here to commissions specifically)."""
    records = load_ledger(ledger_path)
    real = [r for r in records if r.get("environment") == "REAL"]
    test = [r for r in records if r.get("environment") == "TEST"]
    simulation = [r for r in records if r.get("environment") == "SIMULATION"]

    confirmed_or_paid = [r for r in real if r.get("commission_status") in ("CONFIRMED", "PAID")]
    paid = [r for r in real if r.get("commission_status") == "PAID"]

    return {
        "generated_at": _now_iso(),
        "real_commission_records": len(real),
        "real_confirmed_or_paid_commission_usd": round(sum(r["net_commission"] for r in confirmed_or_paid), 2),
        "real_paid_commission_usd": round(sum(r["net_commission"] for r in paid), 2),
        "test_records": len(test),
        "simulation_records": len(simulation),
        "note": "Only CONFIRMED/PAID REAL records count as real commercial revenue -- EXPECTED/PENDING REAL records exist but are explicitly excluded from this total, matching the directive's own rule that only CONFIRMED/PAID commissions become real commercial revenue.",
    }


# ---------------------------------------------------------------------------
# Phase 38b ("Chief Commercial Engineer" directive, ADR-234, 2026-08-08),
# Section 11 -- the formal, named FIRST_REAL_DOLLAR gate.
# ---------------------------------------------------------------------------

def first_real_dollar_status(ledger_path=None):
    """Real, computed directly from real_commission_summary()'s own
    real CONFIRMED/PAID totals -- never a second, competing truth
    source. FIRST_REAL_DOLLAR can only ever become True after an
    independently-verifiable real commission/payout exists (a real
    external_transaction_id + real evidence, enforced upstream by
    record_commission()'s own AntiFabricationError guard). No
    exceptions, no partial credit, no averaging toward true."""
    summary = real_commission_summary(ledger_path=ledger_path)
    records = load_ledger(ledger_path)
    real_confirmed_or_paid = [r for r in records if r.get("environment") == "REAL" and r.get("commission_status") in ("CONFIRMED", "PAID")]
    real_paid = [r for r in real_confirmed_or_paid if r.get("commission_status") == "PAID"]

    first_real_dollar = summary["real_confirmed_or_paid_commission_usd"] > 0

    return {
        "generated_at": _now_iso(),
        "FIRST_REAL_DOLLAR": first_real_dollar,
        "REAL_REVENUE": summary["real_confirmed_or_paid_commission_usd"] if first_real_dollar else 0,
        "REAL_COMMISSION_REVENUE": summary["real_confirmed_or_paid_commission_usd"] if first_real_dollar else 0,
        "REAL_CUSTOMERS": len({r["customer_id"] for r in real_confirmed_or_paid if r.get("customer_id")}) if first_real_dollar else 0,
        "REAL_DEALS": len({r["deal_id"] for r in real_confirmed_or_paid if r.get("deal_id")}) if first_real_dollar else 0,
        "REAL_PAYOUTS": len(real_paid) if first_real_dollar else 0,
        "evidence": [{"commission_id": r["commission_id"], "external_transaction_id": r["external_transaction_id"], "evidence": r["evidence"]} for r in real_confirmed_or_paid] if first_real_dollar else [],
        "note": (
            "First real dollar confirmed -- see the evidence field for the real ledger record(s)."
            if first_real_dollar else
            "FIRST_REAL_DOLLAR is False. Every REAL_* field is 0, with no exceptions, until an independently "
            "verifiable real commission/payout exists in this ledger's own REAL/CONFIRMED-or-PAID records."
        ),
    }
