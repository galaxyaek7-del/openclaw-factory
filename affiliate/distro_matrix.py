#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Distribution capability matrix (evidence audit 2026-09-22). Verdict: B —
only founder-gated paths exist. No code executes publication."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
MATRIX_PATH = _FACTORY_ROOT / "data" / "distribution_matrix.json"

MATRIX = [
    {"CHANNEL": "Gumroad", "ACCESS": "AVAILABLE", "AUTHORIZED": "YES (own listings)",
     "API_AVAILABLE": "YES (products+sales)", "PUBLICATION_AVAILABLE": "GATED (test discipline)",
     "AUTOMATION_AVAILABLE": "PARTIAL (poll+reads)", "MEASUREMENT_AVAILABLE": "purchases only",
     "COST": "$0", "FOUNDER_ACTION": "listing edits (frozen during V1)",
     "CURRENT_STATUS": "LIVE_LISTING (passive exposure only)", "BLOCKER": "no traffic API"},
    {"CHANNEL": "Medium", "ACCESS": "AVAILABLE (account exists)", "AUTHORIZED": "HUMAN-ONLY",
     "API_AVAILABLE": "NO (no mechanism)", "PUBLICATION_AVAILABLE": "FOUNDER_GATE",
     "AUTOMATION_AVAILABLE": "post-publish verify+measure only", "MEASUREMENT_AVAILABLE": "founder stats",
     "COST": "$0", "FOUNDER_ACTION": "paste f386 + reply URL",
     "CURRENT_STATUS": "APPROVED_UNPUBLISHED", "BLOCKER": "human click"},
    {"CHANNEL": "GitHub Pages", "ACCESS": "UNAVAILABLE", "AUTHORIZED": "UNKNOWN",
     "API_AVAILABLE": "NO (no CNAME, no deploy workflow, no gh-pages branch)",
     "PUBLICATION_AVAILABLE": "NO", "AUTOMATION_AVAILABLE": "NO",
     "MEASUREMENT_AVAILABLE": "NO", "COST": "$0",
     "FOUNDER_ACTION": "configure Pages + deploy (multi-step, not minimal)",
     "CURRENT_STATUS": "35 local files, undeployed", "BLOCKER": "no deployment configured"},
    {"CHANNEL": "Telegram", "ACCESS": "AVAILABLE (bot token set)", "AUTHORIZED": "notify-only",
     "API_AVAILABLE": "UNKNOWN (getMe failed from here)", "PUBLICATION_AVAILABLE": "NO (notify, not publish)",
     "AUTOMATION_AVAILABLE": "PARTIAL", "MEASUREMENT_AVAILABLE": "NO",
     "COST": "$0", "FOUNDER_ACTION": "none (not a distribution path)",
     "CURRENT_STATUS": "notify path unverified", "BLOCKER": "not a publishing channel"},
    {"CHANNEL": "X", "ACCESS": "AVAILABLE (4 creds set)", "AUTHORIZED": "GATED (external publication)",
     "API_AVAILABLE": "UNKNOWN (oauthlib missing; 402-depletion history)",
     "PUBLICATION_AVAILABLE": "FOUNDER_GATE", "AUTOMATION_AVAILABLE": "NO",
     "MEASUREMENT_AVAILABLE": "NO", "COST": "$0",
     "FOUNDER_ACTION": "approve single product post (after cred verification)",
     "CURRENT_STATUS": "BLOCKED (library + depletion + gate)", "BLOCKER": "credits + approval"},
    {"CHANNEL": "LinkedIn", "ACCESS": "UNAVAILABLE (zero credentials)",
     "AUTHORIZED": "NO", "API_AVAILABLE": "NO", "PUBLICATION_AVAILABLE": "NO",
     "AUTOMATION_AVAILABLE": "NO", "MEASUREMENT_AVAILABLE": "NO", "COST": "N/A",
     "FOUNDER_ACTION": "account + ToS decision (HIGH risk, not recommended now)",
     "CURRENT_STATUS": "ISOLATED", "BLOCKER": "no account"},
    {"CHANNEL": "n8n", "ACCESS": "UNAVAILABLE (no host/key configured)",
     "AUTHORIZED": "UNKNOWN", "API_AVAILABLE": "NO", "PUBLICATION_AVAILABLE": "NO",
     "AUTOMATION_AVAILABLE": "NO", "MEASUREMENT_AVAILABLE": "NO", "COST": "$0",
     "FOUNDER_ACTION": "host + wire workflows (not minimal)",
     "CURRENT_STATUS": "6 files, unwired", "BLOCKER": "no live instance"},
    {"CHANNEL": "Affiliate link", "ACCESS": "AVAILABLE (link HEALTHY)",
     "AUTHORIZED": "YES (EXP_001)", "API_AVAILABLE": "N/A",
     "PUBLICATION_AVAILABLE": "NO (no surface to place it)",
     "AUTOMATION_AVAILABLE": "health checks", "MEASUREMENT_AVAILABLE": "none (no clicks)",
     "COST": "$0", "FOUNDER_ACTION": "distribution surface (same Medium gate covers it)",
     "CURRENT_STATUS": "LINK_ACTIVE undistributed", "BLOCKER": "no permitted surface"},
]


def build():
    doc = {"at": datetime.now(timezone.utc).isoformat(), "verdict": "B",
           "verdict_meaning": "Only founder-gated distribution paths exist. "
                              "Minimum action: Medium f386 click.",
           "matrix": MATRIX}
    MATRIX_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc
