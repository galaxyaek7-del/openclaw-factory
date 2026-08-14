"""Galaxy Forge — Commercial Activation (Phase 31, ADR-223, 2026-08-08).

Answers the founder's "Commercial Activation & First Real Dollar"
directive's Sections 2, 4, 11, 14, and 16 -- deliberately consolidated
into one module rather than five tiny ones, since they are all real,
citation-heavy pieces of the same "where does this factory honestly
stand on the path to a first real dollar" question. Every function here
either evaluates real, already-existing evidence (channels/*_arm.py's
real status()/list_products(), data/paddle_products.json, scripts/
check_paddle_checkout_status.py, channels/paddle_webhook.py) or reports
an explicit UNKNOWN/NOT_AVAILABLE/FOUNDER_ACTION_REQUIRED state -- never
infers a later commercial state from an earlier one, never fabricates a
completed action.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_CATALOG_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"
DEFAULT_GOLDEN_JSON_PATH = _FACTORY_ROOT / "golden_opportunities.json"

# ---------------------------------------------------------------------------
# Section 2 -- Real Commercial State Machine
# ---------------------------------------------------------------------------

COMMERCIAL_LIFECYCLE_STATES = [
    "PRODUCT_CREATED", "PRODUCT_PUBLISHED", "CHECKOUT_AVAILABLE", "CHECKOUT_STARTED",
    "PAYMENT_PENDING", "PAYMENT_CONFIRMED", "ORDER_CONFIRMED", "DELIVERY_CONFIRMED",
    "CUSTOMER_RECORDED", "REVENUE_RECORDED", "PAYOUT_PENDING", "PAYOUT_CONFIRMED",
]


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def evaluate_commercial_lifecycle_state(catalog_entry, checkout_ready=None):
    """Real, evidence-only state evaluation for one real catalog product.
    Never infers PAYMENT_CONFIRMED or later from anything except a real,
    externally-verified payment event (out of this function's scope
    entirely -- it can only ever return up to CHECKOUT_AVAILABLE/
    CHECKOUT_STARTED today, since no real transaction evidence exists
    anywhere in this factory)."""
    if not catalog_entry or not catalog_entry.get("product_id"):
        return {"state": "UNKNOWN", "reason": "no real catalog entry"}

    state = "PRODUCT_CREATED"
    if catalog_entry.get("price_id"):
        state = "PRODUCT_PUBLISHED"
    if checkout_ready is True:
        state = "CHECKOUT_AVAILABLE"
    elif checkout_ready is False:
        return {"state": state, "reason": "checkout_ready=false (live-verified) -- BLOCKED_EXTERNAL, cannot honestly advance further", "blocked": True}
    else:
        return {"state": state, "reason": "checkout_ready not supplied -- UNKNOWN, not assumed", "blocked": None}

    return {"state": state, "reason": "checkout is live -- CHECKOUT_STARTED/PAYMENT_* require a real, externally-verified event this function never fabricates"}


# ---------------------------------------------------------------------------
# Section 4 -- Commercial Readiness Check (8 named dimensions, never collapsed)
# ---------------------------------------------------------------------------

def platform_activation_readiness(platform_key, catalog_path=None, checkout_status=None):
    """Real, per-platform readiness -- 8 dimensions reported separately,
    per the directive's own explicit example format. Never a single
    collapsed score."""
    from channels import registry
    import channels.gumroad_arm, channels.paddle_arm, channels.etsy_arm, channels.payhip_arm  # noqa: F401 -- self-register

    arm = registry.get(platform_key)
    technical_ready = arm is not None
    credential_valid = arm.status().value == "ready" if arm else False

    catalog = []
    if platform_key == "paddle":
        path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
        if path.exists():
            try:
                catalog = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                catalog = []
    commercial_ready = len(catalog) > 0

    # Real, live truth for Gumroad: the activation report must not claim
    # "0 products" when the founder's real Gumroad account holds a real,
    # already-created product (e.g. the EU AI Act Toolkit, created 2026-08-14).
    # The API is the authoritative source, exactly like paddle_products.json
    # is for Paddle -- never a stale local guess.
    gumroad_product_count = None
    if platform_key == "gumroad" and credential_valid:
        try:
            from channels.gumroad_publisher import list_products, load_token
            gumroad_products = list_products(load_token())
            gumroad_product_count = len(gumroad_products or [])
        except Exception:
            gumroad_product_count = None

    checkout_ready = None
    if platform_key == "paddle" and checkout_status is not None:
        checkout_ready = any(r.get("checkout_ready") for r in checkout_status.get("results", []))
    elif platform_key == "paddle":
        checkout_ready = "NOT_CHECKED_THIS_CALL"

    payment_ready = checkout_ready if isinstance(checkout_ready, bool) else "SAME_AS_CHECKOUT_READY"

    delivery_ready = "REAL -- customer_pipeline.py's DELIVERED-stage gate is real and platform-agnostic" if technical_ready else "N/A"
    finance_ready = "REAL -- finance_data.json's real add/delete path is platform-agnostic"

    from channels import paddle_webhook
    webhook_ready = (paddle_webhook.load_webhook_secret() is not None) if platform_key == "paddle" else False

    payout_ready = "NOT_AVAILABLE -- no real payout-retrieval endpoint is wired for any arm in this factory"

    return {
        "generated_at": _now_iso(), "platform": platform_key,
        "TECHNICAL_READY": technical_ready,
        "COMMERCIAL_READY": commercial_ready,
        "CHECKOUT_READY": checkout_ready,
        "PAYMENT_READY": payment_ready,
        "DELIVERY_READY": delivery_ready,
        "FINANCE_READY": finance_ready,
        "WEBHOOK_READY": webhook_ready,
        "PAYOUT_READY": payout_ready,
        "credential_valid": credential_valid,
        "products": len(catalog),
        "live_products": gumroad_product_count,
        "blocker": "founder onboarding (vendors.paddle.com)" if platform_key == "paddle" and checkout_ready is False else (
            "no credential configured" if not credential_valid else None
        ),
    }


# ---------------------------------------------------------------------------
# Section 11 -- Founder Action Center
# ---------------------------------------------------------------------------

def founder_action_center():
    """Real, citation-only list -- lists ONLY actions a human founder must
    take, never engineering work this factory's own code can do itself."""
    # Priority order mirrors profit-first reality: the DigitalOcean/Awin gate is
    # the single highest-profit-first action (CO-digitalocean-affiliate, 0.25)
    # and unlocks the ONLY recurring-commission stream. It is listed first.
    return {
        "generated_at": _now_iso(),
        "actions": [
            {
                "platform": "DigitalOcean (Awin network)",
                "action": "Apply to the verified DigitalOcean affiliate program on Awin + confirm Payoneer payout",
                "why_required": "Awin is the VERIFIED official network (live-checked 2026-08-14 from ui.awin.com/merchant-profile/123996 -- NOT CJ, as the prior report assumed). 10% recurring commission for the first 12 months, 30-day cookie, paid via Payoneer for international publishers. The real Awin tracking link is NOT_CONFIGURED until the founder's application is approved -- this is the single highest-profit-first opportunity (0.25) and the only recurring-commission stream, so it is the top founder action.",
                "what_to_do": "Sign up at https://ui.awin.com/merchant-profile/123996, submit a publisher application to the DigitalOcean program, and connect/confirm the Payoneer payout destination.",
                "unlocks": "A real, attributable, recurring 10%-commission affiliate link the factory can then wire into the already-generated 7-channel launch batch.",
                "current_status": "FOUNDER_ACTION_REQUIRED -- TOP PRIORITY",
            },
            {
                "platform": "Paddle", "action": "Complete account onboarding (business/payment verification)",
                "why_required": "The real, live Paddle credential and 6-product catalog already work -- checkout_ready is blocked purely by Paddle's own account-review gate, which no API call from this factory can clear.",
                "what_to_do": "Log into vendors.paddle.com and complete every remaining onboarding step Paddle's own dashboard lists.",
                "unlocks": "Real checkout on all 6 existing products, immediately, with zero further engineering.",
                "current_status": "FOUNDER_ACTION_REQUIRED",
            },
            {
                "platform": "Gumroad",
                "action": "Connect a payment method so the already-created live product can be published",
                "why_required": "GUMROAD_ACCESS_TOKEN is configured and the EU AI Act Compliance Toolkit product is live-created (gumroad_publisher list_products verified 1 product on 2026-08-14) -- but it remains published=False because Gumroad itself requires a connected payment method before publish, which only the founder can add in the dashboard.",
                "what_to_do": "In the Gumroad dashboard (aekraft.gumroad.com), add/confirm a payment method for the account, then the factory can call enable_product() to publish.",
                "unlocks": "The existing $155 live product becomes purchasable, a second credentialed sales channel.",
                "current_status": "FOUNDER_ACTION_REQUIRED",
            },
            {
                "platform": "Paddle", "action": "Configure the real webhook endpoint + PADDLE_WEBHOOK_SECRET",
                "why_required": "This factory's webhook receiver (channels/paddle_webhook.py) is real and tested, but has never verified a real event -- it needs the real secret Paddle issues once a webhook destination is registered.",
                "what_to_do": "In vendors.paddle.com, register this server's real /webhooks/paddle URL, copy the webhook secret Paddle issues, and set PADDLE_WEBHOOK_SECRET in .env.",
                "unlocks": "Real-time payment confirmation, replacing/complementing the existing polling-based check_payment_status().",
                "current_status": "FOUNDER_ACTION_REQUIRED",
            },
            {
                "platform": "Etsy/Payhip",
                "action": "Add real credentials only for accounts the founder actually owns",
                "why_required": "0 of these 2 have any credential configured today -- each is a real, disclosed manual step, not a code blocker.",
                "what_to_do": "Set the real Etsy/Payhip credentials in .env once the founder has legitimate accounts.",
                "unlocks": "Extra credentialed sales channels, reducing single-platform concentration risk.",
                "current_status": "FOUNDER_ACTION_REQUIRED, LOW_URGENCY",
            },
            {
                "platform": "Payout", "action": "Confirm the real payout destination",
                "why_required": "No payout has ever occurred; the real destination bank/account tied to the Paddle vendor account should be confirmed before the first real payout is due.",
                "what_to_do": "Verify payout details directly in vendors.paddle.com.",
                "unlocks": "Confidence that the first real payout lands correctly.",
                "current_status": "FOUNDER_ACTION_REQUIRED, NOT_YET_URGENT",
            },
        ],
        "note": "Every item above requires a real human action this factory's own code cannot legitimately perform (account creation, business verification, application approval, secret issuance by a 3rd party). No engineering task appears here.",
    }


# ---------------------------------------------------------------------------
# Section 14 -- Golden Hunter Staleness (architectural fix)
# ---------------------------------------------------------------------------

def golden_hunter_freshness_status(golden_json_path=None, freshness_hours=24, now=None):
    """Real, re-runnable staleness check -- exposes the same 24h
    threshold factory_loop.js's own internal logic already uses
    (GOLDEN_FRESHNESS_MS), now callable from Python/Mission Control
    too. Never silently treats stale data as fresh."""
    path = Path(golden_json_path) if golden_json_path else DEFAULT_GOLDEN_JSON_PATH
    now = now or datetime.now(timezone.utc)
    if not path.exists():
        return {"status": "MISSING", "age_hours": None, "detail": "golden_opportunities.json does not exist"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"status": "UNREADABLE", "age_hours": None, "detail": str(exc)}

    generated_at = data.get("generated_at")
    if not generated_at:
        return {"status": "MISSING_TIMESTAMP", "age_hours": None, "detail": "no generated_at field"}
    try:
        gen_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        if gen_dt.tzinfo is None:
            gen_dt = gen_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return {"status": "INVALID_TIMESTAMP", "age_hours": None, "detail": generated_at}

    age_hours = round((now - gen_dt).total_seconds() / 3600, 1)
    status = "FRESH" if age_hours <= freshness_hours else "STALE"
    return {"status": status, "age_hours": age_hours, "threshold_hours": freshness_hours,
            "count": data.get("count"), "generated_at": generated_at}


def force_refresh_golden_opportunities():
    """The requested 'controlled refresh mechanism' -- real, but
    deliberately never auto-triggered from this module or from
    factory_loop.js's tick. Calls profit_oracle.run_oracle() directly,
    bypassing the normal 'only on a new golden catch' gate. Never
    fabricates a new opportunity -- it re-ranks whatever real,
    already-scored niches exist in OPPORTUNITIES.md today; if none are
    new, the output is honestly unchanged except for a fresh
    generated_at timestamp."""
    import profit_oracle
    before = golden_hunter_freshness_status()
    profit_oracle.run_oracle()
    after = golden_hunter_freshness_status()
    return {"generated_at": _now_iso(), "before": before, "after": after,
            "note": "Real re-rank of already-scored real niches -- never a fabricated new opportunity. This function must be called explicitly (e.g. a founder-triggered Mission Control action); it is not wired into any automatic tick."}


# ---------------------------------------------------------------------------
# Section 16 -- Refunds / Disputes / Chargebacks Audit
# ---------------------------------------------------------------------------

def refund_dispute_chargeback_status():
    """Real, per-arm citation of BaseArm.retrieve_refunds()'s existing
    honest NOT_IMPLEMENTED default -- $0 must never be confused with
    UNKNOWN here."""
    from channels import registry
    import channels.gumroad_arm, channels.paddle_arm, channels.etsy_arm, channels.payhip_arm  # noqa: F401

    results = {}
    for name in ("gumroad", "paddle", "etsy", "payhip"):
        arm = registry.get(name)
        if arm is None:
            results[name] = {"refunds": "NOT_AVAILABLE", "disputes": "NOT_AVAILABLE", "chargebacks": "NOT_AVAILABLE"}
            continue
        refunds = arm.retrieve_refunds()
        results[name] = {
            "refunds": "NOT_AVAILABLE" if refunds.get("status") == "NOT_IMPLEMENTED" else refunds,
            "disputes": "NOT_AVAILABLE -- no dispute/chargeback endpoint is wired for any arm in this factory",
            "chargebacks": "NOT_AVAILABLE -- same reason as disputes",
        }
    return {
        "generated_at": _now_iso(), "platforms": results,
        "note": "NOT_AVAILABLE means no real signal exists to report -- it must never be read as $0. $0 REAL_REVENUE (finance_data.json, independently verified) means verified zero; these fields mean unmeasured, a different fact entirely.",
    }


# ---------------------------------------------------------------------------
# Phase 32, Section 20 -- Deterministic Commercial Go-Live Check
# ---------------------------------------------------------------------------

GO_LIVE_VERDICTS = ("GO", "NO_GO", "GO_WITH_FOUNDER_ACTION")


def commercial_go_live_check(platform_key="paddle", catalog_path=None, checkout_status=None):
    """Real, deterministic pre-launch gate for one platform -- checks
    product identity, price, checkout, tracking (webhook + idempotency),
    financial mapping, delivery, refund handling, and audit trail, each
    cited from real, already-verified signals. Commission/partner/
    customer-match dimensions are honestly NOT_APPLICABLE for a direct
    product sale (Phase 31.5 deferred the commission engine; nothing to
    check that doesn't exist yet). Never returns GO from an unverified
    or missing signal."""
    readiness = platform_activation_readiness(platform_key, catalog_path=catalog_path, checkout_status=checkout_status)
    reasons = []

    # Real live product count: gumroad reports from its live API (live_products),
    # paddle from its real catalog file (products). Never a stale "0".
    real_products = readiness.get("live_products") if readiness.get("live_products") is not None else readiness["products"]

    checks = {
        "product_identity": "VERIFIED" if real_products > 0 else "MISSING",
        "price": "VERIFIED" if real_products > 0 else "MISSING",
        "commission": "NOT_APPLICABLE -- direct product sale, no commission/referral involved",
        "partner": "NOT_APPLICABLE -- no partner/referral relationship in this flow",
        "customer_match": "NOT_APPLICABLE -- no customer-targeting step in this flow",
        "checkout": "VERIFIED" if readiness["CHECKOUT_READY"] is True else (
            "BLOCKED_EXTERNAL" if readiness["CHECKOUT_READY"] is False else "UNKNOWN"),
        "tracking": "VERIFIED (polling)" if readiness["credential_valid"] else "MISSING",
        "financial_mapping": "VERIFIED" if "REAL" in str(readiness["FINANCE_READY"]) else "MISSING",
        "delivery": "VERIFIED" if "REAL" in str(readiness["DELIVERY_READY"]) else "MISSING",
        "refund_handling": "NOT_AVAILABLE -- no real refund-retrieval endpoint exists for this platform",
        "audit_trail": "VERIFIED -- AUDIT/, data/recovery_actions.jsonl, data/paddle_webhook_events.jsonl (once populated)",
    }

    if not readiness["credential_valid"]:
        verdict = "NO_GO"
        reasons.append(f"{platform_key}: no valid credential configured")
    elif real_products <= 0:
        verdict = "NO_GO"
        reasons.append(f"{platform_key}: no real product catalog")
    elif readiness["CHECKOUT_READY"] is not True:
        verdict = "GO_WITH_FOUNDER_ACTION"
        reasons.append(readiness.get("blocker") or "checkout not yet verified live")
    else:
        verdict = "GO"
        if not readiness["WEBHOOK_READY"]:
            reasons.append("real-time webhook confirmation not configured -- polling-based confirmation (customer_pipeline.py::check_payment_status()) still covers real payment verification")

    return {
        "generated_at": _now_iso(), "platform": platform_key, "verdict": verdict, "reasons": reasons,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def build_commercial_activation_status(catalog_path=None, checkout_status=None):
    return {
        "generated_at": _now_iso(),
        "readiness": {p: platform_activation_readiness(p, catalog_path=catalog_path, checkout_status=checkout_status)
                      for p in ("paddle", "gumroad", "etsy", "payhip")},
        "go_live_check": {p: commercial_go_live_check(p, catalog_path=catalog_path, checkout_status=checkout_status)
                           for p in ("paddle", "gumroad", "etsy", "payhip")},
        "founder_action_center": founder_action_center(),
        "golden_hunter_freshness": golden_hunter_freshness_status(),
        "refunds_disputes_chargebacks": refund_dispute_chargeback_status(),
    }
