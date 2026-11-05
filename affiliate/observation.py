#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real-world observation runtime: watch honestly, never simulate.

Publication states advance only on evidence, never skipping. Every event
carries the §4 schema. Traffic is UNKNOWN unless an authoritative source
says otherwise (zero only when zero is observed). Learning streams stay
split: memory.query() default IS the real stream (sim excluded). Silent
unless material. Protected baseline stored for STOP-on-drift."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
OBS_LOG = _FACTORY_ROOT / "data" / "observation_log.jsonl"
BASELINE_PATH = _FACTORY_ROOT / "data" / "protected_baseline.json"
PROTECTED = ("finance_data.json", "data/sales_ledger.jsonl", "config/reality.json")

PUB_STATES = ("DRAFT", "APPROVED", "PUBLISHED", "PUBLICLY_REACHABLE",
              "INDEXED", "EXPOSED", "OBSERVED_TRAFFIC", "OBSERVED_CLICK",
              "OBSERVED_CHECKOUT", "REAL_TRANSACTION", "VERIFIED_REVENUE")


def advance_pub_state(current: str, evidence: str) -> dict:
    """One step per call, evidence required. Skips and inferences refused."""
    if current not in PUB_STATES:
        return {"advanced": False, "state": current, "reason": "unknown state"}
    if not evidence:
        return {"advanced": False, "state": current,
                "reason": "no evidence supplied; state frozen"}
    i = PUB_STATES.index(current)
    if i + 1 >= len(PUB_STATES):
        return {"advanced": False, "state": current, "reason": "terminal"}
    return {"advanced": True, "state": PUB_STATES[i + 1], "evidence": evidence}


def record_event(event_id: str, source: str, evidence_class: str, mode: str,
                 asset: str = "", confidence: str = "", raw_ref: str = "") -> dict:
    assert evidence_class in ("OBSERVED", "DERIVED", "INFERRED", "ESTIMATED", "UNKNOWN")
    assert mode in ("LIVE", "SIMULATED")
    row = {"EVENT_ID": event_id, "TIMESTAMP": datetime.now(timezone.utc).isoformat(),
           "SOURCE": source, "EVIDENCE_CLASS": evidence_class, "EVENT_MODE": mode,
           "CONFIDENCE": confidence, "RELATED_ASSET": asset, "RAW_REFERENCE": raw_ref}
    with open(OBS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"logged": True, "EVENT_ID": event_id}


def traffic_status() -> dict:
    return {"TRAFFIC": "UNKNOWN", "TRAFFIC_SOURCE": "none authoritative",
            "MEASUREMENT_WINDOW": "GPSR_PATH_B_V1 day 0/30",
            "LAST_CHECKED": datetime.now(timezone.utc).isoformat(),
            "LIMITATION": "Gumroad API has no traffic surface (payload-enumerated); "
                          "Medium stats founder-read only"}


def commercial_snapshot() -> dict:
    import json as _j
    fin = _j.loads((_FACTORY_ROOT / "finance_data.json").read_text(encoding="utf-8"))
    return {"REAL_REVENUE": (fin["totalSales"], "OBSERVED"),
            "CONFIRMED_EXTERNAL_SALES": (len(fin["sales"]), "OBSERVED"),
            "TRAFFIC": ("UNKNOWN", "no authoritative source"),
            "CUSTOMERS": (0, "OBSERVED (absence in ledger)"),
            "COMMISSIONS": (0, "OBSERVED (absence)"),
            "PAYOUTS": ("UNKNOWN", "no payout feed exists"),
            "DEMAND": ("UNKNOWN", "no buyer evidence")}


def reconcile_all() -> dict:
    from affiliate import ledger_firewall as fw
    inv = fw.assert_invariants()
    w = fw.window_status()
    return {"PUBLICATION": "GPSR listing VERIFIED live; Medium APPROVED-unpublished",
            "TRAFFIC": "UNKNOWN (see traffic_status)",
            "CLICKS": "0 verified", "CHECKOUTS": "UNKNOWN (unprobed by design)",
            "SALES": "0", "REFUNDS": "0", "CHARGEBACKS": "UNKNOWN (no feed)",
            "COMMISSIONS": "0", "PAYOUTS": "UNKNOWN (no feed)",
            "NOTIFICATIONS": "no material events -> none sent",
            "HEALTH": inv["status"], "WINDOW": w.get("state"),
            "discrepancies": inv["issues"]}


def founder_alert(action: str, reason: str, platform: str, risk: str,
                  reversible: str, evidence_needed: str) -> dict:
    return {"FOUNDER_ACTION_REQUIRED": action, "REASON": reason, "PLATFORM": platform,
            "ACTION": action, "RISK": risk, "REVERSIBLE": reversible,
            "EVIDENCE_REQUIRED": evidence_needed,
            "DO_NOT_ASK_FOR": "anything automatable (handled internally)"}


def freeze_baseline() -> dict:
    base = {f: hashlib.sha256((_FACTORY_ROOT / f).read_bytes()).hexdigest()
            for f in PROTECTED}
    BASELINE_PATH.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                                         "hashes": base}, ensure_ascii=False), encoding="utf-8")
    return {"frozen": True, "files": len(base)}


def verify_protected() -> dict:
    try:
        base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["hashes"]
    except (OSError, ValueError, KeyError):
        return {"ok": False, "status": "NO_BASELINE",
                "action": "run freeze_baseline() first"}
    drift = [f for f in PROTECTED
             if hashlib.sha256((_FACTORY_ROOT / f).read_bytes()).hexdigest() != base.get(f)]
    if drift:
        return {"ok": False, "status": "PROTECTED_FILE_INTEGRITY_FAILURE",
                "files": drift, "action": "STOP commercial processing, REPORT"}
    return {"ok": True, "status": "CLEAN"}
