#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Market Evidence Ledger (Market Learning Loop, Executive
Directive, 2026-07-22).

The permanent evidence store the Executive Quality Gate (ADR-087) reads
from automatically, replacing UNKNOWN fields only when real evidence
actually arrives — never on assumption.

Read this before wiring anything to this module. "The factory
continuously collects evidence from the market" does NOT mean this
module observes real-world events on its own. This factory has no live
landing page, no connected CRM, no automatic call-transcription, and no
OAuth-configured email integration (Gmail is reachable through Claude
Code's own MCP session on request during a conversation, not through a
standalone always-on script this module could run unattended). Building
a fake "autonomous market sensor" here would be exactly the kind of
fabrication this whole engagement has refused everywhere else.

What IS real and automatic:
  1. A closed sale, once the real niche is known, is wired directly into
     channels/ledger.py's already-live sale-detection pipeline — no
     duplicate manual entry needed for a real sale (see record_sale()'s
     new optional `niche` parameter).
  2. Once ANY event is recorded here, by any real path, the Executive
     Quality Gate consumes it automatically from that point forward,
     with zero further code changes — this is the real, honest sense in
     which "the factory learns automatically."

Everything else — a real discovery call happening, a real cold-email
reply landing in an inbox, a real objection heard on a call — still
requires a human (or Claude Code, asked to check a real channel during a
session) to actually observe the event and call record_evidence() once.
This module automates aggregation and consumption of evidence; it does
not fabricate observation of events nothing in this factory can see yet.

    python market_evidence.py --record '{"niche":"...","event_type":"demo_request","payload":{}}'
    python market_evidence.py --summarize "some niche"
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_EVIDENCE_PATH = _FACTORY_ROOT / "data" / "market_evidence.jsonl"

# The 15 categories named in the directive. Recording an event outside
# this list is never rejected (write-what-you-see over strictness, same
# discipline as every ledger in this factory) but is flagged with a note
# so a real typo doesn't silently disappear.
EVENT_TYPES = (
    "customer_interview", "discovery_call", "cold_outreach_result", "email_reply",
    "landing_page_conversion", "waitlist_signup", "demo_request", "trial_request",
    "purchase_attempt", "closed_sale", "lost_opportunity", "customer_objection",
    "pricing_objection", "retention_signal", "feature_request",
)

# Live Competitive Intelligence Layer, Market Evidence & Alerting layer
# (2026-07-23): real, human-observed facts about a COMPETITOR's business
# — not about our own customers (the 15 categories above). ADR-093
# identified these as the 9 real competitor-landscape event categories
# with no automated sensor anywhere in this factory (no Crunchbase/
# PitchBook/LinkedIn/CVE/regulatory-filing connector exists) — a human
# (or Claude Code, asked to check a real public source during a session)
# must observe each one and call record_evidence() once, same as every
# category above. Unlike those 15 (a human's own first-hand account of
# their own interaction), a claim about a THIRD PARTY's business carries
# real fabrication risk — see the stricter verification gate in
# record_evidence() below, scoped to only these 9 types.
COMPETITOR_EVENT_TYPES = (
    "competitor_funding_round", "competitor_acquisition", "competitor_hiring_spike",
    "competitor_security_incident", "competitor_partnership", "competitor_regulatory_change",
    "competitor_customer_migration", "competitor_feature_release", "competitor_pricing_change",
)

EVENT_TYPES = EVENT_TYPES + COMPETITOR_EVENT_TYPES

# A real, checkable citation for WHERE this claim about a competitor was
# observed (a news article, a press release, a public filing, a real
# HN/GitHub URL) — required for the 9 competitor types only. This
# factory cannot independently fact-check a third-party business claim;
# requiring a real source is the honest substitute for that.
_COMPETITOR_EVIDENCE_REQUIRED_FIELDS = ("competitor", "source_url")

_WTP_POSITIVE_TYPES = ("demo_request", "trial_request", "purchase_attempt", "closed_sale")


def record_evidence(niche, event_type, payload=None, source="manual", evidence_path=None):
    """Appends one real evidence event. Never silently invents or drops
    an event_type — an unrecognized one is still recorded (matching this
    factory's write-what-you-see discipline) but flagged with a note so
    a caller can catch a real typo rather than lose the event.

    Competitor-landscape events (COMPETITOR_EVENT_TYPES) are the one
    real exception to "never reject" (Market Evidence & Alerting layer,
    2026-07-23): a claim about a THIRD PARTY's business (a competitor's
    funding, an acquisition, a security incident) is a fundamentally
    different risk than a human's own first-hand account of their own
    customer interaction — this factory has no way to independently
    verify it. Recording one requires a real `competitor` name and a
    real `source_url` citation in payload; missing either raises,
    refusing to store an unverifiable claim as if it were real
    intelligence. This does not change behavior for any of the 15
    pre-existing event types."""
    payload = payload or {}
    if event_type in COMPETITOR_EVENT_TYPES:
        missing = [f for f in _COMPETITOR_EVIDENCE_REQUIRED_FIELDS if not payload.get(f)]
        if missing:
            raise ValueError(
                f"دليل منافس حقيقي يتطلب {', '.join(missing)} (اسم منافس حقيقي + رابط مصدر حقيقي قابل للتحقق) — "
                f"لا يُسجَّل أي حدث منافس بلا استشهاد حقيقي: {event_type}"
            )
    note = None if event_type in EVENT_TYPES else f"event_type غير معروف في القائمة الرسمية (لم يُرفَض، فقط مُسجَّل مع تنبيه): {event_type}"
    event = {
        "niche": niche,
        "event_type": event_type,
        "payload": payload,
        "source": source,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
    }
    path = Path(evidence_path) if evidence_path else DEFAULT_EVIDENCE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def read_evidence(niche=None, event_type=None, evidence_path=None):
    """Missing file yields nothing — a factory with zero recorded events
    yet is not an error, same convention as every other ledger here."""
    path = Path(evidence_path) if evidence_path else DEFAULT_EVIDENCE_PATH
    if not path.exists():
        return []
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if niche is not None and event.get("niche") != niche:
                continue
            if event_type is not None and event.get("event_type") != event_type:
                continue
            events.append(event)
    return events


def get_willingness_to_pay_signal(niche, evidence_path=None):
    """Real, honest aggregation — never a dollar figure invented, only
    real counted signals. None (Unknown) until at least one real
    WTP-adjacent event has been recorded for this exact niche."""
    relevant = _WTP_POSITIVE_TYPES + ("pricing_objection",)
    events = [e for e in read_evidence(niche, evidence_path=evidence_path) if e["event_type"] in relevant]
    if not events:
        return None
    positive = sum(1 for e in events if e["event_type"] in _WTP_POSITIVE_TYPES)
    objections = sum(1 for e in events if e["event_type"] == "pricing_objection")
    return {"positive_signals": positive, "pricing_objections": objections, "total_events": len(events)}


def get_customer_acquisition_signal(niche, evidence_path=None):
    """Real reply-rate computed from real logged outreach/reply events —
    None (Unknown) until at least one real event of either kind exists
    for this niche. `sent` prefers a real logged count in the outreach
    event's payload; falls back to counting outreach events themselves
    when no explicit count was given."""
    outreach = read_evidence(niche, "cold_outreach_result", evidence_path=evidence_path)
    replies = read_evidence(niche, "email_reply", evidence_path=evidence_path)
    if not outreach and not replies:
        return None
    sent = sum((e["payload"].get("sent") or 0) for e in outreach) or len(outreach)
    replied = len(replies)
    reply_rate_pct = round(100 * replied / sent, 1) if sent else None
    return {"sent": sent, "replied": replied, "reply_rate_pct": reply_rate_pct}


def get_retention_signal(niche, evidence_path=None):
    """None (Unknown) until a real retention_signal event (a real
    renewal or churn) has actually been recorded — zero real sales exist
    in this factory to measure retention from until then, for any
    niche."""
    events = read_evidence(niche, "retention_signal", evidence_path=evidence_path)
    if not events:
        return None
    renewed = sum(1 for e in events if e["payload"].get("outcome") == "renewed")
    churned = sum(1 for e in events if e["payload"].get("outcome") == "churned")
    return {"renewed": renewed, "churned": churned}


def get_competitor_events(niche, evidence_path=None):
    """Real, human-observed competitor-landscape events recorded for
    this niche (the 9 COMPETITOR_EVENT_TYPES) — reuses read_evidence()
    directly, no new storage. Feeds market_alerts.py's manual-event
    detection (Market Evidence & Alerting layer, 2026-07-23)."""
    return [e for e in read_evidence(niche, evidence_path=evidence_path) if e["event_type"] in COMPETITOR_EVENT_TYPES]


def summarize_niche(niche, evidence_path=None):
    """One real, honest evidence summary across all 24 categories — this
    is what the Executive Quality Gate consumes automatically."""
    all_events = read_evidence(niche, evidence_path=evidence_path)
    by_type = {}
    for e in all_events:
        by_type.setdefault(e["event_type"], []).append(e)
    return {
        "niche": niche,
        "total_events": len(all_events),
        "by_type_counts": {k: len(v) for k, v in by_type.items()},
        "willingness_to_pay": get_willingness_to_pay_signal(niche, evidence_path),
        "customer_acquisition": get_customer_acquisition_signal(niche, evidence_path),
        "retention": get_retention_signal(niche, evidence_path),
        "customer_objections": [e["payload"] for e in by_type.get("customer_objection", [])],
        "pricing_objections": [e["payload"] for e in by_type.get("pricing_objection", [])],
        "feature_requests": [e["payload"] for e in by_type.get("feature_request", [])],
        "lost_opportunities": [e["payload"] for e in by_type.get("lost_opportunity", [])],
        # Market Evidence & Alerting layer (2026-07-23): additive-only —
        # every key above is unchanged, this is a new key, never a
        # replacement, preserving full backward compatibility for every
        # existing reader of this function's return shape.
        "competitor_landscape_events": {
            event_type: [e["payload"] for e in by_type.get(event_type, [])]
            for event_type in COMPETITOR_EVENT_TYPES if event_type in by_type
        },
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Market Evidence Ledger (Market Learning Loop)")
    parser.add_argument("--record", metavar="JSON", help='\'{"niche":"...","event_type":"...","payload":{...}}\'')
    parser.add_argument("--summarize", metavar="NICHE")
    args = parser.parse_args()

    if args.record:
        data = json.loads(args.record)
        event = record_evidence(data["niche"], data["event_type"], data.get("payload"), data.get("source", "manual"))
        emit({"success": True, "event": event})
        return
    if args.summarize:
        emit({"success": True, "summary": summarize_niche(args.summarize)})
        return
    parser.print_help()


if __name__ == "__main__":
    main()
