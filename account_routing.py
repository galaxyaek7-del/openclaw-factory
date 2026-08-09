"""Account Routing & Payment Identity Policy (ADR-241, 2026-08-09).

Answers the founder's explicit "Account Routing & Payment Identity Policy"
directive: make Galaxy Forge permanently aware of which commercial-account
identity owns each platform, so opportunity discovery, the affiliate/
commission engine, the revenue ledger, and any future publishing adapter
never have to guess -- and never do.

This module is the single, authoritative, read-only source of truth for
platform -> commercial_identity -> payout_identity -> status. It holds only
non-secret routing metadata (email addresses the founder has already
disclosed as real account identities, never passwords, API keys, tokens,
or any other secret). It performs zero I/O, zero network calls, zero
subprocess calls -- it cannot register an account, connect a payment
method, send outreach, or trigger any transaction, by construction, not
by a runtime check.

Design principle, stated by the founder and enforced here literally: the
factory must never INFER account ownership from opportunity data (niche,
commission rate, country, product type, etc.). Account routing is
authoritative configuration -- a platform is either explicitly listed
below (added by a human, following a real, disclosed founder instruction)
or it is UNKNOWN. There is no fuzzy/substring matching anywhere in this
module; "amazon-something-else" does NOT route to the Amazon identity
just because the string contains "amazon".

Relationship to OpenClaw_Brain/00_Governance/IDENTITY_ARCHITECTURE.md
(2026-07-11, ADR-014/ADR-015): that document is real infrastructure-tool
identity (GitHub, Groq, Anthropic, n8n-as-automation-tool) and stated "no
documented exception to date" to the single-account model. This module
governs a narrower, distinct, real exception the founder disclosed
2026-08-09: Amazon/KDP + Payoneer use a second real email
(aekgalaxy47@gmail.com), while every other commercial platform continues
to use the original identity (galaxyaek7@gmail.com). See that document's
own §1 for a cross-reference note added alongside this module.
"""

from __future__ import annotations

# ── Real, founder-disclosed identities (non-secret account routing
# metadata only -- email addresses, never passwords/tokens/keys). ──
AMAZON_KDP_IDENTITY = "aekgalaxy47@gmail.com"
PAYONEER_IDENTITY = "aekgalaxy47@gmail.com"
PRIMARY_COMMERCIAL_IDENTITY = "galaxyaek7@gmail.com"

VERIFIED = "VERIFIED"
UNKNOWN = "UNKNOWN"
BLOCKED = "BLOCKED"

# Category "amazon_kdp": Amazon/KDP identity + real, founder-confirmed
# Payoneer payout identity. The ONLY category with a fully VERIFIED
# overall status today, because it is the only one where the founder
# explicitly confirmed both the commercial AND payout identity.
_AMAZON_KDP_PLATFORMS = {
    "amazon",
    "amazon_kdp",
    "kdp",
    "amazon_associates",
    "CO-amazon-affiliate",  # real commission_engine.py opportunity_id
}

# Category "non_amazon_commercial": every other real commercial/affiliate
# platform this factory currently touches, explicitly classified by the
# founder's own general rule ("Gumroad, affiliate platforms and commercial
# platforms other than Amazon/KDP, digital-product marketplaces"). Routed
# to the primary commercial identity. Payout method is honestly UNKNOWN
# for every one of these -- the founder was explicit: do not assume
# Payoneer, do not assume any payout method, until separately verified.
_NON_AMAZON_COMMERCIAL_PLATFORMS = {
    # Already real, live-integrated commission_engine.py opportunities
    "gumroad", "CO-gumroad-affiliate", "CO-gumroad-marketplace",
    "paddle", "CO-paddle-partnership",
    "etsy", "CO-etsy-affiliate", "CO-etsy-marketplace",
    "creative_market", "CO-creative_market-affiliate",
    "envato", "CO-envato-affiliate",
    "adobe", "CO-adobe-affiliate",
    "google", "google_workspace", "CO-google-affiliate",
    "canva", "CO-canva-affiliate",
    "zapier", "CO-zapier-affiliate",
    "n8n", "CO-n8n-affiliate",
    # Real, externally-researched this session, not yet integrated into
    # commission_engine.py's live portfolio -- still explicitly
    # classified here so a future integration never has to guess.
    "nordvpn", "nordpass", "kinsta", "systeme_io", "hubspot",
    "cloudways", "pipedrive",
}

# Category "payment_infrastructure": not a sales platform -- a payout
# rail. Payoneer itself is explicitly tied to the Amazon/KDP identity per
# the founder's policy, and ONLY that identity, until the founder
# separately verifies another platform uses it.
_PAYMENT_INFRASTRUCTURE_PLATFORMS = {
    "payoneer",
}


def _normalize(platform_id):
    return (platform_id or "").strip()


def route_platform(platform_id):
    """Return the authoritative routing record for one platform.

    Never raises, never guesses, never infers from anything other than
    this module's own explicit, founder-declared classification tables.
    An unlisted platform is honestly BLOCKED, not silently assigned an
    identity -- exactly the "never register a new platform automatically,
    never guess" rule the founder stated.
    """
    key = _normalize(platform_id)

    if key in _AMAZON_KDP_PLATFORMS:
        return {
            "platform": platform_id,
            "category": "amazon_kdp",
            "commercial_identity": AMAZON_KDP_IDENTITY,
            "commercial_identity_status": VERIFIED,
            "payout_identity": PAYONEER_IDENTITY,
            "payout_method": "Payoneer",
            "payout_status": VERIFIED,
            "status": VERIFIED,
            "missing_requirements": [],
            "blocking_reason": None,
        }

    if key in _NON_AMAZON_COMMERCIAL_PLATFORMS:
        return {
            "platform": platform_id,
            "category": "non_amazon_commercial",
            "commercial_identity": PRIMARY_COMMERCIAL_IDENTITY,
            "commercial_identity_status": VERIFIED,
            "payout_identity": None,
            "payout_method": UNKNOWN,
            "payout_status": UNKNOWN,
            "status": UNKNOWN,
            "missing_requirements": ["payout_method_verification"],
            "blocking_reason": "Commercial identity is real and founder-confirmed; payout method has not been separately verified for this platform -- never assumed to be Payoneer or any other method.",
        }

    if key in _PAYMENT_INFRASTRUCTURE_PLATFORMS:
        return {
            "platform": platform_id,
            "category": "payment_infrastructure",
            "commercial_identity": None,
            "commercial_identity_status": "NOT_APPLICABLE",
            "payout_identity": PAYONEER_IDENTITY,
            "payout_method": "Payoneer",
            "payout_status": VERIFIED,
            "status": VERIFIED,
            "missing_requirements": [],
            "blocking_reason": None,
        }

    return {
        "platform": platform_id,
        "category": UNKNOWN,
        "commercial_identity": None,
        "commercial_identity_status": UNKNOWN,
        "payout_identity": None,
        "payout_method": UNKNOWN,
        "payout_status": UNKNOWN,
        "status": BLOCKED,
        "missing_requirements": ["explicit_founder_classification"],
        "blocking_reason": "This platform is not present in the authoritative account-routing policy. Per standing policy, an unclassified platform is never guessed -- it requires explicit founder approval and an explicit addition to account_routing.py before any account-identity assumption may be made.",
    }


def account_routing_table():
    """Every explicitly-classified platform's routing record, plus a
    real count of how many are fully VERIFIED vs still UNKNOWN --
    the read-only view Mission Control's account-routing panel and this
    factory's audit reports both consume, never recomputed differently
    in two places."""
    all_platforms = sorted(
        _AMAZON_KDP_PLATFORMS
        | _NON_AMAZON_COMMERCIAL_PLATFORMS
        | _PAYMENT_INFRASTRUCTURE_PLATFORMS
    )
    routes = [route_platform(p) for p in all_platforms]
    verified = [r for r in routes if r["status"] == VERIFIED]
    unknown = [r for r in routes if r["status"] == UNKNOWN]
    return {
        "routes": routes,
        "total_platforms": len(routes),
        "verified_count": len(verified),
        "unknown_count": len(unknown),
        "primary_commercial_identity": PRIMARY_COMMERCIAL_IDENTITY,
        "amazon_kdp_identity": AMAZON_KDP_IDENTITY,
        "payoneer_identity": PAYONEER_IDENTITY,
        "note": "Read-only, non-secret account routing metadata only. This module cannot register an account, connect a payment method, or trigger any transaction -- it has no network, subprocess, or file-write capability at all.",
    }
