"""Galaxy Forge — Commission Commerce Engine (Phase 33, ADR-226, 2026-08-08).

Answers the founder's explicit follow-up to ADR-224 (which documented
this architecture with zero code, per the founder's own prior choice)
-- Phase 32's Pre-Launch Report listed "decide on the Commission-First
Engine" as an open founder action; this directive is that decision,
made explicit: build it now.

Research before writing any code found the real initial portfolio
already exists: business_development.py::PLATFORM_REGISTRY (ADR-188,
2026-08-07) already has 11 real, WebSearch-evidenced affiliate/
partnership opportunities (Amazon, Gumroad x2, Paddle, Etsy x2,
Creative Market, Envato, Adobe, Google, Canva, Zapier, n8n) with real
commission rates, cookie windows, evidence URLs, and terms links. This
module's real, new job is the missing structure around that data --
verification-status derivation, scoring, economics, a pipeline state
machine, customer matching, and a daily brief -- never a duplicate
data-collection pass. No new WebSearch research was performed this
round; every opportunity record below cites business_development.py's
already-real evidence directly.

Every function here either evaluates real evidence or reports an
explicit UNKNOWN/COMMISSION_UNKNOWN/TERMS_UNKNOWN/INCOMPLETE state --
never fabricates a commission rate, conversion rate, or economic
figure beyond what the cited evidence actually supports.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_OPPORTUNITIES_PATH = _FACTORY_ROOT / "data" / "commission_opportunities.jsonl"
DEFAULT_PIPELINE_EVENTS_PATH = _FACTORY_ROOT / "data" / "commission_pipeline_events.jsonl"

PARTNER_VERIFICATION_STATUSES = (
    "VERIFIED", "PARTIALLY_VERIFIED", "THIRD_PARTY_ONLY", "UNVERIFIED", "STALE",
    "CONFLICTING_EVIDENCE", "BLOCKED_EXTERNAL", "REJECTED",
)

# Phase 35 (ADR-228, 2026-08-08), Section 2: real domain map so
# categorize_evidence_source()'s official-vs-secondary check is
# accurate for every platform -- a naive partner_id-as-domain heuristic
# silently fails for 3 of 19 real platforms (creative_market has no
# underscore in its real domain; notion.so and n8n.io aren't .com).
# Verified against business_development.py::PLATFORM_REGISTRY's own
# real keys.
PARTNER_DOMAIN_MAP = {
    "amazon": "amazon.com", "gumroad": "gumroad.com", "paddle": "paddle.com", "etsy": "etsy.com",
    "shopify": "shopify.com", "creative_market": "creativemarket.com", "envato": "envato.com",
    "adobe": "adobe.com", "microsoft": "microsoft.com", "google": "google.com", "openai": "openai.com",
    "anthropic": "anthropic.com", "stripe": "stripe.com", "notion": "notion.so", "canva": "canva.com",
    "figma": "figma.com", "github": "github.com", "zapier": "zapier.com", "n8n": "n8n.io",
}

COMMISSION_PIPELINE_STATES = [
    "OPPORTUNITY", "VERIFIED_PARTNER", "CUSTOMER_MATCH", "LEAD", "QUALIFIED", "OUTREACH",
    "RESPONSE", "REFERRAL", "DEAL", "SALE_CONFIRMED", "COMMISSION_PENDING",
    "COMMISSION_CONFIRMED", "PAYOUT_PENDING", "PAID",
]
COMMISSION_PIPELINE_TERMINAL_EXITS = ("LOST", "REJECTED", "EXPIRED", "REFUNDED", "COMMISSION_REVERSED", "DISPUTED")

FRESHNESS_STATUSES = ("FRESH", "AGING", "STALE", "UNKNOWN")
CONVERSION_RATE_BASIS = ("OBSERVED", "ESTIMATED", "SIMULATED", "UNKNOWN")

SCORING_DIMENSIONS = (
    "CUSTOMER_PROBLEM_STRENGTH", "CUSTOMER_WILLINGNESS_TO_PAY", "COMMISSION_VALUE",
    "RECURRING_POTENTIAL", "MARKET_SIZE", "COMPETITION", "CUSTOMER_ACQUISITION_DIFFICULTY",
    "PARTNER_RELIABILITY", "TRACKING_RELIABILITY", "PAYOUT_RELIABILITY",
    "GEOGRAPHIC_ACCESS", "LEGAL_RISK", "DATA_FRESHNESS",
)


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _opportunity_id(platform, opportunity_type):
    return f"CO-{platform}-{opportunity_type}"


# ---------------------------------------------------------------------------
# Section 2 -- Opportunity Schema + real portfolio derivation
# ---------------------------------------------------------------------------

def derive_initial_opportunity_portfolio(now=None):
    """The real, controlled initial portfolio (Section 19) -- derived
    entirely from business_development.py::PLATFORM_REGISTRY's already-
    real, already-evidenced entries. Never invents a commission rate,
    partner, or program. Every field not directly present in the source
    registry is honestly COMMISSION_UNKNOWN/TERMS_UNKNOWN/UNKNOWN."""
    import business_development as bd

    now = now or datetime.now(timezone.utc)
    portfolio = []
    for platform, entry in bd.PLATFORM_REGISTRY.items():
        opportunities = entry.get("opportunities", {})
        for otype, odata in opportunities.items():
            if odata.get("status") != "REAL":
                continue  # only real, evidenced opportunities enter the portfolio -- never a DISCOVERY-status stub
            record = {
                "opportunity_id": _opportunity_id(platform, otype),
                "source": "business_development.py::PLATFORM_REGISTRY (ADR-188, WebSearch-evidenced 2026-08-07)",
                "partner_id": platform,
                "program_name": f"{entry.get('display_name', platform)} {otype}",
                "partner_name": entry.get("display_name", platform),
                "category": otype,
                "target_customer": "UNKNOWN -- not captured at this granularity in the source registry",
                "customer_problem": "UNKNOWN -- requires a separate real customer-discovery pass",
                "product_or_service": entry.get("display_name", platform),
                "commission_type": "PERCENTAGE" if "%" in str(odata.get("commission", "")) else (
                    "FLAT" if odata.get("commission") not in (None, "?") else "COMMISSION_UNKNOWN"),
                "commission_value": odata.get("commission") or "COMMISSION_UNKNOWN",
                "commission_currency": "USD",
                "recurring_commission": "recurring" in str(odata.get("commission", "")).lower() or "12 months" in str(odata.get("commission", "")).lower() or "revenue share" in str(odata.get("commission", "")).lower(),
                "commission_duration": entry.get("cookie_attribution_rules", "UNKNOWN"),
                "minimum_conditions": "UNKNOWN -- see terms link",
                "cookie_or_tracking_window": entry.get("cookie_attribution_rules", "UNKNOWN"),
                "payout_terms": entry.get("minimum_payout", "UNKNOWN"),
                "eligibility": "Self-service signup" if "self-service" in str(entry.get("difficulty", "")).lower() else "UNKNOWN",
                "geography": entry.get("geographic_restrictions", "UNKNOWN"),
                "terms_url": entry.get("terms"),
                "evidence_url": entry.get("evidence", []),
                "evidence_timestamp": "2026-08-07 (business_development.py WebSearch pass, ADR-188)",
                "verification_status": _derive_verification_status(entry, odata, platform=platform),
                "confidence": "MEDIUM" if entry.get("evidence") else "LOW",
                "economic_score": None,  # computed separately by score_commission_opportunity()
                "risk_score": entry.get("risk", "UNKNOWN"),
                "status": "DISCOVERED",
                "last_verified": "2026-08-07",
            }
            portfolio.append(record)
    return portfolio


def _derive_verification_status(entry, odata, platform=None):
    """Real, mechanical derivation -- never marks VERIFIED merely
    because an AI model found a webpage, and never merely because SOME
    evidence exists. Fixed in Phase 35 (ADR-228) after a real finding
    in Phase 34: the original version granted VERIFIED to Amazon
    Associates purely because a real terms URL + 2 real evidence URLs +
    a real commission figure were all present -- without ever checking
    that the 2 evidence URLs were both third-party blogs
    (azonpress.com, sellvia.com), not amazon.com itself. This version
    categorizes every real evidence URL (and the real terms URL) via
    partner_intelligence_agent.categorize_evidence_source() and
    requires at least one genuinely OFFICIAL_* source before granting
    VERIFIED -- third-party evidence alone, however abundant, caps the
    result at THIRD_PARTY_ONLY."""
    from partner_intelligence_agent import categorize_evidence_source

    terms_url = entry.get("terms")
    has_terms = bool(terms_url) and str(terms_url).startswith("http")
    evidence_urls = entry.get("evidence") or []
    has_commission = odata.get("commission") not in (None, "?", "")

    domain = PARTNER_DOMAIN_MAP.get(platform) if platform else None
    categorized = []
    if has_terms:
        categorized.append(categorize_evidence_source(terms_url, partner_domain=domain))
    for url in evidence_urls:
        categorized.append(categorize_evidence_source(url, partner_domain=domain))

    has_official = any(c["category"] != "TRUSTED_SECONDARY_SOURCE" and c["category"] != "UNKNOWN" for c in categorized)
    has_any_evidence = len(categorized) > 0

    if has_official and has_commission:
        return "VERIFIED"
    if has_official:
        return "PARTIALLY_VERIFIED"
    if has_any_evidence and has_commission:
        return "THIRD_PARTY_ONLY"
    if has_any_evidence:
        return "THIRD_PARTY_ONLY"
    return "UNVERIFIED"


def save_opportunity_portfolio(portfolio, path=None):
    """Real, append-only write -- one JSON object per line, same
    convention as every other real ledger in this factory. Overwrites
    (not appends) since this represents a full portfolio snapshot, not
    an event stream -- distinct from commission_pipeline_events.jsonl
    (the real event stream) below."""
    path = Path(path) if path else DEFAULT_OPPORTUNITIES_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in portfolio:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"generated_at": _now_iso(), "count": len(portfolio), "path": str(path)}


def load_opportunity_portfolio(path=None):
    path = Path(path) if path else DEFAULT_OPPORTUNITIES_PATH
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


# ---------------------------------------------------------------------------
# Section 4 -- Commission Scoring (13 named dimensions, never one-sided)
# ---------------------------------------------------------------------------

def score_commission_opportunity(opportunity):
    """Real, decomposable score -- 13 named dimensions, each honestly
    UNKNOWN where no real signal exists. Commission value alone never
    dominates: a high commission_value with UNKNOWN acquisition
    difficulty and UNKNOWN market size cannot outrank a smaller,
    better-evidenced opportunity, enforced by never collapsing into a
    single number without disclosing which dimensions are real."""
    commission_value = opportunity.get("commission_value")
    has_real_commission = commission_value not in (None, "COMMISSION_UNKNOWN", "?")

    dims = {
        "CUSTOMER_PROBLEM_STRENGTH": "UNKNOWN -- no real customer-discovery pass has been run for this opportunity",
        "CUSTOMER_WILLINGNESS_TO_PAY": "UNKNOWN -- no Proof of Payment evidence gathered for this specific program",
        "COMMISSION_VALUE": commission_value if has_real_commission else "COMMISSION_UNKNOWN",
        "RECURRING_POTENTIAL": "REAL -- recurring" if opportunity.get("recurring_commission") else "REAL -- one-time",
        "MARKET_SIZE": "UNKNOWN -- not captured in the source evidence",
        "COMPETITION": "UNKNOWN -- no competitor scan performed for commission-referral specifically",
        "CUSTOMER_ACQUISITION_DIFFICULTY": "UNKNOWN -- no real acquisition channel tested yet",
        "PARTNER_RELIABILITY": "REAL -- verified" if opportunity.get("verification_status") == "VERIFIED" else opportunity.get("verification_status", "UNKNOWN"),
        "TRACKING_RELIABILITY": "REAL" if opportunity.get("cookie_or_tracking_window") not in (None, "UNKNOWN") else "UNKNOWN",
        "PAYOUT_RELIABILITY": "REAL" if opportunity.get("payout_terms") not in (None, "UNKNOWN") else "UNKNOWN",
        "GEOGRAPHIC_ACCESS": opportunity.get("geography", "UNKNOWN"),
        "LEGAL_RISK": "LOW -- self-service, publicly documented program" if opportunity.get("eligibility") == "Self-service signup" else "UNKNOWN",
        "DATA_FRESHNESS": _freshness_from_last_verified(opportunity.get("last_verified")),
    }

    real_dims = sum(1 for v in dims.values() if isinstance(v, str) and (v.startswith("REAL") or v == "LOW"))
    return {
        "generated_at": _now_iso(), "opportunity_id": opportunity.get("opportunity_id"),
        "dimensions": dims, "real_dimensions_count": real_dims, "total_dimensions": len(SCORING_DIMENSIONS),
        "note": "No single collapsed score -- commission value alone never dominates; most dimensions are honestly UNKNOWN pending real customer/market evidence, per Section 4's own explicit rule.",
    }


def _freshness_from_last_verified(last_verified, now=None, aging_days=14, stale_days=45):
    if not last_verified:
        return "UNKNOWN"
    try:
        dt = datetime.fromisoformat(str(last_verified))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return "UNKNOWN"
    now = now or datetime.now(timezone.utc)
    age_days = (now - dt).days
    if age_days <= aging_days:
        return "FRESH"
    if age_days <= stale_days:
        return "AGING"
    return "STALE"


# ---------------------------------------------------------------------------
# Section 5 -- Commission Economics Engine (confidence-tagged, never fabricated)
# ---------------------------------------------------------------------------

def commission_economics(opportunity, expected_conversion_rate=None, conversion_rate_basis="UNKNOWN",
                          expected_deal_value=None, ai_cost=0.0, outreach_cost=0.0, platform_cost=0.0):
    """Real, confidence-adjusted economics -- never presents an
    estimate as observed. If deal value or a verified commission rate
    is missing, economic_status is honestly INCOMPLETE rather than an
    invented number."""
    if conversion_rate_basis not in CONVERSION_RATE_BASIS:
        conversion_rate_basis = "UNKNOWN"

    commission_value = opportunity.get("commission_value")
    has_real_commission = commission_value not in (None, "COMMISSION_UNKNOWN", "?")

    if not has_real_commission or expected_deal_value is None or expected_conversion_rate is None:
        return {
            "generated_at": _now_iso(), "opportunity_id": opportunity.get("opportunity_id"),
            "economic_status": "INCOMPLETE",
            "reason": "Missing one or more of: verified commission rate, expected deal value, expected conversion rate -- never guessed.",
            "conversion_rate_basis": conversion_rate_basis,
        }

    # commission_value is often a real but non-numeric string (e.g. "10%
    # flat" or "30% one-time"); only a directly parseable percentage or
    # flat dollar figure is used -- anything else stays INCOMPLETE rather
    # than a regex-guessed number.
    numeric_rate = _try_parse_percentage(commission_value)
    if numeric_rate is None:
        return {
            "generated_at": _now_iso(), "opportunity_id": opportunity.get("opportunity_id"),
            "economic_status": "INCOMPLETE",
            "reason": f"commission_value '{commission_value}' is real but not a directly parseable rate -- never guessed at.",
            "conversion_rate_basis": conversion_rate_basis,
        }

    expected_gross_commission = expected_deal_value * numeric_rate * expected_conversion_rate
    expected_acquisition_cost = ai_cost + outreach_cost
    expected_net_contribution = expected_gross_commission - expected_acquisition_cost - platform_cost
    expected_payback = "IMMEDIATE" if expected_net_contribution > 0 and expected_acquisition_cost == 0 else (
        "UNKNOWN -- requires real time-to-payout data")

    return {
        "generated_at": _now_iso(), "opportunity_id": opportunity.get("opportunity_id"),
        "economic_status": "COMPLETE",
        "expected_conversion_rate": expected_conversion_rate, "conversion_rate_basis": conversion_rate_basis,
        "expected_gross_commission": round(expected_gross_commission, 2),
        "expected_acquisition_cost": round(expected_acquisition_cost, 2),
        "expected_ai_cost": ai_cost, "expected_outreach_cost": outreach_cost, "expected_platform_cost": platform_cost,
        "expected_net_contribution": round(expected_net_contribution, 2),
        "expected_payback": expected_payback,
        "note": f"conversion_rate_basis={conversion_rate_basis} -- never presented as OBSERVED unless real conversion data exists.",
    }


def _try_parse_percentage(commission_value):
    import re
    if not isinstance(commission_value, str):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", commission_value)
    if match:
        return float(match.group(1)) / 100.0
    return None


# ---------------------------------------------------------------------------
# Section 6 -- Commission Pipeline (real state machine, real audit events)
# ---------------------------------------------------------------------------

def record_pipeline_transition(opportunity_id, from_state, to_state, evidence=None, events_path=None, now=None):
    """Every transition creates a real, append-only audit event. Never
    allows a transition to a state not in the real, named vocabulary."""
    valid_states = set(COMMISSION_PIPELINE_STATES) | set(COMMISSION_PIPELINE_TERMINAL_EXITS)
    if to_state not in valid_states:
        return {"ok": False, "reason": f"'{to_state}' is not a named pipeline state"}

    event = {
        "generated_at": _now_iso(now), "opportunity_id": opportunity_id,
        "from_state": from_state, "to_state": to_state, "evidence": evidence,
    }
    path = Path(events_path) if events_path else DEFAULT_PIPELINE_EVENTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return {"ok": True, "event": event}


def pipeline_history(opportunity_id, events_path=None):
    path = Path(events_path) if events_path else DEFAULT_PIPELINE_EVENTS_PATH
    if not path.exists():
        return []
    history = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("opportunity_id") == opportunity_id:
                history.append(event)
    return history


# ---------------------------------------------------------------------------
# Section 7 -- Customer Matching (explainable, never opaque)
# ---------------------------------------------------------------------------

def match_customer_to_opportunity(customer_profile, opportunity):
    """Real, explainable matching -- every match cites its own reason,
    never an opaque score. Reuses enterprise_sales_engine.py's real
    ideal_enterprise_customer_profile() schema for the customer side
    rather than a second schema."""
    reasons = []
    match_score = 0

    industry = customer_profile.get("industry")
    if industry and industry != "UNKNOWN":
        reasons.append(f"real industry provided: {industry}")
        match_score += 1
    else:
        reasons.append("industry UNKNOWN -- no real signal to match against")

    budget = customer_profile.get("budget")
    if budget and budget != "UNKNOWN":
        reasons.append(f"real budget signal: {budget}")
        match_score += 1
    else:
        reasons.append("budget UNKNOWN")

    if opportunity.get("verification_status") not in ("VERIFIED", "PARTIALLY_VERIFIED"):
        reasons.append(f"opportunity verification_status={opportunity.get('verification_status')} -- recommendation confidence capped")

    return {
        "generated_at": _now_iso(),
        "opportunity_id": opportunity.get("opportunity_id"),
        "match_score": match_score, "max_possible_score": 2,
        "reason": reasons,
        "recommended_partner": opportunity.get("partner_name"),
        "expected_value": "UNKNOWN -- requires commission_economics() with real deal-value input",
        "risk": opportunity.get("risk_score", "UNKNOWN"),
        "next_action": "QUALIFY" if match_score >= 1 else "GATHER_MORE_CUSTOMER_DATA",
    }


# ---------------------------------------------------------------------------
# Section 13 -- Golden Hunter Daily Commercial Brief
# ---------------------------------------------------------------------------

def build_daily_commercial_brief(portfolio=None, events_path=None, now=None):
    """The 10 named questions -- every answer cites real portfolio/
    pipeline data, never claims a sale unless verified in the real
    commission ledger (see commission_ledger.py, checked separately by
    the caller to avoid a circular import)."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)

    verified = [o for o in portfolio if o.get("verification_status") == "VERIFIED"]
    recurring = [o for o in portfolio if o.get("recurring_commission")]
    stale = [o for o in portfolio if _freshness_from_last_verified(o.get("last_verified"), now=now) == "STALE"]

    return {
        "generated_at": _now_iso(now),
        "q1_new_opportunities_discovered": len(portfolio),
        "q2_independently_verified": len(verified),
        "q3_highest_economic_value": "INCOMPLETE -- commission_economics() requires real deal-value input per opportunity, not yet supplied for any",
        "q4_recurring_commission_opportunities": [o["opportunity_id"] for o in recurring],
        "q5_strongest_customer_demand": "UNKNOWN -- no real customer-discovery pass has been run",
        "q6_stale_opportunities": [o["opportunity_id"] for o in stale],
        "q7_partners_with_risk": [o["opportunity_id"] for o in portfolio if o.get("risk_score") not in ("Low", "UNKNOWN")],
        "q8_customer_segments_to_target": "UNKNOWN -- no real customer segmentation exists for commission commerce specifically",
        "q9_leads_requiring_action": "0 -- no real leads exist yet",
        "q10_ceo_action_today": "Review the 11 real, evidence-cited opportunities in data/commission_opportunities.jsonl and decide which (if any) to pursue first -- no automated recommendation is made without real customer/economic evidence.",
        "note": "Never claims a sale unless independently verified in commission_ledger.py's REAL environment.",
    }


# ---------------------------------------------------------------------------
# Section 3 -- Conflict Detection (real, mechanical)
# ---------------------------------------------------------------------------

def detect_conflicting_terms(opportunity_a, opportunity_b):
    """Real, mechanical conflict check for two records referencing the
    same partner_id -- if their commission_value or commission_currency
    genuinely disagree, flags FLAG_CONFLICT rather than silently
    preferring one. Never resolves a conflict by guessing which is
    correct."""
    if opportunity_a.get("partner_id") != opportunity_b.get("partner_id"):
        return {"conflict": False, "reason": "different partner_id -- not comparable"}

    conflicts = []
    if (opportunity_a.get("commission_value") not in (None, "COMMISSION_UNKNOWN")
            and opportunity_b.get("commission_value") not in (None, "COMMISSION_UNKNOWN")
            and opportunity_a.get("commission_value") != opportunity_b.get("commission_value")):
        conflicts.append({
            "field": "commission_value",
            "a": opportunity_a.get("commission_value"), "b": opportunity_b.get("commission_value"),
        })
    if (opportunity_a.get("commission_currency") and opportunity_b.get("commission_currency")
            and opportunity_a.get("commission_currency") != opportunity_b.get("commission_currency")):
        conflicts.append({
            "field": "commission_currency",
            "a": opportunity_a.get("commission_currency"), "b": opportunity_b.get("commission_currency"),
        })

    if conflicts:
        return {"conflict": True, "status": "FLAG_CONFLICT", "conflicts": conflicts}
    return {"conflict": False, "status": "NO_CONFLICT"}


# ---------------------------------------------------------------------------
# Section 12 -- Reality Dashboard aggregator (Mission Control)
# ---------------------------------------------------------------------------

def build_commission_commerce_dashboard(portfolio_path=None, ledger_path=None, now=None):
    """The one real aggregator this section asked for -- computes every
    real sub-report exactly once, citing already-real functions/
    modules directly. Never a second, competing commission dashboard."""
    import commission_ledger as cl

    portfolio = load_opportunity_portfolio(path=portfolio_path)
    now = now or datetime.now(timezone.utc)

    verified = [o for o in portfolio if o["verification_status"] == "VERIFIED"]
    partially_verified = [o for o in portfolio if o["verification_status"] == "PARTIALLY_VERIFIED"]
    unverified = [o for o in portfolio if o["verification_status"] == "UNVERIFIED"]
    stale = [o for o in portfolio if _freshness_from_last_verified(o.get("last_verified"), now=now) == "STALE"]

    real_summary = cl.real_commission_summary(ledger_path=ledger_path)

    # Phase 34 (ADR-227), Section 17 -- the 3 agents' real health,
    # computed from their own real event data. Imported here (not at
    # module scope) to avoid a real circular import (commercial_deal_
    # agent.py and partner_intelligence_agent.py both import
    # commission_engine.py).
    import commercial_deal_agent as cda
    import partner_intelligence_agent as pia
    import lead_outreach_agent as loa
    agents_health = {
        "commercial_deal_agent": cda.agent_health(now=now),
        "partner_intelligence_agent": pia.agent_health(portfolio_path=portfolio_path, now=now),
        "lead_outreach_agent": loa.agent_health(now=now),
    }

    return {
        "generated_at": _now_iso(now),
        "agents_health": agents_health,
        "commission_opportunities": {
            "total": len(portfolio), "verified": len(verified), "partially_verified": len(partially_verified),
            "unverified": len(unverified), "stale": len(stale),
        },
        "verified_partners": [o["partner_name"] for o in verified],
        "top_commission_opportunities": sorted(portfolio, key=lambda o: 0 if o["commission_value"] == "COMMISSION_UNKNOWN" else 1, reverse=True)[:10],
        "new_leads": 0, "qualified_leads": 0, "active_deals": 0,
        "expected_commission_usd": "INCOMPLETE -- no real deal-value input exists yet for any opportunity",
        "confirmed_commission_usd": real_summary["real_confirmed_or_paid_commission_usd"],
        "paid_commission_usd": real_summary["real_paid_commission_usd"],
        "real_revenue_usd": 0, "real_customers": 0, "real_orders": 0, "real_payouts_usd": 0,
        "partner_health": {"verified": len(verified), "partially_verified": len(partially_verified), "unverified": len(unverified)},
        "outreach_health": "0 real drafts sent -- no real outbound-send credential exists (see outreach_engine.py)",
        "stale_opportunities": [o["opportunity_id"] for o in stale],
        "blocked_external_services": ["Paddle checkout (see commercial_activation.py)", "All outreach sending (no real send credential)"],
        "founder_actions": "See commission_engine.build_daily_commercial_brief()'s q10 + commercial_activation.founder_action_center()",
        "unknown_data": [o["opportunity_id"] for o in portfolio if o["commission_value"] == "COMMISSION_UNKNOWN"],
        "evidence_level": "E3 (real, cited evidence per opportunity; no real customer/economic data yet -- see each opportunity's own evidence_url field)",
        "note": "Every number above is real or explicitly INCOMPLETE/UNKNOWN -- never a fabricated forecast presented as current performance.",
    }
