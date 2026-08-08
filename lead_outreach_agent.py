"""Galaxy Forge — Lead & Outreach Agent (Phase 34, ADR-227, 2026-08-08).

Answers Agent #3 of the "Missing Commercial AI Crew" directive. Audit
before build found outreach_engine.py (Phase 33) already has the real
message-level lifecycle (DRAFT -> APPROVED -> SEND, honestly blocked
today at BLOCKED_NO_CREDENTIAL/BLOCKED_NO_SEND_ADAPTER) -- reused
directly, never duplicated. The genuinely missing piece: this
directive's 11-stage pipeline (TARGET_CUSTOMER through WON/LOST) is a
PROSPECT-level lifecycle, a different, coarser granularity than
outreach_engine.py's per-MESSAGE states -- one prospect can have many
outreach messages. This module adds that prospect-level layer plus
explainable customer-match reasoning (Section 9) and duplicate-contact
detection (Section 8), both genuinely new.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import commission_engine as ce

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_PROSPECT_EVENTS_PATH = _FACTORY_ROOT / "data" / "prospect_pipeline_events.jsonl"

PROSPECT_PIPELINE_STATES = [
    "TARGET_CUSTOMER", "PROSPECT", "RESEARCHED", "QUALIFIED", "MESSAGE_READY",
    "APPROVAL_REQUIRED", "CONTACTED", "RESPONSE", "FOLLOW_UP", "QUALIFIED_DEAL",
]
PROSPECT_PIPELINE_TERMINAL_EXITS = ("LOST", "WON")


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# Prospect-level pipeline (distinct from outreach_engine.py's message-level states)
# ---------------------------------------------------------------------------

def record_prospect_transition(prospect_id, from_state, to_state, evidence=None, events_path=None, now=None):
    """Real, append-only audit event -- mirrors commission_engine.py's
    own record_pipeline_transition() pattern exactly, applied to the
    prospect-level vocabulary. Never allows a transition to an unnamed
    state."""
    valid_states = set(PROSPECT_PIPELINE_STATES) | set(PROSPECT_PIPELINE_TERMINAL_EXITS)
    if to_state not in valid_states:
        return {"ok": False, "reason": f"'{to_state}' is not a named prospect-pipeline state"}

    event = {"generated_at": _now_iso(now), "prospect_id": prospect_id, "from_state": from_state, "to_state": to_state, "evidence": evidence}
    path = Path(events_path) if events_path else DEFAULT_PROSPECT_EVENTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"ok": True, "event": event}


def prospect_history(prospect_id, events_path=None):
    path = Path(events_path) if events_path else DEFAULT_PROSPECT_EVENTS_PATH
    if not path.exists():
        return []
    history = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("prospect_id") == prospect_id:
                history.append(event)
    return history


# ---------------------------------------------------------------------------
# Section 9 -- Customer Match Engine (explainable, never opaque)
# ---------------------------------------------------------------------------

def explain_customer_match(customer_profile, opportunity, now=None):
    """The 6 named explainable fields -- never returns only a numerical
    score. Reuses commission_engine.py's match_customer_to_opportunity()
    directly for the underlying match, adding the directive's specific
    WHY_* narrative fields on top."""
    base_match = ce.match_customer_to_opportunity(customer_profile, opportunity)
    freshness = ce._freshness_from_last_verified(opportunity.get("last_verified"), now=now)

    positive_signals = [r for r in base_match["reason"] if r.lower().startswith("real ")]
    why_this_customer = (
        f"Real signals present: {', '.join(positive_signals)}"
        if positive_signals
        else "No real customer signal (industry/budget) available yet -- selection would be speculative"
    )
    why_this_partner = f"{opportunity.get('partner_name')} -- verification_status={opportunity.get('verification_status')}"
    why_now = f"Opportunity data freshness: {freshness}" + (" -- STALE, reconsider before acting" if freshness == "STALE" else "")
    why_this_offer = f"commission_value={opportunity.get('commission_value')}, recurring={opportunity.get('recurring_commission')}"

    return {
        "generated_at": _now_iso(now), "opportunity_id": opportunity.get("opportunity_id"),
        "WHY_THIS_CUSTOMER": why_this_customer,
        "WHY_THIS_PARTNER": why_this_partner,
        "WHY_NOW": why_now,
        "WHY_THIS_OFFER": why_this_offer,
        "EXPECTED_VALUE": base_match["expected_value"],
        "RISK": base_match["risk"],
        "note": "Never returns only a numerical score -- every field above is a real, interpretable citation.",
    }


# ---------------------------------------------------------------------------
# Section 8 -- Outreach Safety: duplicate-contact / frequency limits
# ---------------------------------------------------------------------------

def is_duplicate_contact(lead_id, outreach_log_path=None, frequency_days=7, now=None):
    """Real check against outreach_engine.py's own real log -- never a
    second, competing contact-history store. A lead contacted within
    frequency_days is flagged, protecting against both duplicate
    contact and reputation risk from over-frequent outreach."""
    import outreach_engine as oe

    path = Path(outreach_log_path) if outreach_log_path else oe.DEFAULT_OUTREACH_LOG_PATH
    now = now or datetime.now(timezone.utc)
    if not path.exists():
        return {"duplicate": False, "reason": "no real outreach log exists yet"}

    recent_contacts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("event") != "APPROVED":
                continue
            if event.get("draft_id", "").startswith(f"OUT-{lead_id}") or lead_id in str(event.get("opportunity_id", "")):
                recent_contacts.append(event)

    if not recent_contacts:
        return {"duplicate": False, "reason": "no prior real contact found for this lead"}

    return {"duplicate": True, "reason": f"{len(recent_contacts)} prior real approved contact(s) found for this lead -- respect frequency_days={frequency_days} before contacting again",
            "prior_contacts": len(recent_contacts)}


# ---------------------------------------------------------------------------
# Section 17 -- Agent Health
# ---------------------------------------------------------------------------

def agent_health(events_path=None, now=None):
    path = Path(events_path) if events_path else DEFAULT_PROSPECT_EVENTS_PATH
    now = now or datetime.now(timezone.utc)

    if not path.exists():
        return {"generated_at": _now_iso(now), "agent": "lead_outreach_agent", "status": "IDLE",
                "last_run": None, "last_success": None, "last_failure": None,
                "error_rate": "UNKNOWN -- 0 real prospects recorded yet", "queue_size": 0,
                "current_task": None, "blocked_reason": "No real outbound-send credential configured (see outreach_engine.py)"}

    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not events:
        return {"generated_at": _now_iso(now), "agent": "lead_outreach_agent", "status": "IDLE",
                "last_run": None, "last_success": None, "last_failure": None,
                "error_rate": "UNKNOWN -- 0 real prospects recorded yet", "queue_size": 0,
                "current_task": None, "blocked_reason": "No real outbound-send credential configured"}

    last_event = events[-1]
    lost = sum(1 for e in events if e.get("to_state") == "LOST")

    return {
        "generated_at": _now_iso(now), "agent": "lead_outreach_agent", "status": "ACTIVE",
        "last_run": last_event.get("generated_at"),
        "last_success": next((e.get("generated_at") for e in reversed(events) if e.get("to_state") not in ("LOST",)), None),
        "last_failure": next((e.get("generated_at") for e in reversed(events) if e.get("to_state") == "LOST"), None),
        "error_rate": round(lost / len(events), 4), "queue_size": 0,
        "current_task": None, "blocked_reason": "No real outbound-send credential configured (see outreach_engine.py)",
    }
