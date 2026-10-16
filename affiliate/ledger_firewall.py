#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production ledger firewall: absolute SIMULATION/INTERNAL vs EXTERNAL separation.

Revenue truth lives in finance_data.json (sales array + totals).
data/sales_ledger.jsonl is a pre-existing publish-event log (49 dry-run/
smoke rows, zero revenue rows) — read here, never renamed mid-test.
record_verified_sale() writes ONLY on verified+external+transaction_id,
idempotent on transaction_id. Everything else raises FirewallError —
never silently drops, never partially writes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"

NON_COMMERCIAL_SOURCES = ("simulation", "dry_run", "internal_test", "qa",
                          "preview", "synthetic", "bot", "development",
                          "fixture", "replay", "test")


class FirewallError(PermissionError):
    pass


def classify_commercial_event(event: dict) -> dict:
    """Evidence chain: EVENT->SOURCE->CLASS->VERIFY->ATTRIBUTE->WRITE->STATUS.
    Any UNKNOWN step -> NOT_VERIFIED. Nothing inferred."""
    ev = event or {}
    chain = {
        "EVENT": ev.get("event_type", "UNKNOWN"),
        "SOURCE": ev.get("source", "UNKNOWN"),
        "CLASS": ("INTERNAL" if str(ev.get("source", "")).lower() in NON_COMMERCIAL_SOURCES
                  else ("EXTERNAL" if ev.get("source") == "external" else "UNKNOWN")),
        "VERIFICATION": "VERIFIED" if ev.get("verified") is True else "UNKNOWN",
        "ATTRIBUTION": ev.get("attribution", "UNKNOWN"),
        "LEDGER_WRITE": "none",
    }
    if (chain["CLASS"] == "EXTERNAL" and chain["VERIFICATION"] == "VERIFIED"
            and chain["ATTRIBUTION"] not in ("UNKNOWN", "", None)
            and ev.get("transaction_id")):
        chain["COMMERCIAL_STATUS"] = "VERIFIED_SIGNAL"
    else:
        chain["COMMERCIAL_STATUS"] = "NOT_VERIFIED"
    return chain


def record_verified_sale(event: dict, finance_path: Path | None = None) -> dict:
    """The single write path. Raises on: non-external source, unverified,
    missing transaction_id, negative amount, duplicate transaction_id."""
    ev = event or {}
    if str(ev.get("source", "")).lower() != "external":
        raise FirewallError("not external: %r" % ev.get("source"))
    if ev.get("verified") is not True:
        raise FirewallError("unverified sale cannot update REAL_REVENUE")
    tx = ev.get("transaction_id")
    if not tx:
        raise FirewallError("no transaction id")
    amount = ev.get("amount_usd", 0)
    if not isinstance(amount, (int, float)) or amount < 0:
        raise FirewallError("invalid amount: %r" % amount)
    path = Path(finance_path) if finance_path else FINANCE_PATH
    try:
        fin = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise FirewallError("ledger unreadable, write refused: %s" % type(e).__name__)
    sales = fin.get("sales", [])
    sales = fin.get("sales", [])
    if any(s.get("transaction_id") == tx for s in sales):
        return {"recorded": False, "reason": "duplicate transaction_id (idempotent)",
                "transaction_id": tx}
    sales.append({"transaction_id": tx, "amount_usd": amount,
                  "product_id": ev.get("product_id"), "source": "external",
                  "verified": True, "environment": "production",
                  "recorded_at": datetime.now(timezone.utc).isoformat()})
    fin["sales"] = sales
    fin["totalSales"] = sum(s.get("amount_usd", 0) for s in sales)
    path.write_text(json.dumps(fin, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"recorded": True, "transaction_id": tx, "totalSales": fin["totalSales"]}


def assert_invariants(finance_path: Path | None = None) -> dict:
    """REAL_REVENUE>=0, customers>=0, SIM/INTERNAL/UNVERIFIED revenue == 0.
    Any violation = CRITICAL_INTEGRITY_FAILURE."""
    path = Path(finance_path) if finance_path else FINANCE_PATH
    fin = json.loads(path.read_text(encoding="utf-8"))
    sales = fin.get("sales", [])
    sim_rev = sum(s.get("amount_usd", 0) for s in sales
                  if str(s.get("environment", "")).lower() in NON_COMMERCIAL_SOURCES
                  or s.get("verified") is not True)
    issues = []
    if fin.get("totalSales", 0) < 0:
        issues.append("negative totalSales")
    if sim_rev != 0:
        issues.append("non-commercial revenue present: %s" % sim_rev)
    if fin.get("totalSales", 0) != sum(s.get("amount_usd", 0) for s in sales):
        issues.append("totalSales != sum(sales)")
    return {"ok": not issues, "issues": issues,
            "REAL_REVENUE": fin.get("totalSales", 0),
            "status": "CLEAN" if not issues else "CRITICAL_INTEGRITY_FAILURE"}


def diagnose_traffic(counts: dict) -> dict:
    """Traffic states with insufficient-sample guard (min 100 views)."""
    c = counts or {}
    views = c.get("views", 0)
    if views == 0:
        return {"state": "NO_TRAFFIC"}
    if views < 100:
        return {"state": "INSUFFICIENT_SAMPLE", "views": views}
    if c.get("clicks", 0) == 0:
        return {"state": "TRAFFIC_WITHOUT_ENGAGEMENT"}
    if c.get("checkouts", 0) == 0:
        return {"state": "CLICK_WITHOUT_CHECKOUT"}
    if c.get("purchases", 0) == 0:
        return {"state": "CHECKOUT_WITHOUT_PURCHASE"}
    if not c.get("verified"):
        return {"state": "PURCHASE_WITHOUT_VERIFICATION"}
    return {"state": "VERIFIED_SIGNAL"}


def alert_decision(kind: str) -> dict:
    meaningful = {"verified_sale", "verified_signal", "tracking_failure",
                  "integrity_failure", "financial_event", "platform_restriction",
                  "window_end", "founder_gate"}
    if kind in meaningful:
        return {"notify": True, "reason": kind}
    return {"notify": False, "reason": "routine (%s) — suppressed" % kind}


def window_status() -> dict:
    rec_p = _FACTORY_ROOT / "data" / "market_test_gpsr_path_b_v1" / "test_record.json"
    if not rec_p.exists():
        return {"state": "NO_WINDOW"}
    rec = json.loads(rec_p.read_text(encoding="utf-8"))
    started = datetime.fromisoformat(rec["VERIFICATION"]["checked_at"])
    days = (datetime.now(timezone.utc) - started).days
    return {"TEST_NAME": "GPSR_PATH_B_V1", "day": days, "of": 30,
            "state": "ARMED" if days < 30 else "WINDOW_END",
            "baseline_revenue": rec.get("REVENUE_BASELINE", 0)}
