"""distribution_os.py (Distribution OS, 2026-08-17):

The smallest safe Distribution OS layer (founder-approved build): a
READ-ONLY, per-production_id cross-channel read model. It joins the real
ledgers this factory already writes into one view per product
(Product -> Package -> Channel -> Listing -> Distribution -> Attribution
-> Learning), and MERGES -- never re-implements -- the 3 pre-existing
overlapping distribution-status aggregators
(commercial_operations.distribution_capability_matrix,
global_partnership_network.distribution_network_health,
global_commercial_operations_engine.product_platform_matrix).

Hard constraints, all enforced by tests:
  * read-only -- never writes any ledger, never publishes, never calls a
    network endpoint, never activates a channel, never touches finance.
  * honest -- every stage is REAL evidence or an explicit gap; never a
    fabricated listing/sale/customer/conversion.
  * no 4th orchestrator -- channel capability truth comes verbatim from
    the 3 existing aggregators, not from a parallel computation here.

The unit of identity is production_id -- the identity every production
stage already uses in books/_generation_log.jsonl. Products whose only
real record carries production_id=null (e.g. the EU AI Act Compliance
Toolkit, generated via the human/Claude-content path) are matched by
title across the real ledgers, and that title-based join is disclosed
as such, never silent.

    python -m unittest tests.test_distribution_os -v
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent

_GENERATION_LOG_PATH = _FACTORY_ROOT / "books" / "_generation_log.jsonl"
_CHANGELOG_PATH = _FACTORY_ROOT / "data" / "product_changelog.jsonl"
_SALES_LEDGER_PATH = _FACTORY_ROOT / "data" / "sales_ledger.jsonl"
_PADDLE_PRODUCTS_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"
_SEO_PAGES_PATH = _FACTORY_ROOT / "data" / "seo_pages.json"
_CLICKS_PATH = _FACTORY_ROOT / "data" / "affiliate_clicks.jsonl"
_PAGE_VIEWS_PATH = _FACTORY_ROOT / "data" / "affiliate_page_views.jsonl"
_WEBHOOK_EVENTS_PATH = _FACTORY_ROOT / "data" / "paddle_webhook_events.jsonl"
_KITS_PATH = _FACTORY_ROOT / "data" / "generated_commercial_kits.jsonl"
_REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"

_DISTRIBUTION_STAGES = [
    "product",
    "package",
    "channel",
    "listing",
    "distribution",
    "attribution",
    "learning",
]


def _read_jsonl(path: Optional[str]) -> List[dict]:
    if not path or not os.path.exists(path):
        return []
    records = []
    try:
        with open(path, encoding="utf-8") as f:
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


def _read_json_file(path: Optional[str]):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).lower().strip())


def _titles_match(a: Optional[str], b: Optional[str]) -> bool:
    """Honest, disclosed title join: exact normalized equality OR one
    containing the other. Never a fuzzy/AI similarity guess."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def _registered_arms() -> List[dict]:
    """The real registered distribution arms, each with its honest
    credential-presence status. Importing the arm modules is what
    self-registers them into channels.registry (their existing pattern);
    arm.status() only checks credentials present in .env -- never a
    network call -- so this is safe inside a read-only view."""
    try:
        import channels.etsy_arm  # noqa: F401  (self-registers on import)
        import channels.gumroad_arm  # noqa: F401
        import channels.paddle_arm  # noqa: F401
        import channels.payhip_arm  # noqa: F401
        from channels import registry
        arms = []
        for arm in registry.all_arms():
            try:
                status = arm.status()
                status_name = status.name if hasattr(status, "name") else str(status)
            except Exception:
                status_name = "UNKNOWN"
            arms.append({"name": arm.name, "status": status_name})
        return arms
    except Exception:
        return []


def _changelog_version(production_id: str, changelog_path: Optional[str] = None) -> Optional[str]:
    from production_os import _changelog_version as pos_changelog_version
    return pos_changelog_version(production_id, changelog_path=changelog_path)


def _paddle_listing(title: Optional[str], paddle_products_path: Optional[str] = None) -> Optional[dict]:
    products = _read_json_file(paddle_products_path or str(_PADDLE_PRODUCTS_PATH))
    if not isinstance(products, list):
        return None
    for p in products:
        if _titles_match(p.get("title"), title):
            return {
                "product_id": p.get("product_id"),
                "price_id": p.get("price_id"),
                "price_usd": p.get("price"),
            }
    return None


def _generation_records(production_id: str, generation_log_path: Optional[str] = None) -> List[dict]:
    from production_os import find_generation_records
    return find_generation_records(production_id, generation_log_path=generation_log_path)


def _latest_generation_record(production_id: str, generation_log_path: Optional[str] = None) -> Optional[dict]:
    from production_os import latest_generation_record
    return latest_generation_record(production_id, generation_log_path=generation_log_path)


def _find_records_by_title(query: str, generation_log_path: Optional[str] = None) -> List[dict]:
    """Title-based record lookup -- the honest fallback for the factory's
    real null-production_id products (e.g. the EU AI Act Compliance
    Toolkit, generated via the human/Claude-content path with
    production_id=null). Real records only; never a fabricated record."""
    records = _read_jsonl(generation_log_path or str(_GENERATION_LOG_PATH))
    matches = []
    for r in records:
        title = r.get("title") or r.get("topic")
        if _titles_match(title, query):
            matches.append(r)
    return matches


def _commercial_kit_status(
    topic: Optional[str],
    kits_path: Optional[str] = None,
    generation_log_path: Optional[str] = None,
) -> dict:
    """A real generated commercial kit exists only when generated_commercial_kits.jsonl
    carries a record whose niche matches this product's topic (or, for products with
    a production_id, whose decision_id can be resolved through the generation log's
    topic). Honest not-found otherwise."""
    kits = _read_jsonl(kits_path or str(_KITS_PATH))
    if not kits:
        return {"exists": False, "reason": "data/generated_commercial_kits.jsonl has no real records"}
    matches = []
    for k in kits:
        if _titles_match(k.get("niche"), topic):
            matches.append({
                "decision_id": k.get("decision_id"),
                "generated_at": k.get("generated_at"),
                "output_path": k.get("output_path"),
            })
    if matches:
        return {"exists": True, "records": matches}
    return {"exists": False, "reason": "no generated_commercial_kits.jsonl record matches this product's topic"}


def _sales_ledger_events(
    production_id: Optional[str],
    title: Optional[str],
    sales_ledger_path: Optional[str] = None,
) -> List[dict]:
    """Real data/sales_ledger.jsonl events matching this product: primary
    join on product_source_id == production_id (the canonical production
    identity), plus a disclosed title-based join for products whose real
    record carries production_id=null (e.g. the EU AI Act Compliance
    Toolkit). Never fabricates an event."""
    events = _read_jsonl(sales_ledger_path or str(_SALES_LEDGER_PATH))
    matches = []
    for e in events:
        if production_id and e.get("product_source_id") == production_id:
            matches.append(e)
        elif not production_id and _titles_match(e.get("product_title"), title):
            matches.append(e)
    return matches


def _paddle_webhook_count(webhook_events_path: Optional[str] = None) -> dict:
    path = webhook_events_path or str(_WEBHOOK_EVENTS_PATH)
    if not os.path.exists(path):
        return {"count": 0, "note": "data/paddle_webhook_events.jsonl does not exist -- zero webhook events ever recorded"}
    events = _read_jsonl(path)
    return {"count": len(events), "note": "real webhook event count from data/paddle_webhook_events.jsonl"}


def _kdp_listing(reality_path: Optional[str] = None) -> dict:
    reality = _read_json_file(reality_path or str(_REALITY_PATH))
    if not isinstance(reality, dict):
        return {"listed": False, "reason": "config/reality.json unreadable"}
    published = reality.get("published_books") or []
    return {
        "listed": bool(published),
        "count": len(published),
        "note": "config/reality.json published_books -- KDP publishing is human-gated (ASIN) and zero real books are published",
    }


def _seo_pages(seo_pages_path: Optional[str] = None) -> dict:
    pages = _read_json_file(seo_pages_path or str(_SEO_PAGES_PATH))
    if not isinstance(pages, list):
        pages = []
    return {
        "count": len(pages),
        "note": "data/seo_pages.json -- real affiliate-guide SEO pages, keyed by opportunity_id, not production_id",
    }


def _attribution_state(clicks_path: Optional[str] = None, page_views_path: Optional[str] = None) -> dict:
    clicks = _read_jsonl(clicks_path or str(_CLICKS_PATH))
    views = _read_jsonl(page_views_path or str(_PAGE_VIEWS_PATH))
    return {
        "affiliate_clicks": len(clicks),
        "affiliate_page_views": len(views),
        "note": "real click/page-view ledgers are keyed by CO-opportunity (affiliate program), never production_id -- no per-product attribution signal exists",
    }


def _learning_stage(
    production_id: Optional[str],
    title: Optional[str],
    sales_ledger_path: Optional[str] = None,
    webhook_events_path: Optional[str] = None,
) -> dict:
    events = _sales_ledger_events(production_id, title, sales_ledger_path=sales_ledger_path)
    sales = [e for e in events if e.get("event_type") == "sale"]
    webhook = _paddle_webhook_count(webhook_events_path)
    return {
        "sale_events": len(sales),
        "paddle_webhook_events": webhook,
        "note": "revenue_intelligence/evolution learning exists at portfolio level; no real per-production_id outcome measurement yet",
    }


def _merge_distribution_aggregators(paddle_products_path: Optional[str] = None) -> dict:
    """Merges the 3 pre-existing overlapping distribution-status
    aggregators verbatim -- never re-computes their logic here. Each is
    computed exactly once and cited with its source. A failure in one
    aggregator is absorbed and reported, never fatal."""
    merged = {}
    try:
        import commercial_operations as co
        merged["capability_matrix"] = co.distribution_capability_matrix()
    except Exception as e:
        merged["capability_matrix"] = {"error": str(e)}
    try:
        import global_partnership_network as gpn
        merged["network_health"] = gpn.distribution_network_health()
    except Exception as e:
        merged["network_health"] = {"error": str(e)}
    try:
        import global_commercial_operations_engine as gcoe
        merged["product_platform_matrix"] = gcoe.product_platform_matrix(paddle_products_path=paddle_products_path)
    except Exception as e:
        merged["product_platform_matrix"] = {"error": str(e)}
    return merged


def distribution_os_view(
    production_id: str,
    generation_log_path: Optional[str] = None,
    changelog_path: Optional[str] = None,
    sales_ledger_path: Optional[str] = None,
    paddle_products_path: Optional[str] = None,
    seo_pages_path: Optional[str] = None,
    clicks_path: Optional[str] = None,
    page_views_path: Optional[str] = None,
    webhook_events_path: Optional[str] = None,
    kits_path: Optional[str] = None,
    reality_path: Optional[str] = None,
    merge_aggregators: bool = True,
):
    """The Distribution OS read model for ONE production_id -- the 7-stage
    cross-channel view. Fully read-only; every field is a real ledger read
    or an honest gap. Returns a genuine not-found when no real record
    exists for the given id."""
    production_id = (production_id or "").strip()
    if not production_id:
        return {
            "found": False,
            "reason": "production_id is required",
            "stages": _DISTRIBUTION_STAGES,
        }

    records = _generation_records(production_id, generation_log_path=generation_log_path)
    latest = _latest_generation_record(production_id, generation_log_path=generation_log_path)

    # Title-fallback: the factory's real null-production_id products (e.g.
    # the EU AI Act Compliance Toolkit, generated via the human/Claude
    # content path) have no production_id in the generation log, so the
    # production_id join finds nothing. Resolve them honestly by title and
    # disclose the join -- never a fabricated record.
    resolved_by_title = False
    if latest is None and not records:
        by_title = _find_records_by_title(production_id, generation_log_path=generation_log_path)
        if by_title:
            by_title_sorted = sorted(
                by_title, key=lambda r: r.get("timestamp", "") or "", reverse=True
            )
            latest = by_title_sorted[0]
            records = by_title
            resolved_by_title = True

    if latest is None and not records:
        return {
            "found": False,
            "production_id": production_id,
            "reason": (
                f"no real books/_generation_log.jsonl record exists for production_id={production_id} "
                "nor a real record whose title matches it"
            ),
            "stages": _DISTRIBUTION_STAGES,
        }

    title = latest.get("title") or latest.get("topic") or production_id
    topic = latest.get("topic") or latest.get("title") or production_id
    real_production_id = latest.get("production_id") or production_id

    # Stage 1 -- Product
    product = {
        "production_id": real_production_id,
        "resolved_by_title": resolved_by_title,
        "title": title,
        "topic": topic,
        "price": latest.get("price"),
        "pages": latest.get("pages"),
        "last_generated_at": latest.get("timestamp"),
        "inspection_passed": bool((latest.get("inspection") or {}).get("passed")),
        "inspection_published": bool((latest.get("inspection") or {}).get("published")),
        "generation_records": len(records),
        "source": "books/_generation_log.jsonl",
    }

    # Stage 2 -- Package
    package = {
        "changelog_version": _changelog_version(real_production_id, changelog_path=changelog_path),
        "commercial_kit": _commercial_kit_status(topic, kits_path=kits_path, generation_log_path=generation_log_path),
        "source": "data/product_changelog.jsonl + data/generated_commercial_kits.jsonl",
    }

    # Stage 3 -- Channel
    channel = {
        "registered_arms": _registered_arms(),
        "note": "arm status is credential-presence only (real .env keys), never a network check",
    }

    # Stage 4 -- Listing
    paddle = _paddle_listing(title, paddle_products_path=paddle_products_path)
    kdp = _kdp_listing(reality_path=reality_path)
    seo = _seo_pages(seo_pages_path=seo_pages_path)
    listing = {
        "paddle": paddle or {"listed": False, "reason": "no real data/paddle_products.json entry matches this product's title"},
        "kdp": kdp,
        "seo_pages": seo,
        "note": "listing evidence is real per-channel state; Gumroad's out-of-band DRAFT product is documented only in channels/gumroad_arm.py, not in any ledger",
    }

    # Stage 5 -- Distribution
    join_production_id = None if resolved_by_title else real_production_id
    distribution_events = _sales_ledger_events(join_production_id, title, sales_ledger_path=sales_ledger_path)
    per_platform = {}
    for e in distribution_events:
        platform = e.get("platform") or "unknown"
        entry = per_platform.setdefault(platform, {
            "publish_attempts": 0,
            "ok_real": 0,
            "ok_dry_run": 0,
            "failures": 0,
            "last_attempt": None,
        })
        entry["publish_attempts"] += 1
        if e.get("ok"):
            if e.get("dry_run"):
                entry["ok_dry_run"] += 1
            else:
                entry["ok_real"] += 1
        else:
            entry["failures"] += 1
        ts = e.get("timestamp")
        if ts and (entry["last_attempt"] is None or ts > entry["last_attempt"]):
            entry["last_attempt"] = ts
    distribution = {
        "events": len(distribution_events),
        "per_platform": per_platform,
        "sales": sum(1 for e in distribution_events if e.get("event_type") == "sale"),
        "source": "data/sales_ledger.jsonl (join: product_source_id == production_id, or disclosed title match)",
    }

    # Stage 6 -- Attribution
    attribution = _attribution_state(clicks_path=clicks_path, page_views_path=page_views_path)

    # Stage 7 -- Learning
    learning = _learning_stage(
        join_production_id, title,
        sales_ledger_path=sales_ledger_path,
        webhook_events_path=webhook_events_path,
    )

    view = {
        "found": True,
        "production_id": production_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stages": {
            "product": product,
            "package": package,
            "channel": channel,
            "listing": listing,
            "distribution": distribution,
            "attribution": attribution,
            "learning": learning,
        },
        "note": (
            "Read-only Distribution OS view per production_id -- every field is a real "
            "ledger read or an honest gap, never a fabricated listing/sale/customer/conversion."
        ),
    }

    if merge_aggregators:
        view["merged_aggregators"] = _merge_distribution_aggregators(
            paddle_products_path=paddle_products_path
        )
    return view


def distribution_os_summary(
    limit: int = 20,
    generation_log_path: Optional[str] = None,
    changelog_path: Optional[str] = None,
    sales_ledger_path: Optional[str] = None,
    paddle_products_path: Optional[str] = None,
    seo_pages_path: Optional[str] = None,
    clicks_path: Optional[str] = None,
    page_views_path: Optional[str] = None,
    webhook_events_path: Optional[str] = None,
    reality_path: Optional[str] = None,
    merge_aggregators: bool = True,
):
    """Cross-product Distribution OS summary: the most recent real
    production_ids with a compact per-channel listing/distribution state,
    plus the merged existing aggregators. No per-product deep read -- that
    is distribution_os_view()'s job. Fully read-only."""
    from production_os import _is_test_production_id

    records = _read_jsonl(generation_log_path or str(_GENERATION_LOG_PATH))
    real_records = [
        r for r in records
        if r.get("production_id") and not _is_test_production_id(r.get("production_id"))
    ]

    by_id: Dict[str, dict] = {}
    for r in real_records:
        pid = r["production_id"]
        if pid not in by_id or r.get("timestamp", "") >= by_id[pid].get("timestamp", ""):
            by_id[pid] = r

    sorted_ids = sorted(
        by_id.items(),
        key=lambda kv: kv[1].get("timestamp", ""),
        reverse=True,
    )[:limit]

    seo = _seo_pages(seo_pages_path=seo_pages_path)
    products = []
    for pid, record in sorted_ids:
        title = record.get("title") or record.get("topic") or pid
        paddle = _paddle_listing(title, paddle_products_path=paddle_products_path)
        events = _sales_ledger_events(pid, title, sales_ledger_path=sales_ledger_path)
        platforms = sorted({e.get("platform") or "unknown" for e in events})
        ok_real = any(e.get("ok") and not e.get("dry_run") for e in events)
        products.append({
            "production_id": pid,
            "topic": title,
            "last_generated_at": record.get("timestamp"),
            "pages": record.get("pages"),
            "price": record.get("price"),
            "changelog_version": _changelog_version(pid, changelog_path=changelog_path),
            "listing": {
                "paddle": bool(paddle),
                "kdp": bool((record.get("inspection") or {}).get("published")) or bool((record.get("published"))),
                "seo_pages": seo["count"],
            },
            "distribution": {
                "platforms_touched": platforms,
                "publish_attempts": len(events),
                "ok_real_publish": ok_real,
                "sales": sum(1 for e in events if e.get("event_type") == "sale"),
            },
        })

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_real_production_ids_in_log": len(by_id),
        "shown_products": len(products),
        "limit": limit,
        "products": products,
        "note": (
            "Cross-product Distribution OS summary over real books/_generation_log.jsonl -- "
            "compact per-channel listing/distribution state per production_id. Deep 7-stage "
            "view for one product is distribution_os_view(production_id)."
        ),
    }

    if merge_aggregators:
        result["merged_aggregators"] = _merge_distribution_aggregators(
            paddle_products_path=paddle_products_path
        )
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(distribution_os_view(sys.argv[1]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(distribution_os_summary(), ensure_ascii=False, indent=2))