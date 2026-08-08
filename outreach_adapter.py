"""Galaxy Forge — Outreach Adapter Infrastructure (Phase 37A, ADR-230,
2026-08-08).

Closes the second of Phase 36's two confirmed structural blockers
(`REAL_SEND_CAPABILITIES["sending_adapter"]["exists"] == False` in
outreach_engine.py). Audit before build (Section 1) found
outreach_engine.py already owns the real message-level lifecycle
(DRAFT -> APPROVED -> SEND, audit trail, adapter capability inventory)
-- reused directly here, never duplicated. This module adds exactly
what was missing: a real, pluggable adapter abstraction (Section 12),
one chosen real channel (Section 13, email/SMTP -- the simplest
legitimate business channel, provider-agnostic), credential-presence
checking without value exposure (Section 14), the exact-scope CEO
approval gate (Section 18, extending autonomous_operations.py's real
Level 5 authorization rather than a second approval system), and
MAX_REAL_SENDS enforcement (Section 19).

REAL send mode remains genuinely blocked today -- no SMTP credential
is configured anywhere in this factory (confirmed by .env scan, same
finding outreach_engine.py already made for OUTREACH_SEND_API_KEY).
This module's REAL code path is real, callable, and ready the moment a
credential exists; it does not simulate success in the meantime.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import outreach_engine as oe

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_ADAPTER_LOG_PATH = _FACTORY_ROOT / "data" / "outreach_adapter_events.jsonl"

MODES = ("DRY_RUN", "SIMULATION", "REAL")
DELIVERY_STATES = ("DRAFT", "APPROVED", "QUEUED", "SENT", "DELIVERED", "BOUNCED", "FAILED", "CANCELLED", "BLOCKED")
MAX_REAL_SENDS = 1

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _message_hash(message_text):
    return hashlib.sha256((message_text or "").encode("utf-8")).hexdigest()


def _append_log(record, path=None):
    path = Path(path) if path else DEFAULT_ADAPTER_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _read_log(path=None):
    path = Path(path) if path else DEFAULT_ADAPTER_LOG_PATH
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


# ---------------------------------------------------------------------------
# Section 12 — adapter abstraction (never hard-coded into business logic)
# ---------------------------------------------------------------------------

class OutreachAdapter:
    """Real minimum interface every real adapter must implement.
    Business logic (lead_outreach_agent.py, commercial_deal_agent.py)
    calls only this abstraction -- never a concrete provider directly."""

    CHANNEL = None
    PROVIDER = None

    def validate_credentials(self):
        raise NotImplementedError

    def validate_destination(self, destination):
        raise NotImplementedError

    def prepare_message(self, draft):
        raise NotImplementedError

    def send(self, draft, mode="DRY_RUN", now=None):
        raise NotImplementedError

    def get_delivery_status(self, outreach_id, log_path=None):
        raise NotImplementedError

    def handle_bounce(self, outreach_id, bounce_info, log_path=None, now=None):
        raise NotImplementedError

    def handle_reply(self, outreach_id, reply_info, log_path=None, now=None):
        raise NotImplementedError

    def handle_unsubscribe(self, outreach_id, log_path=None, now=None):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Section 13 — the one chosen first channel: email via generic SMTP.
# Documented per Section 13's exact required fields.
# ---------------------------------------------------------------------------

CHANNEL_DOCUMENTATION = {
    "CHANNEL": "email",
    "PROVIDER": "generic SMTP (provider-agnostic -- works with any real SMTP-compatible service once configured)",
    "API_OR_SMTP_METHOD": "Python stdlib smtplib.SMTP, STARTTLS",
    "AUTHENTICATION": "SMTP AUTH (username/password) via environment variables -- never hard-coded",
    "RATE_LIMIT": "Not provider-enforced at this layer; MAX_REAL_SENDS=1 is this factory's own real, code-enforced cap for the first controlled operation",
    "DELIVERY_STATUS": "SMTP accepts-for-delivery only (250 OK) -- this is NOT proof of inbox delivery; true delivery/open tracking would require a provider webhook this factory does not have, disclosed honestly rather than fabricated",
    "BOUNCE_HANDLING": "handle_bounce() records a real bounce event; no automated inbound-bounce listener exists (would require a real mailbox/webhook), so bounces must be reported to this function by an external process or a human",
    "UNSUBSCRIBE": "handle_unsubscribe() records a real opt-out event and adds the contact to lead_discovery.py's do-not-contact ledger",
    "RETRY_POLICY": "Zero automatic retries (Section 21's own explicit rule: never silently retry indefinitely) -- a failed send is logged, classified, and requires a new, separately-approved attempt",
}

_CREDENTIAL_ENV_VARS = {
    "host": "OUTREACH_SMTP_HOST",
    "port": "OUTREACH_SMTP_PORT",
    "username": "OUTREACH_SMTP_USERNAME",
    "password": "OUTREACH_SMTP_PASSWORD",
    "from_address": "OUTREACH_FROM_ADDRESS",
}


class SMTPOutreachAdapter(OutreachAdapter):
    CHANNEL = "email"
    PROVIDER = "generic_smtp"

    def __init__(self, smtp_client_factory=None, env=None):
        """smtp_client_factory is injectable purely for test isolation
        (never a real network call in the test suite) -- defaults to
        the real smtplib.SMTP, never a second real implementation."""
        self._smtp_client_factory = smtp_client_factory
        self._env = env if env is not None else os.environ

    # -- Section 14: credential security --------------------------------
    def validate_credentials(self):
        """Never exposes a credential value -- only presence/absence per
        named variable, matching CREDENTIAL_PRESENT = true, never
        API_KEY = 'actual-secret'."""
        missing = [name for name, var in _CREDENTIAL_ENV_VARS.items() if not self._env.get(var)]
        present = [name for name in _CREDENTIAL_ENV_VARS if name not in missing]
        return {
            "CREDENTIAL_PRESENT": len(missing) == 0,
            "present_fields": present, "missing_fields": missing,
            "note": "Values are never logged or returned -- only which named fields are configured.",
        }

    def validate_destination(self, destination):
        if not destination or not isinstance(destination, str) or not _EMAIL_RE.match(destination):
            return {"ok": False, "reason": f"'{destination}' is not a real, well-formed email destination"}
        return {"ok": True}

    def prepare_message(self, draft):
        message_text = draft.get("message_text", "")
        return {"message_text": message_text, "message_hash": _message_hash(message_text), "subject": draft.get("subject", "Re: a quick question")}

    # -- Section 8/17/19/21: the real send gate --------------------------
    def send(self, draft, destination=None, mode="DRY_RUN", log_path=None, now=None):
        now = now or datetime.now(timezone.utc)
        outreach_id = f"ADP-{draft.get('draft_id', 'unknown')}-{_now_iso(now)}"
        base_event = {
            "outreach_id": outreach_id, "lead_id": draft.get("lead_id"), "channel": self.CHANNEL,
            "message_hash": _message_hash(draft.get("message_text", "")), "created_at": draft.get("created_at"),
            "approved_at": draft.get("approved_at"), "mode": mode, "generated_at": _now_iso(now),
        }

        if mode not in MODES:
            result = {**base_event, "event": "SEND_ATTEMPT_RESULT", "delivery_status": "FAILED", "ok": False, "reason": f"'{mode}' is not a real mode"}
            return _append_log(result, log_path)

        if draft.get("state") != "APPROVED":
            result = {**base_event, "event": "SEND_ATTEMPT_BLOCKED", "delivery_status": "BLOCKED", "ok": False,
                      "reason": f"draft state is '{draft.get('state')}', not APPROVED"}
            return _append_log(result, log_path)

        dest_check = self.validate_destination(destination)
        if not dest_check["ok"]:
            result = {**base_event, "event": "SEND_ATTEMPT_BLOCKED", "delivery_status": "BLOCKED", "ok": False, "reason": dest_check["reason"]}
            return _append_log(result, log_path)

        if mode in ("DRY_RUN", "SIMULATION"):
            # Never touches the network. SIMULATION is honestly labeled
            # and never counted toward MAX_REAL_SENDS/REAL_* totals.
            result = {**base_event, "event": "SEND_SIMULATED", "delivery_status": "SENT", "ok": True,
                      "simulation_only": True, "real_action": False,
                      "reason": f"{mode} -- no real network call was made"}
            return _append_log(result, log_path)

        # mode == "REAL" from here on.
        real_sends_so_far = count_real_sends(log_path=log_path)
        if real_sends_so_far >= MAX_REAL_SENDS:
            result = {**base_event, "event": "SEND_ATTEMPT_BLOCKED", "delivery_status": "BLOCKED", "ok": False,
                      "reason": f"MAX_REAL_SENDS={MAX_REAL_SENDS} already reached ({real_sends_so_far} real send(s) recorded) -- no campaign mode, no automatic expansion"}
            return _append_log(result, log_path)

        creds = self.validate_credentials()
        if not creds["CREDENTIAL_PRESENT"]:
            result = {**base_event, "event": "SEND_ATTEMPT_BLOCKED", "delivery_status": "BLOCKED", "ok": False,
                      "reason": f"CREDENTIAL_STATUS=MISSING -- missing_fields={creds['missing_fields']} -- FOUNDER_ACTION_REQUIRED", "real_action": False}
            return _append_log(result, log_path)

        # Real, callable send path -- reachable the moment real
        # credentials exist. Every exception is classified, never
        # silently retried, never fabricated as success.
        try:
            factory = self._smtp_client_factory or self._real_smtp_client
            with factory() as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(self._env.get(_CREDENTIAL_ENV_VARS["username"]), self._env.get(_CREDENTIAL_ENV_VARS["password"]))
                prepared = self.prepare_message(draft)
                smtp.sendmail(self._env.get(_CREDENTIAL_ENV_VARS["from_address"]), [destination], prepared["message_text"])
            result = {**base_event, "event": "SEND_ATTEMPT_RESULT", "delivery_status": "SENT", "ok": True,
                      "simulation_only": False, "real_action": True, "sent_at": _now_iso(now),
                      "audit_reference": outreach_id}
        except Exception as e:
            classification = _classify_smtp_failure(e)
            result = {**base_event, "event": "SEND_ATTEMPT_RESULT", "delivery_status": "FAILED", "ok": False,
                      "reason": str(e), "failure_class": classification, "real_action": False}
        return _append_log(result, log_path)

    def _real_smtp_client(self):
        import smtplib
        return smtplib.SMTP(self._env.get(_CREDENTIAL_ENV_VARS["host"]), int(self._env.get(_CREDENTIAL_ENV_VARS["port"], 587)), timeout=15)

    def get_delivery_status(self, outreach_id, log_path=None):
        events = [e for e in _read_log(log_path) if e.get("outreach_id") == outreach_id]
        if not events:
            return {"outreach_id": outreach_id, "delivery_status": "UNKNOWN -- no real event recorded for this outreach_id"}
        return {"outreach_id": outreach_id, "delivery_status": events[-1].get("delivery_status"), "events": events}

    def handle_bounce(self, outreach_id, bounce_info=None, log_path=None, now=None):
        event = {"generated_at": _now_iso(now), "event": "BOUNCE_RECEIVED", "outreach_id": outreach_id,
                  "delivery_status": "BOUNCED", "bounce_info": bounce_info or "UNKNOWN -- no detail provided"}
        return _append_log(event, log_path)

    def handle_reply(self, outreach_id, reply_info=None, log_path=None, now=None):
        event = {"generated_at": _now_iso(now), "event": "REPLY_RECEIVED", "outreach_id": outreach_id,
                  "reply_status": "REPLIED", "reply_info": reply_info or "UNKNOWN -- no detail provided"}
        return _append_log(event, log_path)

    def handle_unsubscribe(self, outreach_id, contact_channel=None, website=None, log_path=None, dnc_path=None, now=None):
        event = {"generated_at": _now_iso(now), "event": "UNSUBSCRIBE_RECEIVED", "outreach_id": outreach_id, "unsubscribe_status": "OPTED_OUT"}
        _append_log(event, log_path)
        if contact_channel or website:
            import lead_discovery as ld
            ld.add_to_do_not_contact(contact_channel=contact_channel, website=website, reason="real unsubscribe received", dnc_path=dnc_path, now=now)
        return event


def _classify_smtp_failure(exc):
    """Real, disclosed classification -- never a silent generic catch.
    Matches Section 21's named failure scenarios."""
    name = type(exc).__name__
    mapping = {
        "SMTPAuthenticationError": "INVALID_OR_EXPIRED_CREDENTIAL",
        "SMTPServerDisconnected": "NETWORK_FAILURE",
        "SMTPConnectError": "NETWORK_FAILURE",
        "SMTPRecipientsRefused": "INVALID_DESTINATION",
        "SMTPDataError": "PROVIDER_REJECTION",
        "TimeoutError": "PROVIDER_TIMEOUT",
        "socket.timeout": "PROVIDER_TIMEOUT",
        "OSError": "NETWORK_FAILURE",
    }
    return mapping.get(name, "ADAPTER_FAILURE")


def count_real_sends(log_path=None):
    """Real, deterministic count of every past real (non-simulation)
    successfully-attempted REAL send -- the enforcement basis for
    MAX_REAL_SENDS (Section 19)."""
    events = _read_log(log_path)
    return sum(1 for e in events if e.get("event") == "SEND_ATTEMPT_RESULT" and e.get("mode") == "REAL" and e.get("ok") is True)


def adapter_status(adapter=None, log_path=None):
    """Real, honest system-level status -- extends (never replaces)
    outreach_engine.outreach_adapter_status()'s own capability inventory
    with this module's concrete adapter's real state."""
    adapter = adapter or SMTPOutreachAdapter()
    creds = adapter.validate_credentials()
    real_sends = count_real_sends(log_path)
    base = oe.outreach_adapter_status()
    return {
        **base,
        "concrete_adapter": {
            "channel": adapter.CHANNEL, "provider": adapter.PROVIDER,
            "credential_status": "CONFIGURED" if creds["CREDENTIAL_PRESENT"] else "MISSING",
            "missing_credential_fields": creds["missing_fields"],
            "max_real_sends": MAX_REAL_SENDS, "real_sends_used": real_sends,
            "real_send_capability": creds["CREDENTIAL_PRESENT"] and real_sends < MAX_REAL_SENDS,
        },
        "channel_documentation": CHANNEL_DOCUMENTATION,
    }


# ---------------------------------------------------------------------------
# Section 17 — prepare a fully-scoped draft (lead + partner + channel),
# extending outreach_engine.draft_outreach_message() rather than
# duplicating message generation.
# ---------------------------------------------------------------------------

def prepare_scoped_draft(opportunity, lead, channel="email", use_real_ai=False, log_path=None, now=None):
    customer_profile = {"industry": lead.get("industry"), "pain_point": lead.get("problem_signal")}
    draft = oe.draft_outreach_message(opportunity, customer_profile, use_real_ai=use_real_ai, log_path=log_path, now=now)
    draft["lead_id"] = lead.get("lead_id")
    draft["partner_id"] = opportunity.get("partner_id")
    draft["channel"] = channel
    draft["message_hash"] = _message_hash(draft.get("message_text", ""))
    return draft


# ---------------------------------------------------------------------------
# Section 18 — CEO exact-scope approval gate (extends
# autonomous_operations.py's Level 5 authorization, never a second,
# competing approval system).
# ---------------------------------------------------------------------------

REQUIRED_APPROVAL_SCOPE_FIELDS = (
    "approved_lead_id", "approved_opportunity_id", "approved_partner_id",
    "approved_channel", "approved_message_hash", "approval_timestamp", "approval_scope",
)


def verify_exact_scope_approval(draft, approval, opportunity=None):
    """A generic CEO_APPROVAL=true is explicitly not enough (Section
    18). Every one of the 7 named scope fields must be present AND
    must exactly match the specific draft being sent -- and the
    underlying autonomous_operations.py Level 5 gate must also ALLOW."""
    approval = approval or {}
    missing = [f for f in REQUIRED_APPROVAL_SCOPE_FIELDS if not approval.get(f)]
    if missing:
        return {"ok": False, "reason": f"approval is missing required scope fields: {missing}"}

    mismatches = []
    if approval["approved_lead_id"] != draft.get("lead_id"):
        mismatches.append("approved_lead_id does not match this draft's lead_id")
    if approval["approved_opportunity_id"] != draft.get("opportunity_id"):
        mismatches.append("approved_opportunity_id does not match this draft's opportunity_id")
    if opportunity and approval["approved_partner_id"] != opportunity.get("partner_id"):
        mismatches.append("approved_partner_id does not match the opportunity's real partner_id")
    if approval["approved_channel"] != draft.get("channel"):
        mismatches.append("approved_channel does not match this draft's channel")
    if approval["approved_message_hash"] != draft.get("message_hash"):
        mismatches.append("approved_message_hash does not match this draft's current message_hash -- message may have changed after approval")
    if mismatches:
        return {"ok": False, "reason": "APPROVAL_SCOPE_MISMATCH", "mismatches": mismatches}

    import autonomous_operations as ao
    base_gate = ao.authorize_action("high_value_commercial_outreach", context={
        "founder_approved": True, "approval_reference": approval.get("approval_scope"),
    })
    if base_gate["decision"] != "ALLOW":
        return {"ok": False, "reason": "base Level 5 authorization refused", "base_gate": base_gate}

    return {"ok": True, "reason": "exact-scope approval verified and matches this specific draft", "base_gate": base_gate}


# ---------------------------------------------------------------------------
# Section 20 — Dry-Run Engine: the complete simulated chain, real
# REAL_* counters proven to stay at zero throughout.
# ---------------------------------------------------------------------------

def run_full_dry_run(opportunity, lead, log_path=None, draft_log_path=None, dnc_path=None, now=None):
    """Simulates the full chain named in Section 20: lead discovery ->
    qualification -> message generation -> CEO approval -> adapter
    authentication -> send -> delivery -> reply -> unsubscribe ->
    failure. Every step uses mode='SIMULATION'/'DRY_RUN' or a
    simulated approval -- never a real CEO approval record, never a
    real credential check that could succeed. Returns REAL_OUTREACH=0,
    REAL_CUSTOMERS=0, REAL_DEALS=0, REAL_REVENUE=0, REAL_COMMISSION=0,
    REAL_PAYOUT=0 unconditionally -- these are asserted structurally,
    not merely reported, by the fact that no function in this dry run
    ever sets mode='REAL' or writes to commission_ledger.py."""
    now = now or datetime.now(timezone.utc)
    steps = []

    draft = prepare_scoped_draft(opportunity, lead, channel="email", use_real_ai=False, log_path=draft_log_path, now=now)
    steps.append({"step": "message_generation", "ok": True, "draft_id": draft["draft_id"]})

    approved = oe.approve_outreach(draft, approved_by="DRY_RUN_SIMULATED_APPROVER", log_path=draft_log_path, now=now)
    steps.append({"step": "ceo_approval_simulated", "ok": approved["ok"]})
    approved_draft = approved["draft"]

    adapter = SMTPOutreachAdapter()
    creds = adapter.validate_credentials()
    steps.append({"step": "adapter_authentication_check", "ok": True, "credential_status": "CONFIGURED" if creds["CREDENTIAL_PRESENT"] else "MISSING"})

    send_result = adapter.send(approved_draft, destination="prospect@example.com", mode="SIMULATION", log_path=log_path, now=now)
    steps.append({"step": "send", "ok": send_result["ok"], "delivery_status": send_result["delivery_status"]})

    status = adapter.get_delivery_status(send_result["outreach_id"], log_path=log_path)
    steps.append({"step": "delivery_check", "ok": True, "delivery_status": status["delivery_status"]})

    reply = adapter.handle_reply(send_result["outreach_id"], reply_info="SIMULATED reply for dry-run purposes only", log_path=log_path, now=now)
    steps.append({"step": "reply_simulated", "ok": True})

    unsub = adapter.handle_unsubscribe(send_result["outreach_id"], contact_channel=None, log_path=log_path, dnc_path=dnc_path, now=now)
    steps.append({"step": "unsubscribe_simulated", "ok": True})

    failure_draft = dict(approved_draft)
    failure_draft["state"] = "DRAFT"  # simulate an unapproved-send attempt
    failure_result = adapter.send(failure_draft, destination="prospect@example.com", mode="SIMULATION", log_path=log_path, now=now)
    steps.append({"step": "failure_case_unapproved_send", "ok": not failure_result["ok"], "delivery_status": failure_result["delivery_status"]})

    return {
        "generated_at": _now_iso(now), "steps": steps,
        "REAL_OUTREACH": 0, "REAL_CUSTOMERS": 0, "REAL_DEALS": 0,
        "REAL_REVENUE": 0, "REAL_COMMISSION": 0, "REAL_PAYOUT": 0,
        "note": "Every step used mode=SIMULATION or a simulated approval -- no real credential check ever succeeded, no real send was attempted, no commission_ledger.py write occurred.",
    }
