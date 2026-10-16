#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unified operational memory: what was tested, worked, failed, why;
blocked channels, rejected opportunities, open unknowns, active
experiments, must-not-repeat rules. Append-only JSONL (history never
rewritten); query() filters by kind. No PII, no secrets, no revenue."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
MEMORY_PATH = _FACTORY_ROOT / "data" / "factory_memory.jsonl"

KINDS = ("lesson", "blocked_channel", "rejected_opportunity", "unknown",
         "experiment", "must_not_repeat", "decision")


def remember(kind: str, fact: str, evidence: str = "", simulated: bool = False) -> dict:
    if kind not in KINDS:
        return {"ok": False, "error": "unknown kind: %s" % kind}
    row = {"at": datetime.now(timezone.utc).isoformat(), "kind": kind,
           "fact": fact, "evidence": evidence, "simulated": bool(simulated)}
    with open(MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True}


def query(kind: str | None = None, contains: str = "",
          include_simulated: bool = False) -> list:
    """Simulated rows are excluded by default: the learner never trains on
    synthetic wins unless explicitly asked (with the flag visible)."""
    if not MEMORY_PATH.exists():
        return []
    out = []
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("simulated") and not include_simulated:
                continue
            if kind and r.get("kind") != kind:
                continue
            if contains and contains.lower() not in json.dumps(r).lower():
                continue
            out.append(r)
    return out


def seed() -> dict:
    """One-time seeding from established session evidence (idempotent:
    skips when the file already holds records)."""
    if query(include_simulated=True):
        return {"seeded": False, "reason": "memory already holds records"}
    items = [
        ("lesson", "keyword-tag Apollo search ranks fame, not fit (24/24 excluded)",
         "icp cycles 2026-09-21"),
        ("lesson", "structured geo+size filters work; industry constraint is next variable",
         "corrected cycle 17/20"),
        ("lesson", "services firms feel no GPSR pain (scope attaches to sellers)",
         "pain validation HOLD"),
        ("blocked_channel", "X organic: 402 depleted", "standing state"),
        ("blocked_channel", "LinkedIn automation: UA s.8.2 HIGH risk", "founder directive"),
        ("blocked_channel", "people search: Apollo 403 on free tier", "OBSERVED"),
        ("must_not_repeat", "never patch only one Pioneer entry point (hang root cause)",
         "sensing_link fix"),
        ("must_not_repeat", "never infer a stage from its predecessor (funnel discipline)",
         "standing rule"),
        ("experiment", "GPSR_PATH_B_V1 live, copy-only, $79, day 0/30", "test_record.json"),
        ("experiment", "EXP_001 link ACTIVE (systeme, UTM), undistributed", "registry + verification"),
        ("unknown", "all traffic layers (no API surface)", "exposure probe"),
        ("unknown", "buyer roles/intent/urgency (403)", "icp + pain cycles"),
        ("decision", "Gojiberry NOT_JUSTIFIED at current stage", "provider validation"),
        ("decision", "f386 Medium publish: QA passed, awaiting founder click", "gate ledger"),
    ]
    for kind, fact, ev in items:
        remember(kind, fact, ev)
    return {"seeded": True, "records": len(items)}
