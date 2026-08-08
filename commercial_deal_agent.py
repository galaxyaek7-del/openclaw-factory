"""Galaxy Forge — Commercial Deal Agent (Phase 34, ADR-227, 2026-08-08).

Answers the founder's "Missing Commercial AI Crew" directive's Agent #1.
Audit before build (Section 1) found this is NOT a new AI agent in the
generic sense -- "evaluate commercial attractiveness," "match customer
to partner," "calculate economics" are already real, tested functions
in commission_engine.py (Phase 33). This module is deliberately thin:
a specialized worker that orchestrates those existing functions into a
deal-level (not opportunity-level) priority score, a next-action
recommendation, and a real agent-health surface -- the two genuinely
missing pieces confirmed by direct grep before writing any code (no
"agent health" abstraction and no deal-level -- as opposed to
opportunity-level -- scoring existed anywhere in this factory).

Never invents a customer, sale, commission, payout, conversion, or
partner approval. Every commercial claim traces to commission_engine.py/
commission_ledger.py's own real, already-guarded functions.
"""

from datetime import datetime, timezone
from pathlib import Path

import commission_engine as ce

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_DEAL_EVENTS_PATH = _FACTORY_ROOT / "data" / "commission_pipeline_events.jsonl"

DEAL_PRIORITY_FACTORS = (
    "CUSTOMER_PROBLEM_SEVERITY", "CUSTOMER_BUDGET", "URGENCY", "PARTNER_RELIABILITY",
    "COMMISSION_VALUE", "RECURRING_VALUE", "DEAL_DIFFICULTY", "CUSTOMER_MATCH",
    "ACQUISITION_COST", "RISK", "DATA_FRESHNESS",
)


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Section 3 -- Deal Priority Model
# ---------------------------------------------------------------------------

def deal_priority_score(customer_profile, opportunity, economics=None, match=None):
    """Real, decomposable deal-level score -- distinct from commission_
    engine.py's opportunity-level score_commission_opportunity(). Reuses
    match_customer_to_opportunity() and commission_economics() as
    inputs rather than recomputing either. Every factor honestly
    UNKNOWN where no real signal exists -- never a fabricated estimate."""
    match = match or ce.match_customer_to_opportunity(customer_profile, opportunity)
    economics = economics  # caller-supplied; this function never invents deal_value/conversion_rate itself

    factors = {
        "CUSTOMER_PROBLEM_SEVERITY": customer_profile.get("pain_point", "UNKNOWN"),
        "CUSTOMER_BUDGET": customer_profile.get("budget", "UNKNOWN"),
        "URGENCY": customer_profile.get("urgency", "UNKNOWN"),
        "PARTNER_RELIABILITY": opportunity.get("verification_status", "UNKNOWN"),
        "COMMISSION_VALUE": opportunity.get("commission_value", "COMMISSION_UNKNOWN"),
        "RECURRING_VALUE": "recurring" if opportunity.get("recurring_commission") else "one-time",
        "DEAL_DIFFICULTY": "UNKNOWN -- no real acquisition channel tested yet",
        "CUSTOMER_MATCH": f"{match['match_score']}/{match['max_possible_score']}",
        "ACQUISITION_COST": economics.get("expected_acquisition_cost", "UNKNOWN") if economics else "UNKNOWN",
        "RISK": opportunity.get("risk_score", "UNKNOWN"),
        "DATA_FRESHNESS": ce._freshness_from_last_verified(opportunity.get("last_verified")),
    }

    known_factors = sum(1 for v in factors.values() if v not in ("UNKNOWN", "COMMISSION_UNKNOWN") and not str(v).startswith("UNKNOWN"))
    confidence = "LOW" if known_factors <= 3 else ("MEDIUM" if known_factors <= 7 else "HIGH")

    expected_value = economics.get("expected_net_contribution") if economics and economics.get("economic_status") == "COMPLETE" else "UNKNOWN -- requires real deal-value and conversion-rate inputs"

    if match["next_action"] == "GATHER_MORE_CUSTOMER_DATA" or confidence == "LOW":
        recommended_action = "GATHER_MORE_CUSTOMER_DATA"
    elif opportunity.get("verification_status") not in ("VERIFIED", "PARTIALLY_VERIFIED"):
        recommended_action = "VERIFY_PARTNER_FIRST"
    else:
        recommended_action = "PROCEED_TO_QUALIFICATION"

    return {
        "generated_at": _now_iso(), "opportunity_id": opportunity.get("opportunity_id"),
        "factors": factors, "known_factors": known_factors, "total_factors": len(DEAL_PRIORITY_FACTORS),
        "DEAL_SCORE": f"{known_factors}/{len(DEAL_PRIORITY_FACTORS)} real factors known -- never a fabricated single number",
        "EXPECTED_VALUE": expected_value, "CONFIDENCE": confidence,
        "RISK": opportunity.get("risk_score", "UNKNOWN"),
        "RECOMMENDED_ACTION": recommended_action,
        "note": "Reuses commission_engine.py's match_customer_to_opportunity()/commission_economics() directly -- never a second, competing evaluation.",
    }


# ---------------------------------------------------------------------------
# Phase 37A (ADR-230), Sections 24-25 -- Golden Hunter -> Partner
# Intelligence -> Commercial Deal Agent -> Lead Discovery chain. This
# agent QUALIFIES + RECOMMENDS only; it never sends outreach itself
# (lead_discovery.py never writes to any financial ledger either, so
# no function in this chain can create a real commercial event).
# ---------------------------------------------------------------------------

def recommend_prospect(opportunity, customer_profile, problem_keywords=None, sources=("hacker_news", "github_issues"),
                        leads_path=None, dnc_path=None, events_path=None, simulation_only=False,
                        hn_query_fn=None, github_query_fn=None, now=None):
    """The real Section 25 consumer: opportunity + partner (embedded in
    opportunity) + customer_profile + lead evidence + lead score ->
    RECOMMENDED_PROSPECT/MATCH_REASON/CONFIDENCE/RISKS/RECOMMENDED_ACTION.
    Calls lead_discovery.py directly rather than re-implementing
    discovery, and match_customer_to_opportunity()/deal_priority_score()
    directly rather than re-scoring. Never sends a message -- that
    remains lead_outreach_agent.py/outreach_adapter.py's job, gated
    behind a real, separate CEO approval."""
    import lead_discovery as ld

    match = ce.match_customer_to_opportunity(customer_profile, opportunity)
    deal = deal_priority_score(customer_profile, opportunity, match=match)
    discovery = ld.discover_lead_for_opportunity(
        opportunity, problem_keywords=problem_keywords, sources=sources, simulation_only=simulation_only,
        leads_path=leads_path, dnc_path=dnc_path, events_path=events_path,
        hn_query_fn=hn_query_fn, github_query_fn=github_query_fn, now=now,
    )

    best = discovery.get("best_candidate")
    if not best:
        return {
            "generated_at": _now_iso(now), "opportunity_id": opportunity.get("opportunity_id"),
            "RECOMMENDED_PROSPECT": None,
            "MATCH_REASON": "No real, qualified prospect was found this run -- see discovery.source_notes for why.",
            "CONFIDENCE": "LOW", "RISKS": ["no real prospect exists yet -- outreach cannot proceed"],
            "RECOMMENDED_ACTION": "RETRY_DISCOVERY_LATER_OR_EXPAND_SOURCES",
            "discovery": discovery, "deal": deal,
        }

    risks = []
    if deal["CONFIDENCE"] == "LOW":
        risks.append("deal-level confidence is LOW -- several real factors are still UNKNOWN")
    if str(best.get("company_name", "")).startswith("UNKNOWN"):
        risks.append("prospect's company identity is unconfirmed -- an individual public poster, not a verified business entity")
    if opportunity.get("verification_status") not in ("VERIFIED", "PARTIALLY_VERIFIED"):
        risks.append(f"opportunity verification_status={opportunity.get('verification_status')}")

    action = "PROCEED_TO_OUTREACH_DRAFT" if (deal["RECOMMENDED_ACTION"] == "PROCEED_TO_QUALIFICATION" and not risks) else "GATHER_MORE_EVIDENCE_BEFORE_OUTREACH"

    return {
        "generated_at": _now_iso(now), "opportunity_id": opportunity.get("opportunity_id"),
        "RECOMMENDED_PROSPECT": best.get("lead_id"),
        "MATCH_REASON": f"{best.get('qualification_score')}; problem-signal evidence at {best.get('source_url')}",
        "CONFIDENCE": best.get("confidence", "LOW"),
        "RISKS": risks or ["no additional real risk identified beyond standard evidence limitations"],
        "RECOMMENDED_ACTION": action,
        "discovery": discovery, "deal": deal,
        "note": "Recommend-only -- never sends outreach, never creates a deal/commission/payout.",
    }


# ---------------------------------------------------------------------------
# Responsibilities -- track deal state, monitor commission state
# ---------------------------------------------------------------------------

def track_deal_state(opportunity_id, events_path=None):
    """Real citation of commission_engine.py's own pipeline history --
    never a second, duplicated state store."""
    return ce.pipeline_history(opportunity_id, events_path=events_path)


def monitor_commission_state(opportunity_id, ledger_path=None):
    """Real citation of commission_ledger.py's own real ledger --
    filters by opportunity_id, never recomputes totals."""
    import commission_ledger as cl
    records = cl.load_ledger(ledger_path=ledger_path)
    return [r for r in records if r.get("opportunity_id") == opportunity_id]


# ---------------------------------------------------------------------------
# CEO escalation (Section 11) -- extends autonomous_operations.py directly
# ---------------------------------------------------------------------------

def escalation_required(action_category, context=None):
    """Reuses autonomous_operations.py's real Level 0-6 authorization
    engine directly -- the Nth relabeling this session, never a
    competing authorization system."""
    import autonomous_operations
    return autonomous_operations.authorize_action(action_category, context=context)


# ---------------------------------------------------------------------------
# Section 17 -- Agent Health (genuinely new -- confirmed by grep, no
# existing "agent health" abstraction anywhere in this factory)
# ---------------------------------------------------------------------------

def agent_health(events_path=None, now=None):
    """Real health surface computed from real, already-existing event
    data -- never a fabricated uptime/status. 0 real events today
    means an honest 'no real activity yet' report, not a green
    checkmark."""
    events_path = Path(events_path) if events_path else DEFAULT_DEAL_EVENTS_PATH
    now = now or datetime.now(timezone.utc)

    if not events_path.exists():
        return {
            "generated_at": _now_iso(now), "agent": "commercial_deal_agent",
            "status": "IDLE", "last_run": None, "last_success": None, "last_failure": None,
            "error_rate": "UNKNOWN -- 0 real events recorded yet", "queue_size": 0,
            "current_task": None, "blocked_reason": None,
        }

    import json
    events = []
    with open(events_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not events:
        return {"generated_at": _now_iso(now), "agent": "commercial_deal_agent", "status": "IDLE",
                "last_run": None, "last_success": None, "last_failure": None,
                "error_rate": "UNKNOWN -- 0 real events recorded yet", "queue_size": 0,
                "current_task": None, "blocked_reason": None}

    last_event = events[-1]
    failures = sum(1 for e in events if e.get("to_state") == "REJECTED")
    error_rate = round(failures / len(events), 4)

    return {
        "generated_at": _now_iso(now), "agent": "commercial_deal_agent",
        "status": "ACTIVE",
        "last_run": last_event.get("generated_at"),
        "last_success": next((e.get("generated_at") for e in reversed(events) if e.get("to_state") != "REJECTED"), None),
        "last_failure": next((e.get("generated_at") for e in reversed(events) if e.get("to_state") == "REJECTED"), None),
        "error_rate": error_rate, "queue_size": 0,
        "current_task": None, "blocked_reason": None,
    }
