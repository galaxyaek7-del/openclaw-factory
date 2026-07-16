"""
Publishing engine adapter (ADR-051) — thin wrapper over
distributor.distribute() (untouched). Reuses distributor.py's own
dry_run=True default rather than introducing a second, possibly
inconsistent safety flag — this adapter's `context["dry_run"]` is passed
straight through to it.
"""

from schemas.product import Product

import distributor
from orchestrator.registry import register_engine


@register_engine("publishing")
def run(context):
    production_result = context.get("production_result") or {}
    if not production_result.get("executed") or not production_result.get("success"):
        return {"executed": False, "reason": "لا نتاج إنتاج حقيقي ناجح متاح لهذا النيتش — لا شيء لنشره"}

    product = Product.from_jsonl_record(production_result)
    outcomes = distributor.distribute(product, dry_run=context.get("dry_run", True))
    return {
        "executed": True,
        "outcomes": [{"arm": o["arm"], "attempted": o["attempted"], "ok": o["ok"]} for o in outcomes],
    }
