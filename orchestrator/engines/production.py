"""
Production engine adapter (ADR-051) — real subprocess integration with
book_generator.py's established stdin-JSON-in / stdout-JSON-out CLI
(the same `--json` contract server.js/factory_loop.js already use,
dispatching on `topic` in the payload -> generate_book()).

Safety: dry_run=True by default, same convention distributor.py already
uses for anything with a real-world cost/side effect. This engine is
only reached at all when the Orchestrator's execute_production gate is
True (see orchestrator.py) AND the decision stage's status was
ACCEPTED — a dry_run=True context reaching here regardless still never
spawns the real subprocess, so misconfiguration can never silently
spend real Groq tokens.
"""

import json
import subprocess
import sys
from pathlib import Path

from orchestrator.registry import register_engine
from production_factory.dossier import make_production_id
from product_families import registry as family_registry
from product_families.spec import build_product_specification

_FACTORY_ROOT = Path(__file__).resolve().parent.parent.parent
_BOOK_GENERATOR = _FACTORY_ROOT / "book_generator.py"


@register_engine("production")
def run(context):
    if context.get("dry_run", True):
        return {"executed": False, "reason": "dry_run=True — no subprocess spawned, no Groq cost incurred"}

    niche = context["niche"]
    decision = context.get("decision_result") or {}
    ladder = decision.get("ladder")

    # Packaging Architecture Plan §7 (Phase A, 2026-07-18): a resolved
    # product_family with an actually-registered adapter dispatches
    # in-process through product_families.registry — the new, modular
    # Generation path. Any other case (no family resolved yet, or a
    # family name with no adapter module built, e.g. the 5 not-yet-built
    # families) falls through to the exact hardcoded techdoc/book payload
    # below, byte-for-byte unchanged — this is the deliberate
    # "nothing breaks mid-migration" guarantee from the plan's Risk 4.
    product_family = decision.get("product_family")
    adapter = family_registry.get(product_family) if product_family else None
    if adapter is not None:
        price = (decision.get("evaluation_snapshot") or {}).get("price")
        spec = build_product_specification(
            niche=niche, product_family=product_family, ladder=ladder,
            production_id=make_production_id(decision) if decision.get("decision_id") else None,
            title=niche, topic=niche, author="OpenClaw Factory", price_hint=price,
        )
        result = adapter.generate(spec)
        return {"executed": True, **result}

    if ladder:
        # ADR-077 (Product Generation Pipeline): a ladder-tagged decision
        # (Strategic Production Priority Ladder, MASTER_CHARTER.md §2)
        # routes to the real technical-docs product-package generator,
        # priced against its own real ladder band — the exact same
        # routing factory_loop.js's briefFromGoldenOpportunity() already
        # uses (ADR-071), kept consistent here rather than diverging into
        # a second real decision about what to build for the same
        # decision_path this factory just unified (ADR-076).
        price = (decision.get("evaluation_snapshot") or {}).get("price") or 197
        payload = {"title": niche, "topic": niche, "product_type": "techdoc", "price": price, "author": "OpenClaw Factory"}
        # Requirement #5 (ADR-077): reuse production_factory.dossier's own
        # ID formula (f"PROD-{decision_id}") rather than a second one, so
        # the real generated file's own log entry, the dossier, and the
        # eventual Finance/Telegram trail all key off the same identifier.
        if decision.get("decision_id"):
            payload["production_id"] = make_production_id(decision)
    else:
        payload = {"topic": niche, "title": niche, "author": "OpenClaw Factory"}

    proc = subprocess.run(
        [sys.executable, str(_BOOK_GENERATOR), "--json"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True, text=True, timeout=300, encoding="utf-8",
    )
    try:
        result = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return {"executed": True, "success": False, "error": f"invalid JSON from book_generator.py: {proc.stdout[:500]}"}
    return {"executed": True, **result}
