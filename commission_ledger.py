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


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


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

    if environment == "REAL" and not evidence:
        raise AntiFabricationError(
            "Cannot record a REAL commission without real evidence. "
            "Provide evidence= (e.g. a real webhook event_id, a real transaction confirmation) "
            "or use environment='TEST'/'SIMULATION' instead."
        )
    if environment == "REAL" and commission_status in ("CONFIRMED", "PAID") and not external_transaction_id:
        raise AntiFabricationError(
            "A REAL commission cannot be CONFIRMED or PAID without a real external_transaction_id."
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
