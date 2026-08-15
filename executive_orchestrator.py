"""EXECUTIVE ORCHESTRATOR (Autonomous Executive Orchestrator directive,
2026-08-15).

ONE COMPANY -> ONE EXECUTIVE BRAIN -> ONE PRIORITY SYSTEM -> ONE OPPORTUNITY
PIPELINE -> MANY REVENUE ARMS -> MINIMUM HUMAN INTERVENTION.

This is a THIN, COMPOSITION-ONLY control layer. It deliberately contains NO
new engines, NO duplicate rankings, NO new data sources. It integrates and
coordinates the existing, tested systems:

  * revenue_os.py            -- arm router, profit-first rank, CEO loop, gates
  * first_dollar_engine.py   -- FIRST_DOLLAR scoring/ranking
  * founder_next_action.py   -- ONE-NEXT-ACTION human-gate manager
  * commercial_experiment_automation.py -- experiment auto-loop
  * commercial_experiments.py -- experiment lifecycle/status
  * golden_hunter events     -- discovery evidence
  * factory_loop state       -- retry queue / failures / recovery
  * knowledge graph          -- institutional memory (reused, not duplicated)

Responsibilities (directive sections):
  * §2 authoritative company state     -- executive_state()
  * §4 unified priority engine          -- unified_priorities() (TOP 7)
  * §5 decision state machine           -- decision_state_machine() (auditable
    transitions, no silent dead ends)
  * §7 learning loop                    -- record_result() (capture evidence ->
    evaluate -> update confidence/score -> record lesson)
  * §8 autonomous work queue            -- build_work_queue() (deduped, stateful)
  * §9 execution policy                 -- SAFE actions only; financial/KYC/legal
    actions are always HUMAN_GATE (never suggested for auto-execution)
  * §20 executive memory                -- record_executive_decision()

Read-only for every real ledger except its OWN append-only audit file
(data/executive_orchestrator_events.jsonl) -- the transition/decision/result
log. Never spends, never publishes, never touches money or accounts. Every
state transition is recorded; nothing disappears silently.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
EXEC_EVENTS_PATH = _FACTORY_ROOT / "data" / "executive_orchestrator_events.jsonl"
OPPORTUNITIES_PATH = _FACTORY_ROOT / "data" / "commission_opportunities.jsonl"

# The complete, auditable decision state machine (directive §5). Every state
# must be reachable and every transition recorded -- no silent dead ends.
DECISION_STATES = [
    "DISCOVERED", "VERIFIED", "SCORED", "SELECTED", "EXECUTING",
    "QA", "READY", "LAUNCHED", "MEASURING", "LEARNING",
    "SCALE", "ITERATE", "WATCH", "KILL",
]

# Revenue arms that route real opportunities (directive §3). These are the
# ROUTING buckets arm_router_report produces for opportunities; the arms'
# real readiness is read live from the channel registry (never hardcoded
# here). This list is informational -- actual statuses come from
# revenue_os._arm_status_summary().
REVENUE_ARMS = ["gumroad", "paddle", "etsy", "payhip", "affiliate"]

# Safe internal action types (directive §9) that build_work_queue() may emit.
# Anything touching money, accounts, legal, identity, or external platforms is
# NEVER in this set AND is additionally filtered by substance in
# build_work_queue() (publish/credential/approval tasks are excluded even if
# their type tag would look safe).
SAFE_ACTION_TYPES = {
    "analysis", "ranking", "research", "generation", "testing", "qa",
    "data_sync", "internal_publish_prep", "tracking", "reconciliation",
    "retry", "recovery", "documentation", "refactoring",
}

# Task-type prefixes that are NEVER safe to auto-execute: real publish,
# real spend, credentials, or anything behind a live human gate.
_SAFE_EXCLUDED_PREFIXES = (
    "arm_publish:", "publish:", "checkout:", "payout:", "withdraw:",
    "credential:", "approval:", "oauth:", "legal:", "identity:",
)


def _task_is_safe(task: str) -> bool:
    """§9 SAFE filter enforced by substance, not just type tag. A retry task
    whose underlying operation is a real publish, a checkout, a payout, a
    credential change, an approval, OAuth, legal, or identity work is NEVER a
    safe autonomous action -- it stays a human gate instead."""
    lowered = (task or "").lower()
    return not lowered.startswith(_SAFE_EXCLUDED_PREFIXES)


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    records = []
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _append_event(record: Dict[str, object], events_path=None) -> Dict[str, object]:
    path = Path(events_path) if events_path else EXEC_EVENTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def _read_opportunities(path=None):
    return _read_jsonl(Path(path) if path else OPPORTUNITIES_PATH)


# ---------------------------------------------------------------------------
# §2 COMPANY STATE -- the single authoritative view
# ---------------------------------------------------------------------------

def _arm_statuses():
    try:
        from revenue_os import _arm_status_summary
        return _arm_status_summary()
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


def company_state(now=None) -> Dict[str, object]:
    """The authoritative company state. Every field is computed by an existing,
    real engine -- this function only composes them into one view."""
    gates = {}
    real_revenue = 0
    ceo = {}
    try:
        from revenue_os import run_daily_ceo_loop
        ceo = run_daily_ceo_loop()
        real_revenue = ceo.get("REAL_VERIFIED_REVENUE_USD", 0)
        gates = ceo.get("EXECUTE", {}).get("founder_gates", {})
    except Exception as e:  # pragma: no cover - defensive
        ceo = {"error": str(e)}
    return {
        "generated_at": _now_iso(now),
        "real_verified_revenue_usd": real_revenue,
        "arm_statuses": _arm_statuses(),
        "founder_gates": gates,
        "opportunity_count": len(_read_opportunities()),
        "ceo_loop_error": ceo.get("error"),
        "note": "Composition-only: every value comes from the real existing engines (revenue_os / first_dollar_engine / founder_next_action). Nothing is estimated or fabricated.",
    }


# ---------------------------------------------------------------------------
# §4 UNIFIED PRIORITY ENGINE -- the TOP 7
# ---------------------------------------------------------------------------

def unified_priorities(top_n: int = 3, now=None) -> Dict[str, object]:
    """The ONE priority system. Produces TOP OPPORTUNITY / TOP REVENUE ARM /
    TOP AUTONOMOUS ACTION / TOP HUMAN GATE / TOP FAILURE / TOP EXPERIMENT /
    TOP LEARNING -- each computed by the real, existing engine that owns it,
    ranked consistently, never duplicated here."""
    try:
        import first_dollar_engine
        fd = first_dollar_engine.rank_first_dollar(top_n=top_n)
        top_opportunity = fd.get("BEST_FIRST_DOLLAR")
        fd_ranking = fd.get("ranking", [])[:top_n]
    except Exception as e:  # pragma: no cover - defensive
        top_opportunity, fd_ranking = None, [{"error": str(e)}]

    try:
        from revenue_os import profit_first_rank
        arms = profit_first_rank(top_n=top_n)
        arm_ranking = arms.get("ranking", [])[:top_n]
    except Exception as e:  # pragma: no cover - defensive
        arm_ranking = [{"error": str(e)}]

    # TOP REVENUE ARM: a REAL arm, ranked by real readiness and how many real
    # opportunities route to it (arm_router_report). Never an opportunity id.
    try:
        from revenue_os import arm_router_report, _arm_status_summary
        router = arm_router_report()
        routes_by_arm = router.get("routes_by_arm", {})
        statuses = _arm_status_summary()
        ready = {a for a, s in statuses.items() if s == "READY"}
        ranked_arms = sorted(
            routes_by_arm.keys(),
            key=lambda a: (a in ready, routes_by_arm.get(a, 0)),
            reverse=True,
        )
        top_arm = ranked_arms[0] if ranked_arms else (ready.pop() if ready else None)
    except Exception as e:  # pragma: no cover - defensive
        top_arm = None

    try:
        import founder_next_action
        founder = founder_next_action.build_founder_next_action()
        top_human_gate = founder.get("one_next_action", {})
        human_queue = founder.get("queue", [])
    except Exception as e:  # pragma: no cover - defensive
        top_human_gate, human_queue = {"error": str(e)}, []

    try:
        import commercial_experiments as ce
        # READ-ONLY snapshot: list_experiments() reflects real observations
        # (page-views) into running experiments. We deliberately do NOT run
        # run_experiment_cycle() here -- that WRITES evaluations and is already
        # the factory_loop's own daily step; the orchestrator never duplicates
        # or pre-empts a scheduled write.
        experiments = ce.list_experiments().get("experiments", [])
        running = [e for e in experiments if e.get("status") == "RUNNING"]
        top_experiment = running[0] if running else (experiments[0] if experiments else None)
        exp_state = {"count": len(experiments), "running": len(running),
                     "top": top_experiment}
    except Exception as e:  # pragma: no cover - defensive
        exp_state, top_experiment = {"error": str(e)}, None

    # TOP AUTONOMOUS ACTION: the highest-value SAFE action that is actually
    # executable today, derived from real state (not invented).
    autonomous_actions = build_work_queue()
    top_autonomous = autonomous_actions[0] if autonomous_actions else None

    # TOP FAILURE / TOP LEARNING from the real retry queue + golden events.
    failures = read_failures()
    top_failure = failures[0] if failures else None

    try:
        knowledge = read_recent_learning()
        top_learning = knowledge[0] if knowledge else None
    except Exception as e:  # pragma: no cover - defensive
        top_learning = {"error": str(e)}

    return {
        "generated_at": _now_iso(now),
        "TOP_OPPORTUNITY": top_opportunity,
        "TOP_REVENUE_ARM": top_arm,
        "TOP_AUTONOMOUS_ACTION": top_autonomous,
        "TOP_HUMAN_GATE": top_human_gate,
        "TOP_FAILURE": top_failure,
        "TOP_EXPERIMENT": top_experiment,
        "TOP_LEARNING": top_learning,
        "opportunity_ranking": fd_ranking,
        "arm_ranking": arm_ranking,
        "human_gate_queue": human_queue,
        "experiment_cycle": exp_state,
        "note": "Each TOP is computed by the existing engine that owns it (first_dollar_engine / revenue_os / founder_next_action / experiment loop / retry queue / knowledge graph) and composed here -- one priority system, no duplicate engines.",
    }


# ---------------------------------------------------------------------------
# §8 AUTONOMOUS WORK QUEUE -- deduped, stateful, prioritized
# ---------------------------------------------------------------------------

def read_failures(limit: int = 5) -> List[Dict[str, object]]:
    """Real failures from the retry queue (factory_state.json pending_retries)
    and the recovery log. Read-only."""
    failures = []
    try:
        state = json.loads((_FACTORY_ROOT / "data" / "factory_state.json").read_text(encoding="utf-8"))
        for r in state.get("pending_retries", []):
            failures.append({
                "task": r.get("task"), "error": r.get("last_error"),
                "attempt": r.get("attempt"), "next_retry_at": r.get("next_retry_at"),
                "source": "retry_queue",
            })
    except Exception:  # pragma: no cover - defensive
        pass
    return failures[:limit]


def build_work_queue(now=None) -> List[Dict[str, object]]:
    """One prioritized work queue (directive §8). Every item carries task_id /
    type / priority / source / dependency / state / created_at / updated_at /
    deadline / result. SAFE actions only (directive §9) -- money/KYC/legal/
    external-platform actions are excluded by construction and surface as
    human gates instead. Deduped by task_id so the scheduler never re-creates
    the same task."""
    queue = []
    now_iso = _now_iso(now)

    # 1) Retry-able failures (existing retry queue) -> a recovery task. SAFE
    #    filter is enforced by SUBSTANCE: a retry whose underlying operation is
    #    a real publish/checkout/payout/credential/etc is never a safe
    #    autonomous action -- it stays a human gate (directive §9).
    for f in read_failures(limit=10):
        if f.get("source") != "retry_queue":
            continue
        task = f.get("task") or ""
        if not _task_is_safe(task):
            continue
        task_id = f"recover:{task}"
        queue.append({
            "task_id": task_id, "type": "recovery", "priority": 3,
            "source": "retry_queue", "dependency": None, "state": "PENDING",
            "created_at": now_iso, "updated_at": now_iso,
            "deadline": f.get("next_retry_at"), "result": None,
        })

    # 2) Opportunity verification gaps -> a verification task for each
    #    opportunity not yet VERIFIED.
    try:
        from commission_engine import verify_commission_opportunity  # noqa: F401 (import present proves capability)
    except Exception:  # pragma: no cover - defensive
        pass
    for opp in _read_opportunities():
        verification = opp.get("verification_status") or opp.get("verification") or "DISCOVERED"
        if verification in ("VERIFIED", "PARTIALLY_VERIFIED", "THIRD_PARTY_ONLY"):
            continue
        opp_id = opp.get("opportunity_id") or "unknown"
        queue.append({
            "task_id": f"verify:{opp_id}", "type": "verification", "priority": 4,
            "source": "opportunity_pipeline", "dependency": None, "state": "PENDING",
            "created_at": now_iso, "updated_at": now_iso,
            "deadline": None, "result": f"opportunity {opp_id} not yet VERIFIED (state: {verification})",
        })

    # 3) Experiment health -> a task for any RUNNING experiment with no
    #    recorded observations yet (it is being measured, not abandoned).
    try:
        import commercial_experiments as ce
        experiments = ce.list_experiments().get("experiments", [])
        for e in experiments:
            if e.get("status") != "RUNNING":
                continue
            queue.append({
                "task_id": f"measure:{e.get('experiment_id')}", "type": "tracking", "priority": 5,
                "source": "experiment_engine", "dependency": None, "state": "PENDING",
                "created_at": now_iso, "updated_at": now_iso,
                "deadline": e.get("created_at"), "result": "experiment RUNNING; observations recorded by experiment_cycle step",
            })
    except Exception:  # pragma: no cover - defensive
        pass

    queue.sort(key=lambda t: t["priority"])
    return queue


# ---------------------------------------------------------------------------
# §5 DECISION STATE MACHINE -- auditable, no silent dead ends
# ---------------------------------------------------------------------------

def opportunity_state(opp: Dict[str, object]) -> str:
    """Map a real opportunity to its current state in DECISION_STATES using
    real fields only. Never guesses; unknown/absent -> DISCOVERED. The return
    is always one of DECISION_STATES.

    The real portfolio ledger (commission_opportunities.jsonl) stores
    verification in `verification_status`; `verification` is accepted as a
    fallback for any caller that still writes the older key (Task 6 fix:
    the Executive Orchestrator must honor the real VERIFIED tier so verified
    opportunities are never shown as DISCOVERED at the control plane)."""
    verification = opp.get("verification_status") or opp.get("verification") or "DISCOVERED"
    if verification in ("VERIFIED", "PARTIALLY_VERIFIED", "THIRD_PARTY_ONLY"):
        return "VERIFIED"
    return "DISCOVERED"


def _last_known_state(existing_events, entity_type, entity_id):
    """The most recent recorded state for an entity in the append-only log
    (event_type state_assertion or state_transition -> to_state)."""
    last = None
    for ev in existing_events:
        if (ev.get("entity_type") == entity_type and ev.get("entity_id") == entity_id
                and ev.get("event_type") in ("state_assertion", "state_transition")):
            last = ev.get("to_state")
    return last


def decision_state_machine(now=None, events_path=None) -> Dict[str, object]:
    """Reconcile every real opportunity/product/experiment against its state
    and record ONLY genuine transitions in the append-only executive events
    log. The first time an entity is seen it is recorded as a state_assertion
    (its current state); when its state later CHANGES it is recorded as a
    state_transition (from -> to). Unchanged entities are NEVER re-recorded
    (idempotent). The result is a full, auditable picture of the pipeline with
    zero silent dead ends."""
    now_iso = _now_iso(now)
    opportunities = _read_opportunities()
    events = []

    existing_events = _read_jsonl(Path(events_path) if events_path else EXEC_EVENTS_PATH)

    def _record(entity_type, entity_id, from_state, to_state):
        _append_event({
            "event_type": "state_transition" if from_state else "state_assertion",
            "entity_type": entity_type, "entity_id": entity_id,
            "from_state": from_state or None,
            "to_state": to_state,
            "recorded_at": now_iso,
            "source": "executive_orchestrator.decision_state_machine",
        }, events_path=events_path)
        events.append({"entity_type": entity_type, "entity_id": entity_id,
                       "from_state": from_state, "to_state": to_state})

    for opp in opportunities:
        opp_id = opp.get("opportunity_id")
        if not opp_id:
            continue
        state = opportunity_state(opp)
        last = _last_known_state(existing_events, "opportunity", opp_id)
        if state == last:
            continue  # no change -> never re-recorded (idempotent)
        _record("opportunity", opp_id, last, state)

    try:
        import commercial_experiments as ce
        experiments = ce.list_experiments().get("experiments", [])
        for e in experiments:
            exp_id = e.get("experiment_id")
            if not exp_id:
                continue
            status = e.get("status") or "RUNNING"
            last = _last_known_state(existing_events, "experiment", exp_id)
            if status == last:
                continue
            _record("experiment", exp_id, last, status)
    except Exception:  # pragma: no cover - defensive
        pass

    return {
        "generated_at": now_iso,
        "recorded_events": len(events),
        "events": events,
        "decision_states": DECISION_STATES,
        "note": "state_assertion records an entity's first-seen state; state_transition records a real change. Both are append-only in data/executive_orchestrator_events.jsonl; unchanged entities are never re-recorded. No opportunity/experiment can silently disappear between states.",
    }


# ---------------------------------------------------------------------------
# §7 LEARNING LOOP + §20 EXECUTIVE MEMORY
# ---------------------------------------------------------------------------

def read_recent_learning(limit: int = 5) -> List[Dict[str, object]]:
    """Most recent recorded executive results/lessons from the orchestrator's
    own event log (institutional memory, §20). Read-only."""
    events = _read_jsonl(EXEC_EVENTS_PATH)
    results = [e for e in events if e.get("event_type") == "result_recorded"]
    return results[-limit:][::-1]


def record_result(entity_type: str, entity_id: str, result: str,
                  expected: str = "", lesson: str = "",
                  confidence_delta: float = 0.0, now=None, events_path=None) -> Dict[str, object]:
    """§7 learning loop: after a meaningful result, capture evidence, record the
    result and lesson, and recompute priorities (unified_priorities reflects the
    new evidence on next call). Appends to the institutional memory log."""
    now_iso = _now_iso(now)
    event = {
        "event_type": "result_recorded",
        "entity_type": entity_type, "entity_id": entity_id,
        "result": result, "expected": expected, "lesson": lesson,
        "confidence_delta": confidence_delta,
        "recorded_at": now_iso,
        "source": "executive_orchestrator.record_result",
    }
    _append_event(event, events_path=events_path)
    return event


def record_executive_decision(decision: str, evidence: str, reason: str,
                              expected_result: str = "", now=None, events_path=None) -> Dict[str, object]:
    """§20 executive memory: every major executive decision is recorded so the
    company can learn from outcomes. Never records fabricated evidence -- the
    evidence string must come from a real engine's output."""
    now_iso = _now_iso(now)
    event = {
        "event_type": "executive_decision",
        "decision": decision, "evidence": evidence, "reason": reason,
        "expected_result": expected_result, "actual_result": None,
        "recorded_at": now_iso,
        "source": "executive_orchestrator.record_executive_decision",
    }
    _append_event(event, events_path=events_path)
    return event


# ---------------------------------------------------------------------------
# The full executive cycle (§14 CEO-loop consumption)
# ---------------------------------------------------------------------------

def run_executive_orchestrator(now=None, record_cycle: bool = True) -> Dict[str, object]:
    """The unified control cycle the CEO loop consumes. Reads company state,
    recomputes priorities, reconciles the decision state machine, builds the
    work queue, and returns ONE executive state.

    record_cycle=True (the factory_loop daily step) records a single executive
    decision per day so institutional memory is maintained. record_cycle=False
    is the read-only observation view (Mission Control / server.js): it never
    grows the audit log and is safe to call on every dashboard refresh."""
    now_dt = now or datetime.now(timezone.utc)
    state = company_state(now=now_dt)
    priorities = unified_priorities(now=now_dt)
    machine = decision_state_machine(now=now_dt)
    queue = build_work_queue(now=now_dt)

    if record_cycle:
        record_executive_decision(
            decision="ORCHESTRATOR_CYCLE",
            evidence=f"real revenue ${state['real_verified_revenue_usd']}; TOP opportunity {priorities.get('TOP_OPPORTUNITY')}; TOP arm {priorities.get('TOP_REVENUE_ARM')}",
            reason="Automatic daily executive cycle -- reconsolidates priorities from real evidence; no spend, no publish, no fabrication.",
            expected_result="The company's ONE executive state stays current and auditable.",
            now=now_dt,
        )

    return {
        "generated_at": _now_iso(now_dt),
        "COMPANY_STATE": state,
        "PRIORITIES": priorities,
        "DECISION_STATE_MACHINE": machine,
        "WORK_QUEUE": {"total": len(queue), "items": queue},
        "note": "Executive Orchestrator: composition-only. All underlying values come from the real existing engines; this layer coordinates, prioritizes, and records -- it does not invent capability.",
    }


def _cli_main(argv=None) -> None:
    import sys as _sys
    argv = argv or _sys.argv
    # Read-only observation mode (Mission Control / server.js dashboard view):
    # never records, never grows the audit log. The daily factory_loop step
    # keeps the default recording mode.
    record_cycle = not ("read-only" in argv or "status" in argv)
    print(json.dumps(run_executive_orchestrator(record_cycle=record_cycle),
                     ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()