"""Automated submission-state monitor for the Freelancer pipeline.

--once : check every ACTIVE + HELD project via the public API, compare
         against the stored baseline, print one JSON line:
           {"checked": N, "changes": [...], "action": "silent"|"changed"}
         Updates the baseline ONLY with observed values (never inferred).
         Exit 0 always. No auth, no writes except the baseline file.

Material changes (award/close/reopen/freeze-status flips) are reported
as structured events for the tick to surface; everything else is silent.
"""
import json
import os
import sys

BASELINE_PATH = "data/freelancer_monitor_baseline.json"
PIPELINE_PATH = "data/global_pipeline.json"


def detect_changes(old, new):
    """Pure: list material changes between stored baseline and fresh facts."""
    events = []
    for pid, prev in old.items():
        cur = new.get(pid)
        if cur is None:
            events.append({"project": pid, "event": "UNTRACKED"})
            continue
        if cur.get("status") != prev.get("status") or cur.get(
            "sub_status"
        ) != prev.get("sub_status"):
            events.append(
                {
                    "project": pid,
                    "event": "STATUS_CHANGE",
                    "from": "%s/%s"
                    % (prev.get("status"), prev.get("sub_status")),
                    "to": "%s/%s"
                    % (cur.get("status"), cur.get("sub_status")),
                }
            )
        if cur.get("frontend_status") != prev.get("frontend_status"):
            events.append(
                {
                    "project": pid,
                    "event": "FRONTEND_CHANGE",
                    "to": cur.get("frontend_status"),
                }
            )
    for pid in new:
        if pid not in old:
            events.append({"project": pid, "event": "NEW_TRACKED"})
    return events


def main():
    from freelancer_api import get_project

    try:
        with open(PIPELINE_PATH) as fh:
            pipe = json.load(fh)
    except (OSError, ValueError):
        print(json.dumps({"checked": 0, "changes": [], "action": "no-pipeline"}))
        return 0
    ids = [a["id"] for a in pipe.get("active", [])] + [
        h["id"] for h in pipe.get("held", []) if isinstance(h, dict) and "id" in h
    ]

    try:
        with open(BASELINE_PATH) as fh:
            base = json.load(fh)
    except (OSError, ValueError):
        base = {"projects": {}}
    old = base.get("projects", {})

    fresh = {}
    for pid in ids:
        try:
            p = get_project(int(pid))
            fresh[str(pid)] = {
                "status": p.get("status"),
                "sub_status": p.get("sub_status"),
                "frontend_status": p.get("frontend_project_status"),
                "bid_count": ((p.get("bid_stats") or {}).get("bid_count")),
            }
        except Exception as e:
            fresh[str(pid)] = {"error": type(e).__name__}

    changes = detect_changes(old, {k: v for k, v in fresh.items() if "error" not in v})
    base["projects"] = {
        k: v for k, v in fresh.items() if "error" not in v
    }
    try:
        with open(BASELINE_PATH, "w") as fh:
            json.dump(base, fh, indent=1)
    except OSError:
        pass
    print(
        json.dumps(
            {
                "checked": len(fresh),
                "changes": changes,
                "action": "changed" if changes else "silent",
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
