#!/usr/bin/env python3
"""Loop step: check the USPTO fee schedule at most once per UTC day.

Runs data_products/uspto_fee_monitor.py (one GET of the official page) and
prints one JSON line for factory_loop.js: action none (already checked today),
unchanged, changed (a new release is due; the founder dashboard shows it via
the log) or unreadable. Never edits the release.

    python scripts/uspto_fee_monitor_daily.py --once
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data_products"))
import uspto_fee_monitor as monitor  # noqa: E402


def last_check_date(log=monitor.LOG):
    try:
        lines = Path(log).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            return json.loads(line)["checked_at"][:10]
        except (ValueError, KeyError, TypeError):
            continue
    return None


def once(now=None, log=monitor.LOG, page_html=None, releases=monitor.RELEASES):
    now = now or datetime.now(timezone.utc)
    if last_check_date(log) == now.date().isoformat():
        return {"action": "none", "detail": "USPTO fees already checked today"}
    out = monitor.run(page_html, releases=releases, log=log, now=now)
    detail = "release %s vs page (last revised %s): %s" % (out["release"], out.get("page_last_revised"), out["status"])
    if out["changes"]:
        detail += "; " + ", ".join("%s %s->%s" % (c["fee_code"], c["release"], c["page"]) for c in out["changes"])
    if out.get("codes_not_found"):
        detail += "; codes not found: " + ", ".join(out["codes_not_found"])
    return {"action": out["status"].lower(), "detail": detail}


if __name__ == "__main__":
    print(json.dumps(once()))
