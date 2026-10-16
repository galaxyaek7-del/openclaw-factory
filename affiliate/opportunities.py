#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Opportunity queue (append-only JSONL, shared file with prior intel).

Reuses data/opportunity_candidates.jsonl (existing entries keep their own
schema and are never rewritten). New entries must carry the full required
field set; the five-evidence-gate check (PROBLEM + BUYER + PRODUCT +
AFFILIATE + CONTENT evidence) decides whether an entry may become ACTIVE.
Max active opportunities enforced (default 5) to prevent backlog sprawl.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE_PATH = _FACTORY_ROOT / "data" / "opportunity_candidates.jsonl"

REQUIRED_FIELDS = ("id", "problem", "target_buyer", "product",
                   "program_status", "evidence_status", "content_angle",
                   "commercial_rationale", "risks", "founder_gates",
                   "next_safe_test")

EVIDENCE_GATES = ("problem_evidence", "buyer_evidence", "product_evidence",
                  "affiliate_evidence", "content_angle_evidence")

MAX_ACTIVE = 5


def _now():
    return datetime.now(timezone.utc).isoformat()


def read_queue(queue_path=None) -> list:
    """Read-only; tolerates legacy entries with partial schemas."""
    path = Path(queue_path) if queue_path else DEFAULT_QUEUE_PATH
    out = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


PLACEHOLDERS = {"x", "tbd", "n/a", "na", "none", "todo", "-", "?"}


def _real_evidence(value) -> bool:
    s = str(value or "").strip().lower()
    return len(s) >= 12 and s not in PLACEHOLDERS


SYNTHETIC_MODES = ("TEST", "SIMULATION")


def evidence_gate_check(entry: dict, mode: str = "REAL") -> dict:
    """All five evidence gates must hold REAL evidence (>=12 chars,
    no placeholders) for ACTIVE. Missing/placeholder gates are named,
    never assumed.

    mode="TEST"/"SIMULATION" (BKL-003, 2026-10-16) exists only so a labelled
    simulation can walk the pipeline. It applies ONLY when the entry itself
    carries SIMULATED=True, and the result always says real_evidence=False.
    Asking for a synthetic mode on an unlabelled entry falls back to the
    strict check, so the mode can never be used to wave real candidates
    through. add_opportunity() and assess_opportunity_status() always use
    the strict default."""
    if mode in SYNTHETIC_MODES and entry.get("SIMULATED") is True:
        return {"pass": True, "missing": [], "mode": mode, "real_evidence": False,
                "warning": "SYNTHETIC_EVIDENCE_ACCEPTED"}
    missing = [g for g in EVIDENCE_GATES if not _real_evidence(entry.get(g))]
    return {"pass": not missing, "missing": missing, "mode": "REAL",
            "real_evidence": not missing}


EVIDENCE_RECORD_FIELDS = ("source", "timestamp", "confidence", "data_url")


def validate_evidence(evidence: dict, mode: str = "REAL") -> dict:
    """Validate one measurement-evidence record (BKL-003, 2026-10-16).

    REAL: every field in EVIDENCE_RECORD_FIELDS must be present and truthy
    (so confidence 0.0 - "no data" - is not valid evidence), and text fields
    must not be placeholders. TEST/SIMULATION: accepted, but always marked
    real_evidence=False so no caller can mistake it for real data."""
    if mode in SYNTHETIC_MODES:
        return {"valid": True, "mode": mode, "warning": "SYNTHETIC_EVIDENCE_ACCEPTED",
                "real_evidence": False}
    evidence = evidence if isinstance(evidence, dict) else {}
    missing = [f for f in EVIDENCE_RECORD_FIELDS
               if f not in evidence or not evidence[f]
               or (isinstance(evidence[f], str) and evidence[f].strip().lower() in PLACEHOLDERS)]
    if missing:
        return {"valid": False, "mode": "REAL", "missing_fields": missing,
                "error": "EVIDENCE_INCOMPLETE"}
    return {"valid": True, "mode": "REAL", "real_evidence": True}


def assess_opportunity_status(entry: dict, program_available: bool = True) -> dict:
    """Pure reassessment of one queue entry against current evidence.

    ACTIVE: all five evidence gates still PRESENT and program available.
    DOWNGRADE: some gate weakened (present-but-stale/partial) — entry names it.
    HOLD: a gate's evidence disappeared (falsy now).
    HIBERNATE: program itself unavailable, regardless of evidence.
    Read-only: returns the verdict, never rewrites the ledger."""
    if not program_available:
        return {"verdict": "HIBERNATE",
                "reason": "program unavailable — evidence frozen, not deleted"}
    gate = evidence_gate_check(entry)
    if gate["pass"]:
        weakened = [g for g in (entry.get("weakened_gates") or []) if g in EVIDENCE_GATES]
        if weakened:
            return {"verdict": "DOWNGRADE",
                    "reason": "weakened (not gone): %s" % ", ".join(weakened)}
        return {"verdict": "ACTIVE", "reason": "all five evidence gates hold"}
    return {"verdict": "HOLD", "reason": "missing: %s" % ", ".join(gate["missing"])}


def add_opportunity(entry: dict, queue_path=None, max_active: int = MAX_ACTIVE) -> dict:
    """Validate + append. Rejects incomplete entries and caps active ones.
    Never edits existing rows."""
    for field in REQUIRED_FIELDS:
        if not str(entry.get(field, "") or "").strip():
            return {"ok": False, "error": "missing required field: %s" % field}
    gate = evidence_gate_check(entry)
    active = sum(1 for e in read_queue(queue_path)
                 if str(e.get("status", "")).upper() == "ACTIVE")
    if gate["pass"] and active >= max_active:
        return {"ok": False, "error": "active cap reached (%d); hibernate one first" % max_active}
    record = dict(entry)
    record["status"] = "ACTIVE" if gate["pass"] else "OPPORTUNITY_CANDIDATE"
    record["gate_check"] = gate
    record["ts"] = _now()
    path = Path(queue_path) if queue_path else DEFAULT_QUEUE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "status": record["status"], "id": record["id"]}
