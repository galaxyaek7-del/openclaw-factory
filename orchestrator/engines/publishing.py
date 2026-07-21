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
every registered arm.

EOS Phase 2, Round 2 (2026-07-19) — production-safety hardening: this
adapter's `context["dry_run"]` used to pass straight through to
run_publish_pipeline() unchanged, meaning `FACTORY_AUTO_PRODUCE=true`
alone was enough to attempt a REAL live publish on the modern ladder
pipeline (`orchestrator.orchestrator --run-ladder-opportunity` hardcodes
`execute_production=True`). This diverges from the founder's own,
already-documented design: `AUTO_PRODUCE_ACTIVATION_CHECKLIST.md` and
ADR-009 §9.2 both state explicitly that live publishing needs "three
independent barriers" (Dual Inspection, FACTORY_LIVE_PUBLISH, and a real
platform token) — "لا يُنشَر تلقائياً على أي منصة إلا إذا اجتاز الفحص
المزدوج و FACTORY_LIVE_PUBLISH و التوكن." `FACTORY_LIVE_PUBLISH` was
never actually checked anywhere in this modern path (confirmed by grep
across distributor.py/orchestrator/engines/publishing.py/
commercial_execution/pipeline.py before this fix) — the legacy
book_generator/Gumroad path already honors it
(`factory_loop.js::triggerDistribute()`'s `dry_run: !LIVE_PUBLISH_ENABLED`),
this path just never got the same protection when it was built. Fixed
here, at the one real publishing dispatch point, rather than conflating
it with `execute_production` (which must keep controlling whether
PRODUCTION itself runs for real, independently of whether the result is
ever actually published live) — tightens the gate, never loosens it:
`context["dry_run"]` can still force a dry run; it just can no longer be
the ONLY thing keeping a real publish from firing.
"""

import os

from schemas.product import Product

from commercial_execution.pipeline import run_publish_pipeline
from orchestrator.registry import register_engine


def _live_publish_enabled():
    return os.environ.get("FACTORY_LIVE_PUBLISH") == "true"


@register_engine("publishing")
def run(context):
    production_result = context.get("production_result") or {}
    if not production_result.get("executed") or not production_result.get("success"):
        return {"executed": False, "reason": "لا نتاج إنتاج حقيقي ناجح متاح لهذا النيتش — لا شيء لنشره"}

    product = Product.from_jsonl_record(production_result)
    decision_result = context.get("decision_result") or {}
    product_family = decision_result.get("product_family")
    version = (production_result.get("dossier_bundle") or {}).get("version")

    # Third independent barrier (see module docstring): a real, live
    # publish attempt additionally requires FACTORY_LIVE_PUBLISH=true,
    # regardless of what context["dry_run"] says.
    dry_run = context.get("dry_run", True) or not _live_publish_enabled()

    record = run_publish_pipeline(
        product, product_family=product_family, dry_run=dry_run, version=version,
    )
    return {
        "executed": True,
        "outcomes": [
            {"arm": m["marketplace"], "attempted": m["attempted"], "ok": m["publish_status"] == "ok"}
            for m in record["marketplaces"]
        ],
        "publish_record": record,
    }
