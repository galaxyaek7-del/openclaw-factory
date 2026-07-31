#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Executive Brain — Phase Next (ADR-156, 2026-07-31).

Answers the founder's "Enterprise Executive Brain (Phase Next)"
directive -- the 4th round today asking to unify every division into
one executive intelligence layer (after ADR-144 Executive Brain,
ADR-147 GF-OS, ADR-154 Executive Intelligence Layer, ADR-155 Enterprise
Operations Center). Same "consolidate, extend, never duplicate"
resolution, now the directive's own explicit hard rule. Almost every
function here is citation over already-real modules; the few genuinely
new pieces (duplicate-work detection, missing-dependency detection,
cascade-impact/cycle detection, a 3-scenario simulator) are each real,
mechanical, and honestly disclosed where no real signal exists --
never a fabricated metric or prediction.

Real, disclosed cost discipline: build_executive_brief()/
build_global_opportunity_exchange_dashboard()/
build_capital_allocation_dashboard() are each real, expensive full-
portfolio scans. unified_decision_engine() computes each exactly ONCE
-- a real bug this exact pattern caught in the immediately preceding
round (ADR-155's company_pulse() redundant-computation timeout).
"""

from datetime import datetime, timezone
from pathlib import Path

NOT_ARCHITECTED = "NOT_ARCHITECTED"
WAITING_FOR_REAL_SOURCE = "WAITING FOR REAL SOURCE"

_FACTORY_ROOT = Path(__file__).resolve().parent
_AI_COST_LOG_FILE = _FACTORY_ROOT / "data" / "ai_cost_log.jsonl"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Objective 1: Unified Executive Decision Engine ──

def _detect_duplicated_work():
    """Real, mechanical check -- department pairs whose real forward-
    dependency sets (dependency_graph.py) share 3+ of the same real
    imported modules. The same disclosed proxy evolution_queue.py::
    _duplicate_architecture_check() already uses per-proposal, applied
    company-wide instead. A real code-structure signal, never semantic
    duplicate-work detection (this factory has no embeddings infra --
    same honest gap knowledge_graph/build.py's own docstring already
    discloses)."""
    import dependency_graph
    import gfos
    import department_events

    graph_result = dependency_graph.build_graph()
    graph = graph_result["graph"]
    depts = sorted(department_events.VALID_DEPARTMENTS)
    primary_by_dept = gfos._DEPARTMENT_PRIMARY_MODULE

    dept_deps = {dept: set(graph.get(primary_by_dept.get(dept), [])) for dept in depts}

    flagged = []
    for i, a in enumerate(depts):
        for b in depts[i + 1:]:
            overlap = dept_deps[a] & dept_deps[b]
            if len(overlap) >= 3:
                flagged.append({"departments": [a, b], "shared_real_modules": sorted(overlap), "shared_count": len(overlap)})

    return {
        "answer": flagged,
        "method": "Real, mechanical check -- department pairs whose real forward-dependency sets share 3+ of the same real imported modules (dependency_graph.py). Never semantic duplicate-work detection.",
    }


def _detect_missing_dependencies():
    """Real citation of launch_readiness.py's already-honest
    not_architected divisions (ADR-153) -- a division with zero real
    architecture has, by definition, zero real dependencies to report.
    Narrow: covers only the 5 divisions launch_readiness.py already
    tracks, not the full 17-division Mission Control taxonomy -- same
    disclosed narrow-citation discipline gfos.py::department_registry()
    already established."""
    import launch_readiness

    readiness = launch_readiness.launch_readiness_score()
    missing = [
        div["division"] for div in readiness["divisions"].values()
        if div["dimensions"]["architecture"]["value"] == launch_readiness.NOT_ARCHITECTED
    ]
    return {
        "answer": missing,
        "source": "launch_readiness.py::launch_readiness_score() (ADR-153) -- divisions with no real architecture have no real dependency to report. Narrow: covers the 5 divisions launch_readiness.py tracks, not the full 17-division taxonomy.",
    }


def unified_decision_engine():
    import strategic_intelligence_core
    import global_opportunity_exchange
    import capital_allocation_engine
    import evolution_queue
    import executive_brain
    import executive_decision_memory
    from executive_intelligence import inactivity

    brief = strategic_intelligence_core.build_executive_brief()
    gox = global_opportunity_exchange.build_global_opportunity_exchange_dashboard()
    cap = capital_allocation_engine.build_capital_allocation_dashboard()
    evo_queue = evolution_queue.list_evolution_queue()

    candidates = executive_brain._candidate_directives(brief, gox, cap, evo_queue)
    directive = executive_brain._arbitrate(candidates)

    return {
        "prioritized_action_list": {
            "answer": directive, "all_candidates_count": len(candidates),
            "source": "executive_brain.py::_candidate_directives()/_arbitrate() (ADR-144) -- same real arbitration this factory's own Executive Brain already runs.",
        },
        "conflicts_detected": {
            "answer": executive_decision_memory.detect_ledger_conflicts(),
            "source": "executive_decision_memory.py::detect_ledger_conflicts() (ADR-145) -- real, mechanical same-niche opposing-stance check.",
        },
        "duplicated_work_detected": _detect_duplicated_work(),
        "idle_divisions": {
            "answer": inactivity.detect_inactive_components(),
            "source": "executive_intelligence/inactivity.py::detect_inactive_components() (ADR-052) -- real zero-execution engines + real zero-publish-attempt channel arms.",
        },
        "bottlenecks_detected": {
            "answer": brief["top_bottlenecks"],
            "source": "strategic_intelligence_core.py::build_executive_brief()['top_bottlenecks'] -- same real source Executive Brief/Executive Intelligence already cite.",
        },
        "missing_dependencies_detected": _detect_missing_dependencies(),
        "generated_at": _now_iso(),
    }


# ── Objective 2: Executive KPI System ──

def executive_kpi_system():
    """Per-division 8 named KPIs, reusing launch_readiness.py's real
    5-division registry (the only division-level structure in this
    factory with genuine per-division real signal). Most of the 8 named
    KPIs have only a real COMPANY-WIDE signal, not a true per-division
    one -- disclosed honestly as such rather than force-fit into a fake
    per-division number. Intelligence Score and Production Capacity
    have no real source anywhere -- honestly NOT_ARCHITECTED."""
    import launch_readiness
    import autonomous_operations_status
    import gfos

    readiness = launch_readiness.launch_readiness_score()
    ops_summary = autonomous_operations_status.autonomous_operations_summary()
    automatic = ops_summary["counts"].get("automatic", 0) + ops_summary["counts"].get("automatic_new", 0)
    automation_level_pct = round(automatic / ops_summary["total_named_activities"] * 100, 1) if ops_summary["total_named_activities"] else None

    lifecycle = gfos.mission_lifecycle_summary()
    queue_depth = len(lifecycle["real_buckets"].get("run_now", [])) + len(lifecycle["real_buckets"].get("wait", []))

    kpis = {}
    for key, div in readiness["divisions"].items():
        dims = div["dimensions"]
        kpis[key] = {
            "division": div["division"],
            "health": {"value": dims["monitoring"]["value"], "source": "launch_readiness.py's real monitoring dimension (SERVICE_REGISTRY health-check presence)."} if dims["monitoring"]["value"] != launch_readiness.NOT_ARCHITECTED else {"value": NOT_ARCHITECTED, "reason": dims["monitoring"].get("reason")},
            "readiness": {"value": dims["operational_readiness"]["value"], "source": "launch_readiness.py::launch_readiness_score() (ADR-153) -- real per-division composite."},
            "progress": {"value": WAITING_FOR_REAL_SOURCE, "reason": "execution_status.py (ADR-102/105) tracks real per-opportunity (niche-level) progress, not per-division -- no real division-level progress metric exists."},
            "revenue_potential": {"value": WAITING_FOR_REAL_SOURCE, "reason": "capital_allocation_engine.py's top_roi_initiatives is a company-wide ranked list, not division-matched -- see the unified-decision-engine/enterprise-scheduler panels for the real ranking."},
            "automation_level": {"value": automation_level_pct, "source": "autonomous_operations_status.py::autonomous_operations_summary() -- a real COMPANY-WIDE ratio, not yet a per-division metric.", "note": "company-wide signal cited per-division for context only"},
            "intelligence_score": {"value": NOT_ARCHITECTED, "reason": "strategic_intelligence_core.py's Strategic Score is per-NICHE (11 real dimensions), not per-division -- no real per-division intelligence score exists."},
            "production_capacity": {"value": NOT_ARCHITECTED, "reason": "No real production-capacity/throughput model exists anywhere in this factory.", "closest_real_signal": {"company_wide_queue_depth": queue_depth, "source": "gfos.py::mission_lifecycle_summary() real run_now+wait bucket sizes -- a queue-depth proxy, not a capacity measurement."}},
            "risk_level": {"value": WAITING_FOR_REAL_SOURCE, "reason": "resilience_monitor.py's real active alerts are not reliably division-keyed (confirmed, ADR-154's which_division_is_slowing_the_company) -- see the company-pulse panel for the real company-wide risk signal."},
        }

    return {"divisions": kpis, "generated_at": _now_iso()}


# ── Objective 3: Enterprise Dependency Graph ──

def enterprise_dependency_graph():
    """Extends enterprise_operations.py::dependency_matrix() (ADR-155,
    reused verbatim, never recomputed differently) with real reverse-
    dependents and a real cascade-impact view, both from dependency_
    graph.py's already-real functions, plus real cycle detection --
    never surfaced in Mission Control until now."""
    import dependency_graph
    from enterprise_operations import dependency_matrix as _base_matrix
    import gfos
    import department_events

    base = _base_matrix()
    graph_result = dependency_graph.build_graph()
    cycles = dependency_graph.find_cycles()
    depts = sorted(department_events.VALID_DEPARTMENTS)
    primary_by_dept = gfos._DEPARTMENT_PRIMARY_MODULE

    enriched = []
    for row in base["matrix"]:
        dept = row["department"]
        primary = row["primary_module"]
        real_dependents = dependency_graph.dependents_of(primary, graph_result) if primary else []
        cascade_depts = [
            d for d in depts if d != dept and primary_by_dept.get(d)
            and any(m == primary_by_dept[d] or m.startswith(primary_by_dept[d] + ".") for m in real_dependents)
        ]
        enriched.append({**row, "real_dependent_modules": real_dependents, "cascades_to_departments": cascade_depts})

    return {
        "matrix": enriched,
        "real_cycles_detected": cycles,
        "method": base["method"] + " Reverse dependents/cascade-impact reuse dependency_graph.py::dependents_of()'s real transitive closure; cycle detection reuses dependency_graph.py::find_cycles() verbatim -- \"worth a human look,\" never \"confirmed broken,\" per that function's own documented caveat.",
        "generated_at": _now_iso(),
    }


# ── Objective 4: Enterprise Scheduler ──

def enterprise_scheduler():
    """Merges capital_allocation_engine's real ROI ranking with
    gfos.py::mission_lifecycle_summary()'s real scheduler buckets into
    one ranked view -- no new ranking algorithm, no new queue."""
    import gfos
    import capital_allocation_engine

    lifecycle = gfos.mission_lifecycle_summary()
    cap = capital_allocation_engine.build_capital_allocation_dashboard()

    return {
        "ranked_by_roi": {
            "answer": cap["top_roi_initiatives"],
            "source": "capital_allocation_engine.py::build_capital_allocation_dashboard()['top_roi_initiatives'] (ADR-139).",
        },
        "real_buckets": lifecycle["real_buckets"],
        "parallel_execution": lifecycle["parallel_execution"],
        "execution_time_estimate": {
            "value": "Unknown",
            "reason": "No real historical per-stage duration tracking exists anywhere in this factory (execution_status.py's own established disclosure, ADR-102/105) -- never a guessed date/duration.",
        },
        "requires_founder_approval": {
            "answer": lifecycle["lifecycle"]["waiting"],
            "source": "gfos.py::mission_lifecycle_summary() (ADR-147) -- scheduler.py's real wait bucket.",
        },
        "source": "gfos.py::mission_lifecycle_summary() (ADR-147) + capital_allocation_engine.py (ADR-139), merged -- no new ranking algorithm, no new queue.",
        "generated_at": _now_iso(),
    }


# ── Objective 5: Executive Scenario Simulator ──

def _ai_cost_trailing_daily_avg(now=None, log_path=None):
    """Real trailing-daily-average AI spend -- mirrors channels/
    ledger.py::revenue_trend()'s exact real technique (7-day recent vs.
    trailing daily average), applied to data/ai_cost_log.jsonl. No
    Python-side equivalent existed before this (only the JS-side
    infrastructure-status panel computed a cost trend) -- a small, real,
    honest addition, not a duplicate module."""
    import json
    from datetime import timedelta

    now = now or datetime.now(timezone.utc)
    since_recent = now - timedelta(days=7)
    path = Path(log_path) if log_path else _AI_COST_LOG_FILE
    if not path.exists():
        return None

    by_day = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                dt = datetime.fromisoformat((event.get("timestamp") or "").replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            day_key = dt.strftime("%Y-%m-%d")
            by_day[day_key] = by_day.get(day_key, 0.0) + float(event.get("cost_usd") or 0)

    if not by_day:
        return None
    trailing_days = [d for d in by_day if datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc) < since_recent]
    return (sum(by_day[d] for d in trailing_days) / len(trailing_days)) if trailing_days else None


def executive_scenario_simulator(assumed_revenue_growth_pct=10, assumed_ai_cost_growth_pct=10, cascade_department=None):
    """3 real, disclosed-assumption projections off a real baseline; 4
    honestly NOT_ARCHITECTED (no real, distinct baseline exists to
    honestly perturb). Every projection is explicitly labeled
    HYPOTHETICAL -- never a prediction, never written to any ledger
    (pure, on-demand what-if functions, not event streams). Does not
    touch simulation_mode.py's AFFILIATE_MODE switch or any production
    code path."""
    from channels import ledger as sales_ledger

    revenue = sales_ledger.revenue_trend()
    baseline_daily = revenue.get("trailing_daily_avg_usd")
    if baseline_daily is None:
        revenue_growth = {"value": "NOT_ENOUGH_DATA", "reason": "channels/ledger.py::revenue_trend() reports no real trailing daily revenue average yet -- nothing real to project growth from."}
    else:
        revenue_growth = {
            "value": "HYPOTHETICAL PROJECTION -- not a prediction",
            "assumed_growth_pct": assumed_revenue_growth_pct,
            "real_baseline_trailing_daily_avg_usd": round(baseline_daily, 2),
            "projected_30d_revenue_usd": round(baseline_daily * (1 + assumed_revenue_growth_pct / 100) * 30, 2),
            "source": "channels/ledger.py::revenue_trend() real baseline + a disclosed assumed growth rate -- never a real forecast algorithm.",
        }

    ai_baseline = _ai_cost_trailing_daily_avg()
    if ai_baseline is None:
        ai_cost_increase = {"value": "NOT_ENOUGH_DATA", "reason": "No real trailing daily AI-cost average exists yet in data/ai_cost_log.jsonl."}
    else:
        ai_cost_increase = {
            "value": "HYPOTHETICAL PROJECTION -- not a prediction",
            "assumed_growth_pct": assumed_ai_cost_growth_pct,
            "real_baseline_trailing_daily_avg_usd": round(ai_baseline, 4),
            "projected_30d_cost_usd": round(ai_baseline * (1 + assumed_ai_cost_growth_pct / 100) * 30, 2),
            "source": "data/ai_cost_log.jsonl real baseline + a disclosed assumed growth rate -- never a real forecast algorithm.",
        }

    dep_graph = enterprise_dependency_graph()
    if cascade_department:
        row = next((r for r in dep_graph["matrix"] if r["department"] == cascade_department), None)
        infra_failure = (
            {"value": "REAL CASCADE IMPACT -- not a prediction", "department": cascade_department, "cascades_to_departments": row["cascades_to_departments"], "source": "enterprise_dependency_graph()'s real dependents_of() transitive closure -- a real code-import cascade, not a fabricated failure model."}
            if row else {"value": "NOT_ENOUGH_DATA", "reason": f"{cascade_department!r} is not a real named department."}
        )
    else:
        infra_failure = {
            "value": "REAL CASCADE IMPACT PER DEPARTMENT -- pass cascade_department= for one specific department",
            "all_departments": [{"department": r["department"], "cascades_to_departments": r["cascades_to_departments"]} for r in dep_graph["matrix"]],
            "source": "enterprise_dependency_graph()'s real dependents_of() transitive closure.",
        }

    honest_gaps = {
        "traffic_spikes": {"value": NOT_ARCHITECTED, "reason": "No real traffic/analytics data exists anywhere in this factory to establish a baseline."},
        "publishing_delays": {"value": NOT_ARCHITECTED, "reason": "No real historical per-stage publishing-duration data exists (same gap execution_status.py already discloses for 'expected completion')."},
        "affiliate_expansion": {"value": NOT_ARCHITECTED, "reason": "Would require projecting off already-SIMULATED affiliate data (ADR-153) -- a real projection over a simulation, two layers removed from real revenue; not honest to present as a scenario result."},
        "digital_product_expansion": {"value": NOT_ARCHITECTED, "reason": "No real per-unit production-to-revenue conversion rate exists yet (zero real published products, config/reality.json)."},
    }

    return {
        "revenue_growth": revenue_growth,
        "ai_cost_increase": ai_cost_increase,
        "infrastructure_failure_cascade": infra_failure,
        **honest_gaps,
        "generated_at": _now_iso(),
    }
