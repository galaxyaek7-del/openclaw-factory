"""Pricing Review Trigger (new, ADR-182, 2026-08-07) -- the founder's
explicit instruction after approving Premium-tier ($155) pricing for the
EU AI Act Compliance Toolkit: "After the first verified customer and
testimonials, schedule an automatic pricing review to determine whether
the product should move toward the Elite tier."

Real, mechanical, evidence-only -- never recommends a tier change on
elapsed time or a guess. Reads customer_pipeline.py's own real, already-
live ledgers (data/customer_pipeline_state.json, data/customer_reviews.jsonl)
directly, the same file-reading convention several other modules already
use for these exact files, rather than reaching into
customer_pipeline.py's private _load_state()/_load_reviews() helpers.

Elite tier ($310) is already real and verified -- economics.evaluate(310,
'gumroad_elite', config, page_count=31) returns market_realistic=True,
approved=True (see commit 571fc62's own investigation). This module's
only job is deciding WHEN it's evidence-backed to act on that, not
re-deriving whether $310 is a valid number."""

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "customer_pipeline_state.json"
DEFAULT_REVIEWS_PATH = _FACTORY_ROOT / "data" / "customer_reviews.jsonl"

_PAID_OR_LATER_STAGES = {"PAID", "PRODUCTION", "QUALITY_INSPECTION", "PACKAGING", "DELIVERED", "FOLLOWED_UP"}


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _load_reviews(path):
    reviews = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    reviews.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return reviews


def check_pricing_review_readiness(
    product_id, state_path=None, reviews_path=None,
    elite_price=None, elite_platform="gumroad_elite", page_count=None,
):
    """Real, mechanical check: does this product have >=1 real paid
    customer (a request whose catalog_match.product_id matches and whose
    stage reached PAID or later) with >=1 real review tied to one of
    those same real requests? Both real and disclosed -- never a guess,
    never triggered by elapsed time alone."""
    state = _load_json(state_path or DEFAULT_STATE_PATH, {}) or {}
    reviews = _load_reviews(reviews_path or DEFAULT_REVIEWS_PATH)
    reviewed_request_ids = {r["request_id"] for r in reviews if "request_id" in r}

    matched_requests = [
        request_id for request_id, record in state.items()
        if (record.get("catalog_match") or {}).get("product_id") == product_id
        and record.get("stage") in _PAID_OR_LATER_STAGES
    ]
    reviewed_matches = [rid for rid in matched_requests if rid in reviewed_request_ids]

    ready = len(matched_requests) >= 1 and len(reviewed_matches) >= 1
    result = {
        "product_id": product_id,
        "real_paid_customers": len(matched_requests),
        "real_reviews_on_paid_requests": len(reviewed_matches),
        "ready_for_elite_tier_review": ready,
        "evidence": f"{len(matched_requests)} real paid customer(s) found, {len(reviewed_matches)} of them left a real review",
    }
    if ready and elite_price is not None:
        import economics
        config = economics.load_config()
        result["elite_tier_evaluation"] = economics.evaluate(elite_price, elite_platform, config, page_count=page_count)
    return result


# The one real product this was built for -- kept as a named constant
# rather than hardcoded inside factory_loop.js's own dispatch, so a
# second product can reuse this module by adding a second entry here
# rather than duplicating the check.
EU_AI_ACT_TOOLKIT_REVIEW = {
    "product_id": "pro_01kzdzzh4kv6bkpzfhd5r1jnkn",
    "elite_price": 310.0,
    "elite_platform": "gumroad_elite",
    "page_count": 31,
}


def check_eu_ai_act_toolkit_pricing_review(state_path=None, reviews_path=None):
    return check_pricing_review_readiness(
        EU_AI_ACT_TOOLKIT_REVIEW["product_id"],
        state_path=state_path, reviews_path=reviews_path,
        elite_price=EU_AI_ACT_TOOLKIT_REVIEW["elite_price"],
        elite_platform=EU_AI_ACT_TOOLKIT_REVIEW["elite_platform"],
        page_count=EU_AI_ACT_TOOLKIT_REVIEW["page_count"],
    )
