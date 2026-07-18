"""The unified Publish Pipeline (Universal Production Engine Roadmap
Step 4, 2026-07-19): Publishing -> Verification -> Revenue Registration
-> Audit Trail in one call, plus the one PublishRecord requirement #3
asks every publication to produce.

Discovery/Generation/QA/Packaging already happened upstream (Content
Generation, Asset Generation, Dual Inspection — Roadmap Steps 1-3); this
module starts from an already-generated, already-QA'd Product and
distributes it. Knowledge Update stays the existing, unchanged
`_full_cycle()`/decision_engine.learning mechanism — no new code needed
there (see COMMERCIAL_EXECUTION.md).
"""

import distributor
from channels import ledger
import factory_state


def resolve_target_arms(product_family):
    """None (fan out to every registered arm — distributor.distribute()'s
    own real default, unchanged) when `product_family` is falsy or has no
    registered ProductManifest (kdp_books/knowledge_bases, and any legacy
    call, keep today's exact behavior). Otherwise the manifest's real,
    computed compatible_arms() — never the manifest's own possibly-stale
    supported_marketplaces list blindly."""
    if not product_family:
        return None
    from product_families.manifest import get as get_manifest, compatible_arms
    manifest = get_manifest(product_family)
    if manifest is None:
        return None
    return compatible_arms(manifest)


def _recovery_token(arm_name, product_source_id):
    """The EXACT task-name string distributor.py's own
    factory_state.enqueue_retry() call already uses for a failed real
    publish (f"arm_publish:{arm}:{source_id}") — a real, traceable
    reference into factory_state.json's pending_retries, never a second,
    parallel ID scheme."""
    return f"arm_publish:{arm_name}:{product_source_id}"


def _pending_retry_for(recovery_token, state_path=None):
    state = factory_state.load_state(state_path)
    for r in state.get("pending_retries") or []:
        if r.get("task") == recovery_token:
            return r
    return None


def _revenue_status(product_source_id, ledger_path=None):
    """Real, computed status from channels/ledger.py's own events — never
    fabricated. `listed_on` is reliable: record_publish_attempt() already
    tags every event with the real product_source_id. Per-product SALE
    attribution is honestly NOT reliable today — real platform sale
    payloads (Paddle transactions, Gumroad sales) don't consistently echo
    back our internal production_id, so `sale_attribution` says so
    explicitly rather than fabricating a match."""
    listed_on = sorted({
        e.get("platform") for e in ledger.read_events(event_type="publish_attempt", ledger_path=ledger_path)
        if e.get("product_source_id") == product_source_id and e.get("ok")
    })
    return {"listed_on": listed_on, "sale_attribution": "platform_wide_not_yet_per_product"}


def build_publish_record(product, outcomes, version=None, ledger_path=None, state_path=None):
    """Assembles the mandatory per-publish record (Universal Production
    Engine Roadmap Step 4): Product ID, Marketplace ID (per arm), Version,
    Publish Status, Revenue Status, Recovery Token, Audit Trail — from
    real existing sources (PublishResult/channels.ledger/factory_state),
    nothing fabricated.

    product: the schemas.product.Product this was published from.
    outcomes: distributor.distribute()'s own real return list.
    version: dossier_bundle's real per-build version string, when known
    (honestly None when the caller doesn't have one — never guessed).
    """
    product_source_id = product.source_id

    marketplaces = []
    for outcome in outcomes:
        result = outcome.get("result")
        recovery_token = _recovery_token(outcome["arm"], product_source_id)
        pending_retry = _pending_retry_for(recovery_token, state_path=state_path) if outcome["attempted"] else None
        error_text = str((result.error if result else None) or "")
        marketplaces.append({
            "marketplace": outcome["arm"],
            "attempted": outcome["attempted"],
            "publish_status": (
                "not_attempted" if not outcome["attempted"] else
                "ok" if outcome.get("ok") else
                # Same "arm not ready" distinction distributor.py's own
                "not_ready" if error_text.startswith("arm not ready:") else "failed"
            ),
            "skip_reason": outcome.get("skip_reason"),
            "marketplace_id": result.product_id if result else None,
            "url": result.url if result else None,
            "error": result.error if result else None,
            "dry_run": result.dry_run if result else None,
            "recovery_token": recovery_token,
            "has_pending_retry": pending_retry is not None,
        })

    audit_trail = [
        e for e in ledger.read_events(event_type="publish_attempt", ledger_path=ledger_path)
        if e.get("product_source_id") == product_source_id
    ]

    return {
        "product_id": product_source_id,
        "version": version,
        "marketplaces": marketplaces,
        "revenue_status": _revenue_status(product_source_id, ledger_path=ledger_path),
        "audit_trail": audit_trail,
    }


def run_publish_pipeline(product, product_family=None, dry_run=True,
                          ledger_path=None, state_path=None, version=None):
    """The unified Publish Pipeline. Reuses distributor.distribute()
    unchanged for the actual fan-out/ledger/retry mechanism — the one new
    integration is arm selection: a product_family with a registered
    ProductManifest (Step 3) publishes only to its declared
    supported_marketplaces, computed for real against channels.registry;
    a family with no manifest (or none given) keeps today's exact
    behavior — every registered arm."""
    target_arms = resolve_target_arms(product_family)
    outcomes = distributor.distribute(product, arm_names=target_arms, dry_run=dry_run, ledger_path=ledger_path)
    return build_publish_record(
        product, outcomes, version=version, ledger_path=ledger_path, state_path=state_path,
    )
