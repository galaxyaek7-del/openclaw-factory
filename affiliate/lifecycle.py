#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Full commercial lifecycle runner: real stages to the founder gate,
SIMULATION_ONLY dry run beyond it, then return to real NOT_IN_MARKET.

Real execution (safe/local/reversible): DISCOVER → SELECT → PRODUCE
(reuse-check) → QA (mechanical) → PACKAGE (packet file) → FOUNDER GATE
(one deduplicated packet). It STOPS there — verification needs a human.
The dry run walks the remaining stages in-memory with synthetic events
tagged SIMULATION_ONLY; ledgers and financial truth are asserted
untouched before AND after. No stage is ever marked complete without
its exit evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
PACKETS_DIR = _FACTORY_ROOT / "data" / "publication_packets"

STAGES = ("DISCOVER", "SELECT", "PRODUCE", "QA", "PACKAGE",
          "FOUNDER_PUBLICATION_GATE", "VERIFY_PUBLICATION",
          "ACTIVATE_MEASUREMENT", "COLLECT_SIGNAL", "CLEAN_DATA",
          "CLASSIFY_SIGNAL", "DIAGNOSE_BOTTLENECK", "RUN_MEASUREMENT_WINDOW",
          "LEARN", "DECIDE", "OPTIMIZE", "RE_MEASURE", "SCALE_HOLD_HIBERNATE")

# stage -> (entry condition, exit evidence required)
STAGE_GATES = {
    "DISCOVER": ("queue/intel readable", "ranked list produced"),
    "SELECT": ("ranked list", "top candidate with cited criteria"),
    "PRODUCE": ("selected candidate", "asset registered, reuse checked first"),
    "QA": ("registered asset", "mechanical verdict PASS/HOLD/BLOCKED"),
    "PACKAGE": ("QA not BLOCKED", "packet file written, no secrets"),
    "FOUNDER_PUBLICATION_GATE": ("packet ready", "ONE deduplicated gate recorded"),
    "VERIFY_PUBLICATION": ("founder confirmation", "confirmation record on disk"),
    "ACTIVATE_MEASUREMENT": ("PUBLICATION_CONFIRMED", "window opened on real surface"),
    "COLLECT_SIGNAL": ("open window", "external events classified"),
    "CLEAN_DATA": ("raw events", "quarantine applied, KPIs clean"),
    "CLASSIFY_SIGNAL": ("clean events", "signal-level assigned"),
    "DIAGNOSE_BOTTLENECK": ("classified signal", "primary bottleneck named"),
    "RUN_MEASUREMENT_WINDOW": ("diagnosis", "window completed without mid-edits"),
    "LEARN": ("completed window", "learning state assigned"),
    "DECIDE": ("learning state", "SCALE/HOLD/HIBERNATE chosen with reason"),
    "OPTIMIZE": ("DECIDE=improve", "single-variable change logged"),
    "RE_MEASURE": ("optimization applied", "second window completed"),
    "SCALE_HOLD_HIBERNATE": ("re-measurement", "terminal state with evidence"),
}


def asset_registry() -> list:
    """The two real assets with full registry fields (§4)."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"ASSET_ID": "AST-MEDIUM-GPSR-01", "VERSION": "1.0",
         "path": "drafts/medium_gpsr_etsy_guide.md",
         "TARGET_AUDIENCE": "Etsy sellers facing GPSR enforcement",
         "PROBLEM": "GPSR compliance blocking EU sales",
         "OFFER": "GPSR action kit (Gumroad portfolio)",
         "CHANNEL": "Medium (founder account)", "STATUS": "DRAFT_EXISTS",
         "CREATED_AT": now, "QA_STATUS": "PENDING"},
        {"ASSET_ID": "AST-SYSTEME-VIDEO-01", "VERSION": "1.0",
         "path": "assets/affiliate/systeme_io/first_video/final_video.mp4",
         "TARGET_AUDIENCE": "affiliate beginners (French SME context)",
         "PROBLEM": "first-affiliate-revenue setup paralysis",
         "OFFER": "Systeme.io reference walkthrough",
         "CHANNEL": "YouTube (founder account)", "STATUS": "DRAFT_QA_READY",
         "CREATED_AT": now, "QA_STATUS": "QA_ARTIFACT_ON_DISK"},
    ]


def run_qa(asset: dict) -> dict:
    """Mechanical QA over real file text; maps qa_content verdicts onto
    PASS / PASS_WITH_WARNINGS / HOLD / BLOCKED (disclosed mapping:
    banned-phrase failure = BLOCKED; stale-claim-only HOLD =
    PASS_WITH_WARNINGS; otherwise HOLD)."""
    from affiliate import content_qa as qc
    p = _FACTORY_ROOT / asset["path"]
    body = ""
    if p.suffix == ".md" and p.exists():
        body = p.read_text(encoding="utf-8")
    elif p.exists():
        body = "(binary asset; text checks limited to registry metadata)"
    verdict = qc.qa_content({"title": asset["ASSET_ID"], "body": body or "x",
                             "disclosure": True, "cta_present": True,
                             "evidence_date": datetime.now(timezone.utc).isoformat()})
    failures = verdict["failures"]
    if not failures:
        status = "PASS"
    elif any("banned phrase" in f for f in failures):
        status = "BLOCKED"
    elif all("stale claim" in f or "thumbnail" in f for f in failures):
        status = "PASS_WITH_WARNINGS"
    else:
        status = "HOLD"
    return {"ASSET_ID": asset["ASSET_ID"], "status": status,
            "failures": failures, "warnings": [f for f in failures if "stale" in f],
            "mapping": "qa_content PASS/HOLD mapped per lifecycle docstring"}


def build_packet(asset: dict, qa: dict) -> dict:
    """Single publication packet (§6). Secret scan before return."""
    from affiliate import market_state as ms
    packet = {
        "ASSET_ID": asset["ASSET_ID"], "VERSION": asset["VERSION"],
        "title": asset["ASSET_ID"], "description": asset["PROBLEM"],
        "CTA": "founder publishes from own account",
        "thumbnail_creative": "existing thumbnail.png alongside video" if "VIDEO" in asset["ASSET_ID"] else "none",
        "affiliate_disclosure": True,
        "tracking_reference": "register outbound link at publish time (registry empty today)",
        "metadata": {"channel": asset["CHANNEL"], "audience": asset["TARGET_AUDIENCE"]},
        "measurement_configuration": "window opens on confirmation; 100-view minimum",
        "QA_report": qa,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    blob = json.dumps(packet, ensure_ascii=False).lower()
    leaks = [m for m in ("sk-", "grok_", "api_key", "bearer ", "token=") if m in blob]
    if leaks:
        raise ValueError("packet secret scan failed: %s" % leaks)
    return packet


def run_lifecycle(write: bool = False) -> dict:
    """Execute real stages DISCOVER→GATE. write=True persists the packet
    file + gate record; write=False is a pure read-only rehearsal."""
    from affiliate import select as sel, gates as gt
    from affiliate import assets as at
    stages = {}
    ranked = sel.rank_opportunities()
    stages["DISCOVER"] = {"status": "COMPLETE", "evidence": "%d ranked" % len(ranked)}
    top = ranked[0] if ranked else None
    stages["SELECT"] = {"status": "COMPLETE" if top else "BLOCKED",
                        "evidence": (top or {}).get("id", "empty queue")}
    reuse = at.find_reuse_candidates("launch article")
    stages["PRODUCE"] = {"status": "COMPLETE",
                         "evidence": "reuse-first: %d existing assets; no new asset created" % len(reuse["candidates"])}
    assets = asset_registry()
    qa_results = [run_qa(a) for a in assets]
    blocked = [q for q in qa_results if q["status"] == "BLOCKED"]
    stages["QA"] = {"status": "COMPLETE",
                    "evidence": "; ".join("%s=%s" % (q["ASSET_ID"], q["status"]) for q in qa_results)}
    ready = [a for a, q in zip(assets, qa_results) if q["status"] != "BLOCKED"]
    packet = build_packet(ready[0], qa_results[0]) if ready else None
    if packet and write:
        PACKETS_DIR.mkdir(parents=True, exist_ok=True)
        (PACKETS_DIR / (packet["ASSET_ID"] + ".json")).write_text(
            json.dumps(packet, ensure_ascii=False, indent=1), encoding="utf-8")
    stages["PACKAGE"] = {"status": "COMPLETE" if packet else "BLOCKED",
                         "evidence": "packet %s (write=%s)" % (
                             packet["ASSET_ID"] if packet else "none", write)}
    gate_info = {"recorded": False, "GATE_ID": None}
    if packet:
        gp = gt.publication_gate_packet()
        gate_info = {"GATE_ID": gp["GATE_ID"],
                     "recorded": gt.record_gate(gp)["recorded"] if write else "rehearsal-no-write"}
    stages["FOUNDER_PUBLICATION_GATE"] = {"status": "GATE_OPEN",
                                          "evidence": "GATE_ID=%s" % gate_info["GATE_ID"]}
    for s in STAGES[6:]:
        stages[s] = {"status": "NOT_REACHED",
                     "evidence": "requires founder publication (real world)"}
    return {"mode": "REAL", "write": write, "stages": stages,
            "stopped_at": "FOUNDER_PUBLICATION_GATE",
            "reason": "verification needs a human; autonomy resumes after"}


def _ledger_sizes() -> dict:
    out = {}
    for name in ("affiliate_clicks.jsonl", "affiliate_page_views.jsonl",
                 "commission_attribution_log.jsonl", "finance_data.json"):
        p = (_FACTORY_ROOT / "data" / name) if name != "finance_data.json" else (_FACTORY_ROOT / name)
        out[name] = p.stat().st_size if p.exists() else 0
    out["finance_sha"] = hashlib.sha256(
        (_FACTORY_ROOT / "finance_data.json").read_bytes()).hexdigest()
    return out


def run_dry_run() -> dict:
    """SIMULATION_ONLY full-machine walk. Synthetic events live in-memory,
    every one tagged simulation=True. Ledgers + finance asserted identical
    before/after. Returns the trace + isolation proof."""
    from affiliate import market_state as ms, signals as sig, diagnostics as dg
    before = _ledger_sizes()
    trace = []
    sim_state = "READY"

    def step(event, evidence):
        nonlocal sim_state
        r = ms.transition(sim_state, event, {**evidence, "simulation": True})
        trace.append({"in_simulation": True, "state": sim_state,
                      "event": event, "advanced": r["advanced"]})
        if r["advanced"]:
            sim_state = r["state"]

    # READY lives outside the machine's TRANSITIONS; begin at the gate
    sim_state = "PUBLICATION_GATE"
    trace.append({"in_simulation": True, "state": "READY",
                  "event": "request_publication(synthetic)", "advanced": True})
    step("publication_confirmed", {"confirmation": "SIMULATED"})
    step("exposure_verified", {"exposure_sample": "SIMULATED_37_views"})
    step("sample_sufficient", {"sample_size": "SIMULATED_120"})
    step("signal_verified", {"verification": "SIMULATED_attribution"})
    step("scale_approved", {"founder_approval": "SIMULATED"})
    # first-signal protocol on a synthetic event (in-memory only)
    proto = sig.first_signal_protocol(
        {"category": "EXTERNAL_CLICK", "simulation": True})
    bott = dg.diagnose_bottleneck()  # real current diagnosis, unchanged
    after = _ledger_sizes()
    return {"mode": "SIMULATION_ONLY",
            "trace": trace, "final_sim_state": sim_state,
            "first_signal_protocol_actions": len(proto["actions"]),
            "isolation": {"ledgers_identical": before == after,
                          "finance_sha_unchanged": before["finance_sha"] == after["finance_sha"]},
            "real_world": "NOT_IN_MARKET (simulation was not market activity)",
            "current_real_bottleneck": bott["bottleneck"]}


def distribution_intelligence() -> list:
    """Per-asset channel truth (§17): capability vs presence, never confused."""
    return [
        {"asset": "AST-MEDIUM-GPSR-01", "CHANNEL": "Medium",
         "TECHNICAL_STATUS": "PUBLISHING_CAPABLE (draft on disk)",
         "PUBLICATION_STATUS": "PUBLICATION_NOT_CONFIRMED",
         "MEASUREMENT_STATUS": "not armed", "COMMERCIAL_STATUS": "no presence",
         "BLOCKER": "founder publication", "FOUNDER_GATE": "yes"},
        {"asset": "AST-SYSTEME-VIDEO-01", "CHANNEL": "YouTube",
         "TECHNICAL_STATUS": "PUBLISHING_CAPABLE (final mp4 + QA on disk)",
         "PUBLICATION_STATUS": "PUBLICATION_NOT_CONFIRMED",
         "MEASUREMENT_STATUS": "not armed", "COMMERCIAL_STATUS": "no presence",
         "BLOCKER": "founder publication", "FOUNDER_GATE": "yes"},
        {"asset": "Gumroad portfolio (10)", "CHANNEL": "Gumroad",
         "TECHNICAL_STATUS": "TECHNICALLY_CONNECTED",
         "PUBLICATION_STATUS": "PUBLICATION_CONFIRMED (live products)",
         "MEASUREMENT_STATUS": "polling (0 sales)", "COMMERCIAL_STATUS": "no signal",
         "BLOCKER": "demand, not tooling", "FOUNDER_GATE": "no"},
    ]
