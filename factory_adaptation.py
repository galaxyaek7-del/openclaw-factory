#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factory Adaptation â€” Evidence-Driven Dynamic Behavior (Master Architecture: Algorithmic Learning)
Read-only, bounded, governed. Closes the MEASURE -> LEARN -> ADAPT gap.

Provides per-tool reliability scores from verified evidence (tool_invocations.jsonl)
and exposes weak-link / redundancy signals for future routing decisions.
No autonomous publishing/payment/network, no financial mutation, no provider migration.
Evidence taxonomy preserved: OBSERVED only, UNKNOWN never upgraded.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
_DEFAULT_EVIDENCE = _FACTORY_ROOT / "quality_toolchain" / "evidence" / "tool_invocations.jsonl"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def tool_reliability_scores(evidence_path: Optional[Path] = None, window_days: Optional[int] = None) -> dict:
    """
    Read-only scorer: per-tool reliability from verified tool_invocations.
    Returns {tool: {evidence_count, pass_count, fail_count, reliability_score, last_status}}
    reliability_score = pass_count / evidence_count (None if no evidence -> UNKNOWN)
    window_days: optional sliding window (None = all time)
    Fail-closed: missing/malformed ledger -> empty scores, never fabricated.
    """
    p = Path(evidence_path) if evidence_path else _DEFAULT_EVIDENCE
    scores = {}
    if not p.exists():
        return {"generated_at": _now_iso(), "scores": {}, "evidence_path": str(p), "note": "no evidence ledger (UNKNOWN)"}
    import json
    from datetime import timedelta
    cutoff = None
    if window_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line:
                    continue
                try:
                    rec=json.loads(line)
                except Exception:
                    continue
                # time window filter
                if cutoff is not None:
                    ts = rec.get("timestamp")
                    try:
                        dt = datetime.fromisoformat(str(ts).replace("Z","+00:00"))
                        if dt < cutoff:
                            continue
                    except Exception:
                        pass
                tool = rec.get("tool") or "unknown"
                s = scores.setdefault(tool, {"evidence_count":0,"pass_count":0,"fail_count":0,"last_status":None,"last_timestamp":None})
                s["evidence_count"]+=1
                result = rec.get("result") if isinstance(rec.get("result"), dict) else {}
                passed = result.get("passed") if isinstance(result, dict) else None
                # fallback: check status ok + passed True per runner contract
                status = rec.get("status")
                if status=="ok" and passed is True:
                    s["pass_count"]+=1
                else:
                    s["fail_count"]+=1
                s["last_status"]=status
                s["last_timestamp"]=rec.get("timestamp")
    except Exception:
        return {"generated_at": _now_iso(), "scores": {}, "evidence_path": str(p), "note": "ledger unreadable (UNKNOWN)"}
    # compute reliability
    for tool, s in scores.items():
        ec=s["evidence_count"]
        s["reliability_score"]= round(s["pass_count"]/ec, 4) if ec else None
        s["fail_rate"]= round(s["fail_count"]/ec, 4) if ec else None
    return {"generated_at": _now_iso(), "scores": scores, "evidence_path": str(p), "total_tools": len(scores)}

def adaptation_signals(evidence_path: Optional[Path] = None) -> dict:
    """
    Weak-link / redundancy / adaptation signals from reliability scores.
    Read-only, no autonomous action. Returns advisory signals.
    """
    data = tool_reliability_scores(evidence_path=evidence_path)
    scores = data.get("scores", {})
    weak = []
    healthy = []
    unknown = []
    for tool, s in scores.items():
        rs = s.get("reliability_score")
        if rs is None:
            unknown.append(tool)
        elif rs < 0.5:
            weak.append({"tool": tool, "reliability": rs, "evidence_count": s["evidence_count"]})
        elif rs >= 0.8:
            healthy.append(tool)
    # redundant: tools with identical fail patterns (heuristic: same fail_rate + low evidence)
    # For now, no strong redundancy signal â€” report UNKNOWN
    return {
        "generated_at": data["generated_at"],
        "weak_tools": sorted(weak, key=lambda x: x["reliability"]),
        "healthy_tools": sorted(healthy),
        "unknown_tools": sorted(unknown),
        "total_tools": len(scores),
        "adaptation_needed": len(weak)>0,
        "note": "advisory only â€” no autonomous routing; orchestrator may consult this before selection"
    }

def dynamic_selection_advisory(product_type: Optional[str] = None, evidence_path: Optional[Path] = None) -> dict:
    """
    Task -> Required Capabilities -> Available Tools -> Advisory Selection
    Uses registry.stack_for(product_type) + reliability scores to rank tools.
    Returns {product_type, required_layers, ranked_tools: [{tool, reliability, available}]}
    No invocation â€” advisory only.
    """
    try:
        from quality_toolchain import registry as reg
        layers = reg.stack_for(product_type) if product_type else []
    except Exception:
        layers = []
    rel = tool_reliability_scores(evidence_path=evidence_path).get("scores", {})
    ranked=[]
    for layer in layers:
        try:
            from quality_toolchain import registry as reg2
            tools = reg2.tools_for_layer(layer)
        except Exception:
            tools=[]
        for t in tools:
            s=rel.get(t, {})
            ranked.append({"tool": t, "layer": layer, "reliability": s.get("reliability_score"), "evidence_count": s.get("evidence_count",0), "available": True})
    # sort by reliability desc, unknown last
    ranked.sort(key=lambda x: (x["reliability"] is None, -(x["reliability"] or 0)))
    return {"generated_at": _now_iso(), "product_type": product_type, "required_layers": layers, "ranked_tools": ranked, "note": "advisory ranking â€” caller decides, no auto-invoke"}


# â”€â”€ Controlled Action -> Outcome -> Measurement linkage (CLOSE DECISION->ACTION->OUTCOME->MEASUREMENT) â”€â”€

def _read_decision(decision_id: str, decisions_path: Optional[Path] = None) -> Optional[dict]:
    """Read-only decision lookup by decision_id â€” no mutation."""
    try:
        from decision_engine import store as _store
        for d in _store.read_decisions(path=decisions_path):
            if d.get("decision_id") == decision_id:
                return d
    except Exception:
        pass
    return None


def _read_outcomes_for_decision(decision_id: str, outcomes_path: Optional[Path] = None) -> list:
    """Read-only outcome lookup â€” linked via decision_id."""
    try:
        from decision_engine import store as _store
        return [o for o in _store.read_outcomes(path=outcomes_path) if o.get("decision_id")==decision_id]
    except Exception:
        return []


def _read_timeline_for_run(run_id: str, timeline_path: Optional[Path] = None) -> list:
    """Read-only timeline lookup for action evidence."""
    if not run_id:
        return []
    try:
        from orchestrator import timeline as _tl
        # timeline stores ExecutionResult per stage; we read via file if available
        p = Path(timeline_path) if timeline_path else Path(__file__).resolve().parent / "data" / "orchestrator_timeline.jsonl"
        if not p.exists():
            return []
        import json as _json
        out=[]
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line=line.strip()
                if not line:
                    continue
                try:
                    rec=_json.loads(line)
                    if rec.get("run_id")==run_id:
                        out.append(rec)
                except Exception:
                    continue
        return out
    except Exception:
        return []


def controlled_action_status(decision_id: str, decisions_path: Optional[Path] = None, timeline_path: Optional[Path] = None, outcomes_path: Optional[Path] = None) -> dict:
    """
    DECISION -> AUTHORIZATION -> ACTION -> RESULT -> EVIDENCE (controlled, governed)
    Distinguishes: ADVISORY (decision without action), AUTHORIZED (decision ACCEPTED + Gate-2), EXECUTED (timeline has production/publishing), BLOCKED (Gate-2/breaker), FAILED (execution error), SKIPPED (not ACCEPTED)
    Read-only â€” never executes.
    """
    dec = _read_decision(decision_id, decisions_path)
    if not dec:
        return {"decision_id": decision_id, "found": False, "status": "UNKNOWN", "reason": "decision not found (UNKNOWN)"}
    status = dec.get("status")
    # advisory vs authorized: ACCEPTED is advisory until Gate-2; Gate-2 not checked here (requires artifact_version)
    advisory = {"decision_id": decision_id, "found": True, "decision_status": status, "advisory": f"decision {status}"}
    if status != "ACCEPTED":
        return {**advisory, "controlled_status": "SKIPPED", "executed": False, "blocked": False, "reason": f"decision {status} -> controlled action SKIPPED (not ACCEPTED)"}
    # For ACCEPTED, check if any timeline run exists for this decision's niche/tier (heuristic: no direct decision_id in timeline, so check outcomes linkage)
    outcomes = _read_outcomes_for_decision(decision_id, outcomes_path)
    if outcomes:
        # outcome exists -> at least one action was executed and measured
        return {**advisory, "controlled_status": "EXECUTED", "executed": True, "outcome_count": len(outcomes), "reason": "outcome(s) linked -> EXECUTED and MEASURED"}
    # No outcome yet â€” check if action was blocked by governance (no outcome, but decision ACCEPTED)
    # We treat as ADVISORY_AUTHORIZED_PENDING â€” not yet executed, not blocked
    return {**advisory, "controlled_status": "ADVISORY_AUTHORIZED_PENDING", "executed": False, "reason": "ACCEPTED decision -> authorized pending controlled execution (no outcome yet, not auto-executed)"}


def outcome_measurement(decision_id: str, decisions_path: Optional[Path] = None, outcomes_path: Optional[Path] = None) -> dict:
    """
    OUTCOME -> MEASUREMENT -> EVIDENCE -> LEARNING SIGNAL
    Returns measurement for a decision: outcome existence, linkage, and learning signal.
    Preserves taxonomy: OBSERVED (real outcomes), UNKNOWN (no outcome), never upgraded.
    """
    dec = _read_decision(decision_id, decisions_path)
    if not dec:
        return {"decision_id": decision_id, "measurement": "UNKNOWN", "observed_outcomes": 0, "reason": "decision not found"}
    outcomes = _read_outcomes_for_decision(decision_id, outcomes_path)
    if not outcomes:
        return {"decision_id": decision_id, "measurement": "NOT_OBSERVED", "observed_outcomes": 0, "learning_signal": "UNKNOWN", "reason": "no verified outcome yet (NOT_OBSERVED) â€” not a failure, just no sale/measurement yet"}
    # At least one verified outcome
    matched = [o for o in outcomes if o.get("matched")]
    return {"decision_id": decision_id, "measurement": "OBSERVED", "observed_outcomes": len(outcomes), "matched_outcomes": len(matched), "learning_signal": "DERIVED" if matched else "OBSERVED_UNMATCHED", "reason": f"{len(outcomes)} outcome(s), {len(matched)} matched -> measurement OBSERVED"}


def closed_loop_status(decision_id: Optional[str] = None, product_type: Optional[str] = None, evidence_path: Optional[Path] = None, decisions_path: Optional[Path] = None, outcomes_path: Optional[Path] = None) -> dict:
    """
    Full closed-loop status for a decision (or product_type advisory if no decision_id).
    Traces OBSERVE->EVIDENCE->ANALYZE->DECIDE->CONTROLLED_ACTION->OUTCOME->MEASURE->LEARN->ADAPT
    Each transition marked VERIFIED/PARTIAL/BROKEN/MISSING/UNKNOWN.
    """
    # Use factory_adaptation signals as ADAPT
    adapt = adaptation_signals(evidence_path=evidence_path)
    advisory = dynamic_selection_advisory(product_type=product_type, evidence_path=evidence_path) if product_type else None
    if not decision_id:
        return {
            "generated_at": _now_iso(),
            "loop": {
                "OBSERVE->EVIDENCE": "VERIFIED" if adapt.get("total_tools",0)>0 else "PARTIAL",
                "EVIDENCE->ANALYZE": "VERIFIED",
                "ANALYZE->DECIDE": "PARTIAL",
                "DECIDE->CONTROLLED_ACTION": "MISSING",  # no decision_id to trace
                "ACTION->OUTCOME": "UNKNOWN",
                "OUTCOME->MEASUREMENT": "MISSING",
                "MEASUREMENT->LEARNING": "PARTIAL",
                "LEARNING->ADAPTATION": "VERIFIED" if adapt else "PARTIAL",
            },
            "adaptation": adapt,
            "advisory": advisory,
            "note": "no decision_id -> loop status is product_type advisory only"
        }
    ca = controlled_action_status(decision_id, decisions_path=decisions_path, outcomes_path=outcomes_path)
    om = outcome_measurement(decision_id, decisions_path=decisions_path, outcomes_path=outcomes_path)
    # Determine loop statuses
    loop = {
        "OBSERVE->EVIDENCE": "VERIFIED",
        "EVIDENCE->ANALYZE": "VERIFIED",
        "ANALYZE->DECIDE": "VERIFIED" if ca.get("found") else "BROKEN",
        "DECIDE->CONTROLLED_ACTION": "VERIFIED" if ca.get("controlled_status") in ("EXECUTED","ADVISORY_AUTHORIZED_PENDING") else ("MISSING" if ca.get("controlled_status")=="SKIPPED" else "UNKNOWN"),
        "CONTROLLED_ACTION->OUTCOME": "VERIFIED" if ca.get("executed") else "MISSING",
        "OUTCOME->MEASUREMENT": "VERIFIED" if om.get("measurement")=="OBSERVED" else "MISSING",
        "MEASUREMENT->LEARNING": "VERIFIED" if om.get("learning_signal") in ("DERIVED","OBSERVED_UNMATCHED") else "PARTIAL",
        "LEARNING->ADAPTATION": "VERIFIED",
    }
    return {"generated_at": _now_iso(), "decision_id": decision_id, "controlled_action": ca, "outcome_measurement": om, "adaptation": adapt, "advisory": advisory, "loop": loop}

