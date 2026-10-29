#!/usr/bin/env python3
"""Weekly Gumroad delivery audit for factory_loop.js (2026-10-29).

Runs scripts/gumroad_delivery_audit.py (GET requests only: what file each live
listing really delivers, and whether its description promises more) when the
newest reports/GUMROAD_DELIVERY_AUDIT_<date>.json is 7 or more days old. The
CEO dashboard reads that report (lib/commercial_funnel.js) and marks it stale
after 8 days; before this step it was only refreshed by hand.

    python scripts/delivery_audit_weekly.py --once
"""
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
AUDIT = ROOT / "scripts" / "gumroad_delivery_audit.py"
MAX_AGE_DAYS = 7


def latest_report_date(reports=REPORTS):
    days = []
    for p in Path(reports).glob("GUMROAD_DELIVERY_AUDIT_*.json"):
        m = re.fullmatch(r"GUMROAD_DELIVERY_AUDIT_(\d{4}-\d{2}-\d{2})\.json", p.name)
        if m:
            days.append(date.fromisoformat(m.group(1)))
    return max(days) if days else None


def _run(timeout_s=1200):
    r = subprocess.run([sys.executable, str(AUDIT)], cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout_s)
    if r.returncode != 0:
        raise RuntimeError(f"audit exited {r.returncode}: {r.stderr.strip()[-200:]}")
    return json.loads(r.stdout.strip().splitlines()[0])


def run_once(today=None, reports=REPORTS, runner=None):
    today = today or datetime.now(timezone.utc).date()
    last = latest_report_date(reports)
    if last and (today - last).days < MAX_AGE_DAYS:
        return {"action": "none", "detail": f"delivery audit from {last} is current"}
    try:
        out = (runner or _run)()
    except Exception as e:
        return {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    counts = out.get("issue_counts") or {}
    return {"action": "recorded",
            "detail": f"{out.get('published')} published listings audited; issues {json.dumps(counts, sort_keys=True)}"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--once" not in argv:
        print(__doc__)
        return 2
    print(json.dumps(run_once()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
