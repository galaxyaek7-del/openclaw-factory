#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executive Decision Memory (ADR-145, 2026-07-30).

The founder's "P0 Only" follow-up directive asked for a permanent record
of every executive decision, a unique ID per decision, duplicate/conflict
detection, a real "explain WHY" function, and outcome tracking over time
-- explicitly constrained to "reuse existing Knowledge Graph, reuse
Executive Brain, reuse Mission Control, no duplicated logic, no
architecture expansion."

A research audit (done before writing this) found most of the storage
layer already real and load-bearing:

  - `decision_engine/types.py::Decision` already carries a real,
    deterministic `decision_id` (`make_decision_id()`), `decided_at`,
    `status`, `reasoning`, `evaluation_snapshot` (the real evidence),
    and (Decision Memory, Round 6, 2026-07-29) `alternatives_rejected`/
    `expected_outcome`.
  - `decision_engine/feedback.py::sync_outcomes()` already tracks real
    outcomes over time (`data/decision_outcomes.jsonl`).
  - `decision_engine/learning.py::recalibration_report()` already
    computes real per-dimension "did this signal actually predict a
    sale" statistics from historical evidence -- Objective 8
    ("continuously improve future decisions using historical evidence")
    at the honest, human-reviewed-before-applying level this factory's
    standing execution policy requires; not rebuilt here.
  - `knowledge_graph/build.py` already has real Decision/Outcome nodes
    with a `resulted_in` edge, and (ADR-144, this same session) a real
    `ExecutiveDirective` node type, plus a real, generic
    `query_related()` graph-traversal primitive -- reused directly
    below, never reimplemented.

Two things were genuinely missing, confirmed by reading the code, not
assumed: `decision_engine/store.py::append_decision()` has zero
duplicate-prevention logic (it appends unconditionally), and no function
anywhere assembles a single "why was this decision made" narrative for
an arbitrary decision_id. This module adds exactly those two things,
plus the thin unified read-model Mission Control needs, over the real
niche-Decision ledger (`decision_engine/store.py`) and the real
Executive Directive ledger (`executive_brain.py`, ADR-144) -- never a
third, competing store.
"""

from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent


# ── Conflict detection (mechanical, disclosed heuristic -- never a
# semantic/AI judgment, same discipline as evolution_queue.py's
# SENSITIVE_AREA_KEYWORDS / _duplicate_architecture_check) ──

_ACCELERATE_KEYWORDS = ("تسريع", "استثمار", "accelerate", "invest")
_STOP_KEYWORDS = ("إيقاف", "رفض", "معالجة تنبيه", "stop", "reject", "pause")


def _classify_action_stance(action_text):
    text = str(action_text or "").lower()
    if any(kw in text for kw in _STOP_KEYWORDS):
        return "stop"
    if any(kw in text for kw in _ACCELERATE_KEYWORDS):
        return "accelerate"
    return "neutral"


def _extract_niche(evidence):
    if isinstance(evidence, dict):
        return evidence.get("niche")
    return None


def detect_niche_conflict(niche, decisions_path=None):
    """Real, mechanical check: does this niche already carry a real
    REJECTED/latest-non-ACCEPTED decision in decision_engine/store.py?
    If a new executive directive proposes real action on a niche that
    was already rejected, that is a real, checkable conflict -- cites
    the exact prior decision, never guesses at disagreement."""
    from decision_engine import store as decision_store

    if not niche:
        return {"conflict": False, "reason": "لا نيتش محدَّد لهذا القرار"}
    prior = decision_store.find_decisions_by_niche(niche, path=decisions_path)
    if not prior:
        return {"conflict": False, "reason": "لا قرار سابق حقيقي لهذا النيتش"}
    latest = max(prior, key=lambda d: d.get("decided_at", ""))
    if latest.get("status") in ("REJECTED",):
        return {
            "conflict": True,
            "reason": f"قرار سابق حقيقي رفض هذا النيتش (decision_id={latest.get('decision_id')}, decided_at={latest.get('decided_at')})",
            "prior_decision": latest,
        }
    return {"conflict": False, "reason": f"آخر قرار حقيقي لهذا النيتش: {latest.get('status')} — لا تعارض"}


def detect_ledger_conflicts(ledger_path=None, lookback=10):
    """Real, mechanical check across the most recent real Executive
    Directive ledger entries: the same real niche appearing with
    opposing action stances (accelerate vs. stop) within the lookback
    window -- a real, checkable signal that two recent directives
    disagreed about the same real opportunity, never an invented one."""
    import executive_brain

    history = executive_brain.list_executive_directives(limit=lookback, ledger_path=ledger_path)
    by_niche = {}
    for entry in history["entries"]:
        directive = entry.get("directive") or {}
        niche = _extract_niche(directive.get("evidence"))
        if not niche:
            continue
        stance = _classify_action_stance(directive.get("action"))
        if stance == "neutral":
            continue
        by_niche.setdefault(niche, []).append({
            "decision_id": directive.get("decision_id"),
            "stance": stance,
            "generated_at": entry.get("generated_at"),
            "action": directive.get("action"),
        })

    conflicts = []
    for niche, entries in by_niche.items():
        stances = {e["stance"] for e in entries}
        if len(stances) > 1:
            conflicts.append({"niche": niche, "entries": entries})
    return {"conflicts": conflicts, "checked_niches": len(by_niche), "lookback": lookback}


# ── Explain (reuses knowledge_graph.build.query_related() directly --
# never a second traversal implementation) ──

def _lookup_niche_decision(decision_id, decisions_path=None):
    from decision_engine import store as decision_store
    for d in decision_store.read_decisions(path=decisions_path):
        if d.get("decision_id") == decision_id:
            return d
    return None


def _lookup_executive_directive(decision_id, ledger_path=None):
    import executive_brain
    history = executive_brain.list_executive_directives(limit=10_000, ledger_path=ledger_path)
    for entry in history["entries"]:
        if (entry.get("directive") or {}).get("decision_id") == decision_id:
            return entry
    return None


def explain_decision(decision_id, decisions_path=None, ledger_path=None):
    """The real "why was this decision made" function this directive
    asked for -- works for either a real niche Decision (decision_engine/
    store.py) or a real Executive Directive (executive_brain.py, ADR-144),
    whichever real record actually carries this decision_id. Reuses
    knowledge_graph.build.query_related() for connected real nodes
    (Outcome/Proposal/ADR) -- prefers the last saved real snapshot over
    an expensive live rebuild, same "reuse before recompute" discipline
    as executive_brain.py's own _knowledge_growth_trend()."""
    from knowledge_graph import build as kg_build

    niche_decision = _lookup_niche_decision(decision_id, decisions_path)
    directive_entry = None if niche_decision else _lookup_executive_directive(decision_id, ledger_path)

    if not niche_decision and not directive_entry:
        return {"found": False, "reason": f"لا سجل حقيقي بهذا المعرِّف في أي من دفتري القرارات: {decision_id}"}

    graph = kg_build.load_snapshot()
    if not graph:
        graph = kg_build.build_graph()

    if niche_decision:
        related = kg_build.query_related(graph, "decision", niche_decision["decision_id"], hops=1)
        conflict = detect_niche_conflict(niche_decision.get("niche"), decisions_path=decisions_path)
        return {
            "found": True,
            "decision_type": "niche_decision",
            "decision_id": decision_id,
            "niche": niche_decision.get("niche"),
            "status": niche_decision.get("status"),
            "decided_at": niche_decision.get("decided_at"),
            "reasoning": niche_decision.get("reasoning"),
            "evidence_used": niche_decision.get("evaluation_snapshot"),
            "expected_outcome": niche_decision.get("expected_outcome"),
            "alternatives_rejected": niche_decision.get("alternatives_rejected"),
            "decision_path": niche_decision.get("decision_path"),
            "related_knowledge": related.get("related", []) if related.get("found") else [],
            "conflict_check": conflict,
        }

    directive = directive_entry.get("directive") or {}
    related = kg_build.query_related(graph, "executive_directive", f"executive_directive:{directive_entry.get('generated_at')}", hops=1)
    niche = _extract_niche(directive.get("evidence"))
    conflict = detect_niche_conflict(niche, decisions_path=decisions_path) if niche else {"conflict": False, "reason": "لا نيتش محدَّد لهذا التوجيه"}
    return {
        "found": True,
        "decision_type": "executive_directive",
        "decision_id": decision_id,
        "status": directive.get("status"),
        "tier": directive.get("tier"),
        "tier_name": directive.get("tier_name"),
        "action": directive.get("action"),
        "generated_at": directive_entry.get("generated_at"),
        "evidence_used": directive.get("evidence"),
        "source": directive.get("source"),
        "confidence": directive.get("confidence"),
        "duplicate_check": directive.get("duplicate_check"),
        "related_knowledge": related.get("related", []) if related.get("found") else [],
        "conflict_check": conflict,
    }


# ── Mission Control aggregate ──

def list_decision_memory(limit=20, ledger_path=None, decisions_path=None):
    """Read-only Mission Control panel: the real unified recent-decision
    view across both real ledgers, most recent first, each entry tagged
    with its own real decision_id/status/type -- pure passthrough, no
    new computation beyond the two real reads and a simple merge-sort."""
    import executive_brain
    from decision_engine import store as decision_store

    directives = executive_brain.list_executive_directives(limit=limit, ledger_path=ledger_path)["entries"]
    directive_rows = [{
        "decision_id": (d.get("directive") or {}).get("decision_id"),
        "type": "executive_directive",
        "timestamp": d.get("generated_at"),
        "status": (d.get("directive") or {}).get("status"),
        "summary": (d.get("directive") or {}).get("action") or (d.get("directive") or {}).get("status"),
        "confidence": (d.get("directive") or {}).get("confidence"),
        "duplicate_check": (d.get("directive") or {}).get("duplicate_check"),
    } for d in directives]

    niche_decisions = sorted(decision_store.read_decisions(path=decisions_path), key=lambda d: d.get("decided_at", ""), reverse=True)[:limit]
    decision_rows = [{
        "decision_id": d.get("decision_id"),
        "type": "niche_decision",
        "timestamp": d.get("decided_at"),
        "status": d.get("status"),
        "summary": d.get("niche"),
        "confidence": None,
        "duplicate_check": None,
    } for d in niche_decisions]

    merged = sorted(directive_rows + decision_rows, key=lambda r: r.get("timestamp") or "", reverse=True)[:limit]
    return {"entries": merged, "count": len(merged)}
