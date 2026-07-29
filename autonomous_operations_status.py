#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomous Operations Status (2026-07-29) — "FINAL EXECUTIVE
DIRECTIVE" (autonomous digital enterprise) directive.

The directive asked for continuous, near-total automation of ~21 named
activities, with Founder approval reduced to only strategic direction
changes, major financial commitments, and legal obligations. Before
any code was written, this was flagged as a real conflict: the literal
ask would loosen 4 standing, explicitly human-gated systems --
`evolution_queue.py`'s Execute step (whose own governing text says
"must not be loosened without asking again"), `capital_allocation_
engine.py`'s "the engine recommends, the Founder decides", business
retirement (no real system exists, by design), and `channels/
publish_protection.py`'s Founder Protection layer for new/elevated-
risk channels. **The Founder's real answer (2026-07-29, via
AskUserQuestion): keep all 4 gates exactly as-is** -- build the real
autonomous loop only for what's already safe.

A second finding: this exact "always-on autonomous company" question
was already asked and declined three times in prior sessions
(`master_loop.py`, ADR-107 -> ADR-110 -> ADR-115) -- a persistent live
daemon was explicitly rejected each time. This module does not
resurrect that; it only adds 2 confirmed-safe, read-only steps to the
already-approved `factory_loop.js` tick (see `activity_status()`'s
`"automatic_new"` entries).

Every function here is a real citation -- no new judgment engine, no
fabricated automation. `activity_status()` tags each of the directive's
21 named activities against this factory's real, current code; every
tag traces to a specific real file/function, never asserted without
one."""

from datetime import datetime, timezone

STATUS_VALUES = ("automatic", "automatic_new", "human_gated_by_design", "ambiguous_not_touched")

# The 4 gates the Founder explicitly confirmed (2026-07-29) stay
# human-gated, unchanged by this directive.
PROTECTED_GATES = (
    "evolution_queue.py's Execute step (code implementation of an approved proposal) -- "
    "its own governing rule: 'must not be loosened without asking again'",
    "capital_allocation_engine.py's capital reallocation/reinvestment -- 'the engine recommends, the Founder decides'",
    "business retirement -- no real system exists to retire a business, by design "
    "(value_engine.py's retirement_recommendation is explicitly 'never a final retirement decision')",
    "channels/publish_protection.py's Founder Protection layer for a genuinely new channel arm's "
    "first publish, or any publish crossing the real high-risk threshold",
)

MASTER_LOOP_PRECEDENT = (
    "An always-on autonomous-company daemon (master_loop.py) was proposed and explicitly declined "
    "three times in prior sessions (ADR-107, reaffirmed ADR-110, reaffirmed a third time ADR-115). "
    "master_loop.py exists today only as a real, read-only citation layer "
    "(trace_lifecycle(), mission_control_heartbeat()) -- deliberately never called from factory_loop.js's "
    "tick. This directive's own autonomy additions (2026-07-29) do not resurrect that proposal; they add "
    "2 confirmed-safe, read-only steps to the already-approved factory_loop.js tick, which already runs "
    "every ~10 minutes once started, with no new standalone process."
)

_ACTIVITY_STATUS = {
    "discover_opportunities": {
        "status": "automatic",
        "source": "factory_loop.js::huntGolden() (Golden Hunter bridge) -- runs every real tick",
    },
    "validate_demand": {
        "status": "automatic",
        "source": "huntGolden()'s real opportunity-score gate + evidence_completeness.py, same real tick path",
    },
    "analyze_competition": {
        "status": "ambiguous_not_touched",
        "reason": "competitor_discovery.py is real but cache-only -- auto-refreshing it from the tick risks "
                   "a real, rate-limit-sensitive live network call, and this factory's standing discipline is "
                   "'never trigger a new scan from a read path'. Deferred to its own dedicated round, not guessed at here.",
    },
    "allocate_capital": {
        "status": "human_gated_by_design",
        "reason": "capital_allocation_engine.py's own directive text: 'the engine recommends, the Founder "
                   "decides' -- confirmed unchanged by the Founder's 2026-07-29 answer to this exact directive.",
    },
    "create_business_blueprints": {
        "status": "automatic_new",
        "source": "factory_loop.js::maybeGenerateBusinessBlueprintsForNewAcceptedDecisions() (new, 2026-07-29) "
                   "-- autonomous_business_builder.business_blueprint(), read-only/no-execution",
    },
    "build_products": {
        "status": "automatic",
        "source": "huntGolden()'s real production trigger, gated by the existing FACTORY_AUTO_PRODUCE env flag",
    },
    "test_products": {
        "status": "automatic",
        "source": "inspectors.py's real Dual Inspection, runs inside the same real production call",
    },
    "publish_products": {
        "status": "automatic",
        "source": "distributor.py::distribute(), gated by the existing FACTORY_LIVE_PUBLISH env flag, "
                   "proven arms only (channels/publish_protection.py's KNOWN_PROVEN_ARMS)",
    },
    "monitor_sales": {
        "status": "automatic",
        "source": "factory_loop.js's sales_poll step + resilience_monitor.py -- both run every real tick",
    },
    "optimize_pricing": {
        "status": "human_gated_by_design",
        "reason": "no real re-pricing mechanism exists anywhere in this factory (confirmed by repo-wide grep) "
                   "-- price is computed once at decision time (profit_oracle.py). A genuine absence, not a "
                   "build gap this round created or could safely close by guessing at a policy.",
    },
    "collect_customer_feedback": {
        "status": "automatic",
        "source": "customer_pipeline.py's real, always-on review submission endpoint -- inherently "
                   "pull-based (customer-initiated), not a scheduled activity to add to any tick",
    },
    "learn_from_results": {
        "status": "ambiguous_not_touched",
        "reason": "decision_engine/feedback.py::sync_outcomes() is called both from a Mission Control action "
                   "and from orchestrator/engines/learning.py (registered into orchestrator.orchestrator."
                   "run_cycle(), itself invoked by factory_loop.js's --run-ladder-opportunity call). Whether "
                   "this makes it already-automatic per tick, or only for niches reaching that specific stage, "
                   "could not be confirmed with full certainty -- deferred rather than risking a redundant or "
                   "wrongly-gated addition.",
    },
    "improve_existing_assets": {
        "status": "automatic",
        "source": "factory_loop.js's daily evolution_queue_intake -- real intake/simulate/decide, stops at "
                   "AWAITING_FOUNDER_APPROVAL; actual code implementation stays human-gated (see PROTECTED_GATES)",
    },
    "expand_successful_businesses": {
        "status": "ambiguous_not_touched",
        "reason": "growth_engine.py::evaluate_channel_expansion() is real but only invoked on-demand inside "
                   "production_blueprint.build_production_blueprint() -- not tick-wired. Kept out of this round "
                   "to hold scope to the 2 confirmed-safe additions rather than expanding scope mid-round.",
    },
    "retire_weak_businesses": {
        "status": "human_gated_by_design",
        "reason": "no real system exists to retire a business, by design -- value_engine.py's own "
                   "retirement_recommendation field is explicitly disclosed as 'never a final retirement decision'.",
    },
    "reinvest_capital": {
        "status": "human_gated_by_design",
        "reason": "same real gate as allocate_capital -- capital_allocation_engine.py stays recommend-only, "
                   "confirmed unchanged by the Founder's 2026-07-29 answer.",
    },
    "generate_executive_reports": {
        "status": "automatic",
        "source": "factory_loop.js's 4 daily reports (evolution_report/ai_doctor_report/department_health_report/executive_brief)",
    },
    "maintain_institutional_knowledge": {
        "status": "automatic_new",
        "source": "factory_loop.js::maybeGenerateDailyKnowledgeGraph() (new, 2026-07-29) -- knowledge_graph.build_graph()",
    },
    "detect_risks": {
        "status": "automatic",
        "source": "resilience_monitor.py::assess_resilience() -- runs every real tick",
    },
    "recover_from_failures": {
        "status": "human_gated_by_design",
        "reason": "detection is automatic (resilience_monitor.py, recovery/startup_check.py); recovery ACTIONS "
                   "(clear_subsystem_unstable, publish-emergency-resume, etc.) stay human-gated by explicit "
                   "founder decision, unchanged.",
    },
    "continuously_improve_itself": {
        "status": "human_gated_by_design",
        "reason": "same real gate as improve_existing_assets -- evolution_queue.py's Execute step is "
                   "explicitly, permanently human-gated ('must not be loosened without asking again'), "
                   "confirmed unchanged by the Founder's 2026-07-29 answer.",
    },
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def activity_status():
    """The directive's 21 named activities, each honestly tagged against
    this factory's real, current code -- every tag citing a real
    function/file, never asserted without one."""
    return {"activities": _ACTIVITY_STATUS, "generated_at": _now_iso()}


def autonomous_operations_summary():
    """Real counts + the 4 protected-gate names + the master_loop.py
    precedent -- so this decision's history is never lost or silently
    re-litigated by a future session."""
    counts = {status: 0 for status in STATUS_VALUES}
    for entry in _ACTIVITY_STATUS.values():
        counts[entry["status"]] += 1

    return {
        "total_named_activities": len(_ACTIVITY_STATUS),
        "counts": counts,
        "protected_gates": list(PROTECTED_GATES),
        "always_on_daemon_precedent": MASTER_LOOP_PRECEDENT,
        "generated_at": _now_iso(),
    }
