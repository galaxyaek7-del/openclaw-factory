"""
Publishing engine adapter (ADR-051, extended Universal Production Engine
Roadmap Step 4, 2026-07-19) — thin wrapper over
commercial_execution.pipeline.run_publish_pipeline(), which itself wraps
distributor.distribute() (still unchanged) with one new integration: a
decision's product_family, when it has a registered ProductManifest
(Product Definition Registry, Step 3), narrows publishing to that
family's declared supported_marketplaces instead of fanning out to every
registered arm. A decision with no product_family (or one with no
manifest — kdp_books/knowledge_bases) keeps today's exact behavior:
every registered arm. Reuses distributor.py's own dry_run=True default
rather than introducing a second, possibly inconsistent safety flag —
this adapter's `context["dry_run"]` is passed straight through to it.
"""

from schemas.product import Product

from commercial_execution.pipeline import run_publish_pipeline
from orchestrator.registry import register_engine


@register_engine("publishing")
def run(context):
    production_result = context.get("production_result") or {}
    if not production_result.get("executed") or not production_result.get("success"):
        return {"executed": False, "reason": "لا نتاج إنتاج حقيقي ناجح متاح لهذا النيتش — لا شيء لنشره"}

    product = Product.from_jsonl_record(production_result)
    decision_result = context.get("decision_result") or {}
    product_family = decision_result.get("product_family")
    version = (production_result.get("dossier_bundle") or {}).get("version")

    record = run_publish_pipeline(
        product, product_family=product_family, dry_run=context.get("dry_run", True), version=version,
    )
    return {
        "executed": True,
        "outcomes": [
            {"arm": m["marketplace"], "attempted": m["attempted"], "ok": m["publish_status"] == "ok"}
            for m in record["marketplaces"]
        ],
        "publish_record": record,
    }
