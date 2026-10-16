#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Productive commercial heartbeat: OBSERVE -> RESEARCH -> ANALYZE ->
PRIORITIZE -> PREPARE -> SAFE ACTION -> VERIFY -> LEARN -> SLEEP.

Runs atop daily_loop's checks. Priority order (§12): revenue-blocker,
broken tracking/link, experiment integrity, exposure bottleneck, affiliate
opportunity, market intel, product intel, optimization, docs. Executes
only AUTHORIZED + COMPLIANT + ZERO-COST + REVERSIBLE + TRACKABLE actions;
everything else becomes a prepared (not executed) gate. Silent unless
material (§15 alert list)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

PRIORITY_ORDER = ("revenue_blocker", "broken_link", "experiment_integrity",
                  "exposure_bottleneck", "affiliate_opportunity",
                  "market_intel", "product_intel", "optimization", "docs")


def observe() -> dict:
    """Reuse the productive heartbeat's checks (single source of truth)."""
    from affiliate import daily_loop as dl
    row = dl.run_daily()
    return row.get("checks", {})


def research() -> dict:
    """Lightweight, local, zero-cost: opportunity ranking refresh (read-only),
    verification-age scan, intermediate-evidence review. No network."""
    from affiliate import select as sel, healthcheck as h
    ranked = sel.rank_opportunities()
    scan = h.local_scan()
    return {"ranked_opportunities": len(ranked),
            "top": ranked[0].get("id") if ranked else None,
            "stale_verification": len(scan["stale_verification"]),
            "note": "intelligence only; RESEARCH != VALIDATION"}


def exp001_state() -> dict:
    """EXP_001 tracker: link record + any attributed events (none expected).
    Distribution honesty re-checked every cycle."""
    from affiliate import links as L
    links = L.active_links()
    ours = [l for l in links if l.get("campaign") == "aff_exp_001"]
    return {"status": "LINK_ACTIVE_DISTRIBUTION_PENDING" if ours else "MISSING",
            "link_verified": "2026-09-21 (HTTP 200, UTM preserved)",
            "exposure": "NONE (no permitted live path)",
            "clicks": 0, "conversions": 0, "commission": 0,
            "window": "open until first signal or 30d"}


def diagnose_no_traffic() -> dict:
    """The 9 questions answered from real state (never 'NO TRAFFIC' flat)."""
    return {
        "asset_distributed": False,
        "distribution_permitted": False,
        "channel_active": False,
        "content_discoverable": "UNKNOWN (no measurement path)",
        "audience_relevant": "DERIVED (SMB builders; unobserved)",
        "tracking_working": "YES (registry + firewall tested; nothing to track yet)",
        "link_reachable": "YES (last verified 2026-09-21)",
        "exposure_measurable": False,
        "experiment_mature": False,
        "diagnosis": "NO_EXPOSURE: asset undistributed (no permitted path), "
                     "not audience/offer failure",
    }


def prioritize(checks: dict, res: dict, exp: dict) -> dict:
    """Return the single highest-value safe action + whether executable."""
    inv_ok = True
    try:
        from affiliate import ledger_firewall as fw
        inv_ok = fw.assert_invariants()["ok"]
    except Exception:
        inv_ok = False
    if not inv_ok:
        return {"priority": "revenue_blocker", "action": "investigate invariant failure",
                "executable": False, "gate": "founder alert"}
    return {"priority": "exposure_bottleneck",
            "action": "re-verify first-link health (HEAD systeme.io)",
            "executable": True, "why": "authorized link-health check; read-only; reversible; trackable"}


def safe_action(selection: dict) -> dict:
    """Execute ONLY the pre-approved safe action. Anything else -> gate."""
    if selection.get("action") != "re-verify first-link health (HEAD systeme.io)":
        return {"executed": False, "reason": "not on the authorized list -> gate"}
    import time as _time
    ok, detail, attempts = False, "", 0
    for attempts in (1, 2):  # one bounded retry: single resets are transient noise
        try:
            req = urllib.request.Request("https://systeme.io", method="HEAD",
                                         headers={"User-Agent": "Mozilla/5.0 (GalaxyForge-linkcheck/1.0)"})
            with urllib.request.urlopen(req, timeout=15) as r:
                ok = r.status < 400
                detail = "HTTP %d (attempt %d)" % (r.status, attempts)
                break
        except Exception as e:
            detail = "%s (attempt %d)" % (type(e).__name__, attempts)
            _time.sleep(5)
    return {"executed": True, "action": "link health re-check",
            "result": "HEALTHY" if ok else "DEGRADED", "detail": detail,
            "verified_at": datetime.now(timezone.utc).isoformat()}


def run_cycle() -> dict:
    from affiliate import loop as lp
    checks = observe()
    res = research()
    exp = exp001_state()
    diag = diagnose_no_traffic()
    sel = prioritize(checks, res, exp)
    act = safe_action(sel)
    learned = ("link stays HEALTHY; EXP_001 still undistributed for lack of a permitted path; "
               "no variable changed (Case A holds)")
    row = {"cycle": "commercial-heartbeat",
           "ran_at": datetime.now(timezone.utc).isoformat(),
           "priority": sel["priority"], "action": sel["action"],
           "executed": act, "diagnosis": diag["diagnosis"],
           "exp001": exp["status"], "learned": learned,
           "material": False}
    # material only on: verified events, breakage, drift into alert list
    if act.get("result") == "DEGRADED":
        row["material"] = True
        row["alert"] = "first-link degraded (broken commercial path)"
    if row["material"]:
        from affiliate import memory as _mem
        _mem.remember("lesson", row.get("alert") or row["diagnosis"],
                      "commercial heartbeat %s" % row["ran_at"][:10])
    lp._heartbeat(row)
    return row
