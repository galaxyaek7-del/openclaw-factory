#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signal state machine + measurement windows + first-signal protocol.

Pure functions (no I/O except optional queue persistence). The machine
advances exactly one state per evidenced event — states are never skipped,
and internal-test signals can never promote the commercial state.

States:
  NO_EXTERNAL_SIGNAL -> FIRST_EXTERNAL_TRAFFIC -> FIRST_EXTERNAL_CLICK
  -> FIRST_EXTERNAL_SIGNUP -> FIRST_EXTERNAL_PURCHASE
  -> FIRST_VERIFIED_COMMISSION -> FIRST_VERIFIED_PAYOUT

Signal categories (never combined):
  INTERNAL_TEST_SIGNAL, EXTERNAL_TRAFFIC_SIGNAL, EXTERNAL_CLICK,
  EXTERNAL_SIGNUP, EXTERNAL_PURCHASE, VERIFIED_COMMISSION, VERIFIED_PAYOUT.
"""

from __future__ import annotations

from datetime import datetime, timezone

STATES = (
    "NO_EXTERNAL_SIGNAL",
    "FIRST_EXTERNAL_TRAFFIC",
    "FIRST_EXTERNAL_CLICK",
    "FIRST_EXTERNAL_SIGNUP",
    "FIRST_EXTERNAL_PURCHASE",
    "FIRST_VERIFIED_COMMISSION",
    "FIRST_VERIFIED_PAYOUT",
)

# Which verified signal category advances out of each state. Anything else
# (views, internal tests, estimates) leaves the state untouched.
_ADVANCE_ON = {
    "NO_EXTERNAL_SIGNAL": "EXTERNAL_TRAFFIC_SIGNAL",
    "FIRST_EXTERNAL_TRAFFIC": "EXTERNAL_CLICK",
    "FIRST_EXTERNAL_CLICK": "EXTERNAL_SIGNUP",
    "FIRST_EXTERNAL_SIGNUP": "EXTERNAL_PURCHASE",
    "FIRST_EXTERNAL_PURCHASE": "VERIFIED_COMMISSION",
    "FIRST_VERIFIED_COMMISSION": "VERIFIED_PAYOUT",
}

_INTERNAL_MARKERS = ("test", "internal", "synthetic", "simulation", "bot", "crawler")


def classify_signal(event: dict) -> dict:
    """Map a raw event to a signal category. Heuristic, disclosed:
    - known internal markers (test/synthetic/bot/unknown-anon bursts) ->
      INTERNAL_TEST_SIGNAL, never commercial;
    - explicit external flags on the event (source == "external" plus an id)
      -> the matching EXTERNAL_* category;
    - everything else -> {"category": "UNCLASSIFIED", ...}, never assumed.
    """
    if not isinstance(event, dict):
        return {"category": "UNCLASSIFIED", "reason": "not an event object"}
    blob = " ".join(str(v).lower() for v in event.values() if isinstance(v, (str, int, float)))
    if any(m in blob for m in _INTERNAL_MARKERS) and event.get("source") != "external":
        return {"category": "INTERNAL_TEST_SIGNAL",
                "reason": "internal marker present; quarantined from commercial evidence"}
    kind = str(event.get("kind", "")).lower()
    mapping = {
        "traffic": "EXTERNAL_TRAFFIC_SIGNAL",
        "click": "EXTERNAL_CLICK",
        "signup": "EXTERNAL_SIGNUP",
        "purchase": "EXTERNAL_PURCHASE",
        "commission": "VERIFIED_COMMISSION",
        "payout": "VERIFIED_PAYOUT",
    }
    if event.get("source") == "external" and event.get("id") and kind in mapping:
        return {"category": mapping[kind], "reason": "externally sourced with id"}
    return {"category": "UNCLASSIFIED",
            "reason": "no external sourcing; never promoted without it"}


def advance_signal_state(current: str, signal_category: str) -> dict:
    """One step at most, only on the exact expected category. Returns the
    (possibly unchanged) state plus whether a diagnostic event fired."""
    if current not in STATES:
        return {"state": "NO_EXTERNAL_SIGNAL", "advanced": False,
                "reason": "unknown state resets to start (never assumed forward)"}
    if _ADVANCE_ON.get(current) == signal_category:
        nxt = STATES[STATES.index(current) + 1]
        return {"state": nxt, "advanced": True,
                "reason": "verified %s observed" % signal_category,
                "diagnostic_event": True}
    return {"state": current, "advanced": False,
            "reason": "%s does not advance %s" % (signal_category, current),
            "diagnostic_event": False}


def first_signal_protocol(signal: dict) -> dict:
    """The 10-step checklist as data (freeze + preserve + timestamp +
    identify asset/channel/campaign + attribution + classification + window
    + fraud/test-contamination check + notify-decision). Returns actions;
    performs none (notification/ledger writes belong to the caller, and the
    notify step always resolves to founder-decision, never auto-send)."""
    return {
        "freeze_unnecessary_changes": True,
        "actions": [
            "preserve raw evidence object",
            "timestamp (UTC, at receipt)",
            "identify asset / channel / campaign",
            "verify attribution if possible",
            "classify evidence (OBSERVED only if externally sourced)",
            "open or update measurement window",
            "fraud/test-contamination check (internal markers?)",
            "diagnose: traffic/audience/content/trust/cta/offer/tracking",
            "notify-decision: FOUNDER (P4 first meaningful external signal)",
            "do NOT scale, clone, or spend",
        ],
        "for_signal": signal.get("category", "UNKNOWN"),
    }


_WINDOW_STATUSES = ("IN_MEASUREMENT_WINDOW", "INSUFFICIENT_DATA",
                    "DIAGNOSE_BEFORE_SCALE", "SCALE_CANDIDATE", "NOT_IN_MARKET")


def measurement_window(campaign: str, start_iso: str, window_days: int,
                       min_data: int, sample: int) -> dict:
    """Window bookkeeping. Status derived only from sample vs minimum —
    never from optimism. A complete window with zero conversions yields
    DIAGNOSE_BEFORE_SCALE only when the caller confirms completeness."""
    try:
        start = datetime.fromisoformat(str(start_iso).replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - start).days
    except ValueError:
        return {"campaign": campaign, "status": "INSUFFICIENT_DATA",
                "reason": "unparseable start time"}
    if sample < 0 or min_data <= 0 or window_days <= 0:
        return {"campaign": campaign, "status": "INSUFFICIENT_DATA",
                "reason": "invalid window parameters"}
    if sample < min_data:
        return {"campaign": campaign, "status": "INSUFFICIENT_DATA",
                "reason": "sample %d below minimum %d (day %d/%d)"
                          % (sample, min_data, elapsed, window_days)}
    return {"campaign": campaign, "status": "IN_MEASUREMENT_WINDOW",
            "reason": "sample sufficient; awaiting window completion",
            "elapsed_days": elapsed, "window_days": window_days}
