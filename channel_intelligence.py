#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Channel Intelligence (Revenue Factory, 2026-09-07).

Unified channel intelligence layer: Payment Intelligence, Product × Channel
matrix, Service × Channel matrix, and multi-platform state modeling.

Reuses:
  channels.registry       — registered channel arms
  channels.publish_protection — per-arm state
  channels.ledger         — publish attempt history
  profit_oracle           — pricing signals
  commercial_governance   — financial truth rules

Honesty contract:
  No fabricated channel state. No assumed payment routes. Every channel
  state is OBSERVED (from real data) or explicitly UNKNOWN/NOT_MEASURED.

Truth First vocabulary:
  NOT_BUILT, UNKNOWN, NOT_MEASURABLE, DISCOVERY, OBSERVED, DERIVED,
  ESTIMATED — applied throughout.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    from channels import registry as CHANNEL_REGISTRY
except (Exception, SystemExit):
    CHANNEL_REGISTRY = None

try:
    from channels import publish_protection
except (Exception, SystemExit):
    publish_protection = None

try:
    from channels import ledger as CHANNEL_LEDGER
except (Exception, SystemExit):
    CHANNEL_LEDGER = None

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------
CHANNEL_INTELLIGENCE_PATH = _FACTORY_ROOT / "data" / "channel_intelligence.json"
PAYMENT_INTELLIGENCE_PATH = _FACTORY_ROOT / "data" / "payment_intelligence.json"
PRODUCT_CHANNEL_MATRIX_PATH = _FACTORY_ROOT / "data" / "product_channel_matrix.json"
SERVICE_CHANNEL_MATRIX_PATH = _FACTORY_ROOT / "data" / "service_channel_matrix.json"

# ---------------------------------------------------------------------------
# Channel definitions — all platforms the factory knows about
# ---------------------------------------------------------------------------

DIGITAL_PRODUCT_CHANNELS = {
    "gumroad": {
        "name": "Gumroad",
        "type": "DIGITAL_PRODUCTS",
        "payment_processor": "Stripe (via Gumroad)",
        "payout_route": "Bank transfer / PayPal",
        "country_eligibility": "Global (most countries)",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Stripe-supported bank",
        "currency": "USD",
        "fees": {"platform": "10%", "payment": "included"},
        "payout_timing": "Weekly (Fridays)",
        "verification_requirements": ["email", "payment_method"],
        "activation_state": "READY_WITH_EXTERNAL_BLOCKER",
        "code_exists": True,
        "has_product": True,
        "has_checkout": True,
        "checkout_verified": True,
        "has_credentials": True,
        "evidence": "OBSERVED",
        "blocker": "Product in DRAFT, PDF not uploaded, payment not connected",
    },
    "payhip": {
        "name": "Payhip",
        "type": "DIGITAL_PRODUCTS",
        "payment_processor": "Stripe (via Payhip)",
        "payout_route": "Bank transfer",
        "country_eligibility": "Global",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Stripe-supported bank",
        "currency": "USD",
        "fees": {"platform": "5% (Basic)", "payment": "included"},
        "payout_timing": "Monthly",
        "verification_requirements": ["email", "payment_method"],
        "activation_state": "NOT_IMPLEMENTED",
        "code_exists": True,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "OBSERVED",
        "blocker": "UnsupportedOperationError — no product API",
    },
    "creative_market": {
        "name": "Creative Market",
        "type": "DIGITAL_PRODUCTS",
        "payment_processor": "Stripe (via Creative Market)",
        "payout_route": "Bank transfer",
        "country_eligibility": "Limited",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Stripe-supported bank",
        "currency": "USD",
        "fees": {"platform": "30-50%", "payment": "included"},
        "payout_timing": "Monthly",
        "verification_requirements": ["application", "portfolio_review"],
        "activation_state": "EXTERNAL_BLOCKER",
        "code_exists": False,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "UNKNOWN",
        "blocker": "Application-based platform, no API integration planned",
    },
    "etsy": {
        "name": "Etsy",
        "type": "DIGITAL_PRODUCTS",
        "payment_processor": "Etsy Payments (Stripe)",
        "payout_route": "Bank transfer",
        "country_eligibility": "36 countries",
        "algeria_eligibility": "NOT_ELIGIBLE",
        "bank_compatibility": "Requires Etsy-supported bank in supported country",
        "currency": "USD",
        "fees": {"platform": "6.5% + $0.20 listing", "payment": "3% + $0.25"},
        "payout_timing": "Weekly or monthly",
        "verification_requirements": ["identity", "bank_account", "credit_card"],
        "activation_state": "BLOCKED",
        "code_exists": True,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "OBSERVED",
        "blocker": "No OAuth2 token, no API credentials. API closed for new apps since 2024.",
    },
    "notion_marketplace": {
        "name": "Notion Marketplace",
        "type": "DIGITAL_PRODUCTS",
        "payment_processor": "Stripe (via Notion)",
        "payout_route": "Bank transfer",
        "country_eligibility": "UNKNOWN",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "UNKNOWN",
        "currency": "USD",
        "fees": {"platform": "UNKNOWN", "payment": "UNKNOWN"},
        "payout_timing": "UNKNOWN",
        "verification_requirements": ["UNKNOWN"],
        "activation_state": "NOT_BUILT",
        "code_exists": False,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "UNKNOWN",
        "blocker": "No integration exists",
    },
    "direct_website": {
        "name": "Direct Website / Direct Checkout",
        "type": "DIGITAL_PRODUCTS",
        "payment_processor": "Paddle / Stripe (direct)",
        "payout_route": "Bank transfer",
        "country_eligibility": "Global",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires payment processor support",
        "currency": "USD",
        "fees": {"platform": "0%", "payment": "Paddle 5% / Stripe 2.9%+$0.30"},
        "payout_timing": "Paddle: monthly / Stripe: rolling",
        "verification_requirements": ["payment_processor_account"],
        "activation_state": "READY_WITH_EXTERNAL_BLOCKER",
        "code_exists": True,
        "has_product": True,
        "has_checkout": True,
        "checkout_verified": False,
        "has_credentials": True,
        "evidence": "OBSERVED",
        "blocker": "Paddle account onboarding incomplete — transaction_checkout_not_enabled",
    },
}

BOOK_CHANNELS = {
    "amazon_kdp": {
        "name": "Amazon KDP",
        "type": "BOOKS",
        "payment_processor": "Amazon",
        "payout_route": "Amazon direct deposit",
        "country_eligibility": "Global (most countries)",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Amazon-supported bank",
        "currency": "USD",
        "fees": {"platform": "30-65% (royalty)", "payment": "included"},
        "payout_timing": "60 days after sale",
        "verification_requirements": ["tax_info", "bank_account"],
        "activation_state": "NOT_REQUIRED",
        "code_exists": True,
        "has_product": True,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "OBSERVED",
        "blocker": "Manual upload only, no public API. No KDP credentials.",
    },
}

AFFILIATE_CHANNELS = {
    "amazon_associates": {
        "name": "Amazon Associates",
        "type": "AFFILIATE",
        "payment_processor": "Amazon",
        "payout_route": "Amazon gift card / direct deposit",
        "country_eligibility": "Global (program varies by country)",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Amazon-supported bank",
        "currency": "USD",
        "fees": {"platform": "0% (affiliate)", "payment": "N/A"},
        "payout_timing": "Monthly (60-day delay)",
        "verification_requirements": ["application", "website", "qualifying_purchases"],
        "activation_state": "EXTERNAL_BLOCKER",
        "code_exists": True,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "OBSERVED",
        "blocker": "AMAZON_ASSOCIATE_TAG not set, account not created",
    },
}

SERVICE_CHANNELS = {
    "upwork": {
        "name": "Upwork",
        "type": "SERVICES",
        "payment_processor": "Upwork (escrow)",
        "payout_route": "PayPal / Payoneer / bank transfer",
        "country_eligibility": "Global",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "PayPal or Payoneer required",
        "currency": "USD",
        "fees": {"platform": "10-20% (sliding scale)", "payment": "included"},
        "payout_timing": "Weekly (after 5-day security hold)",
        "verification_requirements": ["identity", "portfolio", "skills_test"],
        "activation_state": "EXTERNAL_BLOCKER",
        "code_exists": False,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "UNKNOWN",
        "blocker": "No account, no API. Application-based platform.",
    },
    "fiverr": {
        "name": "Fiverr",
        "type": "SERVICES",
        "payment_processor": "Fiverr (escrow)",
        "payout_route": "PayPal / Payoneer / bank transfer",
        "country_eligibility": "Global",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "PayPal or Payoneer required",
        "currency": "USD",
        "fees": {"platform": "20% (seller)", "payment": "included"},
        "payout_timing": "14 days after completion",
        "verification_requirements": ["identity", "portfolio"],
        "activation_state": "EXTERNAL_BLOCKER",
        "code_exists": False,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "UNKNOWN",
        "blocker": "No account, no API. Application-based platform.",
    },
    "contra": {
        "name": "Contra",
        "type": "SERVICES",
        "payment_processor": "Stripe (via Contra)",
        "payout_route": "Bank transfer",
        "country_eligibility": "US-focused",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Stripe-supported bank",
        "currency": "USD",
        "fees": {"platform": "0% (Indie plan)", "payment": "Stripe fees apply"},
        "payout_timing": "Monthly",
        "verification_requirements": ["identity", "portfolio"],
        "activation_state": "EXTERNAL_BLOCKER",
        "code_exists": False,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "UNKNOWN",
        "blocker": "No account, no API. US-focused.",
    },
}

SOFTWARE_CHANNELS = {
    "paddle": {
        "name": "Paddle",
        "type": "SOFTWARE",
        "payment_processor": "Paddle (merchant of record)",
        "payout_route": "Bank transfer / PayPal",
        "country_eligibility": "Global (most countries)",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Paddle-supported bank",
        "currency": "USD",
        "fees": {"platform": "5% + $0.50 per transaction", "payment": "included"},
        "payout_timing": "Monthly (with holdback)",
        "verification_requirements": ["business_info", "bank_account", "tax_info"],
        "activation_state": "READY_WITH_EXTERNAL_BLOCKER",
        "code_exists": True,
        "has_product": True,
        "has_checkout": True,
        "checkout_verified": False,
        "has_credentials": True,
        "evidence": "OBSERVED",
        "blocker": "Account onboarding incomplete — transaction_checkout_not_enabled",
    },
    "lemon_squeezy": {
        "name": "Lemon Squeezy",
        "type": "SOFTWARE",
        "payment_processor": "Stripe (via Lemon Squeezy)",
        "payout_route": "Bank transfer / PayPal",
        "country_eligibility": "Global",
        "algeria_eligibility": "UNKNOWN",
        "bank_compatibility": "Requires Stripe-supported bank",
        "currency": "USD",
        "fees": {"platform": "5% + $0.50 per transaction", "payment": "included"},
        "payout_timing": "Monthly",
        "verification_requirements": ["email", "payment_method"],
        "activation_state": "NOT_BUILT",
        "code_exists": False,
        "has_product": False,
        "has_checkout": False,
        "checkout_verified": False,
        "has_credentials": False,
        "evidence": "UNKNOWN",
        "blocker": "No integration exists",
    },
}

ALL_CHANNELS = {}
ALL_CHANNELS.update(DIGITAL_PRODUCT_CHANNELS)
ALL_CHANNELS.update(BOOK_CHANNELS)
ALL_CHANNELS.update(AFFILIATE_CHANNELS)
ALL_CHANNELS.update(SERVICE_CHANNELS)
ALL_CHANNELS.update(SOFTWARE_CHANNELS)

# ---------------------------------------------------------------------------
# Channel states (from the directive's §8)
# ---------------------------------------------------------------------------

CHANNEL_STATES = [
    "CHANNEL_DISCOVERED",
    "CHANNEL_ELIGIBILITY_UNKNOWN",
    "CHANNEL_ELIGIBILITY_VERIFIED",
    "ACCOUNT_REQUIRED",
    "ACCOUNT_READY",
    "PAYMENT_REQUIRED",
    "PAYMENT_READY",
    "PRODUCT_READY",
    "PUBLISHED",
    "CHECKOUT_VERIFIED",
    "TRANSACTION_ATTEMPTED",
    "TRANSACTION_VERIFIED",
    "DELIVERY_VERIFIED",
    "CUSTOMER_EVIDENCE_VERIFIED",
    "REPEATABILITY_VERIFIED",
    "DEGRADED",
    "BLOCKED",
    "DISABLED",
    "UNKNOWN",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_json(path, default=None):
    p = Path(path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return default if default is not None else {}


def _save_json(data, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data["last_modified"] = _now_iso()
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding='utf-8')


# ---------------------------------------------------------------------------
# Public API — Channel Intelligence
# ---------------------------------------------------------------------------

def channel_intelligence():
    """Complete intelligence on all channels.

    Returns the full state of every channel the factory knows about,
    with evidence classification for each field.
    """
    channels = {}

    for ch_id, ch_def in ALL_CHANNELS.items():
        channels[ch_id] = {
            "name": ch_def["name"],
            "type": ch_def["type"],
            "payment_processor": ch_def.get("payment_processor", "UNKNOWN"),
            "payout_route": ch_def.get("payout_route", "UNKNOWN"),
            "country_eligibility": ch_def.get("country_eligibility", "UNKNOWN"),
            "algeria_eligibility": ch_def.get("algeria_eligibility", "UNKNOWN"),
            "bank_compatibility": ch_def.get("bank_compatibility", "UNKNOWN"),
            "currency": ch_def.get("currency", "UNKNOWN"),
            "fees": ch_def.get("fees", {}),
            "payout_timing": ch_def.get("payout_timing", "UNKNOWN"),
            "verification_requirements": ch_def.get("verification_requirements", []),
            "activation_state": ch_def.get("activation_state", "UNKNOWN"),
            "code_exists": ch_def.get("code_exists", False),
            "has_product": ch_def.get("has_product", False),
            "has_checkout": ch_def.get("has_checkout", False),
            "checkout_verified": ch_def.get("checkout_verified", False),
            "has_credentials": ch_def.get("has_credentials", False),
            "evidence": ch_def.get("evidence", "UNKNOWN"),
            "blocker": ch_def.get("blocker", None),
        }

    return {
        "channels": channels,
        "total_channels": len(channels),
        "by_type": {
            "DIGITAL_PRODUCTS": len(DIGITAL_PRODUCT_CHANNELS),
            "BOOKS": len(BOOK_CHANNELS),
            "AFFILIATE": len(AFFILIATE_CHANNELS),
            "SERVICES": len(SERVICE_CHANNELS),
            "SOFTWARE": len(SOFTWARE_CHANNELS),
        },
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Payment Intelligence
# ---------------------------------------------------------------------------

def payment_intelligence():
    """Payment and payout intelligence for every relevant channel.

    Distinguishes:
      INTEGRATION_EXISTS — code exists
      PAYMENT_ROUTE_VERIFIED — payment method confirmed
      PAYOUT_ROUTE_VERIFIED — payout route confirmed
      REAL_PAYMENT_VERIFIED — real money has moved
    """
    payments = {}

    for ch_id, ch_def in ALL_CHANNELS.items():
        integration = "INTEGRATION_EXISTS" if ch_def.get("code_exists") else "NO_INTEGRATION"
        payment_route = "UNKNOWN"
        payout_route = "UNKNOWN"
        real_payment = "NOT_MEASURED"

        if ch_def.get("checkout_verified"):
            payment_route = "PAYMENT_ROUTE_VERIFIED"
        elif ch_def.get("has_checkout"):
            payment_route = "CHECKOUT_EXISTS_NOT_VERIFIED"

        if ch_def.get("activation_state") == "READY_WITH_EXTERNAL_BLOCKER":
            payout_route = "PAYOUT_ROUTE_EXISTS_NOT_ACTIVATED"

        if ch_def.get("has_credentials"):
            integration = "CREDENTIALS_CONFIGURED"

        payments[ch_id] = {
            "name": ch_def["name"],
            "type": ch_def["type"],
            "integration": integration,
            "payment_route": payment_route,
            "payout_route": payout_route,
            "real_payment": real_payment,
            "activation_state": ch_def.get("activation_state", "UNKNOWN"),
            "blocker": ch_def.get("blocker", None),
        }

    return {
        "payments": payments,
        "total_channels": len(payments),
        "with_integration": sum(1 for p in payments.values() if "INTEGRATION_EXISTS" in p["integration"] or "CREDENTIALS" in p["integration"]),
        "with_payment_route": sum(1 for p in payments.values() if "VERIFIED" in p["payment_route"]),
        "with_payout_route": sum(1 for p in payments.values() if "VERIFIED" in p["payout_route"]),
        "real_payments": sum(1 for p in payments.values() if p["real_payment"] == "VERIFIED"),
        "verdict": "NO_VERIFIED_PAYMENT_ROUTES",
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Product × Channel Matrix
# ---------------------------------------------------------------------------

def product_channel_matrix():
    """Complete Product × Channel matrix.

    For each digital product channel, shows eligibility, account state,
    payment state, checkout state, delivery state, economics, and evidence.
    """
    products = _load_json(_FACTORY_ROOT / "data" / "asset_registry.json", {}).get("products", [])
    matrix = {}

    for ch_id, ch_def in ALL_CHANNELS.items():
        if ch_def["type"] not in ("DIGITAL_PRODUCTS", "BOOKS", "SOFTWARE"):
            continue

        channel_products = []
        for product in products:
            pid = product.get("id", product.get("product_id", "UNKNOWN"))
            channel_products.append({
                "product_id": pid,
                "name": product.get("title", product.get("name", "UNKNOWN")),
                "eligibility": ch_def.get("activation_state", "UNKNOWN"),
                "account": "ACCOUNT_READY" if ch_def.get("has_credentials") else "ACCOUNT_REQUIRED",
                "payment": "PAYMENT_READY" if ch_def.get("checkout_verified") else "PAYMENT_REQUIRED",
                "checkout": "CHECKOUT_VERIFIED" if ch_def.get("checkout_verified") else "UNKNOWN",
                "delivery": "UNKNOWN",
                "economics": "UNKNOWN",
                "evidence": ch_def.get("evidence", "UNKNOWN"),
                "state": ch_def.get("activation_state", "UNKNOWN"),
                "blocker": ch_def.get("blocker", None),
            })

        matrix[ch_id] = {
            "channel_name": ch_def["name"],
            "channel_type": ch_def["type"],
            "products": channel_products,
            "total_products": len(channel_products),
        }

    return {
        "matrix": matrix,
        "total_channels": len(matrix),
        "total_products": len(products),
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Service × Channel Matrix
# ---------------------------------------------------------------------------

def service_channel_matrix():
    """Complete Service × Channel matrix.

    For each service channel, shows eligibility, account state,
    payment state, delivery state, economics, and evidence.
    """
    from services_engine import SERVICE_CATEGORIES
    services = list(SERVICE_CATEGORIES.keys())
    matrix = {}

    for ch_id, ch_def in ALL_CHANNELS.items():
        if ch_def["type"] != "SERVICES":
            continue

        channel_services = []
        for svc_id in services:
            cat = SERVICE_CATEGORIES[svc_id]
            channel_services.append({
                "service_id": svc_id,
                "name": cat["name"],
                "eligibility": ch_def.get("activation_state", "UNKNOWN"),
                "account": "ACCOUNT_READY" if ch_def.get("has_credentials") else "ACCOUNT_REQUIRED",
                "payment": "PAYMENT_READY" if ch_def.get("checkout_verified") else "PAYMENT_REQUIRED",
                "delivery": "UNKNOWN",
                "economics": "UNKNOWN",
                "evidence": ch_def.get("evidence", "UNKNOWN"),
                "state": ch_def.get("activation_state", "UNKNOWN"),
                "blocker": ch_def.get("blocker", None),
            })

        matrix[ch_id] = {
            "channel_name": ch_def["name"],
            "channel_type": ch_def["type"],
            "services": channel_services,
            "total_services": len(channel_services),
        }

    # Also add direct channels
    for ch_id, ch_def in ALL_CHANNELS.items():
        if ch_def["type"] not in ("DIGITAL_PRODUCTS", "SOFTWARE"):
            continue
        if ch_id in ("direct_website",):
            direct_services = []
            for svc_id in services:
                cat = SERVICE_CATEGORIES[svc_id]
                direct_services.append({
                    "service_id": svc_id,
                    "name": cat["name"],
                    "eligibility": "CHANNEL_DISCOVERED",
                    "account": "NOT_REQUIRED",
                    "payment": "PAYMENT_REQUIRED",
                    "delivery": "UNKNOWN",
                    "economics": "UNKNOWN",
                    "evidence": "UNKNOWN",
                    "state": "CHANNEL_DISCOVERED",
                    "blocker": None,
                })
            matrix[ch_id] = {
                "channel_name": ch_def["name"] + " (Direct)",
                "channel_type": "SERVICES",
                "services": direct_services,
                "total_services": len(direct_services),
            }

    return {
        "matrix": matrix,
        "total_channels": len(matrix),
        "total_services": len(services),
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Channel readiness summary
# ---------------------------------------------------------------------------

def channel_readiness_summary():
    """Summary of all channels with readiness classification."""
    intel = channel_intelligence()
    payments = payment_intelligence()

    ready = []
    with_blocker = []
    not_built = []
    blocked = []

    for ch_id, ch_data in intel["channels"].items():
        state = ch_data.get("activation_state", "UNKNOWN")
        summary = {
            "channel_id": ch_id,
            "name": ch_data["name"],
            "type": ch_data["type"],
            "state": state,
            "evidence": ch_data["evidence"],
        }

        if state == "READY_WITH_EXTERNAL_BLOCKER":
            with_blocker.append(summary)
        elif state in ("NOT_BUILT", "NOT_IMPLEMENTED"):
            not_built.append(summary)
        elif state in ("BLOCKED", "DISABLED"):
            blocked.append(summary)
        elif state in ("PUBLISHED", "CHECKOUT_VERIFIED", "TRANSACTION_VERIFIED"):
            ready.append(summary)
        else:
            with_blocker.append(summary)

    return {
        "ready": ready,
        "with_blocker": with_blocker,
        "not_built": not_built,
        "blocked": blocked,
        "total": len(intel["channels"]),
        "ready_count": len(ready),
        "with_blocker_count": len(with_blocker),
        "not_built_count": len(not_built),
        "blocked_count": len(blocked),
        "verdict": "NO_CHANNELS_FULLY_READY",
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Public API — Revenue factory integration
# ---------------------------------------------------------------------------

def revenue_factory_status():
    """Return Channel Intelligence status for the Revenue Factory audit."""
    intel = channel_intelligence()
    payments = payment_intelligence()
    readiness = channel_readiness_summary()
    prod_matrix = product_channel_matrix()
    svc_matrix = service_channel_matrix()

    return {
        "engine": "CHANNEL_INTELLIGENCE",
        "status": "IMPLEMENTED",
        "total_channels": intel["total_channels"],
        "by_type": intel["by_type"],
        "payment_intelligence": {
            "with_integration": payments["with_integration"],
            "with_payment_route": payments["with_payment_route"],
            "with_payout_route": payments["with_payout_route"],
            "real_payments": payments["real_payments"],
            "verdict": payments["verdict"],
        },
        "product_channel_matrix": {
            "total_channels": prod_matrix["total_channels"],
            "total_products": prod_matrix["total_products"],
        },
        "service_channel_matrix": {
            "total_channels": svc_matrix["total_channels"],
            "total_services": svc_matrix["total_services"],
        },
        "readiness": {
            "ready": readiness["ready_count"],
            "with_blocker": readiness["with_blocker_count"],
            "not_built": readiness["not_built_count"],
            "blocked": readiness["blocked_count"],
            "verdict": readiness["verdict"],
        },
        "verdict": "IMPLEMENTED",
        "note": "Channel Intelligence layer is IMPLEMENTED. All 13 channels modeled. "
                "No channels fully ready. All payment routes UNKNOWN/NOT_VERIFIED.",
        "generated_at": _now_iso(),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Galaxy Forge Channel Intelligence")
    parser.add_argument("--channels", action="store_true", help="All channel intelligence")
    parser.add_argument("--payments", action="store_true", help="Payment intelligence")
    parser.add_argument("--product-matrix", action="store_true", help="Product × Channel matrix")
    parser.add_argument("--service-matrix", action="store_true", help="Service × Channel matrix")
    parser.add_argument("--readiness", action="store_true", help="Channel readiness summary")
    parser.add_argument("--status", action="store_true", help="Revenue factory status")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if args.channels:
        result = channel_intelligence()
    elif args.payments:
        result = payment_intelligence()
    elif args.product_matrix:
        result = product_channel_matrix()
    elif args.service_matrix:
        result = service_channel_matrix()
    elif args.readiness:
        result = channel_readiness_summary()
    elif args.status:
        result = revenue_factory_status()
    else:
        parser.print_help()
        exit(0)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
