#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — affiliate performance loop classifier.

SCALE_CANDIDATE MEASURE_MORE DIAGNOSE HOLD DROP from REAL ledger data only.
No external evidence => MEASURE_MORE (honest wait), never auto-DROP, never
auto-SCALE. DROP only on real discontinuation/policy evidence. Read-only.
"""
import json
from collections import Counter
from pathlib import Path
from . import registry

FACTORY_DIR = Path(__file__).resolve().parent.parent
CLICKS = FACTORY_DIR / "data" / "affiliate_clicks.jsonl"
VIEWS = FACTORY_DIR / "data" / "affiliate_page_views.jsonl"
COMMISSIONS = FACTORY_DIR / "data" / "commission_ledger.jsonl"
AFF_COMMISSIONS = FACTORY_DIR / "data" / "affiliate_commission_ledger.jsonl"


def _read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _real_commissions_by_program():
    out = Counter()
    for e in _read_jsonl(COMMISSIONS):
        if e.get("environment") == "REAL" and e.get("status") in ("CONFIRMED", "PAID"):
            out[str(e.get("opportunity_id", "UNKNOWN"))] += 1
    for e in _read_jsonl(AFF_COMMISSIONS):
        if e.get("verified") is True and e.get("status") == "CONFIRMED":
            out[str(e.get("opportunity_id", "UNKNOWN"))] += 1
    return out


def classify_all():
    summary = registry.registry_summary()
    clicks = _read_jsonl(CLICKS)
    views = _read_jsonl(VIEWS)
    real_comms = _real_commissions_by_program()
    clicks_by = Counter(str(c.get("opportunity_id", c.get("program", "UNKNOWN"))) for c in clicks)
    views_by = Counter(str(v.get("page_id", v.get("opportunity_id", "UNKNOWN"))) for v in views)
    results = []
    for r in summary["records"]:
        oid = r["opportunity_id"]
        c = clicks_by.get(oid, 0) + sum(v for k, v in clicks_by.items()
                                        if k != oid and oid.split("-")[-1] in k)
        comms = real_comms.get(oid, 0)
        if r["affiliate_status"] in ("DISCONTINUED", "REJECTED"):
            verdict, reason = "DROP", "program discontinued/rejected on real evidence"
        elif r["affiliate_status"] == "HOLD":
            verdict, reason = "HOLD", "revalidation hold: no link, no traffic"
        elif comms > 0:
            verdict, reason = "SCALE_CANDIDATE", f"{comms} verified real commission(s)"
        elif c >= 50:
            verdict, reason = "DIAGNOSE", f"{c} clicks but zero verified conversions"
        else:
            verdict, reason = "MEASURE_MORE", \
                f"insufficient external evidence ({c} clicks, {comms} verified commissions)"
        results.append({"opportunity_id": oid, "program_name": r["program_name"],
                        "status": r["affiliate_status"], "clicks": c, "views": views_by.get(oid, 0),
                        "verified_commissions": comms, "verdict": verdict, "reason": reason})
    totals = {"clicks": len(clicks), "views": len(views),
              "verified_commissions": sum(real_comms.values())}
    return {"programs": results, "totals": totals,
            "rule": "scale only on verified real commissions; internal clicks never scale"}
