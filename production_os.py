"""Galaxy Forge -- Production OS (new, ADR-203, 2026-08-17).

Closes the two real gaps the Production OS audit (reports/PRODUCTION_OS_
AUDIT_2026-08-17.md) found in the existing, already-real production layer:

  * Build 1 -- the real caller of dossier_bundle.build_product_dossier_bundle().
    That builder (documentation + metadata + marketing + support + build
    manifest + QA report + recovery metadata + real versioned changelog)
    had zero live callers -- the only real product ever produced
    (books/eu_ai_act_compliance_toolkit.pdf) was generated directly by
    book_generator.py, so no product on this factory's books ever got a
    dossier bundle or a real product_changelog.jsonl version entry.
    production_os.build_product_bundle() is that missing caller: it reads
    the real books/_generation_log.jsonl record for a production_id, feeds
    it through the already-real bundle builder unchanged, and returns the
    bundle. It never fabricates -- a production_id with no real
    generation-log record returns an honest not-found result, never an
    invented bundle.

  * Build 2 -- a read-only Product Lifecycle view over real logs. Reads
    the real generation log, real product_changelog.jsonl, and real
    factory_state.json once, groups by production_id (the real product
    identity every production stage already uses), and reuses
    value_engine.classify_lifecycle_stage() -- the one real lifecycle
    classification this factory has -- verbatim for a bounded, disclosed
    subset (classification is ~2-4s per distinct niche and must not make
    a passive view minutes-long). The per-product factory_state signal is
    dossier_bundle.build_bundle._recovery_metadata() -- the same real
    lookup the bundle builder already uses -- never a re-derivation.

No new infrastructure is created: this module is pure assembly over
already-real ledgers, the same "reuse, don't duplicate" discipline this
factory has applied throughout. Nothing here publishes, pays, or touches
financial/payment state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
_GENERATION_LOG_PATH = _FACTORY_ROOT / "books" / "_generation_log.jsonl"
_CHANGELOG_PATH = _FACTORY_ROOT / "data" / "product_changelog.jsonl"

# The real test/demo markers that appear in books/_generation_log.jsonl
# (PROD-dec-test-1, PROD-automation-test-1, PROD-demo-config-only,
# PROD-demo-recovery, ...) -- a disclosed, mechanical filter, never an
# assertion that a record without a marker is a sellable product.
_TEST_PRODUCTION_ID_MARKERS = ("test", "demo")


def _read_generation_log(generation_log_path: Optional[str] = None) -> List[dict]:
    path = Path(generation_log_path) if generation_log_path else _GENERATION_LOG_PATH
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return records


def _is_test_production_id(production_id: Optional[str]) -> bool:
    if not production_id:
        return True
    lowered = str(production_id).lower()
    return any(m in lowered for m in _TEST_PRODUCTION_ID_MARKERS)


def find_generation_records(production_id: str, generation_log_path: Optional[str] = None) -> List[dict]:
    """Read-only: every real books/_generation_log.jsonl record for this
    production_id, in log order. Never a live trigger of any production."""
    return [
        r for r in _read_generation_log(generation_log_path)
        if r.get("production_id") == production_id
    ]


def latest_generation_record(production_id: str, generation_log_path: Optional[str] = None) -> Optional[dict]:
    """Read-only: the latest real generation-log record for this
    production_id, or None when none exists. Never fabricates one."""
    records = find_generation_records(production_id, generation_log_path=generation_log_path)
    return records[-1] if records else None


def build_product_bundle(
    production_id: str,
    generation_log_path: Optional[str] = None,
    changelog_path: Optional[str] = None,
    state_path: Optional[str] = None,
    decisions_path: Optional[str] = None,
):
    """THE real caller of dossier_bundle.build_bundle.build_product_dossier_bundle().

    Finds the latest real generation-log record for `production_id`, builds
    the spec from that record's own real fields, and calls the already-real
    bundle builder unchanged (which writes the real product_changelog.jsonl
    version entry and returns the real QA report from the record's real
    inspection). Returns an honest not-found result -- never a fabricated
    bundle -- when no real record exists.

    changelog_path/state_path/decisions_path: test-isolation overrides,
    same convention as every sibling builder. Defaults (None) mean the real
    data/product_changelog.jsonl, real factory_state.json, and the real
    data/decisions.jsonl -- the intended real behavior when called for a
    genuinely produced product.
    """
    from product_families.spec import build_product_specification
    from dossier_bundle.build_bundle import build_product_dossier_bundle

    record = latest_generation_record(production_id, generation_log_path=generation_log_path)
    if record is None:
        return {
            "production_id": production_id,
            "bundle_built": False,
            "reason": f"no real books/_generation_log.jsonl record exists for production_id={production_id}",
        }

    topic = record.get("topic") or record.get("title") or production_id
    spec = build_product_specification(
        niche=topic,
        product_family=record.get("product_family"),
        production_id=production_id,
        title=topic,
        topic=topic,
        price_hint=record.get("price"),
        components=[],
    )

    # A real ACCEPTED decision for this topic gives the bundle its full real
    # metadata (production_factory.dossier.build_production_dossier()); any
    # other status -- or no decision at all -- honestly produces the reduced
    # metadata subset rather than a fabricated ladder/ROI/market analysis.
    decision = None
    try:
        import factory_orchestrator as fo
        found = fo.find_decision(topic, decisions_path=decisions_path)
        if found is not None and found.get("status") == "ACCEPTED":
            decision = found
    except Exception:
        decision = None

    return build_product_dossier_bundle(
        spec,
        record,
        decision=decision,
        changelog_path=changelog_path,
        state_path=state_path,
    )


def _changelog_version(production_id: str, changelog_path: Optional[str] = None) -> Optional[str]:
    """The real version this product has reached in data/product_changelog.jsonl
    (1.N.0 where N is the real prior-entry count), or None when the product has
    never had a real changelog entry -- reuse, not a separate version store."""
    from dossier_bundle.build_bundle import _count_prior_versions
    path = changelog_path or str(_CHANGELOG_PATH)
    count = _count_prior_versions(production_id, path)
    return None if count == 0 else f"1.{count}.0"


def product_lifecycle_view(
    limit: int = 20,
    classify_limit: int = 5,
    generation_log_path: Optional[str] = None,
    changelog_path: Optional[str] = None,
    decisions_path: Optional[str] = None,
    timeline_path: Optional[str] = None,
    outcomes_path: Optional[str] = None,
    state_path: Optional[str] = None,
):
    """Read-only Product Lifecycle view over the real generation log.

    Groups the real books/_generation_log.jsonl records by production_id
    (the identity every production stage already uses), reports the latest
    real record's facts per product, and reuses
    value_engine.classify_lifecycle_stage() -- the one real lifecycle
    classifier this factory has -- for a bounded, disclosed subset of
    distinct niches (`classify_limit`, default 5). Classification is the
    ~2-4s-per-niche real evidence read (orchestrator_timeline + decisions),
    so a passive view must not silently classify all 75 distinct real
    niches. Anything not classified in this call is honestly reported as
    not-classified-in-this-call, never guessed.

    Per-product factory_state recovery facts reuse
    dossier_bundle.build_bundle._recovery_metadata() -- the same real
    pending_retries/checkpoint lookup the bundle builder already uses --
    never a re-derivation. A product with no real pending retry honestly
    reports had_pending_retry=False rather than a fabricated issue.

    Fully read-only: reads books/_generation_log.jsonl,
    data/product_changelog.jsonl, and factory_state.json once each, writes
    nothing.
    """
    from value_engine import classify_lifecycle_stage
    from dossier_bundle.build_bundle import _recovery_metadata

    records = _read_generation_log(generation_log_path)
    real_records = [r for r in records if r.get("production_id") and not _is_test_production_id(r.get("production_id"))]

    by_production_id: Dict[str, dict] = {}
    for r in real_records:
        pid = r["production_id"]
        if pid not in by_production_id or r.get("timestamp", "") >= by_production_id[pid].get("timestamp", ""):
            by_production_id[pid] = r

    sorted_products = sorted(
        by_production_id.items(),
        key=lambda kv: kv[1].get("timestamp", ""),
        reverse=True,
    )[:limit]

    # Classify lifecycle per distinct niche, bounded and cached per niche --
    # a niche is never re-classified for a second product sharing it.
    niche_cache: Dict[str, dict] = {}
    classified_niche_count = 0
    products = []
    for pid, record in sorted_products:
        topic = record.get("topic") or record.get("title") or pid
        lifecycle = None
        if topic not in niche_cache:
            if classified_niche_count < classify_limit:
                niche_cache[topic] = classify_lifecycle_stage(
                    topic,
                    decisions_path=decisions_path,
                    timeline_path=timeline_path,
                    outcomes_path=outcomes_path,
                )
                classified_niche_count += 1
            else:
                niche_cache[topic] = None
        lifecycle = niche_cache[topic]

        products.append({
            "production_id": pid,
            "topic": topic,
            "last_generated_at": record.get("timestamp"),
            "pages": record.get("pages"),
            "price": record.get("price"),
            "inspection_passed": bool((record.get("inspection") or {}).get("passed")),
            "inspection_published": bool((record.get("inspection") or {}).get("published")),
            "published": record.get("published"),
            "changelog_version": _changelog_version(pid, changelog_path=changelog_path),
            "factory_state": _recovery_metadata(pid, state_path=state_path),
            "lifecycle_stage": (
                lifecycle["current_stage"]
                if lifecycle is not None
                else {"value": None, "reason": f"not classified in this call (classify_limit={classify_limit})"}
            ),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_real_production_ids_in_log": len(by_production_id),
        "shown_products": len(products),
        "classified_distinct_niches": classified_niche_count,
        "classify_limit": classify_limit,
        "products": products,
        "note": (
            "Read-only view over real books/_generation_log.jsonl + data/product_changelog.jsonl + "
            "factory_state.json. Lifecycle stage reuses value_engine.classify_lifecycle_stage() -- the real "
            "evidence-based classifier -- for the " + str(classified_niche_count) + " most recent distinct "
            "niches only (classify_limit=" + str(classify_limit) + "); remaining products honestly report "
            "not-classified rather than a guessed stage. factory_state per product reuses "
            "dossier_bundle.build_bundle._recovery_metadata(). Total real production_ids in the log: "
            + str(len(by_production_id)) + "."
        ),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(build_product_bundle(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(product_lifecycle_view(), ensure_ascii=False, indent=2))
