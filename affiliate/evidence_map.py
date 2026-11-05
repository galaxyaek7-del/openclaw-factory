#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real-world evidence boundary map: what software can/can't obtain, the
first safe experiment, gate enumeration, truth-pipeline audit, forbidden
state transitions. Read-only; UNKNOWN stays UNKNOWN."""

from __future__ import annotations

EVIDENCE_MAP = [
    ("Product published (Gumroad)", "OBSERVED (live listing)", "API GET",
     True, "none (already live)"),
    ("Product published (Medium)", "APPROVED, not PUBLISHED", "human account",
     False, "HUMAN (f386 click)"),
    ("Public URL reachable", "OBSERVED (Gumroad 200)", "HTTP", True, "none"),
    ("Real impressions", "UNKNOWN", "platform analytics", False, "PLATFORM (no API surface)"),
    ("Real visitors", "UNKNOWN", "analytics/API", False, "PLATFORM (none evidenced)"),
    ("Real clicks", "UNKNOWN", "platform/analytics", False, "PLATFORM"),
    ("Checkout initiated", "UNKNOWN", "payment platform", False, "EXTERNAL (customer)"),
    ("Real purchase", "$0 currently", "payment ledger", True, "CUSTOMER (must act)"),
    ("Refund", "0 currently", "payment ledger", True, "CUSTOMER"),
    ("Chargeback", "0 currently", "payment platform", False, "PLATFORM"),
    ("Affiliate conversion", "UNKNOWN", "affiliate platform", False, "PLATFORM (no feed)"),
    ("Payout", "UNKNOWN", "payout provider", False, "PROVIDER"),
    ("Customer feedback", "UNKNOWN", "external world", False, "HUMAN/CUSTOMER"),
    ("Market demand", "UNKNOWN", "external world", False, "MARKET"),
]

FIRST_EXPERIMENT = {
    "name": "FIRST_REAL_WORLD_EVIDENCE_TEST = f386 publish -> first_cycle -> measurement",
    "objective": "move one asset from APPROVED to OBSERVED_TRAFFIC-or-bust, then measure honestly",
    "human_action": "paste draft into own Medium account, reply with URL",
    "platform": "Medium (human) + Gumroad (existing listing)",
    "public_asset": "drafts/medium_gpsr_etsy_guide.md (hash c3d5cf32a3dd38db)",
    "expected_evidence": "public URL 200 + V1 markers + UTM; then sales-poll deltas",
    "evidence_source": "independent HTTP + Gumroad sales API + finance reconciliation",
    "success": "VERIFIED article + measurement open (exposure still UNKNOWN until visits evidenced)",
    "failure": "HOLD/NOT_VERIFIED with exact cause; no silent repair",
    "rollback": "unpublish from Medium account; factory re-arms gate (procedure on file)",
    "safety": "$0, reversible, no new permissions, no traffic manufactured",
    "remains_unknown_after": "visits, buyer intent, demand, price acceptance",
}

GATES = [
    {"GATE_ID": "f386228d0bf5", "ACTION": "paste Medium draft + reply URL",
     "PLATFORM": "Medium", "WHY_SOFTWARE_CANT": "no account, credential, API, or browser mechanism exists in factory",
     "REVERSIBILITY": "unpublish anytime", "FINANCIAL_RISK": "$0", "ACCOUNT_RISK": "LOW (own account, own content)",
     "EVIDENCE": "public URL enables 12-check verification + measurement",
     "EXACT_HUMAN_ACTION": "open Medium, paste file verbatim, publish, reply with URL"},
    {"GATE_ID": "SPEND-ANY", "ACTION": "any purchase/subscription/upgrade/traffic",
     "PLATFORM": "any", "WHY_SOFTWARE_CANT": "$0 hard cap + financial authority is human-only",
     "REVERSIBILITY": "n/a", "FINANCIAL_RISK": "open-ended", "ACCOUNT_RISK": "n/a",
     "EVIDENCE": "none without approval", "EXACT_HUMAN_ACTION": "explicit per-item approval with cap"},
    {"GATE_ID": "ACCOUNTS-ANY", "ACTION": "new accounts, credentials, API keys, OAuth",
     "PLATFORM": "any", "WHY_SOFTWARE_CANT": "credential custody + ToS acceptance are human acts",
     "REVERSIBILITY": "varies", "FINANCIAL_RISK": "$0+commitment", "ACCOUNT_RISK": "HIGH (ToS liability)",
     "EVIDENCE": "account access enables new measurement paths",
     "EXACT_HUMAN_ACTION": "create/connect + record scope; factory never stores secrets outside .env"},
]

PIPELINE = [
    ("CUSTOMER", "externally dependent", "NOT_VERIFIED"),
    ("PLATFORM", "observed (Gumroad live)", "OBSERVED"),
    ("PAYMENT EVENT", "tested (firewall refusal paths) + simulated", "TESTED"),
    ("WEBHOOK/API/POLL", "observed (sales poll reads 0)", "OBSERVED"),
    ("VALIDATION", "tested (chain classifier)", "TESTED"),
    ("DEDUPLICATION", "tested (10000x replay)", "TESTED"),
    ("FINANCIAL LEDGER", "observed ($0, invariants CLEAN)", "OBSERVED"),
    ("RECONCILIATION", "observed (4-source zero agreement)", "OBSERVED"),
    ("NOTIFICATION", "tested (policy matrix)", "TESTED"),
    ("LEARNING INPUT", "simulated only; sim excluded structurally", "GUARDED"),
]

FORBIDDEN = [
    ("SIMULATED_PURCHASE", "VALIDATED"),
    ("CHECKOUT_READY", "REVENUE"),
    ("PUBLISHED", "DEMAND_CONFIRMED"),
    ("UNKNOWN_TRAFFIC", "NO_DEMAND"),
    ("SELF_PURCHASE", "MARKET_VALIDATION"),
]


def states_valid() -> dict:
    """Structural assertion support: funnel + market machines expose only
    evidence-gated transitions (checked by tests)."""
    from affiliate import funnel as fn, market_state as ms
    return {"funnel_states": fn.STATES,
            "market_transitions": sorted(ms.TRANSITIONS.keys())}


def capability_matrix() -> list:
    return [
        ("monitoring", "SOFTWARE-PROVEN", ""), ("recovery", "SOFTWARE-PROVEN", ""),
        ("idempotency", "SOFTWARE-PROVEN", ""), ("financial isolation", "SOFTWARE-PROVEN", ""),
        ("publication", "EXTERNALLY-DEPENDENT", "f386 click"),
        ("traffic measurement", "NOT-VERIFIABLE-BY-CODE", "no API surface"),
        ("customer acquisition", "EXTERNALLY-DEPENDENT", "needs humans"),
        ("real sales", "EXTERNALLY-DEPENDENT", "needs customers"),
        ("real revenue", "EXTERNALLY-DEPENDENT", "needs transactions"),
        ("learning from market", "EXTERNALLY-DEPENDENT", "needs evidence"),
    ]
