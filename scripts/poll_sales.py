#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — sales polling (ADR-016).

Calls each registered arm's get_sales() (if it has one) and records any
sale not already present in data/sales_ledger.jsonl via
channels.ledger.record_sale. Dedup key: (platform, raw sale id) — a sale
already in the ledger is never re-recorded.

Read-only toward Gumroad beyond the GET /sales call itself: never
publishes, never touches GUMROAD_ACCESS_TOKEN directly (that stays inside
channels/gumroad_arm.py), never invents a sale get_sales() did not return.

CLI mirrors distributor.py's stdin-JSON-in / stdout-JSON-out pattern:

    echo '{}' | python scripts/poll_sales.py --json
"""

import argparse
import json
import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import registry
from channels import ledger

# Self-registers "gumroad" in channels.registry on import.
import channels.gumroad_arm  # noqa: F401,E402


def _already_recorded_keys(ledger_path=None):
    keys = set()
    for event in ledger.read_events(event_type="sale", ledger_path=ledger_path):
        raw = event.get("raw") or {}
        keys.add((event.get("platform"), raw.get("id")))
    return keys


def poll_sales(arm_names=None, ledger_path=None):
    """Poll every arm that exposes get_sales() and record any new sale.

    Returns a list of per-arm outcome dicts: {"arm", "checked", "skip_reason",
    "new_sales", "error"}. An arm with no get_sales() method is reported
    with skip_reason "no get_sales() support" — not every arm is expected to
    report sales (BaseArm's contract stays unchanged, ADR-013).
    """
    targets = arm_names if arm_names is not None else [a.name for a in registry.all_arms()]
    already = _already_recorded_keys(ledger_path=ledger_path)
    outcomes = []

    for name in targets:
        arm = registry.get(name)
        if arm is None:
            outcomes.append({"arm": name, "checked": False, "skip_reason": "not registered", "new_sales": 0, "error": None})
            continue

        get_sales_fn = getattr(arm, "get_sales", None)
        if get_sales_fn is None:
            outcomes.append({"arm": name, "checked": False, "skip_reason": "no get_sales() support", "new_sales": 0, "error": None})
            continue

        sales, error = get_sales_fn()
        if error:
            outcomes.append({"arm": name, "checked": True, "skip_reason": None, "new_sales": 0, "error": error})
            continue

        new_count = 0
        for sale in sales:
            key = (name, sale.get("id"))
            if key in already:
                continue
            ledger.record_sale(name, sale, ledger_path=ledger_path)
            already.add(key)
            new_count += 1

        outcomes.append({"arm": name, "checked": True, "skip_reason": None, "new_sales": new_count, "error": None})

    return outcomes


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Sales poller (OpenClaw Factory, ADR-016)")
    parser.add_argument("--json", action="store_true", help="Read a JSON job from stdin, print a JSON result to stdout")
    args = parser.parse_args()

    if not args.json:
        parser.print_help()
        return

    try:
        raw_input = sys.stdin.read().strip()
        job = json.loads(raw_input) if raw_input else {}
        arm_names = job.get("arms")  # None = every registered arm

        outcomes = poll_sales(arm_names=arm_names)
        total_new = sum(o["new_sales"] for o in outcomes)
        emit({"success": True, "total_new_sales": total_new, "outcomes": outcomes})
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
