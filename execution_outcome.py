#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execution outcome classifier + idempotency gate (V71, Tier-1 safe).

For socket-closed / timeout / crash / reset / partial-response / unknown
completion. Pure functions, no IO, no retries performed here:

- classify_outcome(record) -> NOT_STARTED | STARTED_NOT_COMPLETED |
  COMPLETED | PARTIAL | UNKNOWN (disclosed rules below).
- idempotency_check(idempotent, side_effect_known) -> retry_allowed bool.
- retry_policy(outcome, ...) -> ALLOW | HOLD with reason. HOLD whenever a
  retry could repeat an unknown side effect (V71 s6: no blind retry).

Callers perform retries; this module only classifies and gates.
"""
NOT_STARTED = "NOT_STARTED"
STARTED_NOT_COMPLETED = "STARTED_NOT_COMPLETED"
COMPLETED = "COMPLETED"
PARTIAL = "PARTIAL"
UNKNOWN = "UNKNOWN"


def classify_outcome(record):
    """record: {started, completed_clean, response_bytes, incomplete,
    error}. Rules (ordered):
    1. never started -> NOT_STARTED
    2. clean completion flag -> COMPLETED
    3. partial bytes OR explicit incomplete flag -> PARTIAL
    4. started but no clean completion -> STARTED_NOT_COMPLETED
    5. anything else -> UNKNOWN (never guessed)."""
    r = record or {}
    if not r.get("started"):
        return NOT_STARTED
    if r.get("completed_clean") is True:
        return UNKNOWN if r.get("incomplete") else COMPLETED
    if r.get("incomplete") or (r.get("response_bytes") or 0) > 0:
        return PARTIAL
    if r.get("error"):
        return STARTED_NOT_COMPLETED
    return UNKNOWN


def idempotency_check(idempotent=False, side_effect_known=False):
    """Retry is allowed ONLY when the operation is declared idempotent AND
    its side effects are known. Every other combination: HOLD."""
    if idempotent is True and side_effect_known is True:
        return {"retry_allowed": True, "reason": "idempotent, effects known"}
    return {"retry_allowed": False,
            "reason": "HOLD: idempotent=%s side_effect_known=%s" % (idempotent, side_effect_known)}


def retry_policy(outcome, idempotent=False, side_effect_known=False):
    if outcome == NOT_STARTED:
        return {"decision": "ALLOW", "reason": "never started -- nothing to duplicate"}
    if outcome == COMPLETED:
        return {"decision": "HOLD", "reason": "already completed -- retry would duplicate"}
    gate = idempotency_check(idempotent, side_effect_known)
    if gate["retry_allowed"]:
        return {"decision": "ALLOW", "reason": gate["reason"]}
    return {"decision": "HOLD", "reason": "%s is %s; %s" % ("outcome", outcome, gate["reason"])}
