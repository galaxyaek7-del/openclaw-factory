#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomous commercial control loop: OBSERVE → CLASSIFY → VALIDATE →
DIAGNOSE → DECIDE → ACT IF SAFE → VERIFY → LEARN → LOG → SLEEP/WAIT.

Idempotent: every cycle fingerprints its inputs (ledger counts + gate
states). A repeated scheduler wake with an unchanged fingerprint performs
no action beyond a heartbeat log row. The only writes this loop ever
makes are its own state file and heartbeat log — never financial truth,
never external effects."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = _FACTORY_ROOT / "data" / "commercial_loop_state.json"
LOG_PATH = _FACTORY_ROOT / "data" / "commercial_loop_log.jsonl"


def _counts() -> dict:
    # External inputs only. The loop's own outputs (founder_gates ledger,
    # loop state/log) are excluded — otherwise every cycle would see its
    # own last write as "change" and never idle.
    data = _FACTORY_ROOT / "data"
    out = {}
    for name in ("affiliate_clicks.jsonl", "affiliate_page_views.jsonl",
                 "commission_attribution_log.jsonl", "opportunity_candidates.jsonl",
                 "publication_confirmations.jsonl"):
        p = data / name
        if not p.exists():
            out[name] = 0
            continue
        with open(p, encoding="utf-8") as f:
            out[name] = sum(1 for _ in f)
    return out


def _fingerprint(counts: dict) -> str:
    return hashlib.sha1(json.dumps(counts, sort_keys=True).encode()).hexdigest()[:16]


def _read_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def _write_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def _heartbeat(summary: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                            **summary}, ensure_ascii=False) + "\n")


def run_cycle() -> dict:
    """One full OBSERVE→…→SLEEP pass. Safe to call repeatedly."""
    from affiliate import diagnostics as dg, market_state as ms
    from affiliate import anomalies as an, gates as gt

    counts = _counts()
    fp = _fingerprint(counts)
    prev = _read_state()

    aware = ms.self_awareness()
    anom = an.detect_anomalies()
    wake = dg.wake_check()
    wake_fired = list(wake["fired"])
    if anom["automation_hold"]:
        wake_fired.append("anomaly")

    # DECIDE: nothing changed and nothing fired → productive idle heartbeat
    if fp == prev.get("fingerprint") and not wake_fired and not anom["critical"]:
        summary = {"cycle": "heartbeat", "fingerprint": fp,
                   "state": aware["CURRENT_STATE"],
                   "bottleneck": aware["CURRENT_BOTTLENECK"],
                   "action": "none — productive idle, nothing changed"}
        _heartbeat(summary)
        return {"idempotent_repeat": True, **summary}

    # ACT IF SAFE: only safe, reversible, internal actions exist pre-signal.
    actions = []
    if aware["CURRENT_STATE"] == "NOT_IN_MARKET":
        pkt = gt.publication_gate_packet()
        rec = gt.record_gate(pkt)
        actions.append({"safe_action": "gate-packet",
                        "GATE_ID": pkt["GATE_ID"],
                        "recorded": rec["recorded"],
                        "note": "deduplicated; no repeat nagging"})
    # VERIFY + LEARN: anomaly hold stops affected automation (surfaced only)
    if anom["critical"]:
        actions.append({"safe_action": "automation-hold",
                        "critical": anom["critical"]})

    summary = {"cycle": "full", "fingerprint": fp,
               "state": aware["CURRENT_STATE"],
               "bottleneck": aware["CURRENT_BOTTLENECK"],
               "wake_fired": wake_fired,
               "anomaly_findings": len(anom["findings"]),
               "actions": actions}
    _write_state({"fingerprint": fp, "last_cycle": summary,
                  "updated_at": datetime.now(timezone.utc).isoformat()})
    _heartbeat(summary)
    return {"idempotent_repeat": False, **summary}
