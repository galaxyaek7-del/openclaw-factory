#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — affiliate daily health (read-only rollup for tick + panel).

No writes except the returned dict. Network probe is OPT-IN (--probe) and
only HEADs already-registered merchant bare domains with a short timeout.
Default path is pure disk reads.
"""
import json
import sys
from datetime import datetime, timezone
from . import registry, priority, performance


def _revalidation_aging():
    opps = registry.load_opportunities()
    now = datetime.now(timezone.utc)
    stale, fresh, never = [], [], []
    for o in opps:
        lv = o.get("last_verified")
        if not lv or lv == "UNKNOWN":
            never.append(o.get("opportunity_id"))
            continue
        try:
            dt = datetime.fromisoformat(str(lv).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            (stale if (now - dt).days > 45 else fresh).append(o.get("opportunity_id"))
        except ValueError:
            never.append(o.get("opportunity_id"))
    return {"fresh_le_45d": fresh, "stale_gt_45d": stale, "never_verified": never}


def _link_health(probe=False):
    links = registry.load_links()
    out = []
    for l in links:
        domain = l.get("merchant_domain") or l.get("domain")
        row = {"program": l.get("program"), "domain": domain,
               "last_verified": l.get("last_verified"), "http_status": l.get("http_status"),
               "probed": False}
        if probe:
            try:
                from .links import check_link_status
                res = check_link_status("https://" + str(domain or ""), timeout=10)
                row["http_status"] = res.get("http_status", res.get("status"))
                row["probed"] = True
            except Exception as e:
                row["probe_error"] = str(e)[:200]
        out.append(row)
    return out


def daily_health(probe=False):
    reg = registry.registry_summary()
    ranked = priority.rank_all()
    perf = performance.classify_all()
    top3 = [(s["opportunity_id"], s["score"]) for s in ranked["ranked"][:3]]
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "registry": {"total": reg["total_programs"], "by_status": reg["by_status"]},
            "top_priority": top3,
            "performance_totals": perf["totals"],
            "verdicts": {v: sum(1 for p in perf["programs"] if p["verdict"] == v)
                         for v in ("SCALE_CANDIDATE", "MEASURE_MORE", "DIAGNOSE", "HOLD", "DROP")},
            "revalidation_aging": _revalidation_aging(),
            "link_health": _link_health(probe=probe),
            "affiliate_revenue_verified_usd": 0,
            "affiliate_payouts_verified_usd": 0}


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(daily_health(probe="--probe" in sys.argv), ensure_ascii=False))
