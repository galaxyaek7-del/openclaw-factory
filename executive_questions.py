#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Executive Intelligence Layer — Strategic Questions (ADR-154, 2026-07-31).

Answers the founder's 8 named "Executive Intelligence" questions --
almost entirely a citation layer over already-real functions
(executive_brain.py, capital_allocation_engine.py, strategic_
intelligence_core.py, autonomous_operations_status.py,
resilience_monitor.py), never a second, competing computation. Follows
the exact "consolidate rather than add an Nth parallel layer"
resolution ADR-144 (Executive Brain) and ADR-147 (GF-OS) already
established for this identical class of directive.

Named executive_questions.py, not executive_intelligence.py -- a real,
pre-existing top-level package of that exact name already exists
(ADR-052's older "Daily Executive Report," a standalone CLI tool never
wired into server.js/factory_loop.js, conceptually superseded by ADR-
137's build_executive_brief() for most of the same concerns but never
formally deprecated). Left untouched -- out of scope for this round,
disclosed in ADR-154 rather than silently colliding with it.

Real, disclosed cost discipline: capital_allocation_engine's dashboard
and strategic_intelligence_core's brief are each real, ~seconds-to-tens-
of-seconds full-portfolio scans. Both are computed here exactly ONCE
and threaded through every question that needs them -- never
recomputed per-question, matching executive_brain.py's own established
"call every real system exactly once" discipline. Q1 specifically
reuses executive_brain's own internal arbitration helpers
(_candidate_directives/_arbitrate) against this module's own single
brief/gox/cap computation, rather than calling
build_executive_directive() a second time (which would silently
recompute brief/gox/cap again internally).
"""

WAITING_FOR_REAL_SOURCE = "WAITING FOR REAL SOURCE"


def answer_strategic_questions(decisions_path=None, board_path=None, alerts_path=None,
                                brief=None, gox=None, cap=None):
    """`brief`/`gox`/`cap` (Enterprise Operations Center, ADR-155,
    2026-07-31): let a caller that already has a real, freshly-computed
    build_executive_brief()/build_global_opportunity_exchange_dashboard()/
    build_capital_allocation_dashboard() result pass it straight through
    instead of triggering a second, redundant, real full-portfolio
    computation -- the same real pattern scheduler.decide_next_actions()'s
    own `portfolio` parameter already established. Leave as None (the
    default) to compute all three fresh, exactly as before."""
    import strategic_intelligence_core
    import global_opportunity_exchange
    import capital_allocation_engine
    import evolution_queue
    import executive_brain
    import resilience_monitor
    import autonomous_operations_status
    import launch_readiness

    if brief is None:
        brief = strategic_intelligence_core.build_executive_brief(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        )
    if gox is None:
        gox = global_opportunity_exchange.build_global_opportunity_exchange_dashboard(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        )
    if cap is None:
        cap = capital_allocation_engine.build_capital_allocation_dashboard(
            decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        )
    evo_queue = evolution_queue.list_evolution_queue()

    # Q1 -- reuses executive_brain's own real arbitration helpers against
    # the single brief/gox/cap already computed above, rather than
    # calling build_executive_directive() (which would recompute all
    # three internally a second time).
    candidates = executive_brain._candidate_directives(brief, gox, cap, evo_queue)
    directive = executive_brain._arbitrate(candidates)

    resilience = resilience_monitor.assess_resilience()
    readiness = launch_readiness.launch_readiness_score()
    ops_summary = autonomous_operations_status.autonomous_operations_summary()

    return {
        "what_deserves_attention_today": {
            "answer": directive,
            "source": "executive_brain.py::_candidate_directives()/_arbitrate() (ADR-144), same real arbitration this factory's own Executive Brain already runs.",
        },
        "which_division_is_slowing_the_company": _which_division_is_slowing(resilience, readiness),
        "where_is_expected_revenue_highest": {
            "answer": cap["top_roi_initiatives"],
            "source": "capital_allocation_engine.py::build_capital_allocation_dashboard()['top_roi_initiatives'] (ADR-139) -- the exact same real source that answers 'highest ROI' below; not computed twice.",
        },
        "which_automations_are_underutilized": {
            "answer": WAITING_FOR_REAL_SOURCE,
            "reason": "No real automation-utilization RATE metric exists anywhere in this factory -- confirmed by direct search. The closest real signal is autonomous_operations_status.py's categorical automatic/automatic_new/human_gated_by_design/ambiguous_not_touched tagging, which is a category, not a utilization rate.",
            "closest_real_signal": ops_summary,
        },
        "what_should_be_built_next": {
            "answer": brief["products_to_accelerate"],
            "source": "strategic_intelligence_core.py::build_executive_brief()['products_to_accelerate'] -- scheduler.decide_next_actions()'s real accelerate bucket, same source the Executive Brief already cites.",
        },
        "what_should_be_paused": {
            "answer": brief["products_to_pause"],
            "source": "strategic_intelligence_core.py::build_executive_brief()['products_to_pause'] -- scheduler.decide_next_actions()'s real stop bucket, same source the Executive Brief already cites.",
        },
        "what_creates_the_highest_roi": {
            "answer": cap["top_roi_initiatives"],
            "source": "Same real source as 'where is expected revenue highest' above -- capital_allocation_engine.py's top_roi_initiatives answers both questions identically; never a second, independently-computed ranking.",
        },
        "which_bottleneck_blocks_future_scaling": {
            "answer": brief["top_bottlenecks"],
            "source": "strategic_intelligence_core.py::build_executive_brief()['top_bottlenecks'] -- evolution_engine.build_evolution_report()'s real bottlenecks + customer_success_bottleneck, same source the Executive Brief already cites.",
        },
        "generated_at": brief["generated_at"],
    }


def _which_division_is_slowing(resilience, readiness):
    """Real, disclosed methodology: cites resilience_monitor.py's real
    active alerts (each with a real `area` field) -- honestly reports
    that none of today's real alert areas map onto Mission Control's
    17-division taxonomy (confirmed by direct comparison) rather than
    force-fitting an unrelated signal onto a division name."""
    active_alerts = resilience.get("active_alerts", [])
    division_names = set()
    for div in readiness.get("divisions", {}).values():
        division_names.add(div["division"].lower())

    matched = [a for a in active_alerts if any(name in a.get("area", "").lower() for name in division_names)]
    if matched:
        return {
            "answer": matched,
            "source": "resilience_monitor.py::assess_resilience()['active_alerts'], filtered to alerts whose real `area` field matches a named Mission Control division.",
        }
    return {
        "answer": WAITING_FOR_REAL_SOURCE,
        "reason": f"resilience_monitor.py reports {len(active_alerts)} real active alert(s) this cycle, but none of their real `area` values correspond to any of Mission Control's 17 named divisions -- no fabricated mapping applied.",
        "real_active_alerts_this_cycle": active_alerts,
    }
