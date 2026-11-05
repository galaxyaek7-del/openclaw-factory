#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Founder Command Center: every remaining external dependency compressed
into the minimum human session. Only evidence-backed gates listed —
hypothetical requirements excluded. Read-only builder; one JSON artifact."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
CC_PATH = _FACTORY_ROOT / "data" / "founder_command_center.json"

GATES = [
    {"GATE_ID": "f386228d0bf5", "ACTION": "paste approved Medium draft + reply with public URL",
     "PLATFORM": "Medium", "WHY_HUMAN_REQUIRED": "no account, credential, API, or browser mechanism exists in factory",
     "EXACT_INPUT_REQUIRED": "public article URL", "TIME_REQUIRED": "~5 minutes",
     "COST": "$0", "REVERSIBLE": "yes (unpublish)",
     "AUTOMATION_AFTER_ACTION": "12-check verify → evidence record → measurement open → heartbeat diagnosis → reconcile → silent-unless-material",
     "EXPECTED_EVIDENCE": "public URL 200 + V1 markers + UTM; then sales-poll deltas",
     "STATUS": "APPROVED-AWAITING-CLICK"},
    {"GATE_ID": "SPEND-ANY", "ACTION": "any purchase/subscription/upgrade/traffic",
     "PLATFORM": "any", "WHY_HUMAN_REQUIRED": "$0 hard cap; financial authority is human-only",
     "EXACT_INPUT_REQUIRED": "per-item approval with cap (only if factory presents a priced case)",
     "TIME_REQUIRED": "n/a (no case pending)", "COST": "open-ended", "REVERSIBLE": "n/a",
     "AUTOMATION_AFTER_ACTION": "none pending", "EXPECTED_EVIDENCE": "receipt + capability",
     "STATUS": "CONDITIONAL (no live request)"},
    {"GATE_ID": "ACCOUNTS-ANY", "ACTION": "new accounts, credentials, OAuth, API keys",
     "PLATFORM": "any", "WHY_HUMAN_REQUIRED": "credential custody + ToS acceptance are human acts",
     "EXACT_INPUT_REQUIRED": "nothing today (no pending need)",
     "TIME_REQUIRED": "n/a", "COST": "$0+commitment", "REVERSIBLE": "varies",
     "AUTOMATION_AFTER_ACTION": "credential verification (read-only) + capability unlock",
     "EXPECTED_EVIDENCE": "new measurement/distribution path",
     "STATUS": "CONDITIONAL (no live request)"},
]


def compression() -> dict:
    return {"sessions_required": 1,
            "session": "paste f386 + reply URL (~5 min)",
            "covers": ["f386 publication", "URL delivery (same reply)"],
            "deferred": ["SPEND-ANY (no case)", "ACCOUNTS-ANY (no need)"],
            "verdict": "ONE_FOUNDER_SESSION unlocks the entire armed downstream"}


def build() -> dict:
    doc = {"at": datetime.now(timezone.utc).isoformat(),
           "DO_NOW": ["paste f386 into your Medium account", "reply here with the public URL"],
           "DO_NOT_DO": ["copy configs", "edit code", "inspect logs", "reconcile sales",
                         "run tests", "configure systems", "monitor HTTP", "check stats (factory polls)"],
           "AFTER_I_DO_THIS": ["URL verification (12 checks)", "evidence registration",
                               "measurement open", "heartbeat diagnosis", "reconciliation",
                               "silent-unless-material monitoring"],
           "WAITING_FOR_REALITY": ["visitors", "clicks", "buyers", "transactions",
                                   "attribution (no human can force these)"],
           "gates": GATES, "compression": compression()}
    CC_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc
