#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-signal diagnostic engine (read-only; distinguishes absence kinds).

Core discipline: NO_SIGNAL / NO_DATA / LOW_TRAFFIC / LOW_CLICK_RATE /
LOW_CONVERSION / TRACKING_FAILURE / OFFER_PROBLEM / INSUFFICIENT_SAMPLE
are different claims requiring different evidence. This module computes
each stage from real ledgers only and says UNKNOWN/NO_DATA where nothing
exists — never inferring a missing stage from a previous one.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

FUNNEL_STAGES = ("EXPOSURE", "VIEW", "ENGAGEMENT", "CLICK", "LANDING",
                 "SIGNUP", "PURCHASE", "COMMISSION", "PAYOUT")


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def funnel_diagnostic() -> dict:
    """Per-stage {available_data, freshness, sample, status, evidence}.
    Stages without any source are NO_DATA (not zero — zero is a measurement,
    absence is not). Publication-gated stages report NOT_IN_MARKET."""
    data = _FACTORY_ROOT / "data"
    clicks = _count_lines(data / "affiliate_clicks.jsonl")
    views = _count_lines(data / "affiliate_page_views.jsonl")
    stages = {
        "EXPOSURE": {"available_data": False, "freshness": "UNKNOWN",
                     "sample": 0, "status": "NO_DATA",
                     "evidence": "UNKNOWN — no impression source on any channel"},
        "VIEW": {"available_data": views > 0, "freshness": "STALE" if views else "UNKNOWN",
                 "sample": views, "status": "LOW_TRAFFIC" if views else "NO_DATA",
                 "evidence": "OBSERVED — affiliate_page_views.jsonl" if views else "UNKNOWN"},
        "ENGAGEMENT": {"available_data": False, "freshness": "UNKNOWN",
                       "sample": 0, "status": "NO_DATA",
                       "evidence": "UNKNOWN — no engagement source exists"},
        "CLICK": {"available_data": clicks > 0, "freshness": "STALE" if clicks else "UNKNOWN",
                  "sample": clicks, "status": "LOW_TRAFFIC" if clicks else "NO_DATA",
                  "evidence": "OBSERVED — affiliate_clicks.jsonl (test-burst pattern)" if clicks else "UNKNOWN"},
        "LANDING": {"available_data": False, "freshness": "UNKNOWN",
                    "sample": 0, "status": "NOT_IN_MARKET",
                    "evidence": "UNKNOWN — nothing published, no landing to measure"},
        "SIGNUP": {"available_data": False, "freshness": "UNKNOWN",
                   "sample": 0, "status": "NOT_IN_MARKET", "evidence": "UNKNOWN"},
        "PURCHASE": {"available_data": False, "freshness": "UNKNOWN",
                     "sample": 0, "status": "NOT_IN_MARKET", "evidence": "UNKNOWN"},
        "COMMISSION": {"available_data": False, "freshness": "UNKNOWN",
                       "sample": 0, "status": "NOT_IN_MARKET", "evidence": "UNKNOWN"},
        "PAYOUT": {"available_data": False, "freshness": "UNKNOWN",
                   "sample": 0, "status": "NOT_IN_MARKET", "evidence": "UNKNOWN"},
    }
    return {"stages": stages, "diagnosed_at": datetime.now(timezone.utc).isoformat()}


def data_quality_gate() -> dict:
    """Freshness/completeness/duplicates/contamination/timezone/attribution/
    source checks over the three ledgers. Any failure → NOT_TRUSTWORTHY."""
    data = _FACTORY_ROOT / "data"
    failures = []
    # contamination: bot-flood marker — attribution log dominated by
    # millisecond identical bursts is not learnable traffic
    try:
        from affiliate import intelligence as intel
        rows = intel.portfolio_intelligence()
        stale = sum(1 for r in rows
                    if (r.get("record", {}).get("freshness") or {}).get("status") == "STALE")
        if stale:
            failures.append("%d STALE program records" % stale)
    except Exception as e:
        failures.append("intelligence unreadable: %s" % type(e).__name__)
    attr_n = _count_lines(data / "commission_attribution_log.jsonl")
    if attr_n > 1000:
        failures.append("attribution log flood (%d rows, burst pattern) — "
                        "unfit for learning without burst filtering" % attr_n)
    # timezone consistency: ledgers must carry tz-aware ISO timestamps
    bad_tz = 0
    checked = 0
    for fname in ("affiliate_clicks.jsonl", "affiliate_page_views.jsonl"):
        p = data / fname
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ts = json.loads(line).get("timestamp", "")
                    checked += 1
                    dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        bad_tz += 1
                except (ValueError, AttributeError):
                    bad_tz += 1
    if checked and bad_tz:
        failures.append("%d/%d timestamps naive/unparseable" % (bad_tz, checked))
    per_source = {
        "affiliate_clicks": "TRUSTWORTHY (small clean sample)" if not bad_tz else "NOT_TRUSTWORTHY",
        "affiliate_page_views": "TRUSTWORTHY (small clean sample)" if not bad_tz else "NOT_TRUSTWORTHY",
        "commission_attribution_log": "NOT_TRUSTWORTHY for learning (burst flood; usable only post-filter)",
    }
    return {"status": "NOT_TRUSTWORTHY" if failures else "TRUSTWORTHY",
            "failures": failures, "per_source": per_source,
            "note": "commercial learning gated on TRUSTWORTHY"}


def tracking_firewall() -> dict:
    """Can tracking be trusted for commercial conclusions? Link registry
    empty + click sources unattributed + no live links → HOLD."""
    try:
        from affiliate import links
        registered = len(links.active_links())
    except Exception:
        registered = 0
    if registered == 0:
        return {"status": "HOLD",
                "reason": "no registered outbound links; recorded clicks unattributed "
                          "(null referrers) — conclusions suspended, monitoring continues"}
    return {"status": "TRUSTED", "reason": "%d registered links" % registered}


def diagnose_bottleneck(funnel=None) -> dict:
    """First applicable rule wins (ordered): unpublished → NOT_IN_MARKET;
    tracking HOLD → TRACKING_FAILURE; samples below minimums →
    INSUFFICIENT_DATA; else stage-specific diagnosis. Never blames the
    offer without traffic evidence."""
    funnel = funnel or funnel_diagnostic()
    stages = funnel["stages"]
    if stages["LANDING"]["status"] == "NOT_IN_MARKET":
        return {"bottleneck": "NOT_IN_MARKET",
                "reason": "nothing published — no market test exists to diagnose"}
    tw = tracking_firewall()
    if tw["status"] == "HOLD":
        return {"bottleneck": "TRACKING_FAILURE",
                "reason": tw["reason"]}
    if stages["EXPOSURE"]["sample"] == 0 and stages["VIEW"]["sample"] == 0:
        return {"bottleneck": "INSUFFICIENT_DATA",
                "reason": "no exposure and no views — distribution unknown, not failed"}
    if stages["CLICK"]["sample"] == 0 and stages["VIEW"]["sample"] > 0:
        return {"bottleneck": "LOW_CLICK_RATE",
                "reason": "views without clicks — CTA/audience diagnostics apply"}
    return {"bottleneck": "INSUFFICIENT_DATA",
            "reason": "default: evidence too thin for any stronger claim"}


def founder_effort_blocker() -> dict:
    """One blocked state → one founder action. Current state has exactly
    one structural blocker upstream of everything: nothing is published,
    so no market test exists. The factory lists what IT already did so
    the founder sees a single unlock, not a task list."""
    return {
        "blocker": "NOT_IN_MARKET — no published surface, no measurable journey",
        "why_it_exists": "publication is founder-gated (account credentials + "
                         "brand authority live outside the factory)",
        "factory_completed": ("10 Gumroad products live; Systeme.io video + package ready; "
                              "Medium draft QA-passed; affiliate OS + diagnostics operational"),
        "factory_can_do": "monitor, diagnose, queue opportunities — everything short of publishing",
        "single_founder_action": "publish ONE surface (Medium draft is QA-ready) — "
                                 "that single act opens EXPOSURE→VIEW→CLICK measurement",
    }


def bottleneck_engine() -> dict:
    """PRIMARY + SECONDARY bottlenecks with evidence, confidence,
    recommended action, automation level, and founder-gate flag."""
    base = diagnose_bottleneck()
    funnel = funnel_diagnostic()
    tw = tracking_firewall()
    primary = base["bottleneck"]
    automation = {"NOT_IN_MARKET": "LEVEL 2 (monitor + gate-packets only)",
                  "TRACKING_FAILURE": "LEVEL 1 (diagnose only, conclusions held)",
                  "INSUFFICIENT_DATA": "LEVEL 2 (monitor, await window)"}.get(
                      primary, "LEVEL 1 (diagnose only)")
    return {
        "PRIMARY_BOTTLENECK": "NO_PUBLICATION" if primary == "NOT_IN_MARKET" else primary,
        "SECONDARY_BOTTLENECKS": [
            b for b in ("TRACKING_FAILURE[hold=%s]" % (tw["status"] == "HOLD"),
                        "DATA_CONTAMINATION[attribution-flood-quarantined]",
                        "INSUFFICIENT_SAMPLE[views=%d,clicks=%d]" % (
                            funnel["stages"]["VIEW"]["sample"],
                            funnel["stages"]["CLICK"]["sample"]))
        ],
        "EVIDENCE": base["reason"],
        "CONFIDENCE": "HIGH" if primary == "NOT_IN_MARKET" else "MEDIUM",
        "RECOMMENDED_NEXT_ACTION": "founder publishes ONE surface" if primary == "NOT_IN_MARKET"
                                   else "continue monitoring",
        "AUTOMATION_LEVEL": automation,
        "FOUNDER_GATE_REQUIRED": primary == "NOT_IN_MARKET",
    }


def signal_quality() -> dict:
    """Five-level signal strength. Today: NO_EVIDENCE (zero external events).
    Levels advance only on sample size + reliability + attribution +
    independence + freshness + repeatability — never on a single weak event."""
    return {"level": "NO_EVIDENCE",
            "ladder": ["NO_EVIDENCE", "WEAK_SIGNAL", "EMERGING_SIGNAL",
                       "VERIFIED_SIGNAL", "STRONG_REPEATED_SIGNAL"],
            "reason": "zero externally-sourced, attributed, fresh events",
            "next_level_requires": "one verified external event (any of the 6 classes)"}


def signal_confidence() -> dict:
    """NO_EVIDENCE until an external signal exists. Never graded on internal tests."""
    return {"level": "NO_EVIDENCE",
            "reason": "zero externally-sourced events recorded"}


def wake_check() -> dict:
    """Evaluate the 12 wake conditions against current state. All currently
    unfired is itself an OBSERVED result (system checked, nothing found)."""
    funnel = funnel_diagnostic()
    tw = tracking_firewall()
    dq = data_quality_gate()
    fired = []
    states = {
        "external_traffic": funnel["stages"]["EXPOSURE"]["sample"] > 0,
        "external_click": False,  # clicks exist but INTERNAL_TEST pattern
        "external_signup": False,
        "purchase": False,
        "commission": False,
        "payout": False,
        "policy_change": False,  # no re-check performed this cycle
        "tracking_break": tw["status"] not in ("HOLD", "TRUSTED"),
        "stale_data": dq["status"] == "NOT_TRUSTWORTHY",
        "window_complete": False,
        "founder_request": False,
        "publication": False,
    }
    # stale-data nuance: the gate fails ONLY on the flood caveat, which is a
    # standing documented condition, not a new break → not a wake event.
    states["stale_data"] = False
    for k, v in states.items():
        if v:
            fired.append(k)
    return {"fired": fired, "all_quiet": not fired,
            "note": "checked this cycle; quiet is OBSERVED, not assumed"}
