#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge - provider-independent financial connectivity (2026-10-24).

One read-only view of payment providers, settlement rails, sales channels,
orders, fees and verified revenue. It answers a narrower question than the
existing revenue engines: where can money actually enter, where can it leave,
and what has been observed rather than assumed?

Reuses instead of duplicating:
  channels.registry / channels.base_arm   registered publish adapters
  channels.ledger                         append-only sale + publish ledger
  channels.env_config                     exact-key .env reader
  data/payment_connectivity.json          last observed API/checkout state
  data/product_registry.json              product -> platform ids
  data/paddle_products.json               Paddle catalog
  data/commission_ledger.jsonl            affiliate commissions

Honesty contract:
  * Credential *presence* only. Values are never read into the result.
  * No network call, no provider mutation, no transfer, refund or publish.
  * No status is upgraded without recorded evidence. A configured key is not
    a verified payment. A published listing is not revenue.
  * TEST/SANDBOX/SIMULATION rows never count as orders or revenue.
  * Unknown fees/net stay null/UNKNOWN, never zero.
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
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from channels import env_config
except (Exception, SystemExit):
    env_config = None

try:
    from channels import ledger as CHANNEL_LEDGER
except (Exception, SystemExit):
    CHANNEL_LEDGER = None




STATUS = (
    "NOT_CONFIGURED",
    "CONFIGURED_NOT_VERIFIED",
    "AUTHENTICATION_FAILED",
    "CONNECTED_READ_ONLY",
    "PAYMENT_CAPABLE",
    "SETTLEMENT_VERIFIED",
    "BLOCKED_BY_PROVIDER_ELIGIBILITY",
    "UNKNOWN",
)

CHANNEL_STATES = (
    "PUBLIC_LISTING_ONLY",
    "SALES_OBSERVED",
    "BLOCKED",
    "NOT_CONFIGURED",
    "NOT_IMPLEMENTED",
    "PARTIAL",
    "MANUAL_UPLOAD_ONLY",
    "UNKNOWN",
)

SETTLEMENT_STATES = ("OBSERVED", "SETTLEMENT_VERIFIED", "MISMATCH")
TEST_ENVIRONMENTS = {"TEST", "SANDBOX", "SIMULATION", "SIMULATED", "MOCK"}
CURRENCY = "USD"

PROVIDER_ORDER = ("gumroad", "paddle", "stripe", "paypal", "badr")

PROVIDER_SPECS = {
    "gumroad": {
        "display_name": "Gumroad",
        "provider_type": "MARKETPLACE",
        "role": "sales_channel",
        "api_available": True,
        "settlement_model": "Marketplace payout; canonical route is BADR direct bank account, EUR (config/financial_connectivity.json)",
        "required_credentials": ("GUMROAD_ACCESS_TOKEN",),
        "currencies": ["USD"],
        "official_docs": "https://gumroad.com/api",
        "fees_source": "channel_intelligence.py: 10% platform fee, payment included",
        "eligibility": "Seller account exists; routing policy is BANK_ROUTE, but the platform payout method is not recorded as configured.",
    },
    "paddle": {
        "display_name": "Paddle",
        "provider_type": "MERCHANT_OF_RECORD",
        "role": "sales_channel_and_payment_provider",
        "api_available": True,
        "settlement_model": "Merchant-of-record payout; canonical route is Payoneer -> BADR EUR where supported (config/financial_connectivity.json)",
        "required_credentials": ("PADDLE_API_KEY",),
        "optional_credentials": ("PADDLE_WEBHOOK_SECRET",),
        "currencies": ["USD"],
        "official_docs": "https://developer.paddle.com/",
        "fees_source": "channel_intelligence.py: 5% + $0.50 per transaction",
        "eligibility": "Merchant account exists; onboarding incomplete; checkout not enabled.",
    },
    "stripe": {
        "display_name": "Stripe",
        "provider_type": "PAYMENT_PROCESSOR",
        "role": "payment_provider",
        "api_available": True,
        "settlement_model": "Processor payout to a supported bank account",
        "required_credentials": ("STRIPE_SECRET_KEY",),
        "optional_credentials": ("STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"),
        "currencies": [],
        "currency_note": "UNKNOWN: no verified Stripe account or currency capability exists for Algeria.",
        "official_docs": "https://stripe.com/global",
        "fees_source": "UNKNOWN - no live Stripe pricing retrieval in this read model",
        "eligibility": "BLOCKED: Algeria is not in Stripe's official supported-country list (accessed 2026-10-24).",
    },
    "paypal": {
        "display_name": "PayPal",
        "provider_type": "WALLET",
        "role": "payment_provider",
        "api_available": True,
        "settlement_model": "Balance held in PayPal; automatic transfer to linked US bank account or Visa credit card",
        "required_credentials": ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"),
        "optional_credentials": ("PAYPAL_MODE",),
        "currencies": [],
        "currency_note": "UNKNOWN: the Algeria receive agreement does not establish which currencies the account can hold.",
        "official_docs": "https://www.paypal.com/al/legalhub/paypal/recpymt-full?locale.x=en_AL",
        "fees_source": "UNKNOWN - market-specific fee schedule not retrieved in this read model",
        "eligibility": "CONDITIONAL: PayPal's Algeria Receive Funds agreement applies, requires a linked US bank account or Visa credit card and a 30-day hold; the canonical config keeps PayPal fallback-only, never the Gumroad route.",
    },
    "badr": {
        "display_name": "BADR Bank",
        "provider_type": "BANK",
        "role": "settlement_destination",
        "api_available": False,
        "settlement_model": "Bank settlement / manual reconciliation only",
        "required_credentials": (),
        "currencies": ["EUR"],
        "currency_note": "EUR is the account currency recorded in LAUNCH_READINESS.md; BADR's full support is not verified.",
        "official_docs": "https://www.badrbanque.dz/",
        "fees_source": "UNKNOWN - bank fee schedule not retrieved",
        "eligibility": "SETTLEMENT_ONLY: founder-confirmed final treasury (EUR), but no official BADR API, machine credential, or verified settlement record exists.",
    },
}

CHANNEL_SPECS = {
    "gumroad": {
        "display_name": "Gumroad",
        "channel_type": "MARKETPLACE",
        "provider": "gumroad",
        "storefront": True,
        "api_available": True,
        "eligibility": "Seller account exists; product listings observed.",
    },
    "paddle": {
        "display_name": "Paddle Checkout",
        "channel_type": "DIRECT_CHECKOUT",
        "provider": "paddle",
        "storefront": True,
        "api_available": True,
        "eligibility": "Merchant account exists; checkout blocked by incomplete onboarding.",
    },
    "paypal_storefront": {
        "display_name": "PayPal Payment Links",
        "channel_type": "DIRECT_CHECKOUT",
        "provider": "paypal",
        "storefront": True,
        "api_available": True,
        "eligibility": "No PayPal payment-link integration is built or configured.",
    },
    "shopify": {
        "display_name": "Shopify",
        "channel_type": "OWNED_STOREFRONT",
        "provider": None,
        "storefront": True,
        "api_available": True,
        "eligibility": "DISCOVERY: no Shopify store, app or merchant credentials exist; seller/payment eligibility not verified.",
    },
    "direct_website": {
        "display_name": "Galaxy Forge Website",
        "channel_type": "OWNED_STOREFRONT",
        "provider": None,
        "storefront": True,
        "api_available": False,
        "eligibility": "The customer site exists, but it depends on Paddle/PayPal for checkout; no independent payment rail.",
    },
    "etsy": {
        "display_name": "Etsy",
        "channel_type": "MARKETPLACE",
        "provider": None,
        "storefront": True,
        "api_available": True,
        "eligibility": "BLOCKED: Etsy seller eligibility is not met for Algeria; API access is also restricted.",
    },
    "payhip": {
        "display_name": "Payhip",
        "channel_type": "MARKETPLACE",
        "provider": None,
        "storefront": True,
        "api_available": False,
        "eligibility": "NOT_IMPLEMENTED: no product API; no live credentials.",
    },
    "amazon_kdp": {
        "display_name": "Amazon KDP",
        "channel_type": "BOOK_MARKETPLACE",
        "provider": None,
        "storefront": True,
        "api_available": False,
        "eligibility": "MANUAL_UPLOAD_ONLY: no public KDP publishing API.",
    },
}


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _age_days(iso, now=None):
    if not iso:
        return None
    try:
        observed = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return round(((now or datetime.now(timezone.utc)) - observed).total_seconds() / 86400, 1)


def _freshness(iso, now=None, max_days=7):
    age = _age_days(iso, now=now)
    if age is None:
        return {"observed_at": iso, "age_days": None, "state": "UNKNOWN"}
    return {"observed_at": iso, "age_days": age, "state": "STALE" if age > max_days else "CURRENT"}


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _read_jsonl(path):
    if not Path(path).exists():
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if isinstance(value, dict):
                    rows.append(value)
    except OSError:
        return rows
    return rows


def _source(path, root):
    path = Path(path)
    try:
        updated = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    except OSError:
        updated = None
    try:
        label = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        label = str(path)
    return {"file": label, "present": path.exists(), "updated_at": updated}


def _configured(name, env, env_path):
    if env is not None:
        return bool(str(env.get(name) or "").strip())
    if env_config is None:
        return bool(str(os.environ.get(name) or "").strip())
    return bool(env_config.read_env_value(name, env_path=env_path))


ROUTING_CONFIG_REL = "config/financial_connectivity.json"


def _public_mapping(value):
    """Drop account-identity fields; emails are non-secret but not needed here."""
    if isinstance(value, dict):
        return {
            key: _public_mapping(item)
            for key, item in value.items()
            if key not in ("identity", "commercial_identity", "payout_identity")
        }
    if isinstance(value, list):
        return [_public_mapping(item) for item in value]
    return value


def _provider_routing(key, routing_doc):
    """Cite the canonical routing policy without restating or replacing it."""
    if not isinstance(routing_doc, dict) or not routing_doc:
        return None
    classified = routing_doc.get("platform_classification") or {}
    if key in classified and isinstance(classified[key], dict):
        item = classified[key]
        return {
            "classification": item.get("classification"),
            "role": item.get("role"),
            "routing": item.get("routing"),
            "status": item.get("status"),
            "blocking": item.get("blocking"),
            "manual_actions": list(item.get("manual_actions") or []),
            "evidence_type": item.get("evidence_type"),
        }
    if key == "badr":
        treasury = routing_doc.get("treasury") or {}
        return {
            "classification": "FINAL_TREASURY",
            "role": treasury.get("role"),
            "routing": "Platform -> supported payout route -> BADR EUR",
            "status": treasury.get("status"),
            "function": treasury.get("function"),
            "currency": treasury.get("currency"),
        }
    if key == "paypal":
        fallback = (routing_doc.get("fallbacks") or {}).get("paypal") or {}
        return {
            "classification": fallback.get("role"),
            "role": "FALLBACK_EXCEPTION_ONLY",
            "routing": "Not used for Gumroad; no settled route is configured.",
            "status": fallback.get("algeria_receiving"),
            "note": fallback.get("note"),
            "used_for": list(fallback.get("used_for") or []),
        }
    return None


def _account_routing_summary():
    """Non-secret routing metadata only. Identity emails are dropped here."""
    try:
        import account_routing
        table = account_routing.account_routing_table()
    except Exception as exc:  # noqa: BLE001 - honest unavailable, never a guess
        return {
            "available": False,
            "reason": f"{type(exc).__name__}: account_routing.py is unavailable",
        }
    kept = (
        "platform", "category", "payout_method", "payout_status", "status",
        "missing_requirements", "blocking_reason",
    )
    return {
        "available": True,
        "total_platforms": table.get("total_platforms"),
        "verified_count": table.get("verified_count"),
        "unknown_count": table.get("unknown_count"),
        "routes": [
            {field: route.get(field) for field in kept}
            for route in (table.get("routes") or [])
        ],
        "note": "Account identity emails are intentionally omitted from this report.",
    }


def _routing_consistency(routing_doc, account_routing):
    """Surface where the two real routing sources disagree, without resolving it."""
    if not account_routing.get("available"):
        return {"state": "UNKNOWN", "pairs": [], "reason": account_routing.get("reason")}
    by_platform = {
        route.get("platform"): route
        for route in account_routing.get("routes") or []
    }
    classified = routing_doc.get("platform_classification") or {}
    expected = {
        "paddle": "Payoneer",
        "gumroad": "Bank (BADR)",
        "amazon_kdp": "Payoneer",
        "paypal": "Fallback only",
    }
    pairs = []
    for platform, policy_method in expected.items():
        policy = classified.get(platform) or {}
        if platform == "paypal":
            policy = {
                "status": ((routing_doc.get("fallbacks") or {}).get("paypal") or {}).get("algeria_receiving"),
            }
        route = by_platform.get(platform)
        routed_method = route.get("payout_method") if route else None
        if platform == "paypal" and route is None:
            routed_method = "Unlisted"
        consistent = None
        if policy and route is not None and routed_method not in (None, "UNKNOWN"):
            consistent = routed_method == policy_method
        pairs.append({
            "platform": platform,
            "policy_method": policy_method,
            "policy_status": policy.get("status"),
            "account_routing_method": routed_method,
            "account_routing_status": route.get("status") if route else None,
            "state": (
                "CONSISTENT" if consistent is True else
                "UNRECONCILED" if consistent is False or (
                    policy and (route is None or routed_method in (None, "UNKNOWN"))
                ) else
                "UNKNOWN"
            ),
        })
    declared_counts = routing_doc.get("account_routing") or {}
    live_counts = {
        "total_classified_platforms": account_routing.get("total_platforms"),
        "verified_count": account_routing.get("verified_count"),
        "unknown_count": account_routing.get("unknown_count"),
    }
    counts_consistent = None
    if declared_counts:
        counts_consistent = all(
            declared_counts.get(key) == value
            for key, value in live_counts.items()
        )
    state = "CONSISTENT" if (
        all(p["state"] == "CONSISTENT" for p in pairs)
        and counts_consistent is not False
    ) else "UNRECONCILED"
    return {
        "state": state,
        "pairs": pairs,
        "account_routing_counts": {
            "config_declared": declared_counts or None,
            "live": live_counts,
            "consistent": counts_consistent,
        },
        "note": "config/financial_connectivity.json governs payment routing; account_routing.py governs account identity. A disagreement is shown, never silently resolved.",
    }


def _settlement_routes(routing_doc, providers):
    treasury = routing_doc.get("treasury") or {}
    hub = routing_doc.get("hub") or {}
    fallbacks = routing_doc.get("fallbacks") or {}
    badr = providers.get("badr") or {}
    paypal = providers.get("paypal") or {}
    wise = fallbacks.get("wise") or {}
    redotpay = fallbacks.get("redotpay") or {}
    return [
        {
            "route": "badr",
            "role": treasury.get("role") or "FINAL_TREASURY",
            "currency": treasury.get("currency"),
            "policy_status": treasury.get("status"),
            "status": badr.get("status", "UNKNOWN"),
            "reason": "Founder-confirmed treasury; settlement is verified only when a real bank record exists.",
        },
        {
            "route": "payoneer",
            "role": hub.get("role") or "PRIMARY_DIGITAL_FINANCIAL_HUB_WHERE_SUPPORTED",
            "verification": hub.get("verification"),
            "status": "UNKNOWN",
            "reason": "Canonical hub where supported; verification is pending and no balance/transfer API is integrated.",
        },
        {
            "route": "paypal",
            "role": (fallbacks.get("paypal") or {}).get("role") or "FALLBACK_EXCEPTION_ONLY",
            "status": paypal.get("status", "UNKNOWN"),
            "reason": "Fallback only; never the Gumroad route. Receiving in Algeria is conditional on PayPal's own requirements.",
        },
        {
            "route": "wise",
            "role": wise.get("role") or "FALLBACK_EXCEPTION_ONLY",
            "status": "NOT_CONFIGURED",
            "reason": wise.get("used_when") or "No route is configured.",
        },
        {
            "route": "redotpay",
            "role": redotpay.get("role") or "FALLBACK_EXCEPTION_ONLY",
            "status": "NOT_CONFIGURED",
            "reason": redotpay.get("status") or "Absent.",
        },
    ]


def _financial_truth_consistency(routing_doc, sales):
    truth = routing_doc.get("financial_truth") or {}
    declared = truth.get("real_revenue_usd")
    cents = sales.get("verified_revenue_cents")
    verified = round(cents / 100, 2) if isinstance(cents, (int, float)) else None
    consistent = None
    if isinstance(declared, (int, float)) and verified is not None:
        consistent = round(float(declared), 2) == verified
    return {
        "config_declared_real_revenue_usd": declared,
        "ledger_verified_revenue_usd": verified,
        "consistent": consistent,
        "note": "The routing config is static; a mismatch means it is stale relative to the commission ledger, not that revenue was created.",
    }


def credential_presence(spec, env=None, env_path=None):
    required = list(spec.get("required_credentials") or ())
    optional = list(spec.get("optional_credentials") or ())
    names = required + optional
    presence = {name: _configured(name, env, env_path) for name in names}
    missing = [name for name in required if not presence.get(name)]
    return {
        "required": required,
        "optional": optional,
        "present": presence,
        "missing_required": missing,
        "configured": not missing if required else True,
    }


def _amount_cents(event):
    platform = event.get("platform")
    raw = event.get("raw") if isinstance(event.get("raw"), dict) else {}
    if CHANNEL_LEDGER is not None and hasattr(CHANNEL_LEDGER, "_extract_sale_amount"):
        try:
            value = CHANNEL_LEDGER._extract_sale_amount(raw, platform)
        except Exception:
            value = None
        if value is not None:
            return round(float(value) * 100)
    return None


def _fee_cents(event):
    raw = event.get("raw") if isinstance(event.get("raw"), dict) else {}
    value = raw.get("fees")
    if isinstance(value, dict):
        value = value.get("total")
    try:
        if value is None or isinstance(value, bool):
            return None
        return round(float(value) * 100)
    except (TypeError, ValueError):
        return None


def _is_test_event(event):
    raw = event.get("raw") if isinstance(event.get("raw"), dict) else {}
    values = [
        event.get("environment"), event.get("mode"),
        raw.get("environment"), raw.get("mode"), raw.get("test"),
    ]
    for value in values:
        if isinstance(value, bool):
            if value:
                return True
            continue
        if str(value or "").strip().upper() in TEST_ENVIRONMENTS:
            return True
    return False


def _external_id(event):
    raw = event.get("raw") if isinstance(event.get("raw"), dict) else {}
    for value in (
        raw.get("id"), raw.get("sale_id"), raw.get("transaction_id"),
        event.get("external_transaction_id"), event.get("transaction_id"),
    ):
        if value:
            return str(value)
    return None


def sales_summary(ledger_path, commission_path):
    if CHANNEL_LEDGER is None:
        raise RuntimeError("channels.ledger is unavailable; refusing to report zero revenue")
    events = list(CHANNEL_LEDGER.read_events(event_type="sale", ledger_path=ledger_path))
    seen = set()
    orders = []
    duplicates = 0
    test_rows = 0
    unidentified = 0
    for event in events:
        if _is_test_event(event):
            test_rows += 1
            continue
        external_id = _external_id(event)
        key = f"{event.get('platform')}:{external_id}" if external_id else f"unidentified:{len(orders)}"
        if external_id and key in seen:
            duplicates += 1
            continue
        if external_id:
            seen.add(key)
        else:
            unidentified += 1
        orders.append({
            "platform": event.get("platform") or "UNKNOWN",
            "external_id": external_id,
            "external_id_available": external_id is not None,
            "gross_cents": _amount_cents(event),
            "fee_cents": _fee_cents(event),
            "currency": CURRENCY,
            "timestamp": event.get("timestamp"),
            "attribution": {
                key: event.get(key) for key in ("country", "channel", "campaign", "partner", "customer_segment")
                if event.get(key) is not None
            } or None,
        })

    priced = [o for o in orders if o["gross_cents"] is not None]
    unpriced = len(orders) - len(priced)
    gross_complete = unpriced == 0
    gross = sum(o["gross_cents"] for o in priced) if gross_complete else None
    if not orders:
        fees_known = True
        fees = 0
    else:
        fees_known = all(o["fee_cents"] is not None for o in orders)
        fees = sum(o["fee_cents"] for o in orders) if fees_known else None
    net = round(gross - fees) if gross is not None and fees is not None else None

    commissions = []
    for row in _read_jsonl(commission_path):
        status = row.get("commission_status") or row.get("status")
        if str(row.get("environment") or "").upper() != "REAL":
            continue
        if status not in ("CONFIRMED", "PAID"):
            continue
        amount = row.get("net_commission")
        if amount is None:
            amount = row.get("amount_usd")
        try:
            cents = round(float(amount) * 100)
        except (TypeError, ValueError):
            continue
        commissions.append({"commission_id": row.get("commission_id"), "net_cents": cents})
    commission_cents = sum(c["net_cents"] for c in commissions)

    verified = None
    if gross is not None:
        verified = gross + commission_cents

    by_platform = {}
    for order in orders:
        bucket = by_platform.setdefault(order["platform"], {"orders": 0, "gross_cents": 0, "unpriced_orders": 0})
        bucket["orders"] += 1
        if order["gross_cents"] is None:
            bucket["unpriced_orders"] += 1
        else:
            bucket["gross_cents"] += order["gross_cents"]
    for bucket in by_platform.values():
        if bucket["unpriced_orders"]:
            bucket["gross_cents"] = None

    return {
        "currency": CURRENCY,
        "orders_count": len(orders),
        "orders": orders,
        "by_platform": by_platform,
        "gross_revenue_cents": gross,
        "gross_complete": gross_complete,
        "unpriced_orders": unpriced,
        "fees_cents": fees,
        "fees_complete": fees_known,
        "net_revenue_cents": net,
        "net_state": "OBSERVED" if net is not None else "UNKNOWN",
        "commission_revenue_cents": commission_cents,
        "commission_rows": commissions,
        "verified_revenue_cents": verified,
        "verified_definition": "Real sale gross + REAL commissions that reached CONFIRMED or PAID. Fees/net remain UNKNOWN unless every order carries its own fee. TEST/SANDBOX/SIMULATION rows are excluded.",
        "excluded_test_rows": test_rows,
        "duplicate_rows_skipped": duplicates,
        "unidentified_external_ids": unidentified,
    }


def _evidence_text(value):
    return str(value or "").strip().upper()


def _provider_state(key, spec, presence, connectivity, sales, settlement):
    evidence = connectivity.get(key) if isinstance(connectivity, dict) else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    api_text = _evidence_text(evidence.get("api"))
    checkout_text = _evidence_text(evidence.get("checkout"))
    payout_text = _evidence_text(evidence.get("payouts"))
    webhook_text = _evidence_text(evidence.get("webhook"))
    real_orders = sum(b["orders"] for p, b in sales["by_platform"].items() if p == key)
    configured = presence["configured"]
    blockers = []

    if key == "stripe":
        status = "BLOCKED_BY_PROVIDER_ELIGIBILITY"
        reason = spec["eligibility"]
        if not configured:
            blockers.append("Credentials are absent, but credentials alone would not clear the eligibility block.")
        blockers.append("Direct Stripe activation for Algeria is not supported by Stripe's official country list.")
    elif key == "badr":
        verified = settlement.get("verified_count", 0)
        status = "SETTLEMENT_VERIFIED" if verified else "UNKNOWN"
        reason = (
            f"{verified} verified bank settlement(s) recorded."
            if verified else
            "SETTLEMENT_ONLY: no official API, no authorized credential, and no verified settlement record."
        )
        if not verified:
            blockers.append("Record a real bank settlement before treating BADR as verified.")
    elif real_orders:
        status = "PAYMENT_CAPABLE"
        reason = f"{real_orders} real order(s) observed, but settlement is not verified."
        if not configured:
            blockers.append("A real order exists, but the credential needed to read it is absent.")
        blockers.append("A real order does not prove payout settlement.")
    elif key == "paddle" and ("BLOCKED" in checkout_text or "NOT_CONFIGURED" in webhook_text):
        status = "CONNECTED_READ_ONLY"
        reason = "API key is present and reads were observed, but checkout is blocked or the webhook is not configured."
        blockers.append("Complete Paddle onboarding and configure the webhook before treating checkout as capable.")
    elif not configured:
        status = "NOT_CONFIGURED"
        reason = "Required credential name(s) are absent. Presence is checked without reading any value."
        blockers.append("Configure credentials through the founder-controlled environment.")
    elif "CONNECTED" in api_text or "LIVE" in checkout_text:
        status = "CONFIGURED_NOT_VERIFIED"
        reason = "Credentials and/or a listing are observed, but no completed real payment verifies payment capability."
        blockers.append("A completed real payment is required before PAYMENT_CAPABLE.")
    else:
        status = "CONFIGURED_NOT_VERIFIED"
        reason = "Credentials are present; no payment or settlement evidence is recorded."
        blockers.append("Run a founder-authorized real verification before upgrading this status.")

    if any(marker in api_text for marker in (
        "401", "403", "AUTHENTICATION_FAILED", "AUTHENTICATION FAILED", "AUTH FAILED", "UNAUTHORIZED",
    )):
        status = "AUTHENTICATION_FAILED"
        reason = "Recorded provider evidence reports an authentication failure."
        blockers.append("Re-authorize the provider outside this read model.")

    return {
        "status": status,
        "status_reason": reason,
        "account_evidence": evidence or None,
        "api_state": api_text or "UNKNOWN",
        "checkout_state": checkout_text or "UNKNOWN",
        "payout_state": payout_text or "UNKNOWN",
        "webhook_state": webhook_text or "UNKNOWN",
        "executed_orders": real_orders,
        "blockers": blockers,
    }


def provider_report(key, env=None, env_path=None, connectivity=None, sales=None, settlement=None, evidence_freshness=None, routing_policy=None, account_route=None):
    spec = PROVIDER_SPECS[key]
    presence = credential_presence(spec, env=env, env_path=env_path)
    state = _provider_state(key, spec, presence, connectivity or {}, sales or sales_summary_empty(), settlement or {})
    return {
        "provider": key,
        "display_name": spec["display_name"],
        "provider_type": spec["provider_type"],
        "role": spec["role"],
        "status": state["status"],
        "status_reason": state["status_reason"],
        "credential_presence": presence["present"],
        "credentials_required": bool(presence["required"]),
        "missing_credentials": presence["missing_required"],
        "configured": presence["configured"],
        "api_available": spec["api_available"],
        "settlement_model": spec["settlement_model"],
        "currencies": list(spec["currencies"]),
        "currency_note": spec.get("currency_note", "Observed from recorded listings."),
        "official_docs": spec["official_docs"],
        "fees_source": spec["fees_source"],
        "eligibility": spec["eligibility"],
        "api_state": state["api_state"],
        "checkout_state": state["checkout_state"],
        "payout_state": state["payout_state"],
        "webhook_state": state["webhook_state"],
        "executed_orders": state["executed_orders"],
        "evidence_freshness": evidence_freshness or {"state": "UNKNOWN"},
        "routing_policy": routing_policy,
        "account_routing": account_route,
        "blockers": state["blockers"],
    }


def sales_summary_empty():
    return {
        "by_platform": {}, "orders_count": 0, "orders": [],
        "gross_revenue_cents": 0, "gross_complete": True, "unpriced_orders": 0,
        "fees_cents": None, "fees_complete": False, "net_revenue_cents": None,
        "net_state": "UNKNOWN", "commission_revenue_cents": 0, "commission_rows": [],
        "verified_revenue_cents": 0, "verified_definition": "", "excluded_test_rows": 0,
        "duplicate_rows_skipped": 0, "unidentified_external_ids": 0,
    }


def settlement_summary(path):
    rows = _read_jsonl(path)
    verified = [r for r in rows if r.get("status") == "SETTLEMENT_VERIFIED"]
    observed = [r for r in rows if r.get("status") == "OBSERVED"]
    mismatched = [r for r in rows if r.get("status") == "MISMATCH"]
    currencies = sorted({str(r.get("currency")).upper() for r in rows if r.get("currency")})
    total = 0
    for row in verified:
        try:
            total += int(row.get("net_cents", row.get("amount_cents", 0)))
        except (TypeError, ValueError):
            pass
    same_currency = len(currencies) <= 1
    return {
        "mode": "SETTLEMENT_ONLY",
        "entries_count": len(rows),
        "verified_count": len(verified),
        "observed_count": len(observed),
        "mismatch_count": len(mismatched),
        "verified_net_cents": total if verified and same_currency else None,
        "currency": currencies[0] if len(currencies) == 1 else ("MIXED" if currencies else None),
        "note": "Bank settlements are recorded only after a real transfer is observed. No transfer is initiated here.",
    }


def _channel_state(key, provider_states, product_counts, sales):
    published = product_counts.get(key, {}).get("published", 0)
    orders = sales["by_platform"].get(key, {}).get("orders", 0)
    if key == "etsy":
        return "BLOCKED", CHANNEL_SPECS[key]["eligibility"]
    if key == "payhip":
        return "NOT_IMPLEMENTED", CHANNEL_SPECS[key]["eligibility"]
    if key == "amazon_kdp":
        return "MANUAL_UPLOAD_ONLY", CHANNEL_SPECS[key]["eligibility"]
    if key == "shopify":
        return "NOT_CONFIGURED", CHANNEL_SPECS[key]["eligibility"]
    if key == "paypal_storefront":
        state = provider_states.get("paypal", {}).get("status")
        return ("NOT_CONFIGURED" if state == "NOT_CONFIGURED" else "PARTIAL"), "PayPal is a payment rail, not a verified storefront."
    if key == "paddle":
        state = provider_states.get("paddle", {}).get("status")
        return ("BLOCKED" if state == "CONNECTED_READ_ONLY" else "PARTIAL"), "Paddle checkout depends on provider onboarding."
    if key == "direct_website":
        return "PARTIAL", "The site exists; checkout depends on Paddle/PayPal."
    if key == "gumroad":
        if orders:
            return "SALES_OBSERVED", f"{orders} real order(s) observed."
        if published:
            return "PUBLIC_LISTING_ONLY", f"{published} published listing(s); no completed sale recorded."
        return "NOT_CONFIGURED", "No published Gumroad listing observed."
    return "UNKNOWN", "No channel evidence."


def channel_report(product_counts, sales, provider_states):
    channels = []
    for key, spec in CHANNEL_SPECS.items():
        counts = product_counts.get(key, {"products": 0, "published": 0})
        state, reason = _channel_state(key, provider_states, product_counts, sales)
        platform_sales = sales["by_platform"].get(key, {"orders": 0, "gross_cents": 0, "unpriced_orders": 0})
        channels.append({
            "channel": key,
            "display_name": spec["display_name"],
            "channel_type": spec["channel_type"],
            "provider": spec["provider"],
            "state": state,
            "reason": reason,
            "api_available": spec["api_available"],
            "storefront": spec["storefront"],
            "product_count": counts["products"],
            "published_count": counts["published"],
            "real_orders": platform_sales["orders"],
            "gross_revenue_cents": platform_sales["gross_cents"],
            "unpriced_orders": platform_sales["unpriced_orders"],
            "checkout_state": (
                provider_states.get(spec["provider"], {}).get("checkout_state")
                if spec.get("provider") else "NOT_APPLICABLE"
            ),
            "eligibility": spec["eligibility"],
        })
    return channels


def _product_counts(registry, paddle_products):
    counts = {key: {"products": 0, "published": 0} for key in CHANNEL_SPECS}
    for product in (registry or {}).get("products", []) if isinstance(registry, dict) else []:
        ids = product.get("external_ids") if isinstance(product.get("external_ids"), dict) else {}
        for platform in ids:
            key = "amazon_kdp" if platform == "kdp" else platform
            if key in counts:
                counts[key]["products"] += 1
                if product.get("published") is True:
                    counts[key]["published"] += 1
    if isinstance(paddle_products, list):
        counts["paddle"]["products"] += len(paddle_products)
    return counts


def record_bank_settlement(settlement, path=None):
    required = ("settlement_id", "amount_cents", "currency", "settlement_date")
    missing = [field for field in required if settlement.get(field) in (None, "")]
    if missing:
        raise ValueError(f"missing required settlement fields: {', '.join(missing)}")
    status = settlement.get("status", "OBSERVED")
    if status not in SETTLEMENT_STATES:
        raise ValueError(f"status must be one of {SETTLEMENT_STATES}")
    try:
        amount = int(settlement["amount_cents"])
    except (TypeError, ValueError):
        raise ValueError("amount_cents must be an integer")
    if amount < 0:
        raise ValueError("amount_cents cannot be negative")
    row = {
        "settlement_id": str(settlement["settlement_id"]),
        "bank": settlement.get("bank", "BADR"),
        "amount_cents": amount,
        "currency": str(settlement["currency"]).upper(),
        "settlement_date": settlement["settlement_date"],
        "transfer_reference": settlement.get("transfer_reference"),
        "fees_cents": settlement.get("fees_cents"),
        "status": status,
        "evidence": settlement.get("evidence"),
        "recorded_at": _now_iso(),
    }
    if row["fees_cents"] is not None:
        try:
            fees = int(row["fees_cents"])
        except (TypeError, ValueError):
            raise ValueError("fees_cents must be an integer")
        row["net_cents"] = amount - fees
    path = Path(path) if path else _FACTORY_ROOT / "data" / "bank_settlements.jsonl"
    for existing in _read_jsonl(path):
        if existing.get("settlement_id") == row["settlement_id"]:
            return {"recorded": False, "reason": "DUPLICATE", "settlement_id": row["settlement_id"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"recorded": True, "settlement": row}


def build_financial_connectivity_snapshot(root=None, env=None, env_path=None, now=None):
    root = Path(root) if root else _FACTORY_ROOT
    data = Path(root) / "data"
    connectivity_doc = _read_json(data / "payment_connectivity.json") or {}
    connectivity = connectivity_doc.get("connections", {})
    routing_doc = _read_json(Path(root) / ROUTING_CONFIG_REL) or {}
    account_routing = _account_routing_summary()
    account_routes = {route.get("platform"): route for route in account_routing.get("routes") or []}
    registry = _read_json(data / "product_registry.json") or {}
    paddle_products = _read_json(data / "paddle_products.json") or []
    ledger_path = data / "sales_ledger.jsonl"
    commission_path = data / "commission_ledger.jsonl"
    settlement_path = data / "bank_settlements.jsonl"

    sales = sales_summary(ledger_path, commission_path)
    settlement = settlement_summary(settlement_path)
    evidence_freshness = _freshness(connectivity_doc.get("at"), now=now)
    providers = {}
    for key in PROVIDER_ORDER:
        providers[key] = provider_report(
            key, env=env, env_path=env_path, connectivity=connectivity,
            sales=sales, settlement=settlement, evidence_freshness=evidence_freshness,
            routing_policy=_provider_routing(key, routing_doc),
            account_route=account_routes.get(key),
        )
    product_counts = _product_counts(registry, paddle_products)
    channels = channel_report(product_counts, sales, providers)

    verified_revenue = sales["verified_revenue_cents"]
    no_rail = [p["provider"] for p in providers.values() if p["status"] in ("PAYMENT_CAPABLE", "SETTLEMENT_VERIFIED")]
    founder_actions = []
    for provider in providers.values():
        for blocker in provider["blockers"]:
            action = f"{provider['display_name']}: {blocker}"
            if action not in founder_actions:
                founder_actions.append(action)
    if not no_rail:
        founder_actions.append("No payment rail or bank settlement is verified end-to-end yet.")
    if sales["orders_count"] == 0:
        founder_actions.append("Zero real orders exist; no channel has reached PAYMENT_CAPABLE.")
    founder_actions = list(dict.fromkeys(founder_actions))

    return {
        "generated_at": _now_iso(now),
        "mode": "READ_ONLY",
        "network_calls": 0,
        "writes": 0,
        "currency": CURRENCY,
        "status_vocabulary": list(STATUS),
        "evidence_freshness": evidence_freshness,
        "providers": providers,
        "channels": channels,
        "sales": sales,
        "settlements": settlement,
        "product_counts": product_counts,
        "routing": {
            "source": ROUTING_CONFIG_REL,
            "version": routing_doc.get("version"),
            "updated": routing_doc.get("updated"),
            "hard_stop_active": routing_doc.get("hard_stop_active"),
            "governance": routing_doc.get("governance"),
            "treasury": _public_mapping(routing_doc.get("treasury")),
            "hub": _public_mapping(routing_doc.get("hub")),
            "fallbacks": _public_mapping(routing_doc.get("fallbacks")),
            "ledger_requirements": (routing_doc.get("ledger") or {}).get("minimum_fields") or [],
            "platform_policies": {
                key: _public_mapping(_provider_routing(key, routing_doc))
                for key in routing_doc.get("platform_classification", {})
            },
        },
        "settlement_routes": _settlement_routes(routing_doc, providers),
        "account_routing": account_routing,
        "routing_consistency": _routing_consistency(routing_doc, account_routing),
        "financial_truth_consistency": _financial_truth_consistency(routing_doc, sales),
        "unified_financial_state": {
            "state": "ZERO_VERIFIED_REVENUE" if not verified_revenue else "VERIFIED_REVENUE_OBSERVED",
            "verified_revenue_cents": verified_revenue,
            "orders_count": sales["orders_count"],
            "gross_revenue_cents": sales["gross_revenue_cents"],
            "net_revenue_cents": sales["net_revenue_cents"],
            "settled_cents": settlement["verified_net_cents"],
            "available_payment_rails": no_rail,
            "revenue_verified": bool(verified_revenue and verified_revenue > 0),
            "reason": (
                "No transaction has been observed, so no provider may be called payment-capable."
                if sales["orders_count"] == 0 else
                "Real orders exist, but full fees and settlement may still be unknown."
            ),
        },
        "founder_actions": founder_actions,
        "sources": [
            _source(data / "payment_connectivity.json", root),
            _source(Path(root) / ROUTING_CONFIG_REL, root),
            _source(Path(root) / "account_routing.py", root),
            _source(data / "product_registry.json", root),
            _source(data / "paddle_products.json", root),
            _source(ledger_path, root),
            _source(commission_path, root),
            _source(settlement_path, root),
        ],
        "reused": [
            "channels.ledger.read_events/_extract_sale_amount",
            "channels.env_config.read_env_value (presence only)",
            "config/financial_connectivity.json (canonical payment routing policy)",
            "account_routing.py (authoritative account/payout identity, non-secret)",
            "data/payment_connectivity.json",
            "data/product_registry.json",
            "data/paddle_products.json",
            "data/commission_ledger.jsonl",
        ],
        "disclosures": [
            "Credential values are never read into this report; only presence booleans are returned.",
            "A configured credential is CONFIGURED_NOT_VERIFIED, not PAYMENT_CAPABLE.",
            "A published listing is PUBLIC_LISTING_ONLY, not revenue.",
            "Stripe's Algeria block is cited from https://stripe.com/global (accessed 2026-10-24).",
            "PayPal's Algeria receive terms cite its official Receive Funds and Automatic Transfer Agreement (updated 2026-09-22).",
            "BADR is settlement-only; this module cannot and does not initiate a transfer.",
            "Payment routing is cited from config/financial_connectivity.json; account identity is cited from account_routing.py. A disagreement is shown as UNRECONCILED, never silently resolved.",
        ],
    }


def main():
    print(json.dumps(build_financial_connectivity_snapshot(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
