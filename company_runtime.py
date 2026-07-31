#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomous Company Runtime — documented + safe parts (ADR-157,
2026-07-31).

The founder's "Autonomous Company Runtime" directive asked for an
always-on Company Runtime, a Global Event Bus, an Autonomous Workflow
Engine, an Enterprise Queue Manager, and auto-restart Self-Healing --
together an always-on daemon with new real-time event/queue
infrastructure. That exact question has been asked and declined 5
times in this codebase's history (ADR-107->110->115->142->147),
confirmed again via `AskUserQuestion` before this module was written:
document the full architecture (ADR-157), build only the genuinely
safe, real, citation-based parts below. No daemon, no event bus, no
queue, no automatic cross-department execution, no new auto-restart
mechanism exists in this module or anywhere else in this factory.

Every function here is read-only/informational. Nothing in this
factory reads company_state()'s output to change what it does --
it is a real, disclosed status label, never a live behavioral switch.
"""

from datetime import datetime, timezone

NOT_ARCHITECTED = "NOT_ARCHITECTED"

# Objective 5: Company State Machine. SCALING is defined (per the
# directive's own named states) but never real -- no real scale-out
# signal exists anywhere in this factory (single Express process, no
# worker pool, no queue system -- lib/health_checks.js already reports
# this honestly for a different panel). Priority order below is
# real and disclosed: the first true condition wins, same discipline
# executive_brain.py's own PRIORITY_TIERS already established.
STATES = ("BOOT", "RECOVERY", "MAINTENANCE", "PRODUCTION", "OPTIMIZING", "LEARNING", "READY", "SCALING")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Objective 8: Executive Replay ──

def executive_replay(from_date=None, to_date=None, decision_id=None, limit=50):
    """Real chronological replay -- gfos.py::enterprise_timeline()'s
    already-real merge of 6 real ledgers, optionally date-filtered, plus
    (when a real decision_id is passed) executive_decision_memory.py's
    real explain_decision() detail for that one entry. No new storage,
    no new event log -- a real citation-only "replay" over data this
    factory already keeps permanently."""
    import gfos

    timeline = gfos.enterprise_timeline(limit=limit)
    entries = timeline["entries"]
    if from_date:
        entries = [e for e in entries if (e.get("timestamp") or "") >= from_date]
    if to_date:
        entries = [e for e in entries if (e.get("timestamp") or "") <= to_date]

    result = {
        "entries": entries,
        "total_real_events_merged": timeline["total_real_events_merged"],
        "source": "gfos.py::enterprise_timeline() (ADR-147) -- real chronological merge of 6 real ledgers (decisions, department events, evolution proposals, executive directives, council recommendations, ADRs). Pass decision_id= for full real detail on any single decision.",
        "generated_at": _now_iso(),
    }

    if decision_id:
        import executive_decision_memory
        result["explained_decision"] = executive_decision_memory.explain_decision(decision_id)

    return result


# ── Objective 9: Autonomous Daily Cycle (status only, no new automation) ──

# Real, disclosed, static citation of factory_loop.js's real tick-driven
# functions -- same convention execution_status.py's own _OWNER_BY_STAGE
# mapping already established for a different report. Never adds a new
# automatic call; this factory's daily cadence is unchanged by this
# module's existence.
_DAILY_CYCLE_STAGES = {
    "morning_review": (None, "No real, single 'morning review' function exists -- the closest real equivalent is the Executive Report stage below."),
    "opportunity_scan": ("factory_loop.js::huntGolden() + market_hunter.py (real, tick-driven)", None),
    "production": ("factory_loop.js's real production dispatch (triggerGenerateBook/triggerDistribute, tick-driven)", None),
    "qa": ("inspectors.py's real Dual Inspection -- part of the real production pipeline above, not a separate tick", None),
    "publishing": ("distributor.py, invoked by factory_loop.js's real production dispatch", None),
    "affiliate_updates": (None, "affiliate_commerce/ (ADR-149/153) is NOT tick-wired into factory_loop.js -- no daily automation exists for it yet."),
    "analytics": ("enterprise_operations.py::executive_analytics() (ADR-155) -- callable on demand, not yet tick-scheduled", None),
    "knowledge_update": ("factory_loop.js::maybeGenerateDailyKnowledgeGraph() (ADR-142, real, tick-driven, once-per-calendar-day gate)", None),
    "executive_report": ("factory_loop.js::maybeGenerateDailyExecutiveBrief() (ADR-137, real, tick-driven, once-per-calendar-day gate)", None),
}


def autonomous_daily_cycle_status():
    stages = {}
    for stage, (real_function, reason) in _DAILY_CYCLE_STAGES.items():
        stages[stage] = (
            {"status": "tick-wired", "real_function": real_function}
            if real_function else
            {"status": NOT_ARCHITECTED, "reason": reason}
        )
    return {
        "stages": stages,
        "note": "factory_loop.js has no cron/systemd -- every 'tick-wired' stage above only runs when someone runs `node factory_loop.js` and it is left running; there is no always-on daemon.",
        "generated_at": _now_iso(),
    }


# ── Objective 7 (Self-Healing) is deliberately NOT a separate function
# here -- it folds directly into mission_control_api.py's existing
# _recovery() dispatcher (real pending_retries is already there; only
# the real escalation-path citation was genuinely missing), per this
# round's own "no duplicate systems" rule. See ADR-157.


# ── Objective 5: Company State (read-only status label) ──

def company_state():
    """Real, priority-ordered, disclosed status label. Every condition
    cites a real signal; the first true one wins. SCALING is defined
    (the directive's own named state) but never selected -- no real
    scale-out signal exists anywhere in this factory. BOOT is not
    computed here (Python runs as a fresh, stateless subprocess per
    call -- it has no real process uptime to measure); the real Node
    server process uptime is checked at the Mission Control layer
    instead and can override this function's answer to BOOT."""
    import resilience_monitor
    import safe_mode
    import factory_state
    import evolution_queue

    resilience = resilience_monitor.assess_resilience()
    active_critical = [a for a in resilience.get("active_alerts", []) if a.get("severity") in ("critical", "emergency")]
    safe_mode_status = safe_mode.list_safe_mode_status()

    if active_critical or safe_mode_status["marketplace_publishing"]["unstable"]:
        return {
            "state": "RECOVERY",
            "reason": "Real active critical/emergency resilience alert(s) or a real active marketplace-publishing emergency stop.",
            "evidence": {"active_critical_alerts": active_critical, "marketplace_publishing_unstable": safe_mode_status["marketplace_publishing"]},
            "generated_at": _now_iso(),
        }

    if safe_mode_status["ai_generation"]["unstable"] or safe_mode_status["market_intelligence"]["unstable"]:
        return {
            "state": "MAINTENANCE",
            "reason": "A real subsystem (ai_generation or market_intelligence) is marked unstable via safe_mode.py.",
            "evidence": safe_mode_status,
            "generated_at": _now_iso(),
        }

    state = factory_state.load_state()
    if state.get("current_task"):
        # current_task (not active_workflow) is the reliable "in flight
        # right now" signal -- set_current_task()/clear_current_task()
        # correctly set and clear it around every real stage. A real,
        # pre-existing bug (found and fixed this round, both language
        # mirrors) made active_workflow stay permanently "sticky" to
        # whatever task last started, so it is cited here only as
        # secondary evidence, never the primary trigger.
        return {
            "state": "PRODUCTION",
            "reason": "factory_state.py reports a real current_task in flight.",
            "evidence": {"current_task": state.get("current_task"), "active_workflow": state.get("active_workflow")},
            "generated_at": _now_iso(),
        }

    evo = evolution_queue.list_evolution_queue()
    awaiting = evo.get("awaiting_approval", [])
    if awaiting:
        return {
            "state": "OPTIMIZING",
            "reason": "evolution_queue.py reports real proposal(s) AWAITING_FOUNDER_APPROVAL.",
            "evidence": {"awaiting_approval_count": len(awaiting)},
            "generated_at": _now_iso(),
        }

    measured = evolution_queue.list_measured_outcomes()
    not_yet_measured = [e for e in measured.get("entries", []) if e.get("status") == "NOT_YET_MEASURED"]
    if not_yet_measured:
        return {
            "state": "LEARNING",
            "reason": "evolution_queue.py reports real IMPLEMENTED proposal(s) not yet measured for real outcome.",
            "evidence": {"not_yet_measured_count": len(not_yet_measured)},
            "generated_at": _now_iso(),
        }

    return {
        "state": "READY",
        "reason": "No real RECOVERY/MAINTENANCE/PRODUCTION/OPTIMIZING/LEARNING condition is currently true.",
        "note": "SCALING is a defined state (per the directive) but is never real -- no real scale-out signal exists anywhere in this factory (single Express process, no worker pool, no queue system).",
        "generated_at": _now_iso(),
    }
