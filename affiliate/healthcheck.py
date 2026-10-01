#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate health check: local freshness scan (no network, loop-safe) +
on-demand URL reachability (bounded, read-only). Material changes WAKE;
silence otherwise. Never auto-removes programs (history preserved)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone


def local_scan() -> dict:
    """No-network freshness: program count, stale verifications (>30d),
    unattributed click backlog, registry state."""
    from affiliate import intelligence as I
    from affiliate import links as L
    rows = I.portfolio_intelligence()
    today = datetime.now(timezone.utc).date()
    stale = []
    for r in rows:
        lv = ((r.get("record") or {}).get("fields", {}).get("last_verified") or {}).get("value")
        try:
            age = (today - datetime.fromisoformat(str(lv)).date()).days
        except (ValueError, TypeError):
            age = -1
        if age < 0 or age > 30:
            stale.append(r.get("opportunity_id"))
    return {"programs": len(rows), "stale_verification": stale,
            "registered_links": len(L.active_links()),
            "note": "stale = revalidation due, not removal"}


def url_health(urls: list, timeout: int = 8) -> list:
    """Bounded HEAD reachability for evidence URLs. Read-only; failures
    are data (flag/isolate), never exceptions."""
    out = []
    for u in urls[:25]:
        try:
            req = urllib.request.Request(u, method="HEAD",
                                         headers={"User-Agent": "GalaxyForge-health/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out.append({"url": u, "ok": r.status < 400, "status": r.status})
        except Exception as e:
            out.append({"url": u, "ok": False, "status": "%s" % type(e).__name__})
    return out


def revalidate_all(persist=True, portfolio_path=None) -> dict:
    """Full revalidation: fresh reads + first-evidence-URL reachability per
    program. Returns the §12 table rows.

    S3-AFFILIATE-01 fix: previously probed live but never persisted, so
    local_scan()'s stale list grew forever. Now stamps last_verified=today
    on every program actually probed (non-empty URL health result) and
    saves the portfolio. Programs with no evidence URL are reported but
    NOT stamped (stamping them would fabricate a verification)."""
    from affiliate import intelligence as I
    from affiliate import aff_lifecycle as al, economics as ec
    from commission_engine import (
        load_opportunity_portfolio,
        save_opportunity_portfolio,
    )
    raw = {o.get("opportunity_id"): o for o in load_opportunity_portfolio(portfolio_path)}
    today = datetime.now(timezone.utc).date().isoformat()
    rows = I.portfolio_intelligence()
    stale = set(local_scan()["stale_verification"])
    table = []
    stamped = 0
    for r in rows:
        oid = r.get("opportunity_id")
        f = (r.get("record") or {}).get("fields", {})
        urls = (f.get("evidence_url") or {}).get("value") or []
        health = url_health(urls[:1]) if urls else []
        if persist and health and oid in raw:
            raw[oid]["last_verified"] = today
            raw[oid]["last_verified_evidence"] = (
                "revalidate_all URL probe %s: %s"
                % (today, json.dumps(health[0])[:200])
            )
            stamped += 1
        f = (r.get("record") or {}).get("fields", {})
        urls = (f.get("evidence_url") or {}).get("value") or []
        health = url_health(urls[:1]) if urls else []
        eco = ec.model(r)
        stage = al.stage_of(r)
        table.append({
            "PROGRAM": r.get("opportunity_id"),
            "STATUS": (f.get("verification_status") or {}).get("value", "UNKNOWN"),
            "OFFER": (f.get("commission_value") or {}).get("value", "UNKNOWN"),
            "COMMISSION": (f.get("commission_value") or {}).get("value", "UNKNOWN"),
            "PAYOUT": "UNKNOWN (no payout fields on record)",
            "GEOGRAPHY": "UNKNOWN (no geography field on record)",
            "TRACKING": "no affiliate click attributed yet",
            "POLICY_RISK": "per-program terms re-check due" if r.get("opportunity_id") in stale else "no change evidenced",
            "DISTRIBUTION": "NOT_READY (0 registered links)",
            "LAST_VERIFIED": (f.get("last_verified") or {}).get("value", "UNKNOWN"),
            "EVIDENCE": (f.get("source") or {}).get("value", "")[:120],
            "FUNNEL": stage["stage"],
            "ECONOMICS": eco["verdict"],
            "URL_HEALTH": health,
            "NEXT_ACTION": "re-verify terms" if stage["stage"] == "PROGRAM_VERIFIED" else "hold (no link, no traffic)",
        })
    if persist and stamped:
        save_opportunity_portfolio(list(raw.values()), portfolio_path)
    return {"programs": len(table), "table": table,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "restamped": stamped}
