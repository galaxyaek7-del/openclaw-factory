#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge Enterprise Operating System — GF-OS (ADR-147, 2026-07-30).

The founder's "GF-OS" directive asked for a permanent operating layer
above every subsystem, with departments registering Identity/
Responsibilities/Capabilities/Dependencies/Workload/Health/Performance/
Confidence, a Global Mission Queue, an Enterprise Timeline where nothing
is lost, and continuous measurement across 8 named dimensions.

Two real conflicts were surfaced via `AskUserQuestion` before writing
any code, and the founder resolved both:

1. The directive's own "no department operates independently" reads as
   mandatory single-gateway routing, which would have to formally
   supersede `safe_mode.py`'s founder-authored design (ADR-135,
   2026-07-29): "stop only the affected subsystem, keep the rest
   running, never allow cascading failures." **Resolved: GF-OS is a
   coordination/citation layer.** Every module below is still called
   exactly as it already was; nothing here forces a call through this
   module, and Safe Mode's independence is untouched.
2. "Global Mission Queue — every department pulls work from it" implies
   new always-on, pull-based worker infrastructure — a question already
   asked and declined via `AskUserQuestion` at least 4 times (ADR-107,
   ADR-110 — nearly this exact directive under a different name 6 days
   earlier, ADR-115, ADR-142). **Resolved: no new queue infrastructure.**
   `mission_lifecycle_summary()` below is a pure citation of
   `scheduler.py`'s already-real 5 buckets and `orchestrator.py`'s
   already-real execution stages.

Everything else this directive asked for already existed under a
different name — this module's only genuinely new pieces are
`department_registry()` (no prior module unified all 8 named fields
in one place, though every individual field was already real
somewhere) and `enterprise_timeline()` (no prior module merged every
real ledger this factory keeps into one chronological view). Both are
pure citation + merge — zero new computation, zero new ledgers, zero
new logging call sites.
"""

from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# Real, canonical 12-department roster — reused verbatim from
# department_events.py's own VALID_DEPARTMENTS (the same set
# department_health.py's build_department_health() already reports
# against). Never a second, invented department list.
_DEPARTMENT_PRIMARY_MODULE = {
    "executive": "executive_intelligence.engine_health",
    "market_intelligence": "market_intelligence_engine",
    "golden_hunter": "market_hunter",
    "pioneer": "golden_hunter.pioneer",
    "researchers": "research_department",
    "production": "book_generator",
    "publishing": "distributor",
    "finance": "channels.ledger",
    "customer_intelligence": "customer_pipeline",
    "infrastructure": "infrastructure_bridge",
    "recovery": "factory_state",
    "ai_capability_manager": "ai_capability.registry",
}

_DEPARTMENT_IDENTITY = {
    "executive": "Decision & governance engine — real accept/reject/defer verdicts over every niche opportunity.",
    "market_intelligence": "Real external evidence gathering (Hacker News, GitHub, keyless public sources) feeding opportunity scoring.",
    "golden_hunter": "The real, live daily discovery tick (factory_loop.js's own real entry point into market_hunter.py).",
    "pioneer": "Real-world signal intake — a structurally safe-by-design evidence bridge with no production trigger.",
    "researchers": "Deliberately non-automated — a real founder directive requires an explicit request before any research runs (HIGH_VALUE_STRATEGY.md).",
    "production": "The real content/cover/QA manufacturing pipeline (book_generator.py, cover_designer_v2.py, inspectors.py).",
    "publishing": "The real per-arm distribution fan-out (channels/*), gated by publish_protection.py.",
    "finance": "Real per-platform/per-sale revenue ledger (channels/ledger.py).",
    "customer_intelligence": "The real customer-facing pipeline — honestly near-empty today (zero real customer traffic).",
    "infrastructure": "Real CPU/memory/disk/health bridge between the Python and Node halves of this factory.",
    "recovery": "Real crash-safety and startup-check state (factory_state.py).",
    "ai_capability_manager": "Real AI-provider capability registry — which providers are actually configured and callable today.",
}


def department_registry(now=None):
    """The one genuinely new capability this module adds: every field
    the directive asked for, per department, each one a real citation
    of an already-real signal -- never a fabricated status. Reuses
    department_health.build_department_health() verbatim for Health/
    Performance/data-availability (never a second health computation),
    department_events.py's own real per-department event counts for
    Workload, and a real, narrow (single-primary-module) citation of
    dependency_graph.py for Dependencies -- disclosed as narrow, not a
    full per-department dependency audit."""
    import department_health
    import department_events
    import dependency_graph

    health_report = department_health.build_department_health()
    graph = dependency_graph.build_graph(module_level_only=True)
    events = list(department_events.read_events()) if hasattr(department_events, "read_events") else []

    workload_by_dept = {}
    for e in events:
        dept = e.get("department")
        if dept:
            workload_by_dept[dept] = workload_by_dept.get(dept, 0) + 1

    entries = []
    for dept in sorted(department_events.VALID_DEPARTMENTS):
        dept_health = health_report.get(dept, {})
        primary_module = _DEPARTMENT_PRIMARY_MODULE.get(dept)
        dependents = dependency_graph.dependents_of(primary_module, graph) if primary_module else None
        data_source = dept_health.get("data_source")
        confidence = (
            "real data" if data_source == "real"
            else "no real data source yet" if data_source == "none"
            else "unknown"
        )
        entries.append({
            "department": dept,
            "identity": _DEPARTMENT_IDENTITY.get(dept, "No real description recorded for this department."),
            "responsibilities_source": f"department_health.py's own real per-department report ({dept})",
            "capabilities": dept_health,
            "dependencies": {
                "primary_module": primary_module,
                "real_dependent_count": len(dependents) if dependents is not None else None,
                "note": "Narrow citation of this department's one primary real module only -- not a full per-department dependency audit." if primary_module else "No single primary module identified for this department.",
            },
            "current_workload": {
                "recent_events_recorded": workload_by_dept.get(dept, 0),
                "source": "department_events.jsonl (real, append-only correlation index)",
            },
            "health": dept_health,
            "confidence": confidence,
        })

    return {"generated_at": now.isoformat() if now else _now_iso(), "departments": entries, "count": len(entries)}


def mission_lifecycle_summary(decisions_path=None, board_path=None, alerts_path=None):
    """The real "Global Mission Queue" -- a pure citation of scheduler.py's
    already-real 5 buckets (never a new queue) and orchestrator.py's
    already-real execution stages, mapped onto the directive's 8 named
    lifecycle words via a disclosed, honest heuristic -- never a new
    state machine, never new state stored anywhere."""
    import scheduler
    from orchestrator import types as orchestrator_types

    scheduling = scheduler.decide_next_actions(decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path)
    buckets = scheduling["buckets"]

    # Disclosed mapping, not a new state machine -- every real bucket
    # already exists; this only relabels them onto the directive's own
    # 8 lifecycle words.
    lifecycle = {
        "created": {"count": None, "note": "No real 'mission creation' event exists separately from a real Decision being recorded (decision_engine.store) -- see decisions.jsonl for the real creation moment."},
        "validated": {"count": len(buckets.get("run_now", [])) + len(buckets.get("wait", [])) + len(buckets.get("accelerate", [])), "note": "Real ACCEPTED opportunities with no active risk flag (scheduler.py buckets run_now+wait+accelerate)."},
        "scheduled": {"count": len(buckets.get("run_now", [])), "note": "scheduler.py's own real run_now bucket -- the single next real opportunity."},
        "executing": {"count": None, "note": "No real per-mission 'currently executing' flag exists separately from orchestrator/timeline.py's own real event log -- see Enterprise Timeline."},
        "waiting": {"count": len(buckets.get("wait", [])), "note": "scheduler.py's own real wait bucket."},
        "completed": {"count": None, "note": "See production_blueprint.py's real 6-bucket mission board (LIVE) for real completed-production status -- not recomputed here."},
        "measured": {"count": None, "note": "See decision_engine.feedback.sync_outcomes()'s real Outcome records for real measured results -- not recomputed here."},
        "archived": {"count": len(buckets.get("cancel", [])) + len(buckets.get("stop", [])), "note": "scheduler.py's own real cancel+stop buckets."},
    }
    return {
        "generated_at": _now_iso(),
        "real_buckets": buckets,
        "lifecycle": lifecycle,
        "execution_order": list(orchestrator_types.EXECUTION_ORDER),
        "source": "scheduler.py::decide_next_actions() + orchestrator.types.EXECUTION_ORDER -- no new queue, no new state machine",
    }


def enterprise_timeline(limit=50, decisions_path=None, ledger_path=None, evolution_queue_state_path=None,
                         executive_directives_path=None, council_recommendations_path=None,
                         department_events_path=None, governance_dir=None):
    """The real "nothing is lost" Enterprise Timeline -- merges every
    real ledger this factory already keeps, most recent first. Zero new
    logging call sites: every entry already existed in its own real
    file before this function was written; this only reads and
    chronologically merges them."""
    import json
    from decision_engine import store as decision_store
    import executive_brain

    entries = []

    for d in decision_store.read_decisions(path=decisions_path):
        entries.append({"type": "decision", "timestamp": d.get("decided_at"), "summary": f"{d.get('status')}: {d.get('niche')}", "source": "decisions.jsonl"})

    dep_events_path = Path(department_events_path) if department_events_path else (_FACTORY_ROOT / "data" / "department_events.jsonl")
    if dep_events_path.exists():
        with open(dep_events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entries.append({"type": "department_event", "timestamp": e.get("timestamp"), "summary": f"{e.get('department')}: {e.get('event_type')} — {e.get('summary', '')}", "source": "department_events.jsonl"})

    evo_path = Path(evolution_queue_state_path) if evolution_queue_state_path else (_FACTORY_ROOT / "data" / "evolution_queue_state.json")
    if evo_path.exists():
        try:
            with open(evo_path, "r", encoding="utf-8") as f:
                evo_state = json.load(f)
            for pid, record in evo_state.items():
                for h in record.get("stage_history", []):
                    entries.append({"type": "evolution_proposal", "timestamp": h.get("at"), "summary": f"{pid}: {h.get('stage')} — {h.get('detail', '')}", "source": "evolution_queue_state.json"})
        except (json.JSONDecodeError, OSError):
            pass

    directives = executive_brain.list_executive_directives(limit=limit, ledger_path=executive_directives_path)["entries"]
    for d in directives:
        directive = d.get("directive") or {}
        entries.append({"type": "executive_directive", "timestamp": d.get("generated_at"), "summary": f"{directive.get('status')}: {directive.get('action') or ''}", "source": "executive_directives.jsonl"})

    council_path = Path(council_recommendations_path) if council_recommendations_path else (_FACTORY_ROOT / "data" / "council_recommendations.jsonl")
    if council_path.exists():
        with open(council_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    c = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entries.append({"type": "council_recommendation", "timestamp": c.get("convened_at"), "summary": f"{c.get('niche')}: {c.get('council_recommendation')}", "source": "council_recommendations.jsonl"})

    # Executive Intelligence Layer (ADR-154, 2026-07-31): "Company Memory
    # Timeline" architecture-change coverage -- every real ADR this
    # factory has ever written IS a real architecture-change record.
    # Reuses knowledge_graph.build._adr_nodes()'s already-parsed real
    # list verbatim (never re-parses the governance directory a second
    # time); honestly skips any ADR with no real `**Date:**` line rather
    # than guessing a timestamp. Release/milestone events are NOT added
    # here -- no real release log or milestone ledger exists anywhere in
    # this factory to source one from (NOT ARCHITECTED, not invented).
    from knowledge_graph.build import _adr_nodes
    for node in _adr_nodes(governance_dir):
        if not node.get("date"):
            continue
        entries.append({"type": "adr", "timestamp": node["date"], "summary": node["label"], "source": node.get("source_file", "OpenClaw_Brain/00_Governance/")})

    entries.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return {"generated_at": _now_iso(), "entries": entries[:limit], "total_real_events_merged": len(entries),
            "note": "Real merge of decisions.jsonl + department_events.jsonl + evolution_queue_state.json + executive_directives.jsonl + council_recommendations.jsonl -- no new ledger, no new logging call site."}


def gfos_status():
    """The single real aggregate for Mission Control's 'living state of
    the enterprise' ask -- cites (never recomputes) the real Executive
    Brain ledger, the real department registry, the real mission
    lifecycle citation, and the 10 most recent real Enterprise Timeline
    entries. A citation layer, exactly like executive_brain.py/
    galaxy_council.py before it -- never a second judgment engine."""
    import executive_brain

    latest_directives = executive_brain.list_executive_directives(limit=1)["entries"]
    return {
        "generated_at": _now_iso(),
        "latest_executive_directive": latest_directives[0] if latest_directives else None,
        "department_registry": department_registry(),
        "mission_lifecycle": mission_lifecycle_summary(),
        "recent_enterprise_timeline": enterprise_timeline(limit=10)["entries"],
        "note": "Coordination/citation layer only (ADR-147) -- every module cited here is still called directly by every other real caller exactly as before; nothing is force-routed through GF-OS, and safe_mode.py's per-subsystem independence (ADR-135) is unchanged.",
    }
