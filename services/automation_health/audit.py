#!/usr/bin/env python3
"""Automation health audit for an n8n instance, from its public API (2026-10-29).

The customer-safe counterpart of scripts/n8n_workflow_health.py. That script
reads a copy of the factory's own n8n database, which holds encrypted
credentials: acceptable for the factory, never for a customer (backlog B35).
This one takes only what n8n's public API returns with a read-only API key:

  GET /api/v1/workflows                     -> id, name, active
  GET /api/v1/executions?workflowId=<id>    -> status, startedAt (no payloads)

and the customer's own statement of how often each workflow should run. Same
verdict rules as the internal tool, so "the port answers" is never "OK":

  UNKNOWN   no execution evidence (or no declared schedule to judge freshness)
  FAILING   the latest execution errored or crashed
  STALE     the latest success is older than the declared interval allows
  OK        active, latest run succeeded, and fresh
  INACTIVE  the workflow is switched off (reported, not judged)

Excluded on purpose: execution payloads (includeData) can contain customer
data, so whether a successful run did the right business thing is left to
human review. Nothing here writes to n8n.

    python services/automation_health/audit.py services/automation_health/demo_input.json
"""
import json
import sys
from datetime import datetime, timedelta, timezone

FRESH_FACTOR = 2          # same tolerance as the internal tool
GRACE = timedelta(minutes=30)


def _ts(v):
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def assess(workflows, executions, expected_minutes, now):
    """workflows: [{id, name, active}]; executions: [{workflowId, status, startedAt}];
    expected_minutes: {workflow name: minutes between runs, or None for manual}."""
    by_wf = {}
    for e in executions:
        by_wf.setdefault(str(e.get("workflowId")), []).append(e)
    rows = []
    for w in workflows:
        runs = sorted(by_wf.get(str(w.get("id")), []), key=lambda e: str(e.get("startedAt")), reverse=True)
        name = w.get("name")
        rec = {"workflow": name, "active": bool(w.get("active")), "runs": len(runs),
               "errors": sum(1 for e in runs if e.get("status") in ("error", "crashed")),
               "last_status": runs[0].get("status") if runs else None,
               "last_started_at": runs[0].get("startedAt") if runs else None,
               "last_success_at": next((e.get("startedAt") for e in runs if e.get("status") == "success"), None),
               "expected_every_minutes": expected_minutes.get(name), "reasons": []}
        interval = expected_minutes.get(name)
        last_ok = _ts(rec["last_success_at"])
        if not rec["active"]:
            rec["verdict"], rec["reasons"] = "INACTIVE", ["workflow is switched off"]
        elif not runs:
            rec["verdict"], rec["reasons"] = "UNKNOWN", ["no execution evidence"]
        elif rec["last_status"] in ("error", "crashed"):
            rec["verdict"] = "FAILING"
            rec["reasons"].append("latest execution %s" % rec["last_status"])
        elif name not in expected_minutes:
            rec["verdict"], rec["reasons"] = "UNKNOWN", ["no expected schedule declared, freshness cannot be judged"]
        elif interval is not None and (last_ok is None or now - last_ok > timedelta(minutes=interval) * FRESH_FACTOR + GRACE):
            rec["verdict"] = "STALE"
            rec["reasons"].append("no successful run within %d minutes" % (interval * FRESH_FACTOR))
        elif rec["last_status"] == "success":
            rec["verdict"] = "OK"
        else:
            rec["verdict"], rec["reasons"] = "UNKNOWN", ["latest status %s" % rec["last_status"]]
        rows.append(rec)
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    return {"generated_at": now.isoformat(timespec="seconds"), "workflows": rows, "counts": counts,
            "needs_attention": [r["workflow"] for r in rows if r["verdict"] in ("FAILING", "STALE", "UNKNOWN")],
            "scope_note": "status and timing only; business results of successful runs need human review"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    doc = json.load(open(argv[0], encoding="utf-8"))
    now = _ts(doc.get("now")) or datetime.now(timezone.utc)
    out = assess(doc["workflows"], doc["executions"], doc.get("expected_minutes", {}), now)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
