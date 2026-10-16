#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Founder-gate packets: complete, deduplicated, prioritized, acknowledged.

A gate is surfaced only when human action is genuinely unavoidable. GATE_ID
is a stable hash of (action + context) so repeats dedupe; acknowledgment is
persisted in data/founder_gates.jsonl (append-only, non-financial, safe).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
GATES_PATH = _FACTORY_ROOT / "data" / "founder_gates.jsonl"


def make_packet(action_required: str, why_required: str, current_state: str,
                evidence: str, risk: str, cost: str, expected_effect: str,
                exact_human_action: str, post_action_verification: str,
                rollback: str = "N/A (no factory-side change to roll back)",
                blocking_impact: int = 5, evidence_confidence: int = 5,
                human_effort_1_5: int = 3) -> dict:
    gid = hashlib.sha1(("%s|%s" % (action_required, current_state)).encode()).hexdigest()[:12]
    return {
        "GATE_ID": gid,
        "ACTION_REQUIRED": action_required,
        "WHY_REQUIRED": why_required,
        "CURRENT_STATE": current_state,
        "EVIDENCE": evidence,
        "RISK": risk,
        "COST": cost,
        "EXPECTED_EFFECT": expected_effect,
        "EXACT_HUMAN_ACTION": exact_human_action,
        "POST_ACTION_VERIFICATION": post_action_verification,
        "ROLLBACK_IF_APPLICABLE": rollback,
        "priority_score": blocking_impact * evidence_confidence * (6 - human_effort_1_5),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _read_ledger() -> list:
    if not GATES_PATH.exists():
        return []
    out = []
    with open(GATES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def record_gate(packet: dict) -> dict:
    """Append-if-new (dedupe by GATE_ID). Returns {recorded: bool} —
    repeats are acknowledged without nagging."""
    for row in _read_ledger():
        if row.get("GATE_ID") == packet["GATE_ID"] and row.get("status") != "ACKNOWLEDGED":
            return {"recorded": False, "reason": "already pending",
                    "GATE_ID": packet["GATE_ID"]}
    with open(GATES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"GATE_ID": packet["GATE_ID"], "status": "PENDING",
                            "packet": packet}, ensure_ascii=False) + "\n")
    return {"recorded": True, "GATE_ID": packet["GATE_ID"]}


def acknowledge_gate(gate_id: str) -> dict:
    """Persist founder acknowledgment (append-only; history preserved)."""
    with open(GATES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"GATE_ID": gate_id, "status": "ACKNOWLEDGED",
                            "at": datetime.now(timezone.utc).isoformat()},
                           ensure_ascii=False) + "\n")
    return {"ok": True, "GATE_ID": gate_id}


def supersede_gate(gate_id: str, by_gate_id: str, reason: str) -> dict:
    """Mark a duplicate gate SUPERSEDED (history preserved, never surfaced).
    Reversible: the row stays in the ledger with its reason."""
    with open(GATES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"GATE_ID": gate_id, "status": "SUPERSEDED",
                            "superseded_by": by_gate_id, "reason": reason,
                            "at": datetime.now(timezone.utc).isoformat()},
                           ensure_ascii=False) + "\n")
    return {"ok": True, "GATE_ID": gate_id, "superseded_by": by_gate_id}


def pending_gates() -> list:
    """Pending packets minus acknowledged/superseded ones, priority-sorted."""
    rows = _read_ledger()
    acked = {r["GATE_ID"] for r in rows if r.get("status") == "ACKNOWLEDGED"}
    superseded = {r["GATE_ID"] for r in rows if r.get("status") == "SUPERSEDED"}
    done = acked | superseded
    seen = set()
    out = []
    for r in rows:
        gid = r.get("GATE_ID")
        if r.get("status") == "PENDING" and gid not in done and gid not in seen:
            seen.add(gid)
            out.append(r["packet"])
    out.sort(key=lambda p: p.get("priority_score", 0), reverse=True)
    return out


def publication_gate_packet() -> dict:
    return make_packet(
        action_required="Publish ONE surface (Medium draft ready)",
        why_required="No public surface exists; no market measurement is possible",
        current_state="NOT_IN_MARKET",
        evidence="drafts/medium_gpsr_etsy_guide.md on disk; "
                 "data/publication_confirmations.jsonl absent",
        risk="LOW — single article, reversible (unpublishable)",
        cost="$0",
        expected_effect="Opens EXPOSURE→VIEW→CLICK measurement; starts first window",
        exact_human_action="Publish the Medium draft from your account; confirm back here",
        post_action_verification="Factory checks confirmation record + public accessibility",
        blocking_impact=5, evidence_confidence=5, human_effort_1_5=2)
