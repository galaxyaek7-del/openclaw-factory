#!/usr/bin/env python3
"""Static snapshot of the public Solutions Engine (2026-10-29).

The live data route is GET /api/solutions (server.js -> mission_control_api.py
-> commission_engine.public_solutions_catalog()). GitHub Pages serves the
public storefront with no Node process, so on the real deployment that route
404s and the three pages that render it -- customer_site/solutions.html,
recommended.html and compare.html -- showed a visitor nothing but
"Temporarily unavailable" (recommended.html was, at the time this was written,
the #2 result for site:galaxyaek7-del.github.io).

This writes customer_site/solutions.json from the same function the live
route calls, in the same envelope, with one deliberate difference: explore_url
points at each vendor's own real official_link instead of
/api/solutions/click/<id>. That click route records a real click and then
302s to the same official_link, so it cannot work without a backend; the
snapshot therefore loses click tracking (already true today, nothing was
recorded) rather than losing the link itself. Nothing is invented: every
field comes from the engine's own real, verified output.

  python scripts/export_public_solutions.py            # write the snapshot
  python scripts/export_public_solutions.py --check    # exit 1 if stale
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "customer_site" / "solutions.json"


def build(now=None):
    from commission_engine import public_solutions_catalog

    result = public_solutions_catalog(now=now)
    solutions = []
    for s in result.get("solutions") or []:
        entry = dict(s)
        official = entry.get("official_link")
        if official:
            entry["explore_url"] = official
            entry["explore_url_source"] = "official_link"
        else:
            entry["explore_url_source"] = "api_click_route"
        solutions.append(entry)

    return {
        "success": True,
        "static_snapshot": True,
        "generated_at": result.get("generated_at"),
        "category_filter": result.get("category_filter"),
        "available_categories": result.get("available_categories") or [],
        "solutions": solutions,
        "total_shown": len(solutions),
        "note": result.get("note"),
        "snapshot_note": (
            "Static snapshot of the same public Solutions Engine the live route "
            "GET /api/solutions serves. Links go straight to each vendor's own "
            "official page because this host has no backend to record a click; "
            "nothing here is ranked by commission value."
        ),
    }


def render(payload):
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"


def _comparable(payload):
    """generated_at is the moment of the run, not content -- excluded so
    --check tests the data, not the clock."""
    return {k: v for k, v in payload.items() if k != "generated_at"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if customer_site/solutions.json is missing or stale")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    body = render(build())
    out = Path(args.out)

    if args.check:
        try:
            current = json.loads(out.read_text(encoding="utf-8"))
        except OSError:
            print("MISSING: %s" % out)
            return 1
        except ValueError:
            print("UNREADABLE: %s" % out)
            return 1
        # Freshness labels and the 45-day stale cut depend on the date, so the
        # snapshot is rebuilt as of its own generated_at: --check then tests
        # the code and the data, not how many days have passed (2026-10-30:
        # a correct snapshot would otherwise fail CI as soon as one entry
        # crossed the 14-day FRESH/AGING line).
        as_of = None
        try:
            from datetime import datetime
            as_of = datetime.fromisoformat(str(current.get("generated_at")))
        except (TypeError, ValueError):
            as_of = None
        if _comparable(current) != _comparable(build(now=as_of)):
            print("STALE: %s (run scripts/export_public_solutions.py)" % out)
            return 1
        print("OK: %s" % out)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(body, encoding="utf-8", newline="\n")
    os.replace(tmp, out)
    data = json.loads(body)
    print("wrote %s (%d solutions)" % (out, data["total_shown"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
