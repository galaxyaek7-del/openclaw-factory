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

# X (Twitter) arm — self-registers "x" in channels.registry on import.
# Requires X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET.
import channels.x_arm  # noqa: F401,E402

# S3-ARMS-01 (2026-10-01): self-registers "kdp" — was importable via
# channels.kdp_arm directly but never wired into the distributor path, so
# distribute(..., arm_names=["kdp"]) always returned "not registered".
# Same self-registration pattern as every arm above; dry-run behavior
# unchanged (KDP has no API — validate-only by design).
import channels.kdp_arm  # noqa: F401,E402


# Operational product lock (Commercial Closure, 2026-09-17): the live EU
# AI Act Compliance Toolkit must never be touched by automation except
# through an explicit, per-call founder opt-in (allow_protected=True).
# Anchored on the exact generation-record source_id plus the exact title
# (same product under any record shape). Dry runs are exempt (no
# real-world effect); every real-mode path without the flag skips with an
# explicit reason and touches neither platform nor protection state.
PROTECTED_PRODUCTS = frozenset({
    "2026-08-06T23:06:44.375628",
    "EU AI Act Compliance Toolkit",
})


def _is_protected_product(product):
    source_id = getattr(product, "source_id", None) or ""
    title = getattr(product, "title", None) or ""
    return source_id in PROTECTED_PRODUCTS or title in PROTECTED_PRODUCTS


def _already_published_live(product, arm_name, ledger_path=None):
    """Read-only idempotency check: does the ledger already hold a
    successful REAL (non-dry-run) publish_attempt for this product+arm?

    Fail-closed in the safe direction: only a positively-recorded live
    success (ok True AND dry_run False) blocks a new real attempt. A
    missing/unreadable ledger, a malformed line, or a dry-run/failed event
    never blocks — the pre-existing protection gate still fronts every
    real attempt. Never writes, never touches the network.
    """
    path = Path(ledger_path) if ledger_path else ledger.DEFAULT_LEDGER_PATH
    if not path.exists():
        return False
    source_id = getattr(product, "source_id", None)
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if (isinstance(ev, dict)
                        and ev.get("event_type") == "publish_attempt"
                        and ev.get("platform") == arm_name
                        and ev.get("product_source_id") == source_id
                        and ev.get("ok") is True
                        and ev.get("dry_run") is False):
                    return True
    except OSError:
        return False
    return False


def distribute(product, arm_names=None, dry_run=True, ledger_path=None, protection_state_path=None,
               allow_protected=False):
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
                if not allow_protected and _is_protected_product(product):
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": "protected product: explicit founder gate required (allow_protected=True)",
                        "result": None,
                    })
                    continue
                if _already_published_live(product, name, ledger_path=ledger_path):
                    outcomes.append({
                        "arm": name, "attempted": False, "ok": None,
                        "skip_reason": "duplicate: ledger already holds a successful live publish for this product",
                        "result": None,
                    })
                    continue
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
    parser.add_argument("--allow-protected", action="store_true",
                        help="Explicit founder opt-in: allow real-mode publish of a protected product (default: skip it)")
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
        allow_protected = bool(job.get("allow_protected", False))  # explicit True required for protected products

        outcomes = distribute(product, arm_names=arm_names, dry_run=dry_run, allow_protected=allow_protected)
        emit({"success": True, "dry_run": dry_run, "outcomes": [_outcome_to_json(o) for o in outcomes]})
    except Exception as e:
        emit({"success": False, "error": str(e)})
        sys.exit(0)


if __name__ == "__main__":
    main()
