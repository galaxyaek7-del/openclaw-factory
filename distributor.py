#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — distribution backbone (OCTOPUS_ARCHITECTURE.md §1).

Fans one Product out to every registered, supporting arm; isolates each
arm's failure from the others (ADR-5); records every attempt — success or
failure — to data/sales_ledger.jsonl via channels.ledger, replacing the
"published: true" claim OCTOPUS_ARCHITECTURE.md §7 flagged as a lie.

Synchronous only. No queue. This module does not import or modify
server.js/factory_loop.js — wiring an HTTP endpoint or an automatic
factory_loop call is a deliberate later step, not done here.

Safety: dry_run=True by default at every layer (CLI, distribute()). A real
platform push requires an explicit "dry_run": false in the CLI input JSON
— this module never flips that default itself.

CLI mirrors book_generator.py's stdin-JSON-in / stdout-JSON-out pattern so
server.js can spawn it the same way it already spawns book_generator.py,
whenever that wiring is added:

    echo '{"record": {...jsonl record...}, "dry_run": true}' | python distributor.py --json
"""

import argparse
import json
import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from channels import registry
from channels import ledger
from channels import publish_protection
from channels.base_arm import PublishResult
from schemas.product import Product
import factory_state

# Self-registers "gumroad" in channels.registry on import.
import channels.gumroad_arm  # noqa: F401,E402

# ADR-025: self-registers "payhip"/"etsy" — dry-run only today, no real
# token for either. Deliberate override of ADR-8's deferral, by explicit
# presidential request on 2026-07-12.
import channels.payhip_arm  # noqa: F401,E402
import channels.etsy_arm  # noqa: F401,E402

# ADR-065: self-registers "paddle" — dry-run only today, no real
# PADDLE_API_KEY. Preferred arm for the new AI SaaS/B2B ladder ranks
# (MASTER_CHARTER.md §2), alongside (not replacing) gumroad/payhip/etsy —
# see channels/gumroad_arm.py's own docstring for why that one is archived
# rather than removed.
import channels.paddle_arm  # noqa: F401,E402


def distribute(product, arm_names=None, dry_run=True, ledger_path=None, protection_state_path=None):
    """Fan `product` out to arms and record every attempt in the ledger.

    arm_names=None means every currently registered arm. ledger_path
    overrides the default data/sales_ledger.jsonl — used by tests so a test
    run never writes synthetic rows into the real, production ledger.
    Returns a list of outcome dicts: {"arm": str, "attempted": bool,
    "ok": bool|None, "skip_reason": str|None, "result": PublishResult|None}.

    Global Commercial Hardening, Phase 1 (2026-07-29): every REAL (non-dry-
    run) publish now passes through channels/publish_protection.py's
    pre-publish gate first — a blocked arm never reaches arm.publish(),
    exactly like an unsupported product or an unregistered arm above.
    Dry runs never touch real platforms, so the gate is skipped for them
    (no real risk to protect against, and no behavior change to this
    module's existing dry-run-by-default safety net). protection_state_path
    overrides the default data/publish_protection_state.json, same reason
    ledger_path exists.
    """
    targets = arm_names if arm_names is not None else [a.name for a in registry.all_arms()]
    outcomes = []

    for name in targets:
        arm = registry.get(name)
        if arm is None:
            outcomes.append({
                "arm": name, "attempted": False, "ok": None,
                "skip_reason": "not registered", "result": None,
            })
            continue

        gate = None
        try:
            if not arm.supports(product):
                outcomes.append({
                    "arm": name, "attempted": False, "ok": None,
                    "skip_reason": "unsupported product", "result": None,
                })
                continue

            if not dry_run:
                gate = publish_protection.check_publish_allowed(name, state_path=protection_state_path)
                if not gate["allowed"]:
                    blocked_result = PublishResult(
                        ok=False, platform=name, product_id=None, url=None,
                        error=f"blocked by publish protection layer: {gate['reason']}", dry_run=dry_run,
                    )
                    ledger.record_publish_attempt(
                        product, blocked_result, ledger_path=ledger_path,
                        risk_score=gate["risk_score"], protection_decision="blocked",
                    )
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": f"blocked by publish protection layer: {gate['reason']}", "result": None,
                    })
                    continue

            result = arm.publish(product, dry_run=dry_run)
        except Exception as e:
            # Defense in depth (ADR-5): even if an arm breaks its own
            # contract and raises instead of returning a PublishResult, one
            # arm's bug never takes down the rest of the distribution run.
            result = PublishResult(
                ok=False, platform=name, product_id=None, url=None,
                error=f"arm raised unexpectedly: {e}", dry_run=dry_run,
            )

        ledger.record_publish_attempt(
            product, result, ledger_path=ledger_path,
            risk_score=(gate or {}).get("risk_score"),
            protection_decision=("allowed" if gate else None),
        )

        if not dry_run:
            publish_protection.note_publish_outcome(name, result.ok, state_path=protection_state_path)

        # Unified Recovery System §3 (2026-07-18): a real (non-dry-run)
        # publish attempt that failed is remembered for a later retry —
        # the publish_attempt record above already makes this honest and
        # auditable; this just adds "try again once reachable" on top.
        # Never enqueued for a dry run (nothing real to retry) or a
        # config/not-ready failure (retrying won't fix a missing API key).
        if not result.dry_run and not result.ok and not str(result.error or "").startswith("arm not ready:"):
            factory_state.enqueue_retry(f"arm_publish:{name}:{product.source_id}", result.error)

        outcomes.append({
            "arm": name, "attempted": True, "ok": result.ok,
            "skip_reason": None, "result": result,
        })

    return outcomes


def _outcome_to_json(outcome):
    result = outcome["result"]
    return {
        "arm": outcome["arm"],
        "attempted": outcome["attempted"],
        "ok": outcome["ok"],
        "skip_reason": outcome["skip_reason"],
        "result": None if result is None else {
            "ok": result.ok,
            "platform": result.platform,
            "product_id": result.product_id,
            "url": result.url,
            "error": result.error,
            "dry_run": result.dry_run,
        },
    }


def emit(obj):
    sys.stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Distribution backbone (Galaxy Forge)")
    parser.add_argument("--json", action="store_true", help="Read a JSON job from stdin, print a JSON result to stdout")
    args = parser.parse_args()

    if not args.json:
        parser.print_help()
        return

    try:
        job = json.load(sys.stdin)
        record = job.get("record")
        if not isinstance(record, dict):
            raise ValueError("job.record must be a JSONL record object")

        product = Product.from_jsonl_record(record)
        arm_names = job.get("arms")  # None = every registered arm
        dry_run = job.get("dry_run", True)  # explicit False required to go live

        outcomes = distribute(product, arm_names=arm_names, dry_run=dry_run)
        emit({"success": True, "dry_run": dry_run, "outcomes": [_outcome_to_json(o) for o in outcomes]})
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
