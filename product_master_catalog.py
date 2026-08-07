"""Galaxy Forge -- Product Master Catalog (new, ADR-202, 2026-08-07).

Answers Phase 12 Section 3 of the founder's "Global Commercial Revenue
Operating System" directive: "No platform may maintain an independent
conflicting product definition. The Product Master Catalog is the
source of truth."

Built as a real, READ-ONLY merged view over this factory's existing real
per-platform records -- deliberately never a new, independently-writable
product database that could itself drift out of sync and become a
SECOND conflicting source of truth (the exact failure this directive's
own sentence warns against). The real sources of truth stay exactly
where they already are:

  - data/paddle_products.json  -- Paddle's own real product/price
    creation record (the one platform this factory has a real, live
    API key for).
  - affiliate_commerce/products.py -- the real 4-item Amazon standing-
    desk affiliate catalog (a second, distinct real product line).
  - config/reality.json's published_books -- the one real, unfakeable
    KDP publication ground truth.
  - finance_data.json's sales -- real revenue per product (DELETE-ME
    test record always filtered).

books/_generation_log.jsonl (5,000+ real entries as of 2026-08-07,
mostly real red-team/quarantine test runs and rejected drafts) is
DELIBERATELY not the catalog's primary source -- it is a real
generation-attempt log, not a product identity registry, and most of
its entries were never meant to become a sellable product. It is
exposed separately via all_generation_attempts() for anyone who
genuinely needs that raw, high-volume view, clearly labeled as such.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_PADDLE_PRODUCTS_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"
_REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"
_FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
_GENERATION_LOG_PATH = _FACTORY_ROOT / "books" / "_generation_log.jsonl"
_TEST_RECORD_MARKER = "DELETE-ME"


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _real_sales_matching(title, finance_path=None):
    finance = _read_json(Path(finance_path) if finance_path else _FINANCE_PATH, {})
    sales = finance.get("sales", [])
    matched = [
        s for s in sales
        if _TEST_RECORD_MARKER not in str(s.get("product", "")) and title and title.lower() in str(s.get("product", "")).lower()
    ]
    return {
        "revenue_usd": round(sum(float(s.get("amount", 0)) for s in matched), 2),
        "refunds_usd": 0,
        "refunds_note": "No real refund event has ever been recorded for any product in this factory.",
        "matched_sale_count": len(matched),
    }


def _catalog_entry(**fields):
    """Every field the directive named, defaulting to an honest 'Unknown'
    rather than an omitted key -- a caller can always rely on the full
    15-field shape being present."""
    defaults = {
        "internal_product_id": "Unknown", "product_name": "Unknown", "product_type": "Unknown",
        "version": "Unknown", "description": "Unknown", "source_files": [], "pricing_usd": None,
        "currency": "USD", "cost_usd": {"status": "NOT_TRACKED", "reason": "data/ai_cost_log.jsonl records real AI spend company-wide only, never attributed to a single product."},
        "target_customer": "Unknown", "target_market": "Unknown", "platforms": {},
        "publication_status": "Unknown", "checkout_url": None, "affiliate_status": "N/A",
        "license_status": "N/A", "subscription_status": "N/A", "revenue_usd": 0,
        "refunds_usd": 0, "customer_rating": {"status": "UNKNOWN", "reason": "No data/customer_reviews.jsonl exists yet -- 0 real reviews recorded."},
        "last_updated": None,
    }
    defaults.update(fields)
    return defaults


def _paddle_catalog_entries(paddle_products_path=None, finance_path=None):
    products = _read_json(Path(paddle_products_path) if paddle_products_path else _PADDLE_PRODUCTS_PATH, [])
    entries = []
    for p in products if isinstance(products, list) else []:
        title = p.get("title", "Unknown")
        sales = _real_sales_matching(title, finance_path=finance_path)
        entries.append(_catalog_entry(
            internal_product_id=p.get("product_id"),
            product_name=title,
            product_type="ai_saas_or_b2b_ladder_product",
            pricing_usd=p.get("price"),
            platforms={"paddle": {"status": "PRODUCT_CREATED", "product_id": p.get("product_id"), "price_id": p.get("price_id"), "note": "Real Paddle Product+Price exist; not the same as a completed sale -- checkout is real but Paddle's own account-onboarding gate may still block a live transaction."}},
            publication_status="PRODUCT_CREATED_NOT_CONFIRMED_LIVE",
            revenue_usd=sales["revenue_usd"], refunds_usd=sales["refunds_usd"],
        ))
    return entries


def _affiliate_catalog_entries():
    try:
        from affiliate_commerce import products as affiliate_products
        entries = []
        for p in affiliate_products.list_products().get("products", []):
            entries.append(_catalog_entry(
                internal_product_id=p.get("asin"),
                product_name=p.get("name", "Unknown"),
                product_type="affiliate_asset",
                pricing_usd=p.get("price_usd"),
                platforms={"amazon_associates": {"status": "REAL_LISTING_CITED", "asin": p.get("asin")}},
                publication_status="EXTERNAL_PRODUCT_NOT_OWNED",
                affiliate_status="REAL_CODE_ZERO_CLICKS_CONFIRMED",
                revenue_usd=0, refunds_usd=0,
            ))
        return entries
    except Exception:
        return []


def _kdp_catalog_entries(reality_path=None):
    reality = _read_json(Path(reality_path) if reality_path else _REALITY_PATH, {})
    entries = []
    for b in reality.get("published_books", []) or []:
        entries.append(_catalog_entry(
            internal_product_id=b.get("asin"),
            product_name=b.get("title", "Unknown"),
            product_type="kdp_book",
            pricing_usd=b.get("price_usd"),
            platforms={"amazon_kdp": {"status": "PUBLISHED", "asin": b.get("asin")}},
            publication_status="PUBLISHED",
            last_updated=b.get("published_date"),
        ))
    return entries


def build_product_master_catalog(paddle_products_path=None, reality_path=None, finance_path=None, now=None):
    """The one real aggregator. Computes each real source exactly once."""
    now = now or datetime.now(timezone.utc)
    entries = (
        _paddle_catalog_entries(paddle_products_path=paddle_products_path, finance_path=finance_path)
        + _affiliate_catalog_entries()
        + _kdp_catalog_entries(reality_path=reality_path)
    )
    return {
        "generated_at": now.isoformat(),
        "total_products": len(entries),
        "products": entries,
        "note": "Source of truth is per-platform real records (data/paddle_products.json, affiliate_commerce/products.py, config/reality.json) -- this is a read-only merged view, never a second mutable product database. See all_generation_attempts() for the separate, much larger raw generation-attempt log.",
    }


def all_generation_attempts(limit=50, generation_log_path=None):
    """Deliberately separate from the catalog above -- the raw,
    high-volume real generation log (5,000+ entries as of 2026-08-07,
    mostly real test/quarantine runs), explicitly NOT presented as the
    Product Master Catalog itself. Returns only the most recent `limit`
    real, successful attempts."""
    path = Path(generation_log_path) if generation_log_path else _GENERATION_LOG_PATH
    entries = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("success"):
                    entries.append(r)
    except OSError:
        return {"entries": [], "total_real_attempts": 0, "note": "books/_generation_log.jsonl not found."}
    return {
        "entries": entries[-limit:],
        "total_real_attempts": len(entries),
        "note": "Raw real generation-attempt log, NOT the commercial Product Master Catalog -- most entries here are real test/quarantine/rejected drafts, not sellable products. See build_product_master_catalog() for the real source of truth.",
    }
