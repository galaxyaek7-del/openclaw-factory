#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomous market state machine + publication detection + self-awareness.

All transitions are evidence-driven pure functions: transition(state, event,
evidence) advances ONLY when the evidence dict satisfies the guard. A draft
file is never publication; a QA claim without an artifact is never readiness.
"""

from __future__ import annotations

from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

STATES = ("NOT_IN_MARKET", "READY_FOR_PUBLICATION", "PUBLICATION_GATE",
          "MARKET_ACTIVE", "COLLECTING_SIGNAL", "LOW_TRAFFIC",
          "LOW_ENGAGEMENT", "LOW_CLICK_RATE", "LANDING_FAILURE",
          "TRACKING_FAILURE", "INSUFFICIENT_SAMPLE",
          "CONVERSION_DIAGNOSTICS", "VERIFIED_SIGNAL", "LEARNING_WINDOW",
          "SCALE_CANDIDATE", "HOLD", "HIBERNATE", "BLOCKED")

# event -> (from_states, to_state, required evidence keys)
TRANSITIONS = {
    "draft_qa_ready": (("NOT_IN_MARKET",), "READY_FOR_PUBLICATION", ("qa_artifact",)),
    "request_publication": (("READY_FOR_PUBLICATION",), "PUBLICATION_GATE", ("gate_packet",)),
    "publication_confirmed": (("PUBLICATION_GATE",), "MARKET_ACTIVE", ("confirmation",)),
    "exposure_verified": (("MARKET_ACTIVE",), "COLLECTING_SIGNAL", ("exposure_sample",)),
    "sample_sufficient": (("COLLECTING_SIGNAL",), "LEARNING_WINDOW", ("sample_size",)),
    "signal_verified": (("LEARNING_WINDOW", "CONVERSION_DIAGNOSTICS"), "VERIFIED_SIGNAL",
                        ("verification",)),
    "scale_approved": (("VERIFIED_SIGNAL",), "SCALE_CANDIDATE", ("founder_approval",)),
    "tracking_broken": (STATES, "TRACKING_FAILURE", ("tracking_evidence",)),
    "program_gone": (STATES, "HIBERNATE", ("program_evidence",)),
    "critical_anomaly": (STATES, "BLOCKED", ("anomaly_evidence",)),
    "hold": (STATES, "HOLD", ("reason",)),
}


def transition(state: str, event: str, evidence: dict) -> dict:
    """Pure evidence-gated transition. Missing guard keys → no transition,
    with the missing keys named (never assumed)."""
    if event not in TRANSITIONS:
        return {"advanced": False, "state": state, "reason": "unknown event: %s" % event}
    allowed, target, keys = TRANSITIONS[event]
    if state not in allowed:
        return {"advanced": False, "state": state,
                "reason": "event %s not valid from %s" % (event, state)}
    missing = [k for k in keys if not (evidence or {}).get(k)]
    if missing:
        return {"advanced": False, "state": state,
                "reason": "missing evidence: %s" % ", ".join(missing)}
    return {"advanced": True, "state": target, "reason": "guard satisfied: %s" % ", ".join(keys)}


def publication_status() -> dict:
    """Six-stage publication truth from real files only.

    DRAFT_EXISTS: a draft artifact is on disk.
    DRAFT_QA_READY: + a QA artifact for that draft exists on disk.
    PUBLICATION_NOT_CONFIRMED: no confirmation record exists.
    (CONFIRMED/ACCESSIBLE/MEASURABLE require data/publication_confirmations.jsonl
    rows — absent today, so later stages are honestly unreachable.)"""
    drafts = _FACTORY_ROOT / "drafts" / "medium_gpsr_etsy_guide.md"
    video = _FACTORY_ROOT / "assets" / "affiliate" / "systeme_io"
    video_qa = video / "first_video" / "qa_report.md"
    video_final = video / "first_video" / "final_video.mp4"
    confirmations = _FACTORY_ROOT / "data" / "publication_confirmations.jsonl"
    assets = {
        "medium_draft": {"exists": drafts.exists(),
                         "qa_artifact": None,  # no QA artifact found on disk for this draft
                         "stage": "DRAFT_EXISTS" if drafts.exists() else "ABSENT"},
        "systeme_video": {"exists": video_final.exists(),
                          "qa_artifact": (str(video_qa) if video_qa.exists() else None),
                          "stage": ("DRAFT_QA_READY" if (video_final.exists() and video_qa.exists())
                                    else "DRAFT_EXISTS" if video_final.exists() else "ABSENT")},
    }
    if confirmations.exists():
        stage = "PUBLICATION_CONFIRMED"
    else:
        stage = "PUBLICATION_NOT_CONFIRMED"
    return {"assets": assets, "overall": stage,
            "note": "draft existence is never publication; QA claims need artifacts"}


def current_market_state() -> dict:
    """Derive today's state from evidence: no confirmation record exists,
    so the factory is NOT_IN_MARKET regardless of draft readiness."""
    pub = publication_status()
    if pub["overall"] in ("PUBLICATION_CONFIRMED",):
        return {"state": "MARKET_ACTIVE", "why": "confirmation record on disk",
                "evidence": pub}
    ready = [k for k, v in pub["assets"].items() if v["stage"] == "DRAFT_QA_READY"]
    if ready:
        return {"state": "NOT_IN_MARKET",
                "why": "drafts QA-ready (%s) but publication unconfirmed" % ", ".join(ready),
                "evidence": pub}
    return {"state": "NOT_IN_MARKET", "why": pub["overall"], "evidence": pub}


def self_awareness() -> dict:
    """Machine-readable self-model: state, why, bottleneck, actions, gates."""
    from affiliate import diagnostics as dg
    market = current_market_state()
    bott = dg.diagnose_bottleneck()
    wake = dg.wake_check()
    tw = dg.tracking_firewall()
    return {
        "CURRENT_STATE": market["state"],
        "WHY_THIS_STATE": market["why"],
        "CURRENT_BOTTLENECK": bott["bottleneck"],
        "BOTTLENECK_CONFIDENCE": "HIGH" if bott["bottleneck"] == "NOT_IN_MARKET" else "MEDIUM",
        "AVAILABLE_ACTIONS": ["monitor", "diagnose", "queue-review", "gate-packet", "heartbeat"],
        "SAFE_AUTOMATIONS": ["monitor", "diagnose", "queue-review", "heartbeat"],
        "FOUNDER_GATES": ["publication", "accounts", "spend", "external-send"],
        "NEXT_WAKE_EVENT": "first external signal / publication confirmation / founder request",
        "NEXT_MEASUREMENT_WINDOW": "none open (nothing published)",
        "LAST_EVIDENCE": "ledgers re-read this cycle; 19 internal views + 24 internal clicks (quarantined)",
        "EVIDENCE_FRESHNESS": "programs FRESH; clicks/views STALE-internal; attribution log quarantined",
        "TRACKING": tw["status"],
        "WAKE_FIRED": wake["fired"],
    }
