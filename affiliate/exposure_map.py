#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exposure map: per-channel truth + diagnostic state (read-only).

Channels are described, never activated. Statuses from OBSERVED evidence:
Gumroad OPERATIONAL (live listing, sales API, no traffic API); Shopify
DEFERRED (triggers unfired); LinkedIn ISOLATED; Gojiberry HOLD; X
BLOCKED (402 depleted); Apollo EXPERIMENTAL-research (free tier, no
outreach); Medium HUMAN_GATE (draft ready). Diagnostic state today: A
(NO_EXPOSURE) — exposure unmeasured, so B/C/D are unlicensed."""

from __future__ import annotations

CHANNELS = [
    {"channel": "Gumroad", "status": "OPERATIONAL", "cost": "$0",
     "terms_risk": "LOW (own listings, compliant use)",
     "automation": "sales polling + listing reads (proven)",
     "traffic_capability": "NOT_AVAILABLE via API (dashboard founder-read)",
     "exposure": "UNKNOWN", "last_activity": "V1 copy update 2026-09-21 (gated)",
     "visits": "UNKNOWN", "checkouts": "UNKNOWN", "sales": 0,
     "evidence": "OBSERVED (API)", "gate": False},
    {"channel": "Shopify", "status": "DEFERRED", "cost": "$0",
     "terms_risk": "LOW", "automation": "none wired",
     "traffic_capability": "UNKNOWN (store password-gated, no admin)",
     "exposure": "NONE", "last_activity": "deferred (triggers unfired)",
     "visits": "NONE", "checkouts": "NONE", "sales": 0,
     "evidence": "OBSERVED (decision file)", "gate": True},
    {"channel": "LinkedIn", "status": "ISOLATED", "cost": "N/A",
     "terms_risk": "HIGH (UA s.8.2)", "automation": "BLOCKED",
     "traffic_capability": "N/A", "exposure": "NONE",
     "last_activity": "none", "visits": "NONE", "checkouts": "NONE", "sales": 0,
     "evidence": "OBSERVED (founder directive)", "gate": True},
    {"channel": "Gojiberry", "status": "HOLD", "cost": "$99/mo if activated",
     "terms_risk": "HIGH (same UA)", "automation": "BLOCKED",
     "traffic_capability": "N/A", "exposure": "NONE",
     "last_activity": "none", "visits": "NONE", "checkouts": "NONE", "sales": 0,
     "evidence": "OBSERVED (HOLD directive)", "gate": True},
    {"channel": "X", "status": "BLOCKED", "cost": "$0 until credits",
     "terms_risk": "MEDIUM", "automation": "BLOCKED (402 depleted)",
     "traffic_capability": "N/A", "exposure": "NONE",
     "last_activity": "none", "visits": "NONE", "checkouts": "NONE", "sales": 0,
     "evidence": "OBSERVED (402 state)", "gate": True},
    {"channel": "Apollo", "status": "EXPERIMENTAL", "cost": "$0 (free tier)",
     "terms_risk": "LOW (own API key, read-only)",
     "automation": "research only, no outreach",
     "traffic_capability": "N/A (research, not distribution)",
     "exposure": "N/A", "last_activity": "ICP cycles 2026-09-21",
     "visits": "N/A", "checkouts": "N/A", "sales": 0,
     "evidence": "OBSERVED (validated)", "gate": True},
    {"channel": "Medium", "status": "HUMAN_GATE", "cost": "$0",
     "terms_risk": "LOW (founder's own account)",
     "automation": "none (human publishes)",
     "traffic_capability": "founder-read stats post-publish",
     "exposure": "NONE (unpublished)", "last_activity": "draft ready + prep-audited",
     "visits": "NONE", "checkouts": "NONE", "sales": 0,
     "evidence": "OBSERVED (draft on disk)", "gate": True},
]

ORGANIC_OPPORTUNITIES = [
    {"area": "Gumroad search/Discover presence", "state": "already live (tags set)",
     "preparation": "none needed", "gate": False},
    {"area": "Owned customer_site cross-links to GPSR",
     "state": "0 inbound links (OBSERVED); deployment UNKNOWN",
     "preparation": "link map prepared on founder request (no edit made)",
     "gate": True},
    {"area": "Medium article referral (UTM-tagged URL in draft)",
     "state": "draft ready, unpublished", "preparation": "prep audit done",
     "gate": True},
    {"area": "Professional communities / discussions",
     "state": "no accounts created, no participation started (policy)",
     "preparation": "none (would need founder-owned presence)",
     "gate": True},
    {"area": "Documentation/resources (reuse kit excerpts)",
     "state": "not prepared; derivative needs commercial rationale",
     "preparation": "none (DO_NOT_CLONE holds)",
     "gate": True},
]


def diagnostic_state(exposure_measured: bool = False, sales: int = 0) -> dict:
    """A/B/C/D evaluator. Today: A (NO_EXPOSURE) — B/C/D require measured
    exposure that does not exist."""
    if sales > 0:
        return {"state": "D_VERIFIED_PURCHASE", "action": "customer-learning mode"}
    if exposure_measured:
        return {"state": "B_OR_C_PENDING_DATA",
                "action": "separate visits/qualified/checkouts before judging"}
    return {"state": "A_NO_EXPOSURE",
            "action": "improve distribution measurement; no product/price verdict licensed"}


def exposure_map() -> dict:
    return {"channels": CHANNELS, "organic": ORGANIC_OPPORTUNITIES,
            "diagnostic": diagnostic_state()}
