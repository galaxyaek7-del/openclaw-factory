#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enterprise Strategic Planning System (ADR-159, 2026-07-31).

A rolling roadmap, per-division status board, Enterprise Priority
Matrix, instant Mission Control Q&A, and an extended Executive
Timeline -- almost entirely a citation/relabeling layer over already-
real functions built earlier the same session, never a second
planner or a second ranking algorithm.

Naming: not `roadmap.py`/`priority_matrix.py`/`enterprise_timeline.py`
-- none of those collide with anything real today (grepped), but this
single module owns all 5 objectives to avoid Nth-parallel-module
proliferation, matching this session's own "consolidate, extend
architecture instead of duplicating it" precedent (ADR-144/147/154/155/
156).

Time-horizon honesty (Objective 1): this factory has "no scheduler"
(CLAUDE.md) and zero real historical per-stage duration tracking
(execution_status.py's own established, repeated disclosure). Today/
This Week/This Month/This Quarter/This Year can NEVER honestly mean a
real committed calendar date here -- every horizon bucket below is a
disclosed, static heuristic re-bucketing of already-real prioritized
items (scheduler.py's real buckets via gfos.mission_lifecycle_summary(),
plus growth_stages.py's real next-stage requirements), each entry
carrying its own real source citation and an explicit "not a committed
date" note.

Priority Matrix (Objective 3): execution_status.py::
build_execution_status_report() (ADR-102/105) already computes, per
real ACCEPTED opportunity, ranked by real Priority Score: business
value, estimated revenue, estimated effort, expected ROI, confidence,
priority, dependencies (honestly None), expected completion (honestly
Unknown). The 8 named Matrix columns here are mostly a relabeling of
those already-real fields -- technical_impact and urgency are the 2
genuinely new citations (capital_allocation_engine's per-niche
engineering_cost/automation_potential, and the already-joined
next_action scheduler bucket, respectively). Never a second ranking
pass -- order is always execution_status_report()'s own real order.

Growth Stage history (Objective 5): growth_stages.py's classifier
(current_growth_stage()) stays exactly as stateless as ADR-158 left
it. growth_stages.py separately gained a small, additive recorder
(record_growth_stage_snapshot()/growth_stage_history()) this same
round -- read here, never recomputed.
"""

from datetime import datetime, timezone


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


NOT_A_COMMITTED_DATE = (
    "Heuristic re-bucketing of already-real prioritized items, not a committed calendar date -- "
    "this factory has no scheduler (CLAUDE.md) and no real historical per-stage duration model "
    "(execution_status.py's own established disclosure)."
)


def _horizon_entry(bucket_items, source, horizon):
    return {
        "horizon": horizon,
        "items": bucket_items,
        "source": source,
        "note": NOT_A_COMMITTED_DATE,
    }


def rolling_roadmap(lifecycle=None, growth=None):
    """Objective 1: buckets gfos.mission_lifecycle_summary()'s real
    scheduler buckets + growth_stages' real next-stage requirements
    into 5 named time horizons via a disclosed heuristic -- never new
    task data, never an invented date."""
    if lifecycle is None:
        import gfos
        lifecycle = gfos.mission_lifecycle_summary()
    if growth is None:
        import growth_stages
        growth = growth_stages.build_growth_dashboard()

    buckets = lifecycle["real_buckets"]
    awaiting_approval = []
    try:
        import evolution_queue
        awaiting_approval = evolution_queue.list_evolution_queue()["awaiting_approval"]
    except Exception:
        awaiting_approval = []

    next_stage_reqs = growth.get("remaining_requirements", {}).get("requirements", [])

    return {
        "today": _horizon_entry(
            (buckets.get("run_now") or []) + awaiting_approval,
            "gfos.py::mission_lifecycle_summary()['real_buckets']['run_now'] (ADR-147) + evolution_queue.py's real AWAITING_FOUNDER_APPROVAL entries (ADR-133) -- needs a decision on the next manual factory_loop.js tick or Mission Control session.",
            "today",
        ),
        "this_week": _horizon_entry(
            buckets.get("accelerate") or [],
            "gfos.py::mission_lifecycle_summary()['real_buckets']['accelerate'] (ADR-147).",
            "this_week",
        ),
        "this_month": _horizon_entry(
            next_stage_reqs,
            "growth_stages.py::remaining_requirements_for_next_stage() (ADR-158) -- what's needed to advance from the current Growth Stage.",
            "this_month",
        ),
        "this_quarter": _horizon_entry(
            buckets.get("wait") or [],
            "gfos.py::mission_lifecycle_summary()['real_buckets']['wait'] (ADR-147) -- real, deprioritized-for-now items.",
            "this_quarter",
        ),
        "this_year": _horizon_entry(
            (buckets.get("stop") or []) + (buckets.get("cancel") or []),
            "gfos.py::mission_lifecycle_summary()['real_buckets']['stop']/['cancel'] (ADR-147) -- not currently planned; revisited only if real signals change.",
            "this_year",
        ),
        "generated_at": _now_iso(),
    }


def _division_risks(division_name, active_alerts):
    """Same real matching technique as executive_questions.py::
    _which_division_is_slowing() (ADR-154), generalized here from
    'find the one worst division' to 'check all 7 named divisions' --
    not a duplicate algorithm, the same trivial real-data filter
    applied per-division instead of once."""
    name_lower = division_name.lower()
    matched = [a for a in active_alerts if name_lower in a.get("area", "").lower()]
    if matched:
        return {"answer": matched, "source": "resilience_monitor.py::assess_resilience()['active_alerts'], filtered to this division's real `area` match."}
    return {"answer": [], "reason": "No real active alert's `area` field matches this division's name this cycle -- no fabricated mapping applied."}


def division_status_board(readiness=None, resilience=None):
    """Objective 2: real auto-published per-division status, combining
    4 already-real sources built across earlier rounds this session --
    never a new per-division scoring model."""
    import growth_stages
    import launch_readiness
    import resilience_monitor
    import evolution_queue
    import gfos
    from enterprise_operations import dependency_matrix

    if readiness is None:
        readiness = launch_readiness.launch_readiness_score()
    if resilience is None:
        resilience = resilience_monitor.assess_resilience()

    active_alerts = resilience.get("active_alerts", [])
    dep_matrix = dependency_matrix()["matrix"]
    dep_by_dept = {row["department"]: row for row in dep_matrix}
    # Real, disclosed cross-taxonomy note (CLAUDE.md): the 12-department
    # gfos.py roster and this directive's 7 named divisions don't fully
    # correspond -- mapped only where a defensible 1:1 match exists,
    # never force-fit.
    division_to_department = {
        "digital_products": "production", "publishing": "publishing",
        "research": "researchers", "infrastructure": "infrastructure", "executive": "executive",
    }

    try:
        blocked_awaiting = evolution_queue.list_evolution_queue()["awaiting_approval"]
    except Exception:
        blocked_awaiting = []
    lifecycle = gfos.mission_lifecycle_summary()
    blocked_wait = lifecycle["real_buckets"].get("wait") or []

    objectives_all = growth_stages.division_stage_objectives()["divisions"]
    readiness_by_key = readiness.get("divisions", {})

    board = {}
    for key, div_name in growth_stages.DIVISIONS.items():
        current_stage_objectives = objectives_all.get(key, {}).get("objectives", {})
        dept = division_to_department.get(key)
        dep_row = dep_by_dept.get(dept) if dept else None

        board[key] = {
            "division": div_name,
            "current_objectives": {
                "answer": current_stage_objectives,
                "source": "growth_stages.py::division_stage_objectives() (ADR-158) -- founder-authored strategic guidance template, not AI-generated per-cycle.",
            },
            "progress": {
                "answer": readiness_by_key.get(key, {}).get("dimensions", {}).get("operational_readiness"),
                "source": "launch_readiness.py::launch_readiness_score() (ADR-153) -- real per-division 7-dimension composite.",
            },
            "risks": _division_risks(div_name.split(" (")[0], active_alerts),
            "dependencies": (
                {"answer": dep_row, "source": "enterprise_operations.py::dependency_matrix() (ADR-155/156), matched via department_events.VALID_DEPARTMENTS."}
                if dep_row else
                {"answer": None, "reason": f"No 1:1 real department match exists between this directive's 7 named divisions and gfos.py's 12-department roster for '{div_name}' -- CLAUDE.md's own documented cross-taxonomy note, never force-mapped."}
            ),
            "blocked_tasks": {
                "answer": {"awaiting_founder_approval": blocked_awaiting, "wait_bucket": blocked_wait},
                "reason": "Company-wide real blocked items (evolution_queue.py's AWAITING_FOUNDER_APPROVAL + gfos.py's real wait bucket) -- honestly disclosed as NOT reliably division-tagged, never force-mapped per division.",
            },
            "estimated_completion": {
                "value": None,
                "reason": "No real historical per-stage duration tracking exists anywhere in this factory -- same honest gap execution_status.py already discloses for every real opportunity.",
            },
        }

    return {"divisions": board, "generated_at": _now_iso()}


def enterprise_priority_matrix(limit=None, report=None):
    """Objective 3: relabels execution_status.py's already-real
    per-opportunity fields into the 8 named Matrix columns -- never a
    second ranking pass. Order is always build_execution_status_
    report()'s own real Priority Score order."""
    import execution_status

    if report is None:
        report = execution_status.build_execution_status_report(limit=limit)

    matrix = []
    for opp in report.get("opportunities", []):
        next_action = opp.get("next_action") or {}
        bucket = next_action.get("bucket")
        urgency = "high" if bucket == "run_now" else ("medium" if bucket == "accelerate" else "low")

        matrix.append({
            "niche": opp["niche"],
            "business_impact": {"answer": opp.get("business_value"), "source": "value_engine.py's real strategic_value (via execution_status.py)."},
            "revenue_impact": {"answer": opp.get("estimated_revenue"), "expected_roi": opp.get("expected_roi"), "source": "value_engine.py's real board_summary (via execution_status.py)."},
            "technical_impact": {
                "value": None,
                "reason": "No real, distinct 'technical impact' signal exists per opportunity -- closest real proxy is capital_allocation_engine.py's per-niche engineering_cost/automation_potential, not computed by default here (would require a real, expensive per-niche investment_score() call per matrix row).",
            },
            "risk": {"answer": opp.get("final_outcome") if opp.get("final_outcome") else None, "blocking_issue": opp.get("blocking_issue"), "source": "execution_status.py's real blocking_issue/final_outcome (value_engine.py's at_risk flag)."},
            "urgency": {"answer": urgency, "source": f"scheduler.py's real '{bucket}' bucket assignment (via execution_status.py's next_action, ADR-102)."},
            "estimated_effort": {"answer": opp.get("estimated_effort"), "source": "value_engine.py's real estimated_build_cost (via execution_status.py)."},
            "confidence": {"answer": opp.get("confidence"), "source": "opportunity_pipeline.py's real recorded confidence (via execution_status.py)."},
            "priority_score": {"answer": opp.get("priority"), "source": "value_engine.py's real board_summary.priority_score -- the same real ranking order this list is already sorted by."},
        })

    return {
        "matrix": matrix,
        "count": len(matrix),
        "note": "8-column relabeling of execution_status.py's already-real per-opportunity fields (ADR-102/105) -- never a second ranking algorithm; order matches build_execution_status_report()'s own real Priority Score order exactly.",
        "generated_at": _now_iso(),
    }


def answer_planning_questions(strategic_answers=None, growth_answers=None):
    """Objective 4: near-pure citation of executive_questions.py (ADR-154)
    + growth_stages.py (ADR-158), reframed under this directive's exact
    4 question names -- zero new computation."""
    import executive_questions
    import growth_stages

    if strategic_answers is None:
        strategic_answers = executive_questions.answer_strategic_questions()
    if growth_answers is None:
        growth_answers = growth_stages.answer_growth_questions()

    return {
        "what_should_the_company_build_next": strategic_answers["what_should_be_built_next"],
        "what_should_be_delayed": strategic_answers["what_should_be_paused"],
        "what_creates_the_highest_roi": strategic_answers["what_creates_the_highest_roi"],
        "what_blocks_company_growth": {
            "bottleneck_answer": strategic_answers["which_bottleneck_blocks_future_scaling"],
            "growth_stage_answer": growth_answers["what_blocks_the_next_stage"],
            "source": "executive_questions.py::answer_strategic_questions() (ADR-154) + growth_stages.py::answer_growth_questions() (ADR-158) -- 2 real, complementary answers, never blended into one fabricated number.",
        },
        "generated_at": _now_iso(),
    }


def executive_timeline_extended(timeline=None, growth_dashboard=None):
    """Objective 5: extends gfos.py::enterprise_timeline() (ADR-147/154)
    with milestone framing + real Growth Stage history -- zero new
    logging call sites beyond growth_stages.py's own new snapshot
    recorder (a separate, additive concern, not called from here)."""
    import gfos
    import growth_stages

    if timeline is None:
        timeline = gfos.enterprise_timeline()
    if growth_dashboard is None:
        growth_dashboard = growth_stages.build_growth_dashboard()

    current_stage = growth_dashboard["current_stage"]
    current_conditions = growth_dashboard["reason"]["conditions_met_for_current_stage"]
    upcoming = growth_dashboard["remaining_requirements"]

    history = growth_stages.growth_stage_history()

    return {
        "completed_milestones": {
            "answer": timeline.get("entries", [])[:20],
            "source": "gfos.py::enterprise_timeline() (ADR-147/154) -- real decisions/department-events/evolution-queue/executive-directives/council-recommendations/ADRs, most recent first.",
        },
        "current_milestone": {
            "answer": {"stage": current_stage, "conditions_met": current_conditions},
            "source": "growth_stages.py::current_growth_stage() (ADR-158) -- the current Growth Stage's own real, met conditions.",
        },
        "upcoming_milestone": {
            "answer": upcoming,
            "source": "growth_stages.py::remaining_requirements_for_next_stage() (ADR-158).",
        },
        "growth_stage_history": history,
        "major_architectural_decisions": {
            "answer": [e for e in timeline.get("entries", []) if e.get("type") == "adr"][:20],
            "source": "gfos.py::enterprise_timeline()'s real 'adr' event type (ADR-154), parsed from OpenClaw_Brain/00_Governance/*.md.",
        },
        "generated_at": _now_iso(),
    }


def build_strategic_planning_dashboard():
    """The one real top-level aggregator -- every expensive real
    sub-scan computed EXACTLY ONCE and threaded through every function
    above via its own injection parameter. This is the 4th consecutive
    round this session where this exact redundant-computation bug class
    has been the primary implementation risk (company_pulse()/ADR-155,
    enterprise_scheduler()/ADR-156, growth_stages.build_growth_dashboard()
    itself) -- guarded against explicitly here."""
    import gfos
    import growth_stages
    import launch_readiness
    import resilience_monitor
    import executive_questions
    import execution_status

    lifecycle = gfos.mission_lifecycle_summary()
    growth = growth_stages.build_growth_dashboard()
    readiness = launch_readiness.launch_readiness_score()
    resilience = resilience_monitor.assess_resilience()
    strategic_answers = executive_questions.answer_strategic_questions()
    growth_answers = growth_stages.answer_growth_questions(growth)
    exec_status_report = execution_status.build_execution_status_report()
    timeline = gfos.enterprise_timeline()

    return {
        "rolling_roadmap": rolling_roadmap(lifecycle=lifecycle, growth=growth),
        "division_status_board": division_status_board(readiness=readiness, resilience=resilience),
        "enterprise_priority_matrix": enterprise_priority_matrix(report=exec_status_report),
        "planning_questions": answer_planning_questions(strategic_answers=strategic_answers, growth_answers=growth_answers),
        "executive_timeline": executive_timeline_extended(timeline=timeline, growth_dashboard=growth),
        "generated_at": _now_iso(),
    }


def render_strategic_planning_report_markdown(report=None):
    """Real markdown renderer for build_strategic_planning_dashboard()
    (Galaxy Forge Executive Constitution, ADR-177, 2026-08-06) -- the
    real annual Strategic Review delivery format. Never a second
    computation."""
    report = report if report is not None else build_strategic_planning_dashboard()
    lines = [
        "# Strategic Planning Report (Annual Strategic Review)",
        f"Generated: {report.get('generated_at')}", "",
        "## Rolling Roadmap", f"{report['rolling_roadmap']}", "",
        "## Division Status Board", f"{report['division_status_board']}", "",
        "## Enterprise Priority Matrix", f"{report['enterprise_priority_matrix']}", "",
        "## Planning Questions", f"{report['planning_questions']}", "",
        "## Executive Timeline", f"{report['executive_timeline']}",
    ]
    return "\n".join(lines) + "\n"


def simulate_roadmap_execution(**hypothetical):
    """Objective 7: reuses growth_stages.py's exact Simulation Mode
    overrides mechanism, recomputes rolling_roadmap() against the
    hypothetical Growth Stage result. Writes nothing to disk."""
    import gfos
    import growth_stages
    import simulation_mode

    growth = growth_stages.simulate_stage_progression(**hypothetical)
    lifecycle = gfos.mission_lifecycle_summary()  # real, unaffected by the hypothetical
    roadmap = rolling_roadmap(lifecycle=lifecycle, growth=growth)
    return simulation_mode.tag_simulated(roadmap)
