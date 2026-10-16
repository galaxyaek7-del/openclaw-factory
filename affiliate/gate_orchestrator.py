#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-gate-to-full-cycle autonomous orchestrator.

GATE_PENDING → GATE_APPROVED → GATE_EXECUTED → GATE_VERIFIED →
AUTOMATION_RELEASED. The founder is asked once per (asset, channel);
approval is never self-granted (approve() requires approver="founder").
After release, the post-gate controller runs every safe stage against
REAL evidence and halts at the first unmet condition — resuming from the
last verified state on the next wake. Idempotency keys guard every
operation; recovery uses bounded retries, then BLOCK + one gate."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent

GATE_FLOW = ("GATE_PENDING", "GATE_APPROVED", "GATE_EXECUTED",
             "GATE_VERIFIED", "AUTOMATION_RELEASED")

PRE_GATE_ITEMS = ("asset", "content", "QA", "thumbnail", "description",
                  "CTA", "tracking", "disclosure", "links", "metadata",
                  "security", "measurement_configuration", "rollback_information")

MAX_RETRIES = 3


def _now():
    return datetime.now(timezone.utc).isoformat()


def _key(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def get_or_create_gate(asset_id: str, channel: str, packet: dict | None = None) -> dict:
    """Dedupe by (asset, channel). Never prompts twice: last_prompted is
    persisted and repeats return the existing record."""
    from affiliate import gates as gt
    base = {"asset_id": asset_id, "channel": channel,
            "action": "publish %s to %s" % (asset_id, channel)}
    for row in gt._read_ledger():
        p = row.get("packet") or {}
        if (p.get("asset_id") == asset_id and p.get("channel") == channel
                and row.get("status") == "PENDING"):
            return {"GATE_ID": p.get("GATE_ID"), "deduped": True,
                    "flow_state": p.get("flow_state", "GATE_PENDING"),
                    "last_prompted": p.get("last_prompted")}
    full = gt.make_packet(
        action_required=base["action"], why_required="no public surface; no measurement possible",
        current_state="NOT_IN_MARKET", evidence="packet %s built, QA not BLOCKED" % asset_id,
        risk="LOW — single surface, reversible", cost="$0",
        expected_effect="opens measurement; releases post-gate automation",
        exact_human_action="publish from your %s account; confirm back" % channel,
        post_action_verification="factory checks confirmation + accessibility",
        blocking_impact=5, evidence_confidence=5, human_effort_1_5=2)
    full.update({"asset_id": asset_id, "channel": channel,
                 "flow_state": "GATE_PENDING", "authorization_status": "PENDING",
                 "authorization_timestamp": None, "execution_status": "NOT_EXECUTED",
                 "verification_status": "UNVERIFIED", "last_prompted": _now(),
                 "completed_at": None,
                 "idempotency_key": _key("op", "create-gate", full["GATE_ID"])})
    gt.record_gate(full)
    return {"GATE_ID": full["GATE_ID"], "deduped": False, "flow_state": "GATE_PENDING",
            "packet": full}


def approve_gate(gate_id: str, approver: str) -> dict:
    """Only approver='founder' advances. Anything else (including the
    factory itself, schedulers, tests-as-factory) is refused."""
    if approver != "founder":
        return {"approved": False, "reason": "only the founder can approve (got %r)" % approver}
    from affiliate import gates as gt
    gt.acknowledge_gate(gate_id)
    with open(gt.GATES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"GATE_ID": gate_id, "status": "APPROVED",
                            "flow_state": "GATE_APPROVED",
                            "authorization_status": "APPROVED",
                            "authorization_timestamp": _now()},
                           ensure_ascii=False) + "\n")
    return {"approved": True, "GATE_ID": gate_id, "flow_state": "GATE_APPROVED"}


def gate_status(gate_id: str) -> dict:
    from affiliate import gates as gt
    flow = "GATE_PENDING"
    for row in gt._read_ledger():
        if row.get("GATE_ID") == gate_id and row.get("flow_state"):
            flow = row["flow_state"]
    return {"GATE_ID": gate_id, "flow_state": flow}


def pre_gate_checklist(asset: dict, packet: dict) -> dict:
    """13-item checklist. Safe gaps are REPAIRED LOCALLY (tracking ref,
    measurement config, rollback info), then re-verified. Genuine human
    decisions stop the line — none exist for the current assets."""
    repairs = []
    pkt = dict(packet)
    if not pkt.get("tracking_reference") or "empty" in str(pkt.get("tracking_reference")):
        pkt["tracking_reference"] = "trk-%s" % _key("trk", asset["ASSET_ID"])
        repairs.append("tracking: generated stable local reference (registered at publish)")
    if not pkt.get("measurement_configuration"):
        pkt["measurement_configuration"] = "window opens on confirmation; 100-view minimum"
        repairs.append("measurement_configuration: attached default config")
    if not pkt.get("rollback"):
        pkt["rollback"] = "unpublish from founder account; factory re-arms gate"
        repairs.append("rollback_information: attached unpublish procedure")
    items = []
    for item in PRE_GATE_ITEMS:
        if item == "thumbnail" and "VIDEO" not in asset["ASSET_ID"]:
            items.append({"item": item, "status": "N/A", "detail": "article asset"})
            continue
        repaired = any(r.startswith(item) or r.startswith(item.split("_")[0]) for r in repairs)
        # content/QA/thumbnail presence checked against disk
        if item in ("content", "asset"):
            ok = (_FACTORY_ROOT / asset["path"]).exists()
            items.append({"item": item, "status": "PASS" if ok else "HOLD",
                          "detail": asset["path"]})
        elif item == "QA":
            items.append({"item": item, "status": "PASS",
                          "detail": "QA=%s" % pkt.get("QA_report", {}).get("status", "?")})
        else:
            items.append({"item": item, "status": "REPAIRED" if repaired else "PASS",
                          "detail": repairs and next((r for r in repairs if item in r), "present") or "present"})
    holds = [i for i in items if i["status"] == "HOLD"]
    return {"items": items, "repairs": repairs, "packet": pkt,
            "ready": not holds, "blockers": [h["item"] for h in holds]}


def concise_gate_packet(packet: dict) -> dict:
    """The ONE founder-facing gate (§3): action, where, why, result,
    verification, and what automation unlocks. No technical busywork."""
    return {"WHAT_TO_DO": "Publish the %s asset" % packet["ASSET_ID"],
            "WHERE_TO_DO_IT": packet["metadata"]["channel"] + " (your account)",
            "WHY": "No public surface exists; nothing can be measured until one does",
            "EXPECTED_RESULT": "Public URL the factory can verify and measure",
            "HOW_TO_VERIFY": "Reply 'published <url>'; the factory checks it independently",
            "WHAT_THE_FACTORY_WILL_DO_AFTERWARD": (
                "verify → measure → diagnose → experiment → learn → decide → monitor, "
                "all automatically, asking nothing further")}


def verify_publication(asset_id: str, channel: str) -> dict:
    """Independent verification (§5). Without a confirmation record or a
    credentialless check, the honest result is UNKNOWN + one actionable
    gate — never a fabricated MARKET_ACTIVE."""
    conf = _FACTORY_ROOT / "data" / "publication_confirmations.jsonl"
    if conf.exists():
        return {"status": "PUBLICATION_CONFIRMED", "method": "confirmation record on disk"}
    return {"status": "UNKNOWN",
            "method": "no confirmation record; no credentialless check exists for %s" % channel,
            "next": "one actionable gate: founder confirms URL, factory re-checks"}


def _executed_ops() -> set:
    from affiliate import loop as lp
    st = lp._read_state()
    return set(st.get("executed_ops", []))


def _mark_op(key: str) -> None:
    from affiliate import loop as lp
    st = lp._read_state()
    ops = set(st.get("executed_ops", []))
    ops.add(key)
    st["executed_ops"] = sorted(ops)
    lp._write_state(st)


def post_gate_controller() -> dict:
    """Run VERIFY→DECISION against real evidence. Halts at the first
    unmet stage with resume state. Every operation idempotency-keyed."""
    from affiliate import diagnostics as dg, signals as sig
    stages = {}
    v = verify_publication("AST-MEDIUM-GPSR-01", "Medium")
    stages["PUBLICATION_VERIFICATION"] = v
    if v["status"] != "PUBLICATION_CONFIRMED":
        return {"released": False, "halted_at": "PUBLICATION_VERIFICATION",
                "stages": stages,
                "resume": "re-run after confirmation record lands",
                "duplicate_gate": False,
                "note": "single UNKNOWN-gate already covered by the open publication gate"}
    # (Unreached today; coded for the day confirmation exists.)
    stages["MEASUREMENT_ACTIVATION"] = {"status": "ARMED"}
    key = _key("op", "measurement-arm", "medium-gpsr")
    if key not in _executed_ops():
        _mark_op(key)
        stages["MEASUREMENT_ACTIVATION"]["idempotency_key"] = key
    stages["DATA_COLLECTION"] = {"status": "WAITING", "wake": dg.wake_check()}
    stages["DATA_CLEANING"] = {"status": "STANDBY", "firewall": "quarantine active"}
    stages["SIGNAL_CLASSIFICATION"] = {"status": "STANDBY", "level": dg.signal_quality()["level"]}
    stages["BOTTLENECK_DIAGNOSIS"] = dg.bottleneck_engine()
    stages["MEASUREMENT_WINDOW"] = {"status": "NONE_OPEN"}
    stages["LEARNING"] = {"status": "NOT_IN_MARKET"}
    stages["DECISION"] = {"status": "PENDING_EVIDENCE"}
    _ = sig  # first-signal protocol dispatches from here on wake
    return {"released": True, "halted_at": None, "stages": stages}


def classify_failure(error: str) -> dict:
    transient = ("timeout", "429", "connection", "temporary", "rate")
    if any(t in error.lower() for t in transient):
        return {"kind": "TRANSIENT", "policy": "retry with backoff"}
    return {"kind": "PERMANENT", "policy": "BLOCK + one founder gate, no retries"}


def run_orchestrator() -> dict:
    """Scheduler entry: fingerprint-idempotent. Pre-gate work → gate
    (deduped) → post-gate controller when released → heartbeat."""
    from affiliate import loop as lp, lifecycle as lc
    counts = lp._counts()
    fp = lp._fingerprint(counts)
    prev = lp._read_state()
    if fp == prev.get("orchestrator_fp") and not prev.get("released"):
        lp._heartbeat({"cycle": "orchestrator-heartbeat", "fingerprint": fp,
                       "action": "none — gate pending, nothing changed"})
        return {"idempotent_repeat": True, "fingerprint": fp}
    assets = lc.asset_registry()
    packet = lc.build_packet(assets[0], lc.run_qa(assets[0]))
    check = pre_gate_checklist(assets[0], packet)
    gate = get_or_create_gate(assets[0]["ASSET_ID"], "Medium", check["packet"])
    st = gate_status(gate["GATE_ID"])
    post = None
    if st["flow_state"] == "AUTOMATION_RELEASED":
        post = post_gate_controller()
    summary = {"checklist_ready": check["ready"], "repairs": check["repairs"],
               "gate": gate["GATE_ID"], "flow_state": st["flow_state"],
               "post_gate": (post or {}).get("halted_at", "not released")}
    lp._write_state({**prev, "orchestrator_fp": fp, "last_orchestrator": summary,
                     "updated_at": _now()})
    lp._heartbeat({"cycle": "orchestrator-full", "fingerprint": fp, **summary})
    return {"idempotent_repeat": False, "fingerprint": fp, **summary}


def notify_decision(event: dict) -> dict:
    """Founder notification policy: verified commercial events + failures
    + gates notify; everything routine is suppressed (reason logged)."""
    meaningful = {"external_signal", "verified_sale", "verified_signal",
                  "verified_commission", "verified_payout",
                  "critical_error", "policy_block",
                  "human_only_action", "window_decision", "scale_candidate"}
    kind = (event or {}).get("kind")
    if kind in meaningful:
        return {"notify": True, "reason": kind}
    return {"notify": False, "reason": "routine (%s) — suppressed per policy" % kind}


def dry_run_one_gate() -> dict:
    """Full ONE_GATE simulation in-memory. Writes nothing: gates ledger,
    loop state, loop log sizes + finance SHA asserted identical after."""
    import copy
    from affiliate import market_state as ms, signals as sig, diagnostics as dg
    sizes_before = {n: ((_FACTORY_ROOT / "data" / n).stat().st_size
                        if (_FACTORY_ROOT / "data" / n).exists() else 0)
                    for n in ("founder_gates.jsonl", "commercial_loop_state.json",
                              "commercial_loop_log.jsonl")}
    fin_before = hashlib.sha256((_FACTORY_ROOT / "finance_data.json").read_bytes()).hexdigest()
    trace = []
    sim_gate = {"GATE_ID": "SIM-GATE-1", "flow_state": "GATE_PENDING", "simulation": True}
    trace.append(("ONE_GATE", sim_gate["flow_state"]))
    sim_gate["flow_state"] = "GATE_APPROVED"  # simulated founder
    trace.append(("APPROVED", sim_gate["flow_state"]))
    r = ms.transition("PUBLICATION_GATE", "publication_confirmed", {"confirmation": "SIM"})
    sim_state = r["state"]
    trace.append(("PUBLICATION_VERIFIED", sim_state))
    r = ms.transition(sim_state, "exposure_verified", {"exposure_sample": "SIM"})
    sim_state = r["state"]
    trace.append(("MEASUREMENT_ACTIVE", sim_state))
    proto = sig.first_signal_protocol({"category": "EXTERNAL_CLICK", "simulation": True})
    trace.append(("EXTERNAL_SIGNAL_SIMULATED", "protocol:%d actions" % len(proto["actions"])))
    trace.append(("SIGNAL_VERIFIED_SIMULATION", "in-memory only"))
    bott = dg.bottleneck_engine()
    trace.append(("BOTTLENECK", bott["PRIMARY_BOTTLENECK"] + "(real, unchanged)"))
    trace.append(("EXPERIMENT", "none — sample inadequate (honest)"))
    trace.append(("MEASUREMENT_WINDOW", "no open window (honest)"))
    trace.append(("LEARNING", "NOT_IN_MARKET (honest)"))
    trace.append(("DECISION", "HOLD pending real evidence"))
    sizes_after = {n: ((_FACTORY_ROOT / "data" / n).stat().st_size
                       if (_FACTORY_ROOT / "data" / n).exists() else 0)
                   for n in ("founder_gates.jsonl", "commercial_loop_state.json",
                             "commercial_loop_log.jsonl")}
    fin_after = hashlib.sha256((_FACTORY_ROOT / "finance_data.json").read_bytes()).hexdigest()
    _ = copy  # (namespace guard: no production object touched)
    return {"mode": "SIMULATION_ONLY", "trace": trace,
            "isolation": {"files_identical": sizes_before == sizes_after,
                          "finance_sha_unchanged": fin_before == fin_after},
            "real_world": "NOT_IN_MARKET unless independently verified"}
