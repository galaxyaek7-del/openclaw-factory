#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — affiliate cross-ledger reconcile (read-only).

Gumroad/Paddle sales vs affiliate REAL commissions vs SIMULATION.
Simulation is reported on its own line, never merged into revenue.
"""
import json
from pathlib import Path

from channels.ledger import _extract_sale_amount

FACTORY_DIR = Path(__file__).resolve().parent.parent


def _read_jsonl(path):
    p = FACTORY_DIR / path
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _platform_revenue(sales, platform):
    """Sum real sale amounts for one platform.

    THIS WAS STRUCTURALLY ALWAYS $0. The old code read a top-level
    `amount_usd_cents` key that channels/ledger.py::record_sale() has never
    written -- it writes {"event_type","platform","raw",<attribution fields>},
    with the amount living inside `raw`. Every real Gumroad sale therefore
    contributed 0, and `gumroad_revenue_usd` would have read $0.00 with a real
    customer money in it. It also divided by 100, compounding the error: the
    canonical extractor returns whole DOLLARS, not cents.

    Both are fixed here by delegating to channels.ledger._extract_sale_amount,
    the single existing authority for per-platform sale amounts.

    A sale whose amount cannot be recognized is counted as UNKNOWN, never as
    $0 -- an unparseable real sale must not quietly become a zero sale.
    """
    total = 0.0
    unknown = 0
    matched = 0
    for e in sales:
        if e.get("platform") != platform:
            continue
        matched += 1
        amount = _extract_sale_amount(e.get("raw") or {}, platform)
        if amount is None:
            unknown += 1
            continue
        total += float(amount)
    return round(total, 2), matched, unknown


def reconcile():
    sales = [e for e in _read_jsonl("data/sales_ledger.jsonl")
             if e.get("event_type") == "sale"]
    gumroad_usd, gumroad_n, gumroad_unknown = _platform_revenue(sales, "gumroad")
    paddle_usd, paddle_n, paddle_unknown = _platform_revenue(sales, "paddle")
    real_comms = [e for e in _read_jsonl("data/commission_ledger.jsonl")
                  if e.get("environment") == "REAL"
                  and e.get("status") in ("CONFIRMED", "PAID")]
    aff_comms = [e for e in _read_jsonl("data/affiliate_commission_ledger.jsonl")
                 if e.get("verified") is True and e.get("status") == "CONFIRMED"]
    sim = _read_jsonl("data/affiliate_simulation_events.jsonl")
    aff_usd = sum(float(e.get("amount_usd", e.get("amount", 0)) or 0)
                  for e in real_comms + aff_comms)

    unknown_amounts = gumroad_unknown + paddle_unknown
    status = "PASS" if unknown_amounts == 0 else "PARTIAL_AMOUNT_UNRECOGNIZED"
    return {"gumroad_sales_events": gumroad_n,
            "gumroad_revenue_usd": gumroad_usd,
            "gumroad_sales_with_unrecognized_amount": gumroad_unknown,
            "paddle_sales_events": paddle_n,
            "paddle_revenue_usd": paddle_usd,
            "paddle_sales_with_unrecognized_amount": paddle_unknown,
            "sale_amount_status": status,
            "sale_amount_evidence": "OBSERVED" if unknown_amounts == 0
                                    else "PARTIAL -- some real sales have no recognizable amount",
            "affiliate_real_commissions": len(real_comms) + len(aff_comms),
            "affiliate_revenue_verified_usd": round(aff_usd, 2),
            "affiliate_payouts_verified_usd": None,
            "affiliate_payouts_status": "UNKNOWN",
            "affiliate_payouts_note": (
                "No payout feed exists in this factory. This is UNKNOWN, not "
                "$0 -- no payout has been retrieved from any provider."),
            "simulation_events": len(sim),
            "simulation_note": "SIMULATION ledger is not revenue and is never merged above",
            "financial_truth": ("AFFILIATE_REVENUE = $0 until authoritative "
                                "merchant evidence exists") if aff_usd == 0
                               else "AFFILIATE_REVENUE is computed from CONFIRMED/PAID real commission events"}


if __name__ == "__main__":
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(reconcile(), ensure_ascii=False))
