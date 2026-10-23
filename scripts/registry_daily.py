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


def run_once(today=None, state_path=STATE, runner=None):
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
    dc = summary["drift_counts"]
    issues = {k: v for k, v in dc.items() if v}
    detail = (f"{summary['products']} products {summary['states']}, sales {summary['sales_total']}; "
              + ("drift: " + ", ".join(f"{k}={v}" for k, v in issues.items()) if issues else "no drift"))
    return {"action": "drift" if issues else "ok", "detail": detail}


def main():
    try:
        r = run_once()
    except Exception as e:  # reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
