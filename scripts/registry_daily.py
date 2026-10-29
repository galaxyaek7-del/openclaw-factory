#!/usr/bin/env python3
"""Daily product-registry rebuild for factory_loop.js (2026-10-23).

Once per UTC day: rebuild data/product_registry.json from the live Gumroad
catalog (read-only GET) and re-check every published listing page, then
report the drift counts in the loop's one-line JSON shape. Nothing on any
platform is changed.

    python scripts/registry_daily.py --once
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STATE = ROOT / "data" / "registry_daily_state.json"


def _write_arms():
    import business_arms
    return business_arms.write_state()


def run_once(today=None, state_path=STATE, runner=None, arms_writer=None):
    import product_registry
    today = today or datetime.now(timezone.utc).date().isoformat()
    try:
        last = json.loads(Path(state_path).read_text(encoding="utf-8")).get("last_day")
    except (OSError, ValueError):
        last = None
    if last == today:
        return {"action": "none", "detail": f"registry already rebuilt for {today}"}
    summary, drift = (runner or (lambda: product_registry.run(write=True, check_pages=True)))()
    tmp = Path(str(state_path) + ".tmp")
    tmp.write_text(json.dumps({"last_day": today, "summary": summary}), encoding="utf-8")
    os.replace(tmp, state_path)
    # Arm statuses are derived from the registry just rebuilt, so restate them
    # now (data/business_arms_state.json, read by the CEO dashboard). A failure
    # here is reported in the detail, never allowed to hide the registry result.
    arms_note = ""
    if arms_writer is None:
        # Only the real rebuild restates the live arm file; a caller that
        # injects its own runner (tests, tools) must inject a writer too.
        arms_writer = _write_arms if runner is None else (lambda: None)
    try:
        doc = arms_writer()
        if doc and doc.get("problems"):
            arms_note = f"; arm state problems: {len(doc['problems'])}"
    except Exception as e:  # pragma: no cover - reported, not raised
        arms_note = f"; arm state not written ({type(e).__name__})"
    dc = summary["drift_counts"]
    issues = {k: v for k, v in dc.items() if v}
    detail = (f"{summary['products']} products {summary['states']}, sales {summary['sales_total']}; "
              + ("drift: " + ", ".join(f"{k}={v}" for k, v in issues.items()) if issues else "no drift")
              + arms_note)
    return {"action": "drift" if issues else "ok", "detail": detail}


def main():
    try:
        r = run_once()
    except Exception as e:  # reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
