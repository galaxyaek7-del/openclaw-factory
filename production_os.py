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
_SALES_LEDGER_PATH = _FACTORY_ROOT / "data" / "sales_ledger.jsonl"

# LEARN feedback (Evidence-Driven Opportunity Factory): how many days a live
# (non-dry-run) publish gets before zero sales flips its directive from
# "still measuring" to "diagnose channel/demand/offer". A disclosed
# mechanical default, overridable per call -- not a founder-set policy, never
# presented as one. A product is never auto-failed: the output is a diagnose
# directive, and the founder rules it encodes (scale on real transactions,
# never clone weak demand without evidence) are read-side annotations, never
# write-side rejections -- same discipline as executive_decision_memory's
# duplicate detection (ADR-145).
MEASUREMENT_WINDOW_DAYS = 30

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
    ledger_path: Optional[str] = None,
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

    # LEARN stage (Evidence-Driven Opportunity Factory): join the real
    # commercial ledger back onto the same shown products, once -- computed
    # here, never recomputed per product. Read-only; failures degrade to an
    # honest error note rather than breaking the lifecycle view.
    learn_by_pid: Dict[str, dict] = {}
    learn_kpis = None
    try:
        learn_products, learn_kpis = _learn_for_products(
            [{"production_id": pid,
              "topic": by_production_id[pid].get("topic")
              or by_production_id[pid].get("title") or pid}
             for pid, _ in sorted_products],
            ledger_path=ledger_path,
        )
        learn_by_pid = {lp["production_id"]: lp for lp in learn_products}
    except Exception as e:
        learn_kpis = {"error": "learn feedback unavailable: %s: %s" % (type(e).__name__, e)}
    for p in products:
        entry = learn_by_pid.get(p["production_id"])
        p["learn"] = {
            "commercial": entry["commercial"],
            "directive": entry["directive"],
            "do_not_clone_without_evidence": entry["do_not_clone_without_evidence"],
        } if entry is not None else {
            "commercial": None,
            "directive": {"signal": "UNKNOWN", "reason": "learn feedback unavailable for this product"},
            "do_not_clone_without_evidence": False,
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_real_production_ids_in_log": len(by_production_id),
        "shown_products": len(products),
        "classified_distinct_niches": classified_niche_count,
        "classify_limit": classify_limit,
        "products": products,
        "learn_kpis": learn_kpis,
        "note": (
            "Read-only view over real books/_generation_log.jsonl + data/product_changelog.jsonl + "
            "factory_state.json. Lifecycle stage reuses value_engine.classify_lifecycle_stage() -- the real "
            "evidence-based classifier -- for the " + str(classified_niche_count) + " most recent distinct "
            "niches only (classify_limit=" + str(classify_limit) + "); remaining products honestly report "
            "not-classified rather than a guessed stage. factory_state per product reuses "
            "dossier_bundle.build_bundle._recovery_metadata(). Each shown product also carries a read-only "
            "'learn' block (real sales-ledger commercial join + SCALE/DIAGNOSE/MEASURE/NOT_IN_MARKET "
            "directive for future qualification); factory-wide learn_kpis holds the 8 real KPIs. "
            "Total real production_ids in the log: "
            + str(len(by_production_id)) + "."
        ),
    }


def _parse_ts(ts):
    """Parse an ISO timestamp defensively; None when unparseable -- a bad
    timestamp must never crash a passive view, it just yields no date."""
    if not ts or not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _learn_for_products(products_meta, ledger_path=None, now=None):
    """Read-only commercial learning over the real sales ledger.

    products_meta: [{production_id, topic}] -- the same identities the
    lifecycle view already groups by. Returns (per_product_learn, kpis).

    Matching (disclosed): a publish_attempt belongs to a product when its
    real ledger fields product_source_id == production_id or product_title
    == topic. A sale is attributed to a product only when its raw payload's
    real product_name/description field exactly matches the product topic
    (case-insensitive); every other sale counts at factory level only, and
    the product honestly reports attribution UNKNOWN. Traffic/clicks/
    checkout are always UNKNOWN -- no platform in this factory exposes
    them (gumroad_monitor.py classifies views/clicks NOT_AVAILABLE);
    reporting a number would be fabrication.

    Writes nothing, touches no network.
    """
    from channels import ledger as sales_ledger

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        # A naive `now` is assumed UTC, disclosed -- real ledger timestamps
        # are written timezone-aware; mixing the two raises TypeError, and a
        # passive view must never crash on timestamp shapes (same discipline
        # as _parse_ts above).
        now = now.replace(tzinfo=timezone.utc)
    events = list(sales_ledger.read_events(ledger_path=ledger_path))
    publishes = [e for e in events if e.get("event_type") == "publish_attempt"]
    sales = [e for e in events if e.get("event_type") == "sale"]

    live = [e for e in publishes if e.get("dry_run") is False]
    live_ok = [e for e in live if e.get("ok") is True]

    # Real per-sale amounts; unrecognized shapes are UNKNOWN, never $0.
    sale_amounts = []
    for s in sales:
        amt = sales_ledger._extract_sale_amount(s.get("raw") or {}, s.get("platform"))
        if amt is not None:
            sale_amounts.append(amt)

    per_product = []
    for meta in products_meta:
        pid = meta.get("production_id")
        topic = meta.get("topic") or ""
        mine = [
            e for e in publishes
            if e.get("product_source_id") == pid or e.get("product_title") == topic
        ]
        my_live = [e for e in mine if e.get("dry_run") is False]
        my_live_ok = [e for e in my_live if e.get("ok") is True]
        first_live_at = None
        for e in my_live:
            ts = _parse_ts(e.get("timestamp"))
            if ts is not None and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts is not None and (first_live_at is None or ts < first_live_at):
                first_live_at = ts

        attributed, unattributed_note = [], None
        lowered_topic = topic.lower()
        for s in sales:
            raw = s.get("raw") or {}
            name = raw.get("product_name") or raw.get("description") or ""
            if isinstance(name, str) and name and name.lower() == lowered_topic:
                attributed.append(s)
        if sales and not attributed:
            unattributed_note = (
                "factory holds %d real sale event(s) but none carries this "
                "product's exact title -- attribution UNKNOWN, never guessed"
                % len(sales)
            )
        my_revenue = 0.0
        for s in attributed:
            amt = sales_ledger._extract_sale_amount(s.get("raw") or {}, s.get("platform"))
            if amt is not None:
                my_revenue += amt

        days_live = (now - first_live_at).days if first_live_at is not None else None
        if attributed:
            directive = {
                "signal": "SCALE_CANDIDATE",
                "reason": (
                    "%d verified transaction(s), $%.2f attributed revenue -- "
                    "strongest commercial signal; study expansion before "
                    "building anything new" % (len(attributed), round(my_revenue, 2))
                ),
            }
        elif my_live_ok and days_live is not None and days_live >= MEASUREMENT_WINDOW_DAYS:
            directive = {
                "signal": "DIAGNOSE_BEFORE_SCALE",
                "reason": (
                    "live %d day(s), 0 attributed sales -- diagnose channel / "
                    "demand / offer first; not an auto-fail" % days_live
                ),
            }
        elif my_live_ok:
            directive = {
                "signal": "IN_MEASUREMENT_WINDOW",
                "reason": (
                    "live %s day(s), inside the %d-day measurement window -- "
                    "keep measuring" % (days_live, MEASUREMENT_WINDOW_DAYS)
                ),
            }
        else:
            directive = {
                "signal": "NOT_IN_MARKET",
                "reason": "no live (non-dry-run) publish recorded -- no learning applicable",
            }

        per_product.append({
            "production_id": pid,
            "commercial": {
                "publish_attempts": len(mine),
                "live_publishes_ok": len(my_live_ok),
                "live_publishes_failed": len(my_live) - len(my_live_ok),
                "first_live_publish_at": first_live_at.isoformat() if first_live_at else None,
                "days_since_live_publish": days_live,
                "attributed_transactions": len(attributed),
                "attributed_revenue_usd": round(my_revenue, 2),
                "attribution_note": unattributed_note,
                "traffic": {"value": None, "status": "UNKNOWN",
                            "reason": "no platform exposes traffic (gumroad views/clicks NOT_AVAILABLE)"},
                "clicks": {"value": None, "status": "UNKNOWN",
                           "reason": "no platform exposes clicks (gumroad clicks NOT_AVAILABLE)"},
                "checkout": {"value": None, "status": "UNKNOWN",
                             "reason": "no checkout-activity source exists on any arm"},
            },
            "directive": directive,
            "do_not_clone_without_evidence": bool(
                my_live_ok and not attributed
                and days_live is not None and days_live >= MEASUREMENT_WINDOW_DAYS
            ),
        })

    total_live = len(live)
    kpis = {
        # 1-2: unfakeable counts straight off the real ledger.
        "verified_revenue_usd": round(sum(sale_amounts), 2),
        "verified_transactions": len(sales),
        # 3: coarse factory ratio, disclosed as such (sales are
        # factory-wide, not per-publish matched).
        "conversion_evidence": {
            "live_ok_publishes": len(live_ok),
            "sales": len(sales),
            "sales_per_live_publish": (round(len(sales) / len(live_ok), 4) if live_ok else None),
            "note": "factory-wide ratio, not per-product conversion -- no per-publish buyer funnel exists",
        },
        # 4-5: real demand/WTP evidence -- only what the ledger holds.
        "demand_evidence": {
            "real_live_publish_attempts": total_live,
            "platforms_touched": sorted({e.get("platform") for e in live if e.get("platform")}),
            "real_sales": len(sales),
            "strength": ("none observed" if total_live == 0 and not sales
                         else "observed" if sales else "publishing only, no purchase yet"),
        },
        "willingness_to_pay_evidence": {
            "real_amounts_usd": sorted(set(sale_amounts)),
            "count": len(sale_amounts),
            "note": "every amount extracted from a real transaction payload; never a target price",
        },
        # 6: honestly UNKNOWN -- transactions ARE the only real value proof;
        # no separate per-product value signal exists anywhere.
        "pain_economic_value": {
            "value": None, "status": "UNKNOWN",
            "reason": "no per-product willingness-beyond-purchase signal exists; verified transactions are the value proof",
        },
        # 7: real live-publish success rate off the ledger.
        "distribution_efficiency": {
            "live_attempts": total_live,
            "live_ok": len(live_ok),
            "ok_rate": (round(len(live_ok) / total_live, 4) if total_live else None),
        },
        # 8: informational, never a fabricated numeric level.
        "automation_level": {
            "automated_inputs": ["poll_sales tick detection", "daily lifecycle snapshot"],
            "manual_inputs": ["traffic/clicks/checkout (no platform source)",
                              "niche qualification decision"],
            "note": "qualitative routing map, not a score",
        },
    }
    return per_product, kpis


def learn_feedback(limit=20, generation_log_path=None, ledger_path=None, now=None):
    """Read-only LEARN stage for the Product Lifecycle Pipeline
    (Evidence-Driven Opportunity Factory).

    Commercial results (publish attempts, transactions, revenue -- the only
    real signals this factory's ledgers hold) are joined back onto the same
    production identities DISCOVER/QUALIFY already use, producing per-product
    directives (SCALE_CANDIDATE / DIAGNOSE_BEFORE_SCALE /
    IN_MEASUREMENT_WINDOW / NOT_IN_MARKET) plus the 8 factory KPIs. Traffic,
    clicks, and checkout are honestly UNKNOWN -- no arm exposes them.
    Directives are read-side annotations for future qualification; nothing
    here publishes, pays, rejects, or writes. Product count is never
    treated as a KPI.
    """
    records = _read_generation_log(generation_log_path)
    real_records = [r for r in records if r.get("production_id") and not _is_test_production_id(r.get("production_id"))]
    by_production_id: Dict[str, dict] = {}
    for r in real_records:
        pid = r["production_id"]
        if pid not in by_production_id or r.get("timestamp", "") >= by_production_id[pid].get("timestamp", ""):
            by_production_id[pid] = r
    metas = [
        {"production_id": pid,
         "topic": rec.get("topic") or rec.get("title") or pid}
        for pid, rec in sorted(by_production_id.items(),
                               key=lambda kv: kv[1].get("timestamp", ""),
                               reverse=True)[:limit]
    ]
    per_product, kpis = _learn_for_products(metas, ledger_path=ledger_path, now=now)
    return {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "products": per_product,
        "kpis": kpis,
        "note": (
            "Read-only join of real data/sales_ledger.jsonl publish_attempt/sale "
            "events back onto real production identities. Sale attribution "
            "requires an exact raw product_name/description match -- anything "
            "else counts factory-wide only. Traffic/clicks/checkout UNKNOWN "
            "(no real source). Directives annotate future qualification; "
            "nothing auto-fails, auto-scales, or writes."
        ),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(build_product_bundle(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(product_lifecycle_view(), ensure_ascii=False, indent=2))
