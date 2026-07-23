#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Decision Re-open Trigger (Live Competitive
Intelligence Layer, 2026-07-23).

Closes the last deferred piece of ADR-093, named again in ADR-094 and
ADR-095: re-convene the AI Executive Board for a niche ONLY when real,
already-verified evidence (market_alerts.py, ADR-095) materially changes
the picture since the last real board meeting (executive_board.py,
ADR-090/ADR-094) — never on a schedule (no scheduler exists, CLAUDE.md),
never on speculation, never on an LLM's free-form judgment.

The materiality rule is entirely deterministic, grounded in fields other
modules already computed and verified:
  - A real Critical-severity alert (market_alerts.py) since the last
    meeting — by itself: a customer_migration, a regulatory_change, or a
    new Enterprise Leader competitor are each already severe enough on
    their own real terms (see market_alerts.py's own severity rationale).
  - 2+ real High-severity alerts since the last meeting — compounding
    real threats, avoiding a reopen from one High alert alone (the same
    "no alert spam" discipline market_alerts.py's own dedupe already
    established, applied one layer up so reopening doesn't spam either).
Nothing else reopens a decision. A Medium/Low alert, or evidence that
predates the last meeting, is honestly not material.

Reuses, never duplicates: executive_board.get_latest_board_brief() (the
previous real decision), executive_board.convene_board() (the actual
re-convene — this module never produces a board verdict itself),
market_alerts.get_active_alerts()/scan_market_alerts() (the real
evidence), factory_orchestrator.find_decision()/build_spec() (the exact
same real decision->spec mapping every other real caller uses).

Full audit trail, honestly scoped: every reopen event is appended,
never overwritten, to data/decision_reopens.jsonl — the previous board
meeting is never mutated or deleted (it stays exactly as readable via
executive_board.review_board_track_record()/get_latest_board_brief() as
before). "Rollback capability" here means exactly that: the prior real
decision remains fully intact and inspectable. It does NOT mean undoing
an already-executed real action (a real production run, a real
publish) — this factory has no such mechanism, and none is fabricated
here.

    python decision_reopen.py --check "some niche"
    python decision_reopen.py --scan-and-maybe-reopen "some niche"
    python decision_reopen.py --history "some niche"
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_REOPEN_LOG_PATH = _FACTORY_ROOT / "data" / "decision_reopens.jsonl"

# Deterministic materiality thresholds -- see module docstring for the
# real, stated rationale behind each. Named constants, not magic numbers,
# so the rule is auditable at a glance and changeable in exactly one place.
CRITICAL_TRIGGER_COUNT = 1
HIGH_TRIGGER_COUNT = 2


def _parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _new_alerts_since(alerts, since_iso):
    """Real alerts strictly after the previous meeting's real
    convened_at timestamp. An alert with no parseable occurred_at/
    alerted_at is honestly excluded, never assumed new -- this module
    never speculates. When there is no real previous timestamp to
    compare against at all, every currently-active real alert counts
    (there is nothing stale to exclude yet)."""
    since_dt = _parse_iso(since_iso)
    if since_dt is None:
        return list(alerts)
    new = []
    for a in alerts:
        occurred_dt = _parse_iso(a.get("occurred_at") or a.get("alerted_at"))
        if occurred_dt and occurred_dt > since_dt:
            new.append(a)
    return new


def _is_material_change(new_alerts):
    """The one real, deterministic materiality rule -- see module
    docstring for the full rationale. Never a freely-generated judgment."""
    critical = [a for a in new_alerts if a.get("severity") == "Critical"]
    high = [a for a in new_alerts if a.get("severity") == "High"]

    if len(critical) >= CRITICAL_TRIGGER_COUNT:
        return True, f"{len(critical)} تنبيه حرج (Critical) حقيقي جديد منذ آخر اجتماع مجلس"
    if len(high) >= HIGH_TRIGGER_COUNT:
        return True, f"{len(high)} تنبيهات عالية (High) حقيقية جديدة منذ آخر اجتماع مجلس"
    return False, (
        f"لا تغيّر جوهري حقيقي مؤكَّد: {len(critical)} تنبيه حرج، {len(high)} تنبيه عالٍ منذ آخر اجتماع "
        f"(يتطلب إعادة الفتح: تنبيه حرج واحد على الأقل أو تنبيهان عاليان على الأقل)"
    )


def check_for_reopen_trigger(niche, board_path=None, alerts_path=None):
    """Pure, read-only check -- never mutates anything, never convenes a
    new meeting itself. Honest 'nothing to reopen' when this niche has
    never been to the board yet."""
    import executive_board as eb
    import market_alerts

    previous = eb.get_latest_board_brief(niche, board_path=board_path)
    if not previous.get("has_meeting"):
        return {
            "should_reopen": False,
            "reason": "لا اجتماع مجلس حقيقي سابق لهذا النيتش — لا شيء لإعادة فتحه",
            "niche": niche,
            "previous_meeting_convened_at": None,
            "previous_board_decision": None,
            "previous_confidence": None,
            "trigger_alerts": [],
        }

    active = market_alerts.get_active_alerts(niche, alerts_path=alerts_path)
    new_alerts = _new_alerts_since(active.get("alerts") or [], previous.get("convened_at"))
    material, reason = _is_material_change(new_alerts)

    return {
        "should_reopen": material,
        "reason": reason,
        "niche": niche,
        "previous_meeting_convened_at": previous.get("convened_at"),
        "previous_board_decision": previous.get("board_decision"),
        "previous_confidence": (previous.get("decision_summary") or {}).get("confidence"),
        "trigger_alerts": new_alerts,
    }


def _append_reopen_event(event, reopen_log_path=None):
    path = Path(reopen_log_path) if reopen_log_path else DEFAULT_REOPEN_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def execute_reopen(niche, decisions_path=None, board_path=None, alerts_path=None, reopen_log_path=None):
    """The only function that actually re-convenes the board. Refuses
    honestly (reopened: False) when check_for_reopen_trigger() finds no
    material real change, or when no real decision is on record for this
    niche to rebuild a spec from -- never fabricates either. Records one
    permanent, append-only event with the full required audit shape:
    timestamp, reason, previous decision, new evidence, confidence
    delta, and the new real board outcome."""
    import executive_board as eb
    import factory_orchestrator as fo

    trigger = check_for_reopen_trigger(niche, board_path=board_path, alerts_path=alerts_path)
    if not trigger["should_reopen"]:
        return {"reopened": False, **trigger}

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return {
            "reopened": False, "niche": niche, "should_reopen": True,
            "reason": f"تنبيهات جوهرية حقيقية موجودة، لكن لا قرار حقيقي مسجَّل لهذا النيتش بعد لإعادة بنائه: {niche!r}",
            "trigger_alerts": trigger["trigger_alerts"],
        }

    spec = fo.build_spec(decision)
    new_meeting = eb.convene_board(spec, decision_type="production", board_path=board_path, alerts_path=alerts_path)

    previous_confidence = trigger["previous_confidence"]
    new_confidence = (new_meeting.get("decision_summary") or {}).get("confidence")
    confidence_delta = (
        round(new_confidence - previous_confidence, 4)
        if isinstance(previous_confidence, (int, float)) and isinstance(new_confidence, (int, float))
        else None
    )
    new_board_decision = (new_meeting.get("tally") or {}).get("board_decision")

    event = {
        "niche": niche,
        "reopened_at": datetime.now(timezone.utc).isoformat(),
        "reason": trigger["reason"],
        "trigger_alerts": trigger["trigger_alerts"],
        "previous_decision": {
            "convened_at": trigger["previous_meeting_convened_at"],
            "board_decision": trigger["previous_board_decision"],
            "confidence": previous_confidence,
        },
        "new_decision": {
            "convened_at": new_meeting.get("convened_at"),
            "board_decision": new_board_decision,
            "confidence": new_confidence,
        },
        "confidence_delta": confidence_delta,
        "decision_changed": trigger["previous_board_decision"] != new_board_decision,
    }
    _append_reopen_event(event, reopen_log_path)

    return {"reopened": True, **event}


def scan_and_maybe_reopen(niche, decisions_path=None, board_path=None, alerts_path=None,
                           reopen_log_path=None, evidence_path=None, db_file=None):
    """The one real, on-demand, do-everything entrypoint: runs a real
    alert scan first (market_alerts.scan_market_alerts() -- the only
    real detection step), then checks and, only if materially warranted,
    executes the reopen. No scheduler exists in this factory
    (CLAUDE.md) -- this only ever runs when explicitly invoked (a
    Mission Control action, or a human/Claude Code call during a
    session)."""
    import market_alerts

    market_alerts.scan_market_alerts(niche, db_file=db_file, evidence_path=evidence_path, alerts_path=alerts_path)
    return execute_reopen(
        niche, decisions_path=decisions_path, board_path=board_path,
        alerts_path=alerts_path, reopen_log_path=reopen_log_path,
    )


def get_reopen_history(niche, reopen_log_path=None):
    """Read-only -- the full, real, permanent audit trail of every real
    reopen event for this niche, oldest first. Never mutates, never
    triggers a new scan or reopen. The connection point for Opportunity
    Queue and Revenue Engine below."""
    path = Path(reopen_log_path) if reopen_log_path else DEFAULT_REOPEN_LOG_PATH
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
            if event.get("niche") == niche:
                events.append(event)
    return events


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Decision Re-open Trigger (Live Competitive Intelligence Layer)")
    parser.add_argument("--check", metavar="NICHE", help="Read-only: would this niche's decision be reopened right now?")
    parser.add_argument("--scan-and-maybe-reopen", metavar="NICHE", help="Real scan, then reopen only if materially warranted")
    parser.add_argument("--history", metavar="NICHE", help="Read-only: full real reopen history for this niche")
    args = parser.parse_args()

    if args.check:
        emit({"success": True, "result": check_for_reopen_trigger(args.check)})
        return
    if args.scan_and_maybe_reopen:
        emit({"success": True, "result": scan_and_maybe_reopen(args.scan_and_maybe_reopen)})
        return
    if args.history:
        emit({"success": True, "result": get_reopen_history(args.history)})
        return
    parser.print_help()


if __name__ == "__main__":
    main()
