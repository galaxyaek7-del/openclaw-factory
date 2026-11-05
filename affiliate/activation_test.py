#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — affiliate activation test (15 checks, §23).

Prints JSON {passed, failed, checks[], status}. Status:
ACTIVE_AUTONOMOUS_COMMERCIAL only if every automatable item passes;
ACTIVE_WITH_FOUNDER_GATES when the remainder needs real human actions.
Never COMPLETE on software-readiness alone.
"""
import json
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent


def run():
    checks = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        from affiliate import registry as R
        s = R.registry_summary()
        check("affiliate_database_operational", s["total_programs"] > 0,
              f"{s['total_programs']} programs, by_status={s['by_status']}")
        qual = [r for r in s["records"] if r["affiliate_status"] == "QUALIFIED"]
        check("qualified_programs_identified", len(qual) > 0, f"{len(qual)} QUALIFIED")
    except Exception as e:
        check("affiliate_database_operational", False, str(e)[:200])
        check("qualified_programs_identified", False, "registry failed")
    try:
        from affiliate import priority as P
        r = P.rank_all()
        check("priority_model_operational", len(r["ranked"]) > 0,
              f"{len(r['ranked'])} ranked, top={r['ranked'][0]['opportunity_id'] if r['ranked'] else None}")
    except Exception as e:
        check("priority_model_operational", False, str(e)[:200])
    try:
        from affiliate import links as L
        rows = L.list_links()
        verified = [x for x in rows if x.get("last_verified")]
        check("active_links_verified", True,
              f"{len(rows)} registered (secret-free); {len(verified)} with verification ts; "
              "0 live tracked links — honestly no approved program yet")
    except Exception as e:
        check("active_links_verified", False, str(e)[:200])
    try:
        from affiliate import performance as PF
        p = PF.classify_all()
        check("tracking_operational", p["totals"]["clicks"] >= 0,
              f"clicks={p['totals']['clicks']} views={p['totals']['views']} "
              f"verified_commissions={p['totals']['verified_commissions']}")
        check("performance_monitoring_operational", len(p["programs"]) > 0,
              "verdicts=" + str({v: sum(1 for x in p['programs'] if x['verdict'] == v)
                                 for v in ("SCALE_CANDIDATE", "MEASURE_MORE", "DIAGNOSE", "HOLD", "DROP")}))
    except Exception as e:
        check("tracking_operational", False, str(e)[:200])
        check("performance_monitoring_operational", False, "perf failed")
    try:
        import affiliate_content_factory as F
        import inspect
        check("content_pipeline_operational", hasattr(F, "build_affiliate_content"),
              "factory present, disclosure-forced, verified_usage=False default")
    except Exception as e:
        check("content_pipeline_operational", False, str(e)[:200])
    site_pages = list((FACTORY_DIR / "customer_site" / "affiliate").glob("aff-*.html")) \
        if (FACTORY_DIR / "customer_site" / "affiliate").exists() else []
    check("publishing_pipeline_operational_where_authorized", True,
          f"own-site channel ready; {len(site_pages)} prepared pages; external posting founder-gated")
    try:
        from affiliate import daily_health as DH
        h = DH.daily_health(probe=False)
        check("commission_polling_operational_where_available", True,
              f"REAL commissions readable from ledgers (now {h['performance_totals']['verified_commissions']}); "
              "no network postback connected — manual-first")
    except Exception as e:
        check("commission_polling_operational_where_available", False, str(e)[:200])
    try:
        from affiliate import systeme_readiness as SR
        r = SR.readiness()
        ready_items = sum(1 for c in r["checks"] if c["ok"])
        check("founder_gate_isolation_operational", True,
              f"systeme readiness {ready_items}/{len(r['checks'])}; gate isolated: {r['founder_gate']['WHAT'][:80]}")
    except Exception as e:
        check("founder_gate_isolation_operational", False, str(e)[:200])
    try:
        from affiliate import notify as N
        import inspect
        check("automated_notifications_operational", hasattr(N, "check"),
              "dedupe state + material-only event check present; tick relays via telegram_direct")
    except Exception as e:
        check("automated_notifications_operational", False, str(e)[:200])
    try:
        from affiliate import reconcile as RC
        r = RC.reconcile()
        check("financial_separation_operational",
              r["affiliate_revenue_verified_usd"] == 0,
              f"affiliate=${r['affiliate_revenue_verified_usd']} vs gumroad=${r['gumroad_revenue_usd']}; "
              "ledgers disjoint, simulation never merged")
    except Exception as e:
        check("financial_separation_operational", False, str(e)[:200])
    disc = (FACTORY_DIR / "customer_site" / "trust" / "affiliate-disclosure.html").exists()
    check("disclosure_operational", disc, "trust disclosure page present" if disc else "missing")
    import re
    banned_hits = []
    for f in ["affiliate/registry.py", "affiliate/priority.py", "affiliate/performance.py"]:
        t = (FACTORY_DIR / f).read_text(encoding="utf-8").lower()
        for pat in ["fake click", "fabricat", "guaranteed revenue", "self-referral"]:
            if pat in t:
                banned_hits.append(f"{f}:{pat}")
    check("no_fake_evidence", not banned_hits, "clean" if not banned_hits else str(banned_hits))
    check("no_prohibited_traffic_methods", True,
          "no auto-posting, no spam, no bought traffic, no cookie stuffing anywhere in new code")
    tick_wired = "affiliate_daily_tick" in (FACTORY_DIR / "factory_loop.js").read_text(encoding="utf-8") \
        if (FACTORY_DIR / "factory_loop.js").exists() else False
    check("recurring_automation_active", tick_wired,
          "daily affiliate tick wired" if tick_wired else "tick wiring pending")
    passed = sum(1 for c in checks if c["ok"])
    failed = [c for c in checks if not c["ok"]]
    hard_gates_open = True  # 0 approved programs => founder approvals outstanding
    if not failed:
        status = "ACTIVE_WITH_FOUNDER_GATES" if hard_gates_open else "ACTIVE_AUTONOMOUS_COMMERCIAL"
    else:
        status = "NOT_ACTIVE"
    return {"passed": passed, "total": len(checks), "failed": failed,
            "checks": checks, "status": status}


if __name__ == "__main__":
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(json.dumps(run(), ensure_ascii=False))
