#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exposure reality probe: is anyone seeing the offer? Read-only.

First-party result (OBSERVED, pre-documented in gumroad_monitor.py):
Gumroad's API exposes NO traffic/analytics — views, referrers, clicks,
checkouts are NOT_AVAILABLE via accessible means (dashboard is
founder-read UI only). Owned surfaces carry ZERO inbound links to the
GPSR product (fetmu); existing links point to other products.
Nothing here edits, publishes, spends, or infers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = _FACTORY_ROOT / "data" / "exposure_probe.json"

MATRIX = [
    {"DOMAIN": "PUBLIC_ACCESS", "STATUS": "VERIFIED",
     "EVIDENCE": "independent GET 200 + V1 marker + $79 (2026-09-21)",
     "UNKNOWN": "nothing material", "LIMITATION": "point-in-time; re-check periodically"},
    {"DOMAIN": "PAGE_VISITS", "STATUS": "NOT_AVAILABLE",
     "EVIDENCE": "Gumroad API exposes no visit endpoint (pre-documented)",
     "UNKNOWN": "all visit counts", "LIMITATION": "dashboard is founder-read UI only"},
    {"DOMAIN": "EXTERNAL_TRAFFIC", "STATUS": "UNKNOWN",
     "EVIDENCE": "no source evidences external visits",
     "UNKNOWN": "volume, source, geography", "LIMITATION": "no API; no UTM observed inbound"},
    {"DOMAIN": "QUALIFIED_TRAFFIC", "STATUS": "UNKNOWN",
     "EVIDENCE": "requires traffic first; none measured",
     "UNKNOWN": "buyer relevance of any visit", "LIMITATION": "same as above"},
    {"DOMAIN": "TRAFFIC_SOURCE", "STATUS": "NOT_AVAILABLE",
     "EVIDENCE": "referrers NOT_AVAILABLE via API; owned surfaces link to other products, not fetmu",
     "UNKNOWN": "any inbound path performance", "LIMITATION": "dashboard-only"},
    {"DOMAIN": "CHECKOUT_ACTIVITY", "STATUS": "UNKNOWN",
     "EVIDENCE": "no checkout probe permitted (no test purchase); sales API reads purchases only",
     "UNKNOWN": "checkout opens/abandons", "LIMITATION": "by design (test integrity)"},
    {"DOMAIN": "PURCHASE_ACTIVITY", "STATUS": "OBSERVED",
     "EVIDENCE": "platform sales API reads 0; finance + ledger agree at 0",
     "UNKNOWN": "future events", "LIMITATION": "polling cadence, not streaming"},
]

ADVERSARIAL_ANSWERS = [
    "1. external saw page? UNKNOWN (no visit evidence)",
    "2. visitors external? UNKNOWN (no visits to classify)",
    "3. relevant buyers? UNKNOWN (no visits + no buyer data)",
    "4. bots vs humans? UNKNOWN (nothing to separate)",
    "5. internal vs external? SEPARATED BY POLICY (internal quarantined; externals: none observed)",
    "6. checkout independently? NO (by design; sales API only)",
    "7. external transaction? NO (0 across 4 sources)",
    "8. reconcile? YES — all-zero agreement (consistency, not validation)",
    "9. disprove current reading? a dashboard screenshot showing visits would; none available via API",
    "10. missing most? any traffic measurement at all",
]

FREE_OPTIONS = [
    {"OPPORTUNITY": "Gumroad Discover/search presence (already live)",
     "EVIDENCE": "published + 5 tags OBSERVED", "COST": "$0",
     "REQUIREMENTS": "none (active)", "EXPECTED_MEASUREMENT": "none via API (dashboard founder-read)",
     "FOUNDER_GATE_REQUIRED": False},
    {"OPPORTUNITY": "Tag/coverage refinement on live listing",
     "EVIDENCE": "tags editable field OBSERVED", "COST": "$0",
     "REQUIREMENTS": "external edit", "EXPECTED_MEASUREMENT": "none via API",
     "FOUNDER_GATE_REQUIRED": True},
    {"OPPORTUNITY": "Publish ready Medium draft (referral path to GPSR)",
     "EVIDENCE": "draft on disk OBSERVED", "COST": "$0",
     "REQUIREMENTS": "founder publishes from own account",
     "EXPECTED_MEASUREMENT": "Medium stats founder-read; referral UNKNOWN",
     "FOUNDER_GATE_REQUIRED": True},
    {"OPPORTUNITY": "Publish ready systeme video (referral path)",
     "EVIDENCE": "final mp4 + QA on disk OBSERVED", "COST": "$0",
     "REQUIREMENTS": "founder publishes from own account",
     "EXPECTED_MEASUREMENT": "platform analytics founder-read",
     "FOUNDER_GATE_REQUIRED": True},
    {"OPPORTUNITY": "Add GPSR link to owned customer_site pages",
     "EVIDENCE": "pages exist but link only to other products OBSERVED; deployment status UNKNOWN",
     "COST": "$0", "REQUIREMENTS": "site edit + deploy (founder-owned surface)",
     "EXPECTED_MEASUREMENT": "none instrumented (no analytics evidenced)",
     "FOUNDER_GATE_REQUIRED": True},
    {"OPPORTUNITY": "X organic posting",
     "EVIDENCE": "X_API_KEY present BUT 402 credits depleted (standing state)",
     "COST": "$0 until credits", "REQUIREMENTS": "credits + founder approval (outreach-adjacent)",
     "EXPECTED_MEASUREMENT": "platform metrics founder-read",
     "FOUNDER_GATE_REQUIRED": True},
]


def diagnose_case(exposure=None, visits=None, engagement=None, clicks=None,
                    checkouts=None, purchases=None) -> dict:
    """CASE A-G tree. Unknown/None inputs stay UNKNOWN — never forced."""
    if purchases:
        return {"case": "G_PURCHASE", "action": "verify user+transaction+evidence, then revenue check"}
    if checkouts:
        return {"case": "F_CHECKOUT_NO_PURCHASE",
                "action": "analyze checkout/trust/price/payment/access"}
    if clicks:
        return {"case": "E_CLICKS_NO_CHECKOUT",
                "action": "analyze landing/offer/pricing/clarity"}
    if engagement:
        return {"case": "D_ENGAGEMENT_NO_CLICK", "action": "analyze CTA/offer/trust/relevance"}
    if visits:
        return {"case": "C_VISITS_NO_ENGAGEMENT", "action": "analyze content/message/audience"}
    if exposure:
        return {"case": "B_EXPOSURE_NO_VISITS",
                "action": "analyze headline/positioning/channel-fit/discoverability"}
    return {"case": "A_NO_EXPOSURE", "action": "improve/verify distribution; demand stays UNKNOWN"}


CASE_SPEC = {
    "A_NO_EXPOSURE": {"evidence_required": "any traffic/exposure measurement",
                      "minimum": "1 attributed external visit",
                      "diagnosis": "distribution unproven, demand unjudgeable",
                      "safe_to_do": ["verify listing live", "check channels", "prepare gated distribution"],
                      "must_not_do": ["product/price verdicts", "scaling", "new products"],
                      "next_measurement": "first visit evidence",
                      "founder_needed": False},
    "B_EXPOSURE_NO_VISITS": {"evidence_required": "exposure source + visit counts",
                             "minimum": "dated exposure event + 0-visit window",
                             "diagnosis": "headline/positioning/channel-fit/discoverability",
                             "safe_to_do": ["audit discoverability", "review positioning"],
                             "must_not_do": ["price changes", "scaling"],
                             "next_measurement": "visit lift per exposure unit",
                             "founder_needed": False},
    "C_VISITS_NO_ENGAGEMENT": {"evidence_required": "visit + engagement metric",
                               "minimum": "sustained visit sample (no fixed n without variance model)",
                               "diagnosis": "content/message/audience",
                               "safe_to_do": ["content review (no publish)"],
                               "must_not_do": ["listing edits mid-window", "scaling"],
                               "next_measurement": "engagement rate",
                               "founder_needed": False},
    "D_ENGAGEMENT_NO_CLICK": {"evidence_required": "engagement + click counts",
                              "minimum": "same sufficiency rule as C",
                              "diagnosis": "CTA/offer/trust/relevance",
                              "safe_to_do": ["CTA review (no publish)"],
                              "must_not_do": ["mid-window edits", "scaling"],
                              "next_measurement": "click-through",
                              "founder_needed": False},
    "E_CLICKS_NO_CHECKOUT": {"evidence_required": "click + checkout events",
                             "minimum": "same sufficiency rule",
                             "diagnosis": "landing/offer/pricing/clarity",
                             "safe_to_do": ["landing review (no publish)"],
                             "must_not_do": ["price change without gate", "scaling"],
                             "next_measurement": "checkout rate",
                             "founder_needed": False},
    "F_CHECKOUT_NO_PURCHASE": {"evidence_required": "checkout + purchase events",
                               "minimum": "same sufficiency rule",
                               "diagnosis": "checkout/trust/price/payment/access",
                               "safe_to_do": ["friction review (no changes)"],
                               "must_not_do": ["price/product changes", "scaling"],
                               "next_measurement": "purchase completion",
                               "founder_needed": False},
    "G_PURCHASE": {"evidence_required": "verified transaction + reconciliation",
                   "minimum": "1 verified external sale",
                   "diagnosis": "customer learning (source, economics, repeatability)",
                   "safe_to_do": ["forensics chain", "learn loop entry"],
                   "must_not_do": ["auto-scale (needs repeatability)"],
                   "next_measurement": "second purchase / repeat signals",
                   "founder_needed": False},
}


def commercial_decision(case: dict, evidence: str = "") -> dict:
    """10-question decision helper (report-time, pure). Never outputs SCALE."""
    return {
        "what_happened": "no verified commercial event; state=%s" % case.get("case"),
        "evidence": evidence or "reconciled zeros; exposure UNKNOWN",
        "bottleneck": case.get("case"),
        "exposure_or_demand": "exposure (demand unjudgeable without it)",
        "buyer_signal": "none",
        "variable_to_change": "none (no data licenses a change)",
        "smallest_change": "none yet",
        "measure_effect": "sales poll + reconciliation vs $0 baseline",
        "continue": "yes (window open, integrity clean)",
        "scale": "NO (no evidence supports scale)",
    }


def run_probe(sales_count: int | None = None) -> dict:
    probe = {"ran_at": datetime.now(timezone.utc).isoformat(),
             "test": "GPSR_PATH_B_V1 (untouched)",
             "matrix": MATRIX,
             "adversarial_answers": ADVERSARIAL_ANSWERS,
             "interpretation": "INSUFFICIENT_EXPOSURE_DATA",
             "platform_purchases": sales_count,
             "free_options": FREE_OPTIONS,
             "missing_link": "REAL EXPOSURE — page proven reachable, nothing proves it is reached",
             "DO_NOT_CLONE_WITHOUT_EVIDENCE": True}
    PROBE_PATH.write_text(json.dumps(probe, ensure_ascii=False, indent=1), encoding="utf-8")
    return probe
