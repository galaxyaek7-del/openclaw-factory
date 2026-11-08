#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Loop step: refresh data/analytics_snapshot.json at most once an hour (2026-11-07). Prints one JSON line {action, detail}.

    python scripts/analytics_snapshot.py --once

Read-only toward the counter (GET only). With no counter code or no token it still writes an honest UNKNOWN snapshot, so the Founder
Dashboard shows "not measured" instead of an old number. Spends nothing.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
MIN_GAP = timedelta(minutes=55)


def run_once(now=None, snapshot_path=None, builder=None):
    import galaxy_analytics as ga
    now = now or datetime.now(timezone.utc)
    path = Path(snapshot_path) if snapshot_path else ga.SNAPSHOT
    try:
        prev = json.loads(path.read_text(encoding="utf-8"))
        last = datetime.fromisoformat(prev["generated_at"])
        gap = MIN_GAP if prev.get("status") in ("READ_OK", "NOT_CONFIGURED", "NO_TOKEN") else timedelta(minutes=10)  # a partial read is retried sooner
        if now - last < gap:
            return {"action": "none", "detail": f"analytics snapshot is {int((now - last).total_seconds() / 60)} min old; refreshed hourly"}
    except (OSError, ValueError, KeyError):
        pass
    if builder is None:
        import beacon_coverage
        cov = beacon_coverage.scan()
        builder = lambda: ga.build_snapshot(now=now, coverage=cov)  # noqa: E731
    snap = builder()
    ga.write_snapshot(snap, path)
    unknown = sum(1 for v in snap["metrics"].values() if v["class"] == "UNKNOWN")
    return {"action": "ran", "detail": f"analytics {snap['status']}: {len(snap['metrics']) - unknown} metrics read, {unknown} UNKNOWN"}


def main():
    try:
        r = run_once()
    except Exception as e:  # noqa: BLE001
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:160]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
