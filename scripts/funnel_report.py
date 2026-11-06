#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Funnel report + kill-criteria verdict (2026-11-06, founder-approved decisions 1 and 5). Read-only.

    python scripts/funnel_report.py            # human summary
    python scripts/funnel_report.py --json

Funnel today, from real local records only: pins scheduled and already due (data/pinterest_manual_posts.jsonl), measured pin outbound
clicks (connector intake via demand_gate), measured sales (demand_gate SALE signal). Visits to the site are NOT MEASURED (no receiver on
GitHub Pages) and are reported as such. Checkpoints come from config/kill_criteria.json:
  OK        threshold met
  WAITING   checkpoint date not reached
  UNKNOWN   date reached but the click metric is not measured: fix the measurement, do not count it as a miss
  TRIGGERED date reached, metric measured, threshold missed: the checkpoint's `if_missed` action is the founder-visible decision
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CRITERIA = ROOT / "config" / "kill_criteria.json"
LEDGER = ROOT / "data" / "pinterest_manual_posts.jsonl"
INTAKE = ROOT / "data" / "connector_intake.jsonl"


def pin_counts(ledger=LEDGER, today=None):
    today = today or datetime.now(timezone.utc).date()
    total = due = 0
    try:
        for line in Path(ledger).read_text(encoding="utf-8").splitlines():
            if not line.startswith("{"):
                continue
            total += 1
            try:
                d = date.fromisoformat(json.loads(line).get("scheduled_for", "")[:10])
            except ValueError:
                continue
            if d <= today:
                due += 1
    except OSError:
        pass
    return total, due


def clicks_measured(intake=INTAKE):
    """True when the newest pin_metrics record says measured (rows existed); False/None otherwise. Never guesses."""
    newest = None
    try:
        for line in Path(intake).read_text(encoding="utf-8").splitlines():
            if line.startswith("{") and '"pin_metrics"' in line:
                newest = json.loads(line)
    except (OSError, ValueError):
        return None
    return None if newest is None else bool((newest.get("payload") or {}).get("measured"))


def judge(criteria, today, clicks, sales, measured):
    out = []
    for c in criteria.get("checkpoints", []):
        due = date.fromisoformat(c["date"])
        if today < due:
            out.append({"id": c["id"], "date": c["date"], "verdict": "WAITING", "days_left": (due - today).days})
            continue
        met_clicks = clicks >= c.get("min_clicks", c.get("min_pin_clicks", 0))
        met_sales = sales >= c.get("min_sales", 0)
        ok = (met_clicks or met_sales) if c.get("either") else (met_clicks and met_sales)
        if ok:
            v = "OK"
        elif not measured and c.get("min_pin_clicks", 0) > 0 and not met_clicks and (c.get("either") or met_sales):
            v = "UNKNOWN"  # clicks not measured: never a miss
        else:
            v = "TRIGGERED"
        out.append({"id": c["id"], "date": c["date"], "verdict": v, **({"if_missed": c["if_missed"]} if v in ("TRIGGERED", "UNKNOWN") else {})})
    return out


def report(today=None):
    today = today or datetime.now(timezone.utc).date()
    import demand_gate
    sig = demand_gate.evaluate().get("signals", {})
    clicks, sales = int(sig.get("PIN_CLICKS", 0) or 0), int(sig.get("SALE", 0) or 0)
    total, due = pin_counts(today=today)
    measured = clicks_measured()
    crit = json.loads(CRITERIA.read_text(encoding="utf-8"))
    return {"as_of": today.isoformat(), "pins_scheduled_total": total, "pins_due_by_today": due, "pin_outbound_clicks": clicks,
            "pin_clicks_measured": measured, "sales": sales, "site_visits": "NOT MEASURED (no receiver on static GitHub Pages)",
            "checkpoints": judge(crit, today, clicks, sales, bool(measured))}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    r = report()
    if "--json" in argv:
        sys.stdout.write(json.dumps(r, ensure_ascii=False, indent=1) + "\n")
        return 0
    L = [f"FUNNEL {r['as_of']}: pins scheduled {r['pins_scheduled_total']} (due {r['pins_due_by_today']}), measured pin clicks {r['pin_outbound_clicks']} "
         f"(measured={r['pin_clicks_measured']}), sales {r['sales']}, site visits {r['site_visits']}"]
    for c in r["checkpoints"]:
        L.append(f"  {c['id']} {c['date']}: {c['verdict']}" + (f" ({c['days_left']} days)" if "days_left" in c else ""))
    sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
