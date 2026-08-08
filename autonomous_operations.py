"""Galaxy Forge Autonomous Operations Layer (Phase 19, ADR-209, 2026-08-08).

Answers the founder's "AUTONOMOUS OPERATIONS & CONTINUOUS IMPROVEMENT ENGINE"
directive. Research before writing any code found this factory already runs
the real OBSERVE->DETECT->UNDERSTAND->PRIORITIZE->RECOMMEND loop across many
already-real systems (executive_brain.py, resilience_monitor.py,
evolution_queue.py, adaptive_priority_queue.py, founder_console.py) -- this
module's real, narrow job is the two genuinely missing pieces:

1. A named Autonomy Level taxonomy (0-6) + an Action Authorization Engine
   that never infers authorization -- every action category cites the real
   existing enforcement mechanism that actually gates it (or honestly has
   none yet).
2. A unified Autonomous Operations Queue merging 4 already-real sources into
   one shape, plus 2 genuinely new reports (automation-candidate detection,
   an honest incident-lifecycle view) this factory never had before.

No new execution capability is introduced anywhere in this module. Every
`authorize_action()` call is a real, deterministic classification -- it
never approves, publishes, reallocates, or executes anything itself. The 4
permanently human-gated action classes (evolution execution, capital
reallocation, business retirement, elevated-risk publishing) are classified
here as LEVEL 5, exactly matching their real, unchanged, existing gates
(evolution_queue.py::approve_proposal(), channels/publish_protection.py::
approve_first_publish()/approve_elevated_risk_publish()) -- never loosened.
"""

from datetime import datetime, timezone
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEFAULT_VERIFICATION_ATTEMPTS_PATH = os.path.join(DATA_DIR, "verification_attempts.jsonl")


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_jsonl(path):
    if not path or not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


# ---------------------------------------------------------------------------
# Section 2 -- Autonomy Levels
# ---------------------------------------------------------------------------

AUTONOMY_LEVELS = {
    0: {"name": "OBSERVE ONLY",
        "description": "Reads real state, produces no recommendation or action. Example: resilience_monitor.assess_resilience(), knowledge_decay.assess_all_known_knowledge()."},
    1: {"name": "ANALYZE",
        "description": "Computes a real derived judgment over observed state, still produces no action item. Example: executive_questions.answer_strategic_questions()."},
    2: {"name": "RECOMMEND",
        "description": "Surfaces a real, evidence-cited candidate action for a human (or a higher-authority automated step) to consider. Never executes. Example: executive_brain.build_executive_directive(), evolution_queue.simulate_proposal()/decide_proposal()."},
    3: {"name": "EXECUTE REVERSIBLE LOW-RISK ACTIONS",
        "description": "Real, already-automatic actions that touch only this factory's own disposable/regenerable internal state -- never money, never a customer, never an external account. Example: factory_loop.js's daily/weekly/monthly report generation, health-snapshot recording, knowledge-graph snapshot rebuild, resilience incident recording."},
    4: {"name": "EXECUTE CONTROLLED BUSINESS OPERATIONS",
        "description": "Real, already-automatic actions against an external system, gated by a real, already-enforced control at time of execution. Example: distributor.py::distribute() for an already-proven arm, gated live by channels/publish_protection.py::check_publish_allowed()."},
    5: {"name": "HUMAN APPROVAL REQUIRED",
        "description": "A real action that a human can authorize through an explicit, existing mechanism, but that the system never initiates itself. Example: evolution_queue.py::approve_proposal()/mark_implemented(), channels/publish_protection.py::approve_first_publish()/approve_elevated_risk_publish(), any capital-reallocation or business-retirement decision."},
    6: {"name": "NEVER AUTOMATE",
        "description": "No context, override, or founder instruction authorizes this category through this module -- a permanent, hardcoded refusal (Section 29). Example: granting the system its own permissions, disabling monitoring, deleting an audit trail, silently modifying a historical financial record, creating a third-party account, entering credentials, executing a real payment merely to test."},
}

# Section 3 -- Action Authorization Engine. A real, disclosed, small
# taxonomy of action *categories* (not a hand-tagged list of every one of
# this factory's 166+ individual endpoints -- the same "explainable, not
# exhaustive" discipline KNOWLEDGE_QUALITY_REPORT.md already established
# for composite scores). Every entry cites the real function that actually
# enforces it today, or honestly discloses that no real enforcement exists
# yet beyond this module's own classification.
ACTION_CATEGORY_AUTONOMY = {
    "read_only_reporting": {
        "level": 0,
        "citation": "No mutation possible -- every Mission Control SERVICE_REGISTRY GET handler.",
    },
    "recommendation_generation": {
        "level": 2,
        "citation": "executive_brain.py::build_executive_directive() / adaptive_priority_queue.py -- requires_founder_approval is always True.",
    },
    "evolution_simulate_decide": {
        "level": 2,
        "citation": "evolution_queue.py::simulate_proposal()/decide_proposal() -- routes only as far as AWAITING_FOUNDER_APPROVAL, never further.",
    },
    "internal_disposable_state_write": {
        "level": 3,
        "citation": "factory_loop.js's real once-per-calendar-day/week/month tick functions -- write only to this factory's own regenerable reports/*.md, data/*_snapshot*.json(l).",
    },
    "proven_channel_publish": {
        "level": 4,
        "citation": "channels/publish_protection.py::check_publish_allowed() -- real, live-enforced per-arm caps/cooldown/risk-score gate, checked immediately before every real distributor.py::distribute() call.",
    },
    "new_or_elevated_risk_publish": {
        "level": 5,
        "citation": "channels/publish_protection.py::approve_first_publish()/approve_elevated_risk_publish() -- single-use, founder-only, consumed by the very next real attempt.",
    },
    "evolution_approve_execute": {
        "level": 5,
        "citation": "evolution_queue.py::approve_proposal()/reject_proposal()/mark_implemented() -- 'Never called automatically' per the function's own docstring, reconfirmed by this factory's founder 6+ times (ADR-133/134/139/142/144/147/157).",
    },
    "capital_reallocation": {
        "level": 5,
        "citation": "capital_allocation_engine.py has no real reallocation-execution function at all -- 'the engine recommends, the Founder decides' (CLAUDE.md, Capital Allocation Engine section).",
    },
    "business_retirement": {
        "level": 5,
        "citation": "No real business-retirement system exists anywhere in this factory, by design (ADR-142) -- classified Level 5 in anticipation, not because a real execution path exists to gate.",
    },
    "real_payment_or_transaction": {
        "level": 6,
        "citation": "Phase 15's own explicit rule: never initiate a real payment merely to test. No code path in this factory can execute a real transaction without a real, separately-authorized customer action.",
    },
    "governance_or_permission_change": {
        "level": 6,
        "citation": "No code path anywhere in this factory grants itself permissions, disables monitoring, deletes an audit trail, or removes a human-approval requirement -- Section 29, enforced by absence of any such function, not by a runtime check.",
    },
    "account_or_credential_creation": {
        "level": 6,
        "citation": "Claude's own standing operating rule (never create accounts, never handle credentials) plus this factory's own architecture -- confirmed by direct search, zero account-creation code exists anywhere.",
    },
    # Enterprise & Transformation Division (ADR-214, Phase 24,
    # 2026-08-08): 2 real, additive categories -- no existing category
    # precisely named contract/legal commitment before this round.
    "enterprise_contract_commitment": {
        "level": 5,
        "citation": "No real contract-signing code path exists anywhere in this factory -- classified Level 5 in anticipation, matching business_retirement's own precedent (ADR-142), never a real execution path to gate yet.",
    },
    "enterprise_legal_or_liability_commitment": {
        "level": 6,
        "citation": "Legal terms, liability, indemnification, data-processing obligations, and regulatory commitments always require real human/legal review -- no automated path may ever agree to these, per Section 26 of ADR-214's own directive.",
    },
}


def classify_action_autonomy(category):
    """Real, deterministic lookup. Returns None for an unrecognized
    category -- the caller (authorize_action) must never guess a level for
    something this registry doesn't already name."""
    return ACTION_CATEGORY_AUTONOMY.get(category)


def authorize_action(category, context=None):
    """The real Action Authorization Engine (Section 3). Never infers
    authorization: Level 0-4 categories are allowed by design (their real
    enforcement already happens inside the cited function itself, not
    here); Level 5 requires an explicit, real `founder_approved=True` +
    a non-empty `approval_reference` in `context`; Level 6 refuses
    unconditionally, regardless of anything in `context`."""
    context = context or {}
    entry = classify_action_autonomy(category)
    if entry is None:
        return {
            "category": category,
            "required_level": None,
            "decision": "REFUSE",
            "reasoning": "Unrecognized action category -- never infer authorization for an action this registry does not already name.",
        }

    level = entry["level"]
    level_name = AUTONOMY_LEVELS[level]["name"]

    if level <= 4:
        decision, reasoning = "ALLOW", (
            f"Level {level} ({level_name}) -- real enforcement already happens inside the cited function itself; "
            f"this classification does not grant new authority."
        )
    elif level == 5:
        approved = context.get("founder_approved") is True and bool(context.get("approval_reference"))
        decision = "ALLOW" if approved else "REFUSE"
        reasoning = (
            "Level 5 (HUMAN APPROVAL REQUIRED) -- " +
            ("real founder approval reference provided." if approved else
             "no real founder approval reference provided in context; refusing rather than inferring authorization.")
        )
    else:
        decision, reasoning = "REFUSE", (
            "Level 6 (NEVER AUTOMATE) -- no context can authorize this category through this module, by permanent design (Section 29)."
        )

    return {
        "category": category,
        "required_level": level,
        "required_level_name": level_name,
        "real_enforcement_citation": entry["citation"],
        "decision": decision,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Section 15 -- Automation Candidate Detection
# ---------------------------------------------------------------------------

def automation_candidate_report(verification_attempts_path=None, evolution_queue_state_path=None, now=None):
    """Real, disclosed catalog -- not a mechanical task-frequency scanner
    (this factory has no real per-task time-tracking telemetry anywhere to
    scan, confirmed by direct search; building a scanner over a
    nonexistent signal would be fabrication). Each entry cites a real,
    already-logged repeated task."""
    now = now or datetime.now(timezone.utc)
    candidates = []

    attempts = _read_jsonl(verification_attempts_path or DEFAULT_VERIFICATION_ATTEMPTS_PATH)
    if attempts:
        blocked = [a for a in attempts if a.get("status") == "BLOCKED"]
        candidates.append({
            "task": "Manual web-evidence verification for the Proof of Payment gate",
            "frequency": len(attempts),
            "time_cost": "Unknown -- no per-attempt duration tracked",
            "error_risk": "Low -- structured, append-only ledger with a human-recorded real outcome per attempt",
            "business_value": "High -- gates profit_oracle.py's real Proof of Payment doctrine (ADR-121), this factory's universal acceptance hard gate",
            "automation_difficulty": f"High -- {len(blocked)}/{len(attempts)} real recorded attempts were blocked by real target-site anti-bot protection (HTTP 403)",
            "automation_risk": "Bypassing bot-detection controls to force automation is a prohibited action category, not merely a technical gap",
            "potential_savings": "Unknown -- no real time-cost baseline exists to measure savings against",
            "classification": "KEEP_HUMAN",
            "reasoning": "Both technically blocked (real, repeated 403s) and policy-blocked (bot-detection bypass is never authorized) -- a permanent human task by design, not a capability gap awaiting automation.",
            "source": f"multi_source_intelligence/manual_verification.py's real ledger ({verification_attempts_path or DEFAULT_VERIFICATION_ATTEMPTS_PATH})",
        })

    pending_count = None
    try:
        import evolution_queue
        evo = evolution_queue.list_evolution_queue(state_path=evolution_queue_state_path)
        pending_count = len(evo.get("awaiting_approval", []))
    except Exception:
        pending_count = None

    candidates.append({
        "task": "Evolution proposal / capital reallocation / new-channel publish founder approval",
        "frequency": pending_count if pending_count is not None else "Unknown -- evolution_queue.py unavailable",
        "time_cost": "Unknown -- no real per-decision duration tracked",
        "error_risk": "N/A -- a human judgment call, not an automatable computation",
        "business_value": "Critical -- the real enforcement point for this factory's 4 permanently protected human-gates",
        "automation_difficulty": "N/A -- governance-mandated, not a technical gap",
        "automation_risk": "Automating this would directly violate ADR-133/134/139/142 (reconfirmed 6+ times this session)",
        "potential_savings": "None sought -- this is not a cost to reduce",
        "classification": "KEEP_HUMAN",
        "reasoning": "Explicit, repeated founder decision to keep this human-gated (see [[feedback_final_executive_directive_scope]] in memory) -- never a capability gap to close.",
        "source": "evolution_queue.py / channels/publish_protection.py / capital_allocation_engine.py governance design",
    })

    return {
        "generated_at": _now_iso(now),
        "candidates": candidates,
        "note": "A real, disclosed catalog of this factory's known repeated tasks -- not a mechanical scan, since no real task-frequency telemetry exists broadly enough to scan. Every entry classifies AUTOMATE_NOW/AUTOMATE_LATER/KEEP_HUMAN/REMOVE with a cited, real reason -- never 'automate because repetitive.'",
    }


# ---------------------------------------------------------------------------
# Section 24 -- Incident Lifecycle (honest view over resilience_monitor.py)
# ---------------------------------------------------------------------------

INCIDENT_LIFECYCLE_STAGES = [
    "DETECTED", "TRIAGED", "CONTAINED", "INVESTIGATED",
    "RECOVERED", "VERIFIED", "CLOSED", "LEARNED",
]


def incident_lifecycle_view(incidents_path=None):
    """resilience_monitor.py's real incident record (Section 24's
    request) only distinguishes two real states today -- 'opened' and
    'resolved'. This view honestly maps those onto the directive's named
    8-stage vocabulary rather than inventing timestamps for the 6 stages
    this factory has no real, separately-recorded signal for yet."""
    from resilience_monitor import list_incidents
    incidents = list_incidents(incidents_path=incidents_path)

    views = []
    for inc in incidents:
        real_stage = "CLOSED" if inc.get("event") == "resolved" else "DETECTED"
        learned = bool(inc.get("root_cause") and inc.get("root_cause") != "Unknown -- no real root-cause template exists yet for this area")
        views.append({
            "incident_id": inc.get("incident_id"),
            "area": inc.get("area"),
            "real_stage": real_stage,
            "real_stage_position": f"{real_stage} (position {INCIDENT_LIFECYCLE_STAGES.index(real_stage) + 1} of {len(INCIDENT_LIFECYCLE_STAGES)})",
            "unmeasured_stages": [s for s in INCIDENT_LIFECYCLE_STAGES if s not in ("DETECTED", "CLOSED")],
            "learned": "LEARNED" if learned else "NOT_YET -- no real, cited root-cause template exists for this area",
            "raw": inc,
        })

    return {
        "generated_at": _now_iso(),
        "incidents": views,
        "total": len(views),
        "note": "resilience_monitor.py's real incident record only carries 'opened'/'resolved' -- TRIAGED/CONTAINED/INVESTIGATED/RECOVERED/VERIFIED have no real, separately-timestamped signal yet. Disclosed honestly rather than inferred from the resolution event alone.",
    }


# ---------------------------------------------------------------------------
# Section 4 -- Unified Autonomous Operations Queue
# ---------------------------------------------------------------------------

def unified_operations_queue(decisions_path=None, evolution_queue_state_path=None,
                              incidents_path=None, publish_protection_state_path=None,
                              verification_attempts_path=None, now=None):
    """Merges 5 already-real sources into one shape -- never a second,
    competing ranking or priority engine. Priority/Risk/Confidence fields
    stay honestly heterogeneous across source types rather than being
    normalized into one fabricated composite score."""
    now = now or datetime.now(timezone.utc)
    items = []

    try:
        from adaptive_priority_queue import build_adaptive_priority_queue
        apq = build_adaptive_priority_queue(decisions_path=decisions_path)
        for entry in apq.get("queue", [])[:15]:
            items.append({
                "type": "recommendation",
                "priority": entry.get("priority"),
                "reason": entry.get("recommended_action") or entry.get("problem"),
                "evidence": entry.get("evidence"),
                "risk": entry.get("risk"),
                "confidence": entry.get("confidence"),
                "required_resources": entry.get("required_resources", "Unknown"),
                "authorization": authorize_action("recommendation_generation"),
                "owner": entry.get("owner", "founder"),
                "status": entry.get("status", "OPEN"),
                "created": None,
                "updated": entry.get("last_evaluation"),
                "deadline": None,
                "weak_evidence": entry.get("weak_evidence"),
                "source": "adaptive_priority_queue.build_adaptive_priority_queue()",
            })
    except Exception as e:
        items.append({"type": "recommendation", "status": "SOURCE_UNAVAILABLE", "reason": str(e), "source": "adaptive_priority_queue"})

    try:
        from resilience_monitor import list_incidents
        for inc in list_incidents(incidents_path=incidents_path):
            if inc.get("event") == "resolved":
                continue
            items.append({
                "type": "incident",
                "priority": inc.get("severity"),
                "reason": inc.get("detail") or inc.get("area"),
                "evidence": inc.get("evidence"),
                "risk": inc.get("severity"),
                "confidence": "real -- mechanically detected by resilience_monitor.py",
                "required_resources": "Unknown",
                "authorization": authorize_action("read_only_reporting"),
                "owner": "founder",
                "status": "OPEN",
                "created": inc.get("recorded_at"),
                "updated": inc.get("recorded_at"),
                "deadline": None,
                "source": "resilience_monitor.list_incidents()",
            })
    except Exception as e:
        items.append({"type": "incident", "status": "SOURCE_UNAVAILABLE", "reason": str(e), "source": "resilience_monitor"})

    try:
        import evolution_queue
        evo = evolution_queue.list_evolution_queue(state_path=evolution_queue_state_path)
        for entry in evo.get("awaiting_approval", []):
            history = entry.get("stage_history") or []
            items.append({
                "type": "approval_pending",
                "priority": "HIGH -- blocks real evolution progress",
                "reason": entry.get("tool") or entry.get("proposal_id"),
                "evidence": entry.get("decision_flags"),
                "risk": entry.get("simulation", {}).get("rollback_complexity") if isinstance(entry.get("simulation"), dict) else None,
                "confidence": "real",
                "required_resources": "Founder review time",
                "authorization": authorize_action("evolution_approve_execute"),
                "owner": "founder",
                "status": "AWAITING_FOUNDER_APPROVAL",
                "created": history[0].get("at") if history else None,
                "updated": history[-1].get("at") if history else None,
                "deadline": None,
                "source": "evolution_queue.list_evolution_queue().awaiting_approval",
            })
    except Exception as e:
        items.append({"type": "approval_pending", "status": "SOURCE_UNAVAILABLE", "reason": str(e), "source": "evolution_queue"})

    try:
        from founder_console import build_founder_queue_partial
        fq = build_founder_queue_partial(decisions_path=decisions_path,
                                          evolution_queue_state_path=evolution_queue_state_path,
                                          publish_protection_state_path=publish_protection_state_path)
        for item in fq.get("pending_decisions", []):
            niche = item.get("niche", item) if isinstance(item, dict) else item
            items.append({
                "type": "decision_pending",
                "priority": "MEDIUM",
                "reason": f"DEFERRED niche awaiting re-evaluation: {niche}",
                "evidence": item,
                "risk": "Unknown",
                "confidence": "real",
                "required_resources": "Founder review time",
                "authorization": authorize_action("recommendation_generation"),
                "owner": "founder",
                "status": "DEFERRED",
                "created": None,
                "updated": None,
                "deadline": None,
                "source": "founder_console.build_founder_queue_partial().pending_decisions",
            })
    except Exception as e:
        items.append({"type": "decision_pending", "status": "SOURCE_UNAVAILABLE", "reason": str(e), "source": "founder_console"})

    for cand in automation_candidate_report(verification_attempts_path=verification_attempts_path,
                                             evolution_queue_state_path=evolution_queue_state_path, now=now)["candidates"]:
        items.append({
            "type": "automation_candidate",
            "priority": "LOW -- informational",
            "reason": cand["task"],
            "evidence": {"frequency": cand["frequency"]},
            "risk": cand["automation_risk"],
            "confidence": "real",
            "required_resources": "N/A",
            "authorization": authorize_action("read_only_reporting"),
            "owner": "system",
            "status": cand["classification"],
            "created": None,
            "updated": None,
            "deadline": None,
            "source": "autonomous_operations.automation_candidate_report()",
        })

    by_type = {}
    for it in items:
        by_type[it["type"]] = by_type.get(it["type"], 0) + 1

    return {
        "generated_at": _now_iso(now),
        "total_items": len(items),
        "items_by_type": by_type,
        "queue": items,
        "note": "A real merge of 5 already-real sources -- never a second, competing ranking engine. Priority/Risk/Confidence stay honestly heterogeneous across source types, not normalized into one fabricated score.",
    }


# ---------------------------------------------------------------------------
# Section 12 -- Daily Autonomous Review (citation over ceo_home.py)
# ---------------------------------------------------------------------------

def daily_autonomous_review(decisions_path=None, evolution_queue_state_path=None,
                             incidents_path=None, publish_protection_state_path=None, now=None):
    """Real citation aggregator -- ceo_home.py (ADR-184) already computes
    a real, fast 60-second daily briefing; this function reshapes its real
    output plus the real unified queue into the directive's named
    Top-5-by-category buckets, computing nothing twice."""
    now = now or datetime.now(timezone.utc)

    try:
        import ceo_home
        briefing = ceo_home.build_ceo_home_briefing(decisions_path=decisions_path)
    except Exception as e:
        briefing = {"error": str(e)}

    queue = unified_operations_queue(decisions_path=decisions_path,
                                      evolution_queue_state_path=evolution_queue_state_path,
                                      incidents_path=incidents_path,
                                      publish_protection_state_path=publish_protection_state_path,
                                      now=now)

    incidents = [i for i in queue["queue"] if i["type"] == "incident"][:5]
    recs = [i for i in queue["queue"] if i["type"] == "recommendation"][:5]
    approvals = [i for i in queue["queue"] if i["type"] in ("approval_pending", "decision_pending")][:5]
    automation = [i for i in queue["queue"] if i["type"] == "automation_candidate"][:5]

    return {
        "generated_at": _now_iso(now),
        "company_health_briefing": briefing,
        "top_5_risks": incidents,
        "top_5_actions": recs,
        "top_5_opportunities": briefing.get("highest_roi_opportunity") if isinstance(briefing, dict) else None,
        "top_5_improvements": automation,
        "items_requiring_ceo_approval": approvals,
        "note": "Citation-only over ceo_home.build_ceo_home_briefing() (ADR-184) + unified_operations_queue() -- computes nothing new.",
    }


# ---------------------------------------------------------------------------
# Section 26 -- Autonomous Daily Score
# ---------------------------------------------------------------------------

def autonomous_daily_score(now=None, decisions_path=None, evolution_queue_state_path=None,
                            incidents_path=None, publish_protection_state_path=None):
    """Every dimension is either a real citation of an already-real
    function or an honest NOT_MEASURABLE -- no single composite number is
    produced, matching KNOWLEDGE_QUALITY_REPORT.md's own established
    refusal to average dimensions with genuinely different bases."""
    now = now or datetime.now(timezone.utc)
    dims = {}

    try:
        queue = unified_operations_queue(decisions_path=decisions_path,
                                          evolution_queue_state_path=evolution_queue_state_path,
                                          incidents_path=incidents_path,
                                          publish_protection_state_path=publish_protection_state_path, now=now)
        approvals_pending = queue["items_by_type"].get("approval_pending", 0) + queue["items_by_type"].get("decision_pending", 0)
        dims["human_intervention"] = {"value": approvals_pending, "unit": "items awaiting founder action today",
                                       "source": "autonomous_operations.unified_operations_queue()"}
    except Exception as e:
        dims["human_intervention"] = {"value": "UNKNOWN", "reason": str(e)}

    try:
        from resilience_monitor import assess_resilience
        r = assess_resilience()
        dims["commercial_reliability"] = {"value": r.get("resilience_score"), "unit": "0-100, real, only over data-available findings",
                                           "source": "resilience_monitor.assess_resilience()"}
    except Exception as e:
        dims["commercial_reliability"] = {"value": "NOT_MEASURABLE", "reason": str(e)}

    try:
        from ai_capability.registry import list_providers
        providers = list_providers()
        dims["ai_reliability"] = {"value": providers, "unit": "real per-provider Groq stats (only live provider today)",
                                   "source": "ai_capability/registry.py::list_providers()"}
    except Exception as e:
        dims["ai_reliability"] = {"value": "NOT_MEASURABLE", "reason": str(e)}

    try:
        import evolution_queue as eq
        evo = eq.list_evolution_queue(state_path=evolution_queue_state_path)
        dims["continuous_improvement"] = {"value": evo.get("stage_distribution"), "unit": "real proposal stage distribution",
                                           "source": "evolution_queue.list_evolution_queue()"}
    except Exception as e:
        dims["continuous_improvement"] = {"value": "NOT_MEASURABLE", "reason": str(e)}

    try:
        from executive_brain import _knowledge_growth_trend
        dims["knowledge_growth"] = {"value": _knowledge_growth_trend(), "unit": "real node-count delta vs. previous snapshot",
                                     "source": "executive_brain._knowledge_growth_trend()"}
    except Exception as e:
        dims["knowledge_growth"] = {"value": "NOT_MEASURABLE", "reason": str(e)}

    dims["automation_success"] = {"value": "NOT_MEASURABLE", "reason": "No real per-autonomous-action success/failure counter exists across this factory yet -- individual pipelines (e.g. lib/metrics.js's per-route error_rate_pct) measure their own narrow slice, never aggregated into one real 'automation success rate.'"}
    dims["recovery_success"] = {"value": "NOT_MEASURABLE", "reason": "lib/metrics.js tracks per-route lastSuccessAt/lastFailureAt (ADR-157) but no real aggregate recovery-success ratio has been computed from it yet."}
    dims["customer_trust"] = {"value": "SEE trust-audit-report", "reason": "trust_audit.py (ADR-189) is the real, already-built citation source -- not duplicated here."}
    dims["data_integrity"] = {"value": "SEE /health storage_integrity", "reason": "lib/health_checks.js already performs real per-line JSON/JSONL validation -- not duplicated here."}
    dims["decision_accuracy"] = {"value": "SEE evolution_queue outcome measurements", "reason": "evolution_queue.py's real IMPROVED/DEGRADED/NO_CHANGE/NOT_ENOUGH_DATA verdicts (ADR-143) are the real signal -- not duplicated here."}

    return {
        "generated_at": _now_iso(now),
        "dimensions": dims,
        "note": "No single composite score is reported -- 5 of 10 named dimensions are real citations of already-computed values, 5 are honest NOT_MEASURABLE/SEE-elsewhere pointers. Averaging them would produce a number that looks precise and means very little.",
    }
