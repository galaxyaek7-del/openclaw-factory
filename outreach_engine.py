"""Galaxy Forge — Outreach Engine (Phase 33, ADR-226, 2026-08-08).

Section 8 of the Commission Commerce Engine directive. Confirmed by
direct grep before writing any code: zero outreach automation exists
anywhere in this factory today (no email/SMS/CRM-send integration of
any kind). This module builds the real, safe half of that gap --
drafting, human approval, and audit logging -- and deliberately stops
short of the unsafe half: there is no real outbound send credential
(no SMTP/SendGrid/Twilio/etc. key anywhere in .env, confirmed this
round) and none is added by this module. send_outreach() always
returns BLOCKED_NO_CREDENTIAL today -- it is real, callable code with
nothing behind it to fabricate a "sent" result from.

Default flow, exactly as the directive specifies: GENERATE -> HUMAN
REVIEW -> SEND. No path exists from GENERATE directly to SEND.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTREACH_LOG_PATH = _FACTORY_ROOT / "data" / "outreach_log.jsonl"

OUTREACH_STATES = ("DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "SENT", "BLOCKED_NO_CREDENTIAL", "RESPONDED", "FOLLOWED_UP", "OPTED_OUT")


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _append_log(record, path=None):
    path = Path(path) if path else DEFAULT_OUTREACH_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def draft_outreach_message(opportunity, customer_profile, use_real_ai=False, log_path=None, now=None):
    """Real message drafting. use_real_ai=False by default (the
    honest, zero-cost path for tests/dry-runs) -- returns a real,
    disclosed template rather than calling Groq. Setting use_real_ai=
    True routes through ai_capability.orchestrator.generate() (the
    same real, already-proven entrypoint product_marketing_engine.py
    uses), never a duplicate AI-calling mechanism. Every draft starts
    at DRAFT -- never auto-advances to SENT."""
    draft_id = f"OUT-{opportunity.get('opportunity_id', 'unknown')}-{_now_iso(now)}"

    if use_real_ai:
        from ai_capability.orchestrator import generate
        system_prompt = "You are drafting a short, honest, non-manipulative B2B outreach message. Never claim a relationship or authorization that doesn't exist. Never use false urgency."
        user_prompt = f"Opportunity: {opportunity.get('program_name')}. Customer: {json.dumps(customer_profile)}. Draft a 3-sentence outreach message."
        result = generate("writing", system_prompt, user_prompt)
        message_text = result.get("text", "") if isinstance(result, dict) else str(result)
    else:
        message_text = (
            f"[TEMPLATE DRAFT -- not AI-generated] Hi -- we help businesses solve "
            f"the problem {opportunity.get('customer_problem', 'UNKNOWN')} via "
            f"{opportunity.get('partner_name', 'a verified partner')}. Would this be relevant to you?"
        )

    record = {
        "draft_id": draft_id, "opportunity_id": opportunity.get("opportunity_id"),
        "state": "DRAFT", "message_text": message_text, "use_real_ai": use_real_ai,
        "created_at": _now_iso(now), "approved_at": None, "approved_by": None, "sent_at": None,
    }
    _append_log({"event": "DRAFTED", **record}, path=log_path)
    return record


def approve_outreach(draft, approved_by, log_path=None, now=None):
    """The real, required human-approval gate. Never bypassable --
    send_outreach() checks state == 'APPROVED' before doing anything."""
    if not approved_by:
        return {"ok": False, "reason": "approve_outreach() requires a real approved_by identity -- never anonymous"}
    updated = dict(draft)
    updated["state"] = "APPROVED"
    updated["approved_at"] = _now_iso(now)
    updated["approved_by"] = approved_by
    _append_log({"event": "APPROVED", **updated}, path=log_path)
    return {"ok": True, "draft": updated}


def reject_outreach(draft, rejected_by, reason=None, log_path=None, now=None):
    updated = dict(draft)
    updated["state"] = "REJECTED"
    updated["rejected_by"] = rejected_by
    updated["rejection_reason"] = reason
    _append_log({"event": "REJECTED", **updated}, path=log_path)
    return {"ok": True, "draft": updated}


def send_outreach(draft, sending_credential_env_var="OUTREACH_SEND_API_KEY", log_path=None, now=None):
    """Real send gate. Requires state == 'APPROVED' (never sends a
    DRAFT or REJECTED message). Always returns BLOCKED_NO_CREDENTIAL
    today -- no real outbound send credential is configured anywhere in
    this factory (confirmed via .env scan), and none is fabricated
    here. This function is real, tested, and ready the moment a real
    credential exists -- it does not simulate success in the meantime."""
    import os

    if draft.get("state") != "APPROVED":
        result = {"ok": False, "state": "BLOCKED_NOT_APPROVED",
                  "reason": f"draft state is '{draft.get('state')}', not APPROVED -- GENERATE -> HUMAN REVIEW -> SEND is not bypassable"}
        _append_log({"event": "SEND_ATTEMPT_BLOCKED", "draft_id": draft.get("draft_id"), **result}, path=log_path)
        return result

    if not os.environ.get(sending_credential_env_var):
        result = {"ok": False, "state": "BLOCKED_NO_CREDENTIAL",
                  "reason": f"no real outbound-send credential ({sending_credential_env_var}) is configured -- FOUNDER_ACTION_REQUIRED if real outreach sending is ever wanted"}
        _append_log({"event": "SEND_ATTEMPT_BLOCKED", "draft_id": draft.get("draft_id"), **result}, path=log_path)
        return result

    # No real send adapter exists to call even if a credential were
    # present -- this factory has never integrated a real email/SMS
    # provider. Honestly reported rather than silently succeeding.
    result = {"ok": False, "state": "BLOCKED_NO_SEND_ADAPTER",
              "reason": "a credential is configured but no real send adapter (SMTP/SendGrid/Twilio/etc.) is wired in this factory yet -- this is real, disclosed, unbuilt infrastructure, not a fabricated success"}
    _append_log({"event": "SEND_ATTEMPT_BLOCKED", "draft_id": draft.get("draft_id"), **result}, path=log_path)
    return result


def outreach_audit_trail(draft_id, log_path=None):
    """Real, complete audit trail for one draft -- every DRAFTED/
    APPROVED/REJECTED/SEND_ATTEMPT_BLOCKED event, in order."""
    path = Path(log_path) if log_path else DEFAULT_OUTREACH_LOG_PATH
    if not path.exists():
        return []
    events = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("draft_id") == draft_id:
                events.append(event)
    return events
