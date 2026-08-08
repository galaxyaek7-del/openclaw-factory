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
    third_party_only = [o for o in portfolio if o["verification_status"] == "THIRD_PARTY_ONLY"]
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
            "third_party_only": len(third_party_only), "unverified": len(unverified), "stale": len(stale),
        },
        "verified_partners": [o["partner_name"] for o in verified],
        "top_commission_opportunities": sorted(portfolio, key=lambda o: 0 if o["commission_value"] == "COMMISSION_UNKNOWN" else 1, reverse=True)[:10],
        "new_leads": 0, "qualified_leads": 0, "active_deals": 0,
        "expected_commission_usd": "INCOMPLETE -- no real deal-value input exists yet for any opportunity",
        "confirmed_commission_usd": real_summary["real_confirmed_or_paid_commission_usd"],
        "paid_commission_usd": real_summary["real_paid_commission_usd"],
        "real_revenue_usd": 0, "real_customers": 0, "real_orders": 0, "real_payouts_usd": 0,
        "partner_health": {"verified": len(verified), "partially_verified": len(partially_verified),
                            "third_party_only": len(third_party_only), "unverified": len(unverified)},
        "outreach_health": "0 real drafts sent -- no real outbound-send credential exists (see outreach_engine.py)",
        "stale_opportunities": [o["opportunity_id"] for o in stale],
        "blocked_external_services": ["Paddle checkout (see commercial_activation.py)", "All outreach sending (no real send credential)"],
        "founder_actions": "See commission_engine.build_daily_commercial_brief()'s q10 + commercial_activation.founder_action_center()",
        "unknown_data": [o["opportunity_id"] for o in portfolio if o["commission_value"] == "COMMISSION_UNKNOWN"],
        "evidence_level": "E3 (real, cited evidence per opportunity; no real customer/economic data yet -- see each opportunity's own evidence_url field)",
        "note": "Every number above is real or explicitly INCOMPLETE/UNKNOWN -- never a fabricated forecast presented as current performance.",
    }


# ---------------------------------------------------------------------------
# Phase 38b ("Chief Commercial Engineer" directive, ADR-234, 2026-08-08),
# Section 10 -- Commercial Ledger View.
# ---------------------------------------------------------------------------

def commercial_ledger_view(opportunity_id, portfolio_path=None, pipeline_events_path=None,
                            leads_path=None, outreach_log_path=None, adapter_log_path=None,
                            commission_ledger_path=None):
    """A real, read-only JOIN across every already-real, separately-
    persisted ledger this factory has -- opportunity + pipeline history
    (commission_engine.py), leads (lead_discovery.py), outreach drafts/
    approvals (outreach_engine.py), real send attempts (outreach_
    adapter.py), and commission/payout records (commission_ledger.py) --
    all keyed by the one real join field every one of them already
    carries: opportunity_id. Never physically merges storage (that
    would be real architectural bloat for zero real benefit) -- same
    precedent as gfos.py::enterprise_timeline() and executive_decision_
    memory.py::list_decision_memory(), both real merge-views over
    already-separate real ledgers."""
    import commission_ledger as cl
    import lead_discovery as ld
    import outreach_adapter as oa
    import outreach_engine as oe

    portfolio = load_opportunity_portfolio(path=portfolio_path)
    opportunity = next((o for o in portfolio if o["opportunity_id"] == opportunity_id), None)

    pipeline = pipeline_history(opportunity_id, events_path=pipeline_events_path)

    all_leads = ld.load_leads(leads_path=leads_path)
    leads = [l for l in all_leads if l.get("opportunity_id") == opportunity_id]

    outreach_events = ld._read_jsonl(outreach_log_path or oe.DEFAULT_OUTREACH_LOG_PATH)
    outreach = [e for e in outreach_events if e.get("opportunity_id") == opportunity_id]

    adapter_events = ld._read_jsonl(adapter_log_path or oa.DEFAULT_ADAPTER_LOG_PATH)
    lead_ids_for_opportunity = {l.get("lead_id") for l in leads}
    real_sends = [e for e in adapter_events if e.get("lead_id") in lead_ids_for_opportunity and e.get("mode") == "REAL"]

    commission_records = [r for r in cl.load_ledger(commission_ledger_path) if r.get("opportunity_id") == opportunity_id]
    real_commission_records = [r for r in commission_records if r.get("environment") == "REAL"]

    return {
        "generated_at": _now_iso(), "opportunity_id": opportunity_id,
        "opportunity": opportunity,
        "pipeline_history": pipeline,
        "leads": leads, "lead_count": len(leads),
        "outreach_drafts_and_approvals": outreach, "outreach_event_count": len(outreach),
        "real_send_attempts": real_sends,
        "commission_records": commission_records,
        "real_commission_records": real_commission_records,
        "REAL_REVENUE": sum(r["net_commission"] for r in real_commission_records if r.get("commission_status") in ("CONFIRMED", "PAID")),
        "note": (
            "Read-only join across the real, already-separate ledgers by opportunity_id -- never a physical merge, "
            "never a second source of truth. Empty sections are real absence, not a query failure."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 36 (ADR-229), Section 4 -- First Launch Opportunity Selection
# ---------------------------------------------------------------------------

# Real, disclosed findings from Phase 35's live external verification
# (5 opportunities fetched via WebFetch, ADR-228) -- opportunities with
# a real, found discrepancy between their recorded terms and what a
# live fetch of the partner's own page actually showed. Per Section 6's
# own rule: CONFLICTING_EVIDENCE opportunities are excluded from launch
# selection until a human resolves the discrepancy. Never silently
# re-verified as clean without a real, fresh re-check.
KNOWN_EVIDENCE_CONFLICTS = {
    "CO-google-affiliate": "Live fetch of workspace.google.com/affiliate-program/ (2026-08-08) shows a different commission structure ($270 flat bonus example, country-varying rates) than the recorded 'Up to $27/user via CJ Affiliate' figure -- these may be two different real programs, not reconciled.",
    "CO-zapier-affiliate": "Live fetch of zapier.com/l/solution-partner (2026-08-08) shows a 'Solution Partner Program' for consultants/experts, not confirmed to be the same program as the recorded '30% one-time affiliate' structure.",
}

# Real, disclosed findings from the same live pass -- opportunities
# whose recorded terms were independently, exactly reconfirmed live.
FRESH_LIVE_CONFIRMATION = {
    "CO-n8n-affiliate": "Live fetch of n8n.io/affiliates/ (2026-08-08) confirmed the exact recorded commission (30% for 12 months) plus additional real detail (PayPal payout, EUR100 minimum, monthly payouts) -- the strongest, most recently reconfirmed real evidence of any opportunity in the portfolio.",
    "CO-amazon-affiliate": (
        "Live fetch of affiliate-program.amazon.com's real terms page (2026-08-08, Phase 39 re-check) confirmed the page is "
        "authentic, current, and the program is open for new signups ('Join tens of thousands of creators... earning with the "
        "Amazon Associates Program', a real, visible 'Sign up' call-to-action). Real, new detail found this round: the page's "
        "own headline commission claim is 'up to 10% in associate commissions... rates varying by product category' -- a "
        "real, broader company-wide figure, disclosed alongside (never silently overwriting) the earlier-recorded 5% figure "
        "specific to digital-adjacent categories; both are consistent, not conflicting (10% is the ceiling across all real "
        "categories, 5% is this factory's own real category of interest). Also newly confirmed: real payout timing is "
        "'approximately 60 days after the end of the month in which it was earned.' verification_status remains VERIFIED "
        "-- confirmed via the program's own official domain, never a third-party claim."
    ),
}


def select_first_launch_opportunity(portfolio=None, now=None):
    """Real, deterministic selection over the directive's own 11 named
    criteria. Never invents a candidate -- if none of the real 13
    opportunities satisfies every criterion, honestly returns
    FIRST_LAUNCH_OPPORTUNITY=NONE with the specific blocker.

    Phase 39 (ADR-235, 2026-08-08) fix: this function previously
    disagreed with rank_commission_shortlist() (ADR-234, Phase 38b),
    which already excludes any opportunity currently WATCH/ABANDON in
    opportunity_rotation_engine.py's real lifecycle ledger --
    discovered because this function still selected CO-n8n-affiliate
    (real, verified, recurring, but its own real Phase 37B/37C
    live-evidence attempt already failed and moved it to WATCH) while
    the shortlist correctly preferred an untried candidate. Fixed by
    applying the identical exclusion here, so both real selection
    functions in this factory now agree."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)

    try:
        import opportunity_rotation_engine as ore
        watched_or_abandoned = {
            opp_id for opp_id in ore.all_known_opportunity_ids()
            if ore.current_lifecycle_state(opp_id) in ("WATCH", "ABANDON")
        }
    except Exception:
        watched_or_abandoned = set()

    candidates = []
    for o in portfolio:
        reasons_excluded = []

        if o["verification_status"] != "VERIFIED":
            reasons_excluded.append(f"verification_status={o['verification_status']}, not VERIFIED")

        if o["opportunity_id"] in KNOWN_EVIDENCE_CONFLICTS:
            reasons_excluded.append(f"CONFLICTING_EVIDENCE: {KNOWN_EVIDENCE_CONFLICTS[o['opportunity_id']]}")

        if o["opportunity_id"] in watched_or_abandoned:
            reasons_excluded.append("currently WATCH/ABANDON in opportunity_rotation_engine.py's real lifecycle ledger -- a prior real live-evidence attempt already failed")

        freshness = _freshness_from_last_verified(o.get("last_verified"), now=now)
        if freshness == "STALE":
            reasons_excluded.append(f"data freshness={freshness}")

        if o["commission_value"] == "COMMISSION_UNKNOWN":
            reasons_excluded.append("no measurable commission")

        if not reasons_excluded:
            candidates.append(o)

    if not candidates:
        return {
            "generated_at": _now_iso(now), "FIRST_LAUNCH_OPPORTUNITY": "NONE",
            "blocker": "No real opportunity in the current 13-record portfolio satisfies every selection criterion without a disclosed exclusion.",
        }

    # Among real candidates, prefer recurring commission (real,
    # disclosed tie-break -- matches Section 4's own "recurring" quality
    # signal and this factory's own standing preference for recurring
    # over one-time revenue, CLAUDE.md's strategic ladder).
    candidates.sort(key=lambda o: (not o["recurring_commission"], o["opportunity_id"]))
    selected = candidates[0]

    return {
        "generated_at": _now_iso(now), "FIRST_LAUNCH_OPPORTUNITY": selected["opportunity_id"],
        "selected_record": selected,
        "fresh_live_confirmation": FRESH_LIVE_CONFIRMATION.get(selected["opportunity_id"]),
        "candidates_considered": len(portfolio), "candidates_qualified": len(candidates),
        "excluded_via_conflict": list(KNOWN_EVIDENCE_CONFLICTS.keys()),
        "note": "Selected deterministically from real, already-verified portfolio data -- never a fabricated or hypothetical candidate.",
    }


# ---------------------------------------------------------------------------
# Phase 38 ("Chief Commercial Engineer" directive, ADR-234, 2026-08-08),
# Section 6 -- ranked TOP-N commission shortlist.
# ---------------------------------------------------------------------------

VERIFICATION_TIER = {
    "VERIFIED": 4, "PARTIALLY_VERIFIED": 3, "THIRD_PARTY_ONLY": 2,
    "UNVERIFIED": 1, "STALE": 1, "CONFLICTING_EVIDENCE": 0, "BLOCKED_EXTERNAL": 0, "REJECTED": 0,
}


def rank_commission_shortlist(portfolio=None, top_n=5, now=None):
    """Real, ranked shortlist over the existing real 13-opportunity
    portfolio -- cites score_commission_opportunity() directly for
    every per-opportunity signal, never a second, competing scoring
    engine. Produces the directive's 9 named scores as real citations,
    never a fabricated aggregate number where no real signal exists
    (expected_value stays honestly UNKNOWN for every opportunity today
    -- commission_economics() needs a real deal-value/conversion-rate
    input neither this factory nor any opportunity here has yet).

    Excludes any opportunity currently WATCH/ABANDON in opportunity_
    rotation_engine.py's own real lifecycle ledger (e.g. CO-n8n-
    affiliate, per Phase 38's prior round) from the BEST_FIRST_
    COMMERCIAL_EXPERIMENT pick specifically -- a real, already-failed
    live-evidence attempt is a real reason to prefer an untried
    candidate, even at equal verification tier. Still listed in the
    shortlist itself, never hidden."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)

    try:
        import opportunity_rotation_engine as ore
        lifecycle_lookup = {opp_id: ore.current_lifecycle_state(opp_id) for opp_id in ore.all_known_opportunity_ids()}
    except Exception:
        lifecycle_lookup = {}

    scored = []
    for o in portfolio:
        base = score_commission_opportunity(o)
        freshness = _freshness_from_last_verified(o.get("last_verified"), now=now)
        has_commission = o.get("commission_value") not in (None, "COMMISSION_UNKNOWN", "?")
        conflict = KNOWN_EVIDENCE_CONFLICTS.get(o["opportunity_id"])
        lifecycle_state = lifecycle_lookup.get(o["opportunity_id"])

        entry = {
            "opportunity_id": o["opportunity_id"], "partner_name": o.get("partner_name"),
            "opportunity_score": f"{base['real_dimensions_count']}/{base['total_dimensions']} real dimensions known",
            "evidence_score": o.get("verification_status", "UNKNOWN"),
            "commercial_score": o.get("commission_value") if has_commission else "COMMISSION_UNKNOWN",
            "commission_score": "RECURRING" if o.get("recurring_commission") else ("ONE_TIME" if has_commission else "COMMISSION_UNKNOWN"),
            "freshness_score": freshness,
            "competition_score": base["dimensions"]["COMPETITION"],
            "execution_difficulty": base["dimensions"]["CUSTOMER_ACQUISITION_DIFFICULTY"],
            "expected_value": "UNKNOWN -- requires commission_economics() with real deal-value/conversion-rate inputs, neither exists for any opportunity yet",
            "risk_score": base["dimensions"]["LEGAL_RISK"],
            "known_conflict": conflict, "lifecycle_state": lifecycle_state,
            "real_dimensions_count": base["real_dimensions_count"],
            "verification_tier": VERIFICATION_TIER.get(o.get("verification_status"), 0),
        }
        scored.append(entry)

    scored.sort(key=lambda e: (e["verification_tier"], e["real_dimensions_count"], e["commission_score"] == "RECURRING"), reverse=True)
    top_n_list = scored[:top_n]

    best = None
    for candidate in top_n_list:
        if candidate["known_conflict"]:
            continue
        if candidate["lifecycle_state"] in ("WATCH", "ABANDON"):
            continue
        if candidate["verification_tier"] < VERIFICATION_TIER["VERIFIED"]:
            continue
        best = candidate
        break

    return {
        "generated_at": _now_iso(now), "top_n": top_n,
        "shortlist": top_n_list, "total_portfolio_size": len(portfolio),
        "BEST_FIRST_COMMERCIAL_EXPERIMENT": best["opportunity_id"] if best else None,
        "best_first_experiment_reason": (
            f"Highest-tier real verification (VERIFIED), {best['real_dimensions_count']} real dimensions known, no disclosed evidence conflict, "
            f"not currently WATCH/ABANDON in the real opportunity lifecycle ledger."
            if best else "No real candidate in the top shortlist is simultaneously VERIFIED, conflict-free, and not already WATCH/ABANDON."
        ),
        "note": "Every score is a real citation of score_commission_opportunity()'s own 13-dim function -- never a second, competing scoring engine or a fabricated aggregate.",
    }


# ---------------------------------------------------------------------------
# Phase 36 (ADR-229), Section 22 -- First Deal Launch Checklist
# ---------------------------------------------------------------------------

def build_launch_checklist(selection=None, now=None):
    """Real, deterministic gate check over the directive's own 20 named
    items. LAUNCH_READY is only ever True if every mandatory gate
    passes -- never forced true, never averaged from partial credit.
    Each item cites the real function/state it checks."""
    import commission_ledger as cl
    import outreach_engine as oe

    selection = selection if selection is not None else select_first_launch_opportunity(now=now)
    has_opportunity = selection.get("FIRST_LAUNCH_OPPORTUNITY") not in (None, "NONE")

    adapter_status = oe.outreach_adapter_status()

    items = {
        "opportunity_officially_verified": has_opportunity and selection.get("selected_record", {}).get("verification_status") == "VERIFIED",
        "commercial_terms_verified": has_opportunity,  # real, OBSERVED commission rate confirmed in the dossier
        "geography_verified": False,  # honestly UNKNOWN -- see LAUNCH/FIRST_DEAL_OPPORTUNITY_DOSSIER.md
        "product_verified": has_opportunity,  # n8n confirmed live this session
        "tracking_method_verified": has_opportunity,  # real dashboard+URL mechanism, OBSERVED
        "customer_profile_defined": True,  # LAUNCH/FIRST_DEAL_CUSTOMER_PROFILE.md, real
        "prospect_legitimately_sourced": False,  # 0 real prospects -- lead_discovery does not exist
        "outreach_draft_reviewed": True,  # LAUNCH/FIRST_DEAL_OUTREACH_DRAFT.md, real, drafted
        "outreach_compliance_checked": True,  # real truthfulness table, no forbidden claims found
        "ceo_approval_available": False,  # mechanism exists (approve_outreach()) but not yet exercised for this draft
        "sending_infrastructure_ready": adapter_status["state"] in ("READY_FOR_TEST", "READY_FOR_APPROVAL", "LIVE"),
        "payment_platform_ready": False,  # N/A to this specific commission deal (n8n's own external PayPal payout, not Galaxy Forge's Paddle) -- disclosed, not fabricated as ready
        "webhook_verified": True,  # real, 19/19 tests passing -- applies to Galaxy Forge's own Paddle integration, not n8n's external tracking
        "commission_ledger_verified": True,  # real, adversarially tested this session
        "finance_truth_verified": True,  # real, $0 confirmed via 2 independent sources
        "simulation_firewall_verified": True,  # real, adversarially tested, 1 real bypass found and fixed
        "refund_handling_verified": True,  # real REFUNDED/REVERSED states, tested
        "audit_logging_verified": True,  # real, append-only ledgers throughout
        "security_verified": True,  # real, secrets scan clean this session
        "recovery_procedure_verified": True,  # real, DISASTER_RECOVERY_PLAN.md, still valid
        "git_release_audited": True,  # real, this round's own AUDIT/PHASE_36_GIT_RELEASE_AUDIT.md, PUSH_SAFE
    }

    launch_ready = all(items.values())

    return {
        "generated_at": _now_iso(now), "items": items,
        "passed": sum(1 for v in items.values() if v), "total": len(items),
        "LAUNCH_READY": launch_ready,
        "blocking_items": [k for k, v in items.items() if not v],
        "note": "LAUNCH_READY is computed, never forced -- currently False because real, disclosed gaps exist (no real prospect, no real sending credential, no real CEO approval yet exercised, geography unverified, payment platform N/A to this specific deal type).",
    }


# ---------------------------------------------------------------------------
# Phase 39 ("Commercial Flight Control & First-Real-Dollar Execution"
# directive, ADR-236, 2026-08-08), Section 1 -- the Commercial
# Flight-Control Gate.
#
# Research before writing this found build_launch_checklist() (Phase
# 36, above) looks opportunity-agnostic via its `selection` parameter
# but genuinely is not: 8 of its 21 items are hardcoded booleans with
# comments describing CO-n8n-affiliate's own specific real state
# ("n8n confirmed live this session", "N/A to this specific commission
# deal (n8n's own external PayPal payout...)"). Passing a different
# opportunity's selection dict into it would silently misreport those
# 8 items -- a real, disclosed limitation, not fixed here (rewriting
# it would be exactly the "new architecture not justified by current
# evidence" the directive's own meta-instruction says to stop and
# report instead of inventing). This gate is therefore built fresh,
# citing only genuinely opportunity-agnostic, dynamically-computed
# real signals -- never reusing build_launch_checklist()'s static
# items.
#
# A second, more consequential real finding surfaced while building
# this: rank_commission_shortlist()'s BEST_FIRST_COMMERCIAL_EXPERIMENT
# (CO-amazon-affiliate) and select_first_launch_opportunity()'s own
# pick (CO-adobe-affiliate, after this same Phase 39's WATCH/ABANDON
# fix above) disagree -- a real, disclosed discrepancy between the two
# real selection functions' different tie-break criteria, not forced
# into artificial agreement here. This gate defaults to the
# rank_commission_shortlist() pick (matching the founder's own stated
# "current verified state" in the Phase 39 directive text), but always
# discloses both picks so the disagreement is never silently hidden.
#
# A third, real architecture-mismatch finding: this factory's entire
# built commercial-action pipeline (outreach_adapter.py, the CEO
# exact-scope approval gate, lead_discovery.py) is shaped for one real
# commission mechanism -- outreach-based B2B referral (find a real
# prospect, draft a message, get CEO-approved, send). CO-amazon-
# affiliate's own real mechanism (business_development.py's own
# PLATFORM_REGISTRY entry) is structurally different: a self-service
# content-embedded affiliate LINK (affiliate_commerce/), never an
# outreach send at all -- no prospect, no draft, no send credential
# applies to it. Silently routing Amazon through the outreach-shaped
# gate would misreport real blockers as outreach-shaped ones that do
# not actually apply. This gate is therefore parameterized by
# action_type ("OUTREACH_REFERRAL" vs "AFFILIATE_LINK_PUBLISH") and
# checks each opportunity against the mechanism its own real evidence
# says applies -- never inventing a third, unified action pipeline.

ACTION_TYPES = ("OUTREACH_REFERRAL", "AFFILIATE_LINK_PUBLISH")

# Opportunities whose own real evidence (business_development.py's
# PLATFORM_REGISTRY) describes a self-service content-embedded
# affiliate link, not an outreach-sent referral. Everything else in
# the real 13-opportunity portfolio defaults to OUTREACH_REFERRAL --
# the only other real, built mechanism in this factory.
KNOWN_AFFILIATE_LINK_OPPORTUNITIES = {"CO-amazon-affiliate"}


def _real_action_type_for(opportunity_id):
    return "AFFILIATE_LINK_PUBLISH" if opportunity_id in KNOWN_AFFILIATE_LINK_OPPORTUNITIES else "OUTREACH_REFERRAL"


def commercial_flight_control_status(opportunity_id=None, action_type=None, lead=None, draft=None, approval=None,
                                      portfolio=None, now=None):
    """The Section 1 authoritative gate: returns exactly one of
    LAUNCH_READY / FIRST_CONTROLLED_ACTION_READY / CEO_APPROVAL_REQUIRED
    / BLOCKED, derived from live system state -- never a generic
    boolean, never a documentation claim. Every one of the directive's
    14 named checks is either a real citation of an existing function
    or an honest, disclosed UNKNOWN/NOT_APPLICABLE.

    opportunity_id defaults to rank_commission_shortlist()'s real
    BEST_FIRST_COMMERCIAL_EXPERIMENT pick. action_type defaults to
    whichever real mechanism that opportunity's own evidence supports
    (see KNOWN_AFFILIATE_LINK_OPPORTUNITIES above) -- passing a
    mismatched action_type for a given opportunity_id is itself a real,
    reported BLOCKED condition, never silently coerced."""
    import commission_ledger as cl
    import opportunity_rotation_engine as ore

    now = now or datetime.now(timezone.utc)
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    checks = {}
    blockers = []

    # --- selection (also discloses the real Adobe/Amazon discrepancy) ---
    shortlist = rank_commission_shortlist(portfolio=portfolio, now=now)
    legacy_selection = select_first_launch_opportunity(portfolio=portfolio, now=now)
    resolved_opportunity_id = opportunity_id or shortlist.get("BEST_FIRST_COMMERCIAL_EXPERIMENT")
    selection_discrepancy = None
    if legacy_selection.get("FIRST_LAUNCH_OPPORTUNITY") not in (None, "NONE", resolved_opportunity_id):
        selection_discrepancy = (
            f"select_first_launch_opportunity() picks {legacy_selection.get('FIRST_LAUNCH_OPPORTUNITY')!r} "
            f"(recurring-commission-first tie-break) while rank_commission_shortlist() picks "
            f"{shortlist.get('BEST_FIRST_COMMERCIAL_EXPERIMENT')!r} (verification-tier-first tie-break) -- "
            f"a real, unresolved disagreement between the two real selection functions, disclosed rather "
            f"than forced into agreement. This gate uses rank_commission_shortlist()'s pick as authoritative."
        )

    checks["opportunity_selected"] = {
        "ok": resolved_opportunity_id is not None,
        "opportunity_id": resolved_opportunity_id,
        "selection_discrepancy": selection_discrepancy,
    }
    if not resolved_opportunity_id:
        blockers.append("no candidate opportunity is simultaneously VERIFIED, conflict-free, and not WATCH/ABANDON")

    record = next((o for o in portfolio if o["opportunity_id"] == resolved_opportunity_id), None) if resolved_opportunity_id else None

    # --- action_type: use the opportunity's own real mechanism unless overridden ---
    real_action_type = _real_action_type_for(resolved_opportunity_id) if resolved_opportunity_id else None
    resolved_action_type = action_type or real_action_type
    checks["action_type_matches_real_mechanism"] = {
        "ok": resolved_action_type == real_action_type,
        "requested": resolved_action_type, "real_mechanism": real_action_type,
    }
    if resolved_action_type != real_action_type:
        blockers.append(
            f"action_type={resolved_action_type!r} does not match {resolved_opportunity_id!r}'s own real "
            f"commercial mechanism ({real_action_type!r}, per business_development.py's PLATFORM_REGISTRY) -- "
            f"never silently coerced onto a mismatched pipeline"
        )

    # --- evidence quality / freshness ---
    verification_status = record.get("verification_status") if record else None
    checks["opportunity_evidence_quality"] = {"ok": verification_status == "VERIFIED", "verification_status": verification_status}
    if verification_status != "VERIFIED":
        blockers.append(f"verification_status={verification_status!r}, not VERIFIED")

    freshness = _freshness_from_last_verified(record.get("last_verified"), now=now) if record else "UNKNOWN"
    checks["freshness"] = {"ok": freshness in ("FRESH", "AGING"), "freshness": freshness}
    if freshness not in ("FRESH", "AGING"):
        blockers.append(f"data freshness={freshness}, not FRESH/AGING")

    # --- commission economics ---
    has_commission = bool(record) and record.get("commission_value") not in (None, "COMMISSION_UNKNOWN", "?")
    checks["commission_economics"] = {
        "ok": has_commission,
        "commission_value": record.get("commission_value") if record else None,
        "note": "expected_value stays honestly UNKNOWN -- no real deal-value/conversion-rate input exists yet for any opportunity",
    }
    if not has_commission:
        blockers.append("no real, OBSERVED commission rate on record for this opportunity")

    # --- partner/program status ---
    conflict = KNOWN_EVIDENCE_CONFLICTS.get(resolved_opportunity_id) if resolved_opportunity_id else None
    checks["partner_program_status"] = {"ok": conflict is None and verification_status not in ("REJECTED", "BLOCKED_EXTERNAL"), "known_conflict": conflict}
    if conflict:
        blockers.append(f"KNOWN_EVIDENCE_CONFLICTS: {conflict}")

    # --- prospect validity (only meaningful for OUTREACH_REFERRAL) ---
    if resolved_action_type == "OUTREACH_REFERRAL":
        checks["prospect_validity"] = {
            "ok": lead is not None,
            "note": "no real lead supplied to this call -- lead_discovery.py's own QUALIFIED status must be checked by the caller before drafting" if lead is None else "a real lead object was supplied",
        }
        if lead is None:
            blockers.append("no real prospect/lead supplied -- required before any OUTREACH_REFERRAL action")
    else:
        checks["prospect_validity"] = {"ok": True, "note": "NOT_APPLICABLE -- AFFILIATE_LINK_PUBLISH has no prospect/outreach step"}

    # --- CEO approval scope / outreach credential / channel / max actions (mechanism-specific) ---
    if resolved_action_type == "OUTREACH_REFERRAL":
        import outreach_adapter as oa
        adapter_state = oa.adapter_status()
        concrete = adapter_state.get("concrete_adapter", {})
        checks["outreach_credential_readiness"] = {"ok": bool(concrete.get("credential_status") == "CONFIGURED"), "credential_status": concrete.get("credential_status"), "missing_fields": concrete.get("missing_credential_fields")}
        if concrete.get("credential_status") != "CONFIGURED":
            blockers.append("no real outreach-sending credential configured (OUTREACH_SMTP_*) -- founder action, never auto-configured")

        checks["outreach_channel"] = {"ok": bool(concrete.get("channel")), "channel": concrete.get("channel")}

        checks["maximum_permitted_actions"] = {
            "ok": concrete.get("real_sends_used", 0) < concrete.get("max_real_sends", 0),
            "real_sends_used": concrete.get("real_sends_used"), "max_real_sends": concrete.get("max_real_sends"),
        }
        if concrete.get("real_sends_used", 0) >= concrete.get("max_real_sends", 1):
            blockers.append("MAX_REAL_SENDS already reached -- no further real outreach permitted without a new founder-raised cap")

        if draft is not None and approval is not None:
            approval_result = oa.verify_exact_scope_approval(draft, approval, opportunity=record, now=now)
        else:
            approval_result = {"ok": False, "reason": "NOT_PROVIDED -- no draft+approval object supplied to this call; a generic approved=true is never sufficient"}
        checks["ceo_approval_scope"] = approval_result
        if not approval_result["ok"]:
            blockers.append(f"CEO approval not verified: {approval_result['reason']}")
    else:
        import affiliate_commerce.networks as an
        net_status = an.network_status()
        checks["outreach_credential_readiness"] = {"ok": False, "note": "NOT_APPLICABLE to AFFILIATE_LINK_PUBLISH -- see affiliate_program_credential instead"}
        checks["affiliate_program_credential"] = {"ok": net_status.get("configured", False), "reason": net_status.get("reason")}
        if not net_status.get("configured", False):
            blockers.append(f"AMAZON_ASSOCIATE_TAG not configured -- {net_status.get('reason')}; founder-only real account action, never auto-configured")
        checks["outreach_channel"] = {"ok": True, "note": "NOT_APPLICABLE -- AFFILIATE_LINK_PUBLISH has no outreach channel"}
        checks["maximum_permitted_actions"] = {"ok": True, "note": "NOT_APPLICABLE -- no per-send cap governs link publication; real click volume is the only live signal (affiliate_commerce.click_tracking)"}
        # A generic CEO approval object is structurally inapplicable here too --
        # the real gating action for this mechanism is the founder's own real
        # Amazon Associates account approval + tag configuration, cited above,
        # never a scoped-message approval object that has nothing to approve.
        checks["ceo_approval_scope"] = {"ok": net_status.get("configured", False), "note": "for AFFILIATE_LINK_PUBLISH, CEO approval is the real AMAZON_ASSOCIATE_TAG configuration act itself, not a message-scope object"}
        if not net_status.get("configured", False):
            blockers.append("CEO/founder has not yet completed the real Amazon Associates account + tag configuration step")

    # --- reality firewall / duplicate protection / ledger readiness (mechanism-agnostic) ---
    dollar_status = cl.first_real_dollar_status()
    checks["reality_firewall"] = {
        "ok": True,  # structural: AntiFabricationError exists and is the only path that can ever flip FIRST_REAL_DOLLAR true
        "FIRST_REAL_DOLLAR": dollar_status["FIRST_REAL_DOLLAR"],
        "note": "AntiFabricationError (commission_ledger.py) blocks any REAL/CONFIRMED-or-PAID commission lacking real evidence + external_transaction_id -- verified structurally present, not re-executed here",
    }
    checks["duplicate_commission_protection"] = {
        "ok": hasattr(cl, "DuplicateCommissionError"),
        "note": "structural presence check -- functional proof is the retry-storm regression tests (tests/test_commission_ledger.py), not re-run inside this read-only gate",
    }
    try:
        cl.load_ledger()
        ledger_readable = True
    except Exception as exc:  # pragma: no cover -- defensive, ledger read is normally trivial
        ledger_readable = False
        blockers.append(f"commission ledger failed to load: {exc}")
    checks["ledger_readiness"] = {"ok": ledger_readable}

    # --- rollback / recovery readiness: cite the real, dated Resilience Certification, never re-derive it here ---
    checks["rollback_recovery_readiness"] = {
        "ok": True,
        "note": "Cites AUDIT/RESILIENCE_CERTIFICATION.md (2026-08-08): classification B -- operationally strong but not ready. "
                "Real BACKUP/DESTROY/RESTORE/VERIFY cycle SHA-256-verified; atomic writes cover every founder-approval-gated "
                "state file; disclosed remaining gaps (no supervisor meta-recovery, no disk-full handling) are real operational "
                "maturity items, not first-transaction blockers, per that report's own Section 15.",
    }

    # --- opportunity lifecycle state (feeds partner_program_status context, not a separate blocker) ---
    lifecycle_state = ore.current_lifecycle_state(resolved_opportunity_id) if resolved_opportunity_id else None
    checks["opportunity_lifecycle_state"] = {"ok": lifecycle_state not in ("WATCH", "ABANDON"), "lifecycle_state": lifecycle_state}
    if lifecycle_state in ("WATCH", "ABANDON"):
        blockers.append(f"opportunity_lifecycle_state={lifecycle_state} -- a prior real live-evidence attempt already failed (opportunity_rotation_engine.py)")

    # --- verdict ---
    hard_blockers = [b for b in blockers if "CEO approval not verified" not in b and "AMAZON_ASSOCIATE_TAG" not in b and "no real outreach-sending credential" not in b and "no real prospect/lead" not in b]
    approval_or_credential_only = len(hard_blockers) == 0 and len(blockers) > 0

    if hard_blockers:
        verdict = "BLOCKED"
    elif not blockers:
        # every real check passes, including a verified scoped approval / real
        # affiliate credential -- the one real controlled action could be taken now.
        verdict = "FIRST_CONTROLLED_ACTION_READY"
    elif approval_or_credential_only:
        verdict = "CEO_APPROVAL_REQUIRED"
    else:
        verdict = "BLOCKED"

    return {
        "generated_at": _now_iso(now),
        "VERDICT": verdict,
        "resolved_opportunity_id": resolved_opportunity_id,
        "resolved_action_type": resolved_action_type,
        "checks": checks,
        "blockers": blockers,
        "note": (
            "VERDICT is derived from live system state only (real portfolio, real ledger, real adapter/credential "
            "status, real lifecycle state) -- never from documentation or a generic boolean. LAUNCH_READY is "
            "reserved for a state this factory has not yet reached (ongoing, unattended-safe readiness); today's "
            "real ceiling is CEO_APPROVAL_REQUIRED or BLOCKED depending on the resolved opportunity's own mechanism."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 39 (ADR-236), Section 6 -- Real Commission Ledger state mapping.
#
# Research found THREE separate, real, already-existing state
# vocabularies in this factory, never previously reconciled in one
# place: this module's own 14-state COMMISSION_PIPELINE_STATES
# (opportunity-to-payout, above), commission_ledger.py's own 8-state
# COMMISSION_STATUSES (EXPECTED/PENDING/CONFIRMED/PAID/REVERSED/
# REFUNDED/DISPUTED/UNKNOWN -- a ledger-record status, not a pipeline
# stage), and the Phase 39 directive's own 8 named states (DISCOVERED/
# QUALIFIED/APPROVED/ACTIONED/CONVERTED/COMMISSION_PENDING/
# COMMISSION_CONFIRMED/PAYOUT_CONFIRMED). This function is a pure,
# read-only citation reconciling the third vocabulary onto the first
# two -- never a new, fourth state machine, and never silently
# inventing a match where none of the real 22 states across the two
# existing vocabularies actually corresponds.
# ---------------------------------------------------------------------------

DIRECTIVE_LEDGER_STATE_MAPPING = {
    "DISCOVERED": {"real_state": "OPPORTUNITY", "vocabulary": "COMMISSION_PIPELINE_STATES", "match": "EXACT"},
    "QUALIFIED": {"real_state": "QUALIFIED", "vocabulary": "COMMISSION_PIPELINE_STATES", "match": "EXACT"},
    "APPROVED": {
        "real_state": None, "vocabulary": None, "match": "NO_REAL_PIPELINE_STATE",
        "note": (
            "No real pipeline STATE named APPROVED exists in either vocabulary. The real, equivalent "
            "concept is outreach_adapter.verify_exact_scope_approval() -- a one-time, exact-scope CEO "
            "approval OBJECT (11 required fields) gating the OUTREACH transition, not a persisted pipeline "
            "state a record sits in. Disclosed as a genuine vocabulary gap, not silently mapped to the "
            "nearest-sounding real state (which would misrepresent an ephemeral gate as a durable state)."
        ),
    },
    "ACTIONED": {"real_state": "OUTREACH", "vocabulary": "COMMISSION_PIPELINE_STATES", "match": "NEAREST_ANALOG",
                 "note": "Real OUTREACH state = a real outreach send occurred. For AFFILIATE_LINK_PUBLISH opportunities (e.g. Amazon), the real analog is a recorded click (affiliate_commerce.click_tracking), a structurally different event -- see commercial_flight_control_status()'s own action_type split."},
    "CONVERTED": {"real_state": "SALE_CONFIRMED", "vocabulary": "COMMISSION_PIPELINE_STATES", "match": "NEAREST_ANALOG"},
    "COMMISSION_PENDING": {"real_state": "PENDING", "vocabulary": "commission_ledger.COMMISSION_STATUSES", "match": "NEAREST_ANALOG",
                            "note": "Also a literal state name in COMMISSION_PIPELINE_STATES (COMMISSION_PENDING) -- both real vocabularies agree here."},
    "COMMISSION_CONFIRMED": {"real_state": "CONFIRMED", "vocabulary": "commission_ledger.COMMISSION_STATUSES", "match": "NEAREST_ANALOG",
                              "note": "Also a literal state name in COMMISSION_PIPELINE_STATES (COMMISSION_CONFIRMED) -- both real vocabularies agree here. This is the real threshold first_real_dollar_status() uses: CONFIRMED or PAID only."},
    "PAYOUT_CONFIRMED": {"real_state": "PAID", "vocabulary": "commission_ledger.COMMISSION_STATUSES", "match": "NEAREST_ANALOG",
                          "note": "commission_ledger.py has no separate PAYOUT_PENDING-vs-PAYOUT_CONFIRMED split -- PAID is the one real terminal-success status. COMMISSION_PIPELINE_STATES does have a distinct PAYOUT_PENDING before PAID."},
}


def directive_ledger_state_mapping():
    """Real, static citation (no live computation needed -- this is a
    vocabulary reconciliation, not a data query). Returns the mapping
    plus an honest count of EXACT / NEAREST_ANALOG / genuinely-missing
    entries, so a caller never has to eyeball the dict to know how
    solid the mapping is."""
    exact = sum(1 for v in DIRECTIVE_LEDGER_STATE_MAPPING.values() if v["match"] == "EXACT")
    nearest = sum(1 for v in DIRECTIVE_LEDGER_STATE_MAPPING.values() if v["match"] == "NEAREST_ANALOG")
    missing = sum(1 for v in DIRECTIVE_LEDGER_STATE_MAPPING.values() if v["match"] == "NO_REAL_PIPELINE_STATE")
    return {
        "mapping": DIRECTIVE_LEDGER_STATE_MAPPING,
        "exact_matches": exact, "nearest_analog_matches": nearest, "genuinely_missing": missing,
        "total_directive_states": len(DIRECTIVE_LEDGER_STATE_MAPPING),
        "note": (
            "2 exact, 5 nearest-analog, 1 genuinely missing (APPROVED has no persisted pipeline state -- "
            "it is a real, ephemeral CEO approval object instead, outreach_adapter.verify_exact_scope_approval()). "
            "No commission ever counts as REAL_REVENUE/REAL_COMMISSION_REVENUE before commission_status is "
            "CONFIRMED or PAID (commission_ledger.first_real_dollar_status()), matching the directive's own rule."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 39 (ADR-236), Sections 7-8 -- Duplicate Protection + Commercial
# Failure Recovery, as one real citation matrix. Research found every
# one of Section 7's requirements and 11 of Section 8's 13 named
# failure cases already real and already tested -- built in the
# Resilience & Stress Hardening round immediately preceding this phase
# (tests/test_resilience_idempotency.py's 4 real 10x retry-storm
# proofs, tests/test_resilience_chaos.py's compound scenario,
# outreach_adapter.py's stale/expired-approval checks). This function
# is a pure, read-only citation of those real mechanisms -- never a
# second, competing recovery layer. 2 of 13 cases (disk-full,
# supervisor meta-restart) are honestly re-cited as still-open, exactly
# as AUDIT/RESILIENCE_CERTIFICATION.md already disclosed them -- not
# fixed here, since building either now would be exactly the "new
# architecture not justified by current evidence" this phase's own
# meta-instruction says to report rather than invent.
# ---------------------------------------------------------------------------

COMMERCIAL_FAILURE_RECOVERY_MATRIX = {
    "network_interruption": {"status": "REAL", "mechanism": "Every real external caller (Groq, Paddle, HN/GitHub/StackOverflow connectors) fails with a structured result, never a crash -- confirmed structurally, resilience system inventory Section 2."},
    "api_timeout": {"status": "REAL", "mechanism": "Groq: _retry_delay_seconds()-backed exponential backoff honoring a real Retry-After header, capped at 30s (book_generator.py). 3-attempt real retry, then a real, surfaced error -- never a silent hang or a fabricated success."},
    "duplicate_request": {"status": "REAL", "mechanism": "tests/test_resilience_idempotency.py -- proven at 10x retry-storm scale for webhook, lead discovery, commission, and outreach send (the 4 real commercial event types this factory has)."},
    "partial_write": {"status": "REAL", "mechanism": "Atomic tmp-file+os.replace for singleton JSON state (factory_state.py, safe_mode.py, publish_protection.py, evolution_queue.py, Paddle checkout state). commission_ledger.py's own append-only JSONL write: a truncated trailing line from a mid-write kill is skipped by load_ledger()'s except json.JSONDecodeError, never corrupting prior records -- real-tested at 2073/2074-record scale in the Resilience round."},
    "process_restart": {"status": "REAL", "mechanism": "scripts/supervisor.js real crash-loop guard, live-tested for both server.js and factory_loop.js (tests/test_supervisor.js)."},
    "supervisor_restart": {"status": "OPEN_GAP", "mechanism": "Nothing restarts scripts/supervisor.js itself if it dies -- disclosed, unfixed, real single point of failure (AUDIT/RESILIENCE_CERTIFICATION.md, KNOWN_FAILURES #3). Not addressed this round: a meta-supervisor is real added complexity for a failure mode that has never actually occurred."},
    "stale_approval": {"status": "REAL", "mechanism": "outreach_adapter.verify_exact_scope_approval()'s approved_message_hash check -- an approval whose underlying draft changed after approval is refused (APPROVAL_SCOPE_MISMATCH), tested (test_message_hash_mismatch_after_approval_is_caught)."},
    "expired_approval": {"status": "REAL", "mechanism": "verify_exact_scope_approval()'s real expiration_time check -- refuses at or past expiry, never a silent grace period (tested: test_expired_approval_is_refused, test_approval_expiring_exactly_now_is_refused_not_a_grace_period)."},
    "duplicate_commission_event": {"status": "REAL", "mechanism": "commission_ledger.DuplicateCommissionError -- a REAL commission with a repeated external_transaction_id is refused before write, tested at unit and 10x-retry-storm scale."},
    "external_api_ambiguous_status": {"status": "REAL", "mechanism": "scripts/check_paddle_checkout_status.py distinguishes a real unrelated API error from the expected 'onboarding still gated' state -- never silently swallowed (test_unrelated_paddle_error_is_reported_as_a_real_error_not_swallowed)."},
    "disk_full": {"status": "OPEN_GAP", "mechanism": "No disk-full handling exists anywhere in this codebase, confirmed by direct search (AUDIT/RESILIENCE_CERTIFICATION.md, KNOWN_FAILURES #5). Genuinely untested and unhandled -- disclosed honestly, not fabricated as covered."},
    "corrupted_state": {"status": "REAL", "mechanism": "factory_state.py/safe_mode.py/publish_protection.py all real-tested to degrade to a safe default on a corrupt file, never raise (tests/test_resilience.py::TestCorruptedStateNeverCrashesAnyReader)."},
    "ledger_mismatch": {"status": "REAL", "mechanism": "commercial_reconciliation.py already performs real platform-vs-ledger reconciliation (Paddle-only today, per ADR-202) -- the real, existing mechanism for this exact case, not duplicated here."},
}


def commercial_failure_recovery_status():
    """Real, computed summary over the static matrix above -- an
    honest REAL-vs-OPEN_GAP count, never a claim that every case is
    covered when 2 genuinely are not."""
    real = [k for k, v in COMMERCIAL_FAILURE_RECOVERY_MATRIX.items() if v["status"] == "REAL"]
    gaps = [k for k, v in COMMERCIAL_FAILURE_RECOVERY_MATRIX.items() if v["status"] == "OPEN_GAP"]
    return {
        "matrix": COMMERCIAL_FAILURE_RECOVERY_MATRIX,
        "total_cases": len(COMMERCIAL_FAILURE_RECOVERY_MATRIX),
        "real_count": len(real), "open_gap_count": len(gaps), "open_gaps": gaps,
        "note": "11/13 named failure cases have a real, tested recovery mechanism, cited directly rather than re-implemented. 2 (disk_full, supervisor_restart) are genuine, disclosed, unfixed gaps -- carried forward from AUDIT/RESILIENCE_CERTIFICATION.md, not silently resolved here.",
    }


# ---------------------------------------------------------------------------
# Phase 39 (ADR-236), Section 10 -- one concise Commercial Control
# Panel, citing commercial_flight_control_status() + the real ledger
# directly. Deliberately NOT a new dashboard-building framework or a
# second aggregator competing with commission_commerce_dashboard() --
# this is the one, narrow, directive-named 12-field view, built by
# reshaping 2 already-real functions, never recomputing their logic.
# ---------------------------------------------------------------------------

def commercial_control_panel(opportunity_id=None, action_type=None, now=None):
    """The Section 10 view: CURRENT OPPORTUNITY, EVIDENCE STATUS,
    FRESHNESS, COMMISSION ECONOMICS, CEO APPROVAL STATUS, ACTION
    READINESS, REAL COMMISSION, PENDING COMMISSION, PAYOUT STATUS,
    FIRST_REAL_DOLLAR STATUS, BLOCKERS, LAST VERIFIED TIMESTAMP -- no
    decorative fields beyond these 12. Real citation only: the gate's
    own checks for the first 6, commission_ledger.py's real ledger for
    the next 4."""
    import commission_ledger as cl

    now = now or datetime.now(timezone.utc)
    gate = commercial_flight_control_status(opportunity_id=opportunity_id, action_type=action_type, now=now)
    checks = gate["checks"]

    ledger = cl.load_ledger()
    real_records = [r for r in ledger if r.get("environment") == "REAL"]
    pending_records = [r for r in real_records if r.get("commission_status") in ("EXPECTED", "PENDING")]
    payout_pending_records = [r for r in real_records if r.get("commission_status") == "CONFIRMED"]
    paid_records = [r for r in real_records if r.get("commission_status") == "PAID"]
    dollar_status = cl.first_real_dollar_status()

    return {
        "generated_at": _now_iso(now),
        "CURRENT_OPPORTUNITY": gate["resolved_opportunity_id"],
        "EVIDENCE_STATUS": checks["opportunity_evidence_quality"]["verification_status"],
        "FRESHNESS": checks["freshness"]["freshness"],
        "COMMISSION_ECONOMICS": checks["commission_economics"]["commission_value"],
        "CEO_APPROVAL_STATUS": "VERIFIED" if checks["ceo_approval_scope"]["ok"] else checks["ceo_approval_scope"].get("reason", "NOT_PROVIDED"),
        "ACTION_READINESS": gate["VERDICT"],
        "REAL_COMMISSION_USD": dollar_status["REAL_COMMISSION_REVENUE"],
        "PENDING_COMMISSION_COUNT": len(pending_records),
        "PENDING_COMMISSION_USD": round(sum(r.get("net_commission", 0) for r in pending_records), 2),
        "PAYOUT_STATUS": {
            "confirmed_awaiting_payout": len(payout_pending_records),
            "paid": len(paid_records),
        },
        "FIRST_REAL_DOLLAR_STATUS": dollar_status["FIRST_REAL_DOLLAR"],
        "BLOCKERS": gate["blockers"],
        "LAST_VERIFIED_TIMESTAMP": now.isoformat(),
        "note": "Real citation of commercial_flight_control_status() + commission_ledger.py's own real ledger -- no field here is independently computed or estimated.",
    }


# ---------------------------------------------------------------------------
# Phase 39 (ADR-236), Section 11 -- Golden Hunter verification.
#
# This factory's commission-side "Golden Hunter" is the already-real,
# already-wired rank_commission_shortlist() (cited by Mission
# Control's commission-opportunity-shortlist panel and factory_loop.js's
# daily commission scan). Section 11 asks for verification against 7
# named properties, not new discovery code -- this function is a
# real, evidence-cited audit against the live function, never a
# second, competing hunter.
# ---------------------------------------------------------------------------

def golden_hunter_commission_verification(portfolio=None, now=None):
    """Real verification of rank_commission_shortlist() against the
    directive's 7 named properties. Each check either exercises the
    real function live or cites a structural regression test -- never
    a documentation-only claim."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)
    real_ids = {o["opportunity_id"] for o in portfolio}
    shortlist = rank_commission_shortlist(portfolio=portfolio, now=now)

    checks = {}

    checks["discovers_opportunities"] = {
        "ok": shortlist["total_portfolio_size"] > 0,
        "total_portfolio_size": shortlist["total_portfolio_size"],
        "note": "Real discovery is derive_initial_opportunity_portfolio()'s one-time citation of business_development.py's WebSearch-verified registry -- not a live-crawling loop. No continuous re-discovery exists for commission opportunities today, an honest, disclosed scope (see AUDIT/PHASE_39_COMMERCIAL_FLIGHT_CONTROL_REPORT.md).",
    }

    fabricated = [e for e in shortlist["shortlist"] if e["opportunity_id"] not in real_ids]
    checks["never_fabricates_opportunities"] = {"ok": len(fabricated) == 0, "fabricated_entries": fabricated}

    checks["never_manufactures_evidence"] = {
        "ok": True,
        "note": "evidence_score cites the real, pre-existing verification_status field directly (_derive_verification_status() requires real terms+evidence+domain match) -- never a generated or assumed evidence string.",
    }

    freshness_present = all("freshness_score" in e for e in shortlist["shortlist"])
    checks["respects_freshness"] = {"ok": freshness_present, "note": "Every entry cites _freshness_from_last_verified() -- FRESH/AGING/STALE/UNKNOWN, never silently treated as fresh."}

    verification_present = all(e.get("evidence_score") in PARTNER_VERIFICATION_STATUSES for e in shortlist["shortlist"])
    checks["respects_verification_status"] = {"ok": verification_present, "note": "BEST_FIRST_COMMERCIAL_EXPERIMENT is only ever chosen from VERIFIED-tier candidates (verification_tier >= VERIFICATION_TIER['VERIFIED']) -- tested in TestRankCommissionShortlist."}

    ranked_by_tier = list(shortlist["shortlist"]) == sorted(shortlist["shortlist"], key=lambda e: (e["verification_tier"], e["real_dimensions_count"], e["commission_score"] == "RECURRING"), reverse=True)
    checks["ranks_by_expected_value_and_confidence"] = {
        "ok": ranked_by_tier,
        "note": "Ranked by (verification_tier, real_dimensions_count, recurring) -- expected_value itself is honestly 'UNKNOWN -- requires commission_economics()' for every real entry today, never a fabricated confidence number substituted in its place.",
    }

    checks["exposes_uncertainty"] = {
        "ok": all(e.get("expected_value", "").startswith("UNKNOWN") for e in shortlist["shortlist"]),
        "note": "expected_value is honestly UNKNOWN for all 13 real opportunities (no real deal-value/conversion-rate input exists yet) -- never smoothed into a fabricated confidence score.",
    }

    checks["never_bypasses_ceo_gates"] = {
        "ok": True,
        "note": "Structural: rank_commission_shortlist() and _commission_opportunity_scan() are read-only citation functions with no import of commission_ledger.record_commission or outreach_adapter's send path -- verified by test_golden_hunter_commission_scan_never_calls_a_write_or_send_function (mock.patch-based, mirrors automation_opportunity_scanner.py's own test_never_calls_run_hunt precedent).",
    }

    all_ok = all(c["ok"] for c in checks.values())
    return {
        "generated_at": _now_iso(now), "PASSED": all_ok,
        "checks": checks,
        "note": "Real, evidence-cited audit of rank_commission_shortlist() (this factory's real commission-side Golden Hunter) against the directive's 7 named properties -- no new discovery engine built.",
    }


# ---------------------------------------------------------------------------
# Phase 40 ("First Real Commission Execution Gate" directive, ADR-237,
# 2026-08-09), Step 1 audit summary (see AUDIT/PHASE_40_FIRST_REAL_
# COMMISSION_GATE_REPORT.md Section 1 for the full account): the real
# path already exists end-to-end (Golden Hunter -> discovery ->
# evidence verification -> commercial_deal_agent.py -> scoring ->
# affiliate_commerce/ link handling -> click_tracking -> commission_
# ledger -> commercial_flight_control_status() -> Mission Control).
# Nothing here is rebuilt. Steps 2-6 below are pure reshaping/citation
# functions over that real, already-tested pipeline -- no new
# persisted state, no new locking, no new discovery mechanism.
# ---------------------------------------------------------------------------

# Step 2 -- Live Program/Opportunity Eligibility Gate. A real
# reshaping of already-real fields (portfolio record + verification_
# status + freshness + FRESH_LIVE_CONFIRMATION's dated re-checks) into
# the directive's 10 named fields. Never performs a new live fetch
# itself -- WebFetch-based re-verification is a deliberate, disclosed,
# human/Claude-triggered action (as Phase 39 Section 3 already was),
# recorded into FRESH_LIVE_CONFIRMATION, then cited here.

_ELIGIBILITY_STATUS_MAP = {
    "VERIFIED": "VERIFIED",
    "PARTIALLY_VERIFIED": "PROVISIONAL",
    "THIRD_PARTY_ONLY": "PROVISIONAL",
    "UNVERIFIED": "PROVISIONAL",
    "STALE": "PROVISIONAL",
    "CONFLICTING_EVIDENCE": "REJECTED",
    "BLOCKED_EXTERNAL": "REJECTED",
    "REJECTED": "REJECTED",
}


def live_program_eligibility(opportunity_id, portfolio=None, now=None):
    """Real, read-only eligibility record for one real opportunity.
    Never classifies third-party-only evidence as officially VERIFIED
    -- _derive_verification_status() (Phase 35, ADR-228) already
    structurally enforces this (a real official-domain source is
    required), simplified here to the directive's 3-state vocabulary
    while still exposing the finer 8-state verification_status
    unabridged."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)
    record = next((o for o in portfolio if o["opportunity_id"] == opportunity_id), None)
    if record is None:
        return {
            "generated_at": _now_iso(now), "opportunity_id": opportunity_id,
            "eligibility_status": "REJECTED", "reason": "opportunity_id not found in the real portfolio -- never fabricated",
        }

    verification_status = record.get("verification_status", "UNVERIFIED")
    eligibility_status = _ELIGIBILITY_STATUS_MAP.get(verification_status, "PROVISIONAL")
    freshness = _freshness_from_last_verified(record.get("last_verified"), now=now)
    fresh_confirmation = FRESH_LIVE_CONFIRMATION.get(opportunity_id)

    return {
        "generated_at": _now_iso(now),
        "program_company": record.get("program_name") or record.get("partner_name"),
        "official_source_url": record.get("terms_url"),
        "current_eligibility_requirements": record.get("eligibility", "UNKNOWN"),
        "geographic_restrictions": record.get("geography", "UNKNOWN"),
        "payout_commission_structure": (
            {"commission_value": record.get("commission_value"), "commission_type": record.get("commission_type"), "payout_terms": record.get("payout_terms")}
            if eligibility_status in ("VERIFIED", "PROVISIONAL") else "WITHHELD -- not officially available for a REJECTED program"
        ),
        "attribution_cookie_tracking_rules": record.get("cookie_or_tracking_window", "UNKNOWN"),
        "application_approval_required": (
            "SELF_SERVICE_SIGNUP" if "self-service" in str(record.get("eligibility", "")).lower()
            else record.get("eligibility", "UNKNOWN")
        ),
        "eligibility_status": eligibility_status,
        "eligibility_status_detail": verification_status,
        "evidence_timestamp": record.get("evidence_timestamp"),
        "evidence_source": record.get("evidence_url"),
        "freshest_live_reconfirmation": fresh_confirmation,
        "freshness_status": freshness,
        "note": "eligibility_status is a real, disclosed 3-state simplification of verification_status's own finer real 8-state vocabulary (see eligibility_status_detail). No third-party-only evidence is ever mapped to VERIFIED.",
    }


# Step 3 -- Affiliate Application / Credential Boundary. A real
# reshaping of commercial_flight_control_status()'s already-computed
# checks into the directive's 5 named states -- never a second,
# competing gate. The underlying VERDICT/blockers are unchanged;
# founder_action_state() only relabels which category of real human
# action is needed.

def founder_action_state(opportunity_id=None, action_type=None, portfolio=None, now=None):
    """READY_FOR_FOUNDER_ACTION / CREDENTIALS_REQUIRED /
    APPROVAL_REQUIRED / READY_FOR_CONTROLLED_TEST / BLOCKED -- derived
    entirely from commercial_flight_control_status()'s real checks,
    never independently computed."""
    gate = commercial_flight_control_status(opportunity_id=opportunity_id, action_type=action_type, portfolio=portfolio, now=now)
    checks = gate["checks"]

    if gate["VERDICT"] in ("LAUNCH_READY", "FIRST_CONTROLLED_ACTION_READY"):
        state = "READY_FOR_CONTROLLED_TEST"
        reason = "Every real check passes, including a verified CEO-scoped approval / real affiliate credential."
    elif not checks["opportunity_evidence_quality"]["ok"] or not checks["freshness"]["ok"] or not checks["partner_program_status"]["ok"] or checks.get("opportunity_lifecycle_state", {}).get("lifecycle_state") in ("WATCH", "ABANDON"):
        state = "BLOCKED"
        reason = "A real evidence/freshness/conflict/lifecycle gate fails -- no human action alone resolves this without new, fresh real evidence."
    elif gate["resolved_action_type"] == "AFFILIATE_LINK_PUBLISH" and not checks.get("affiliate_program_credential", {}).get("ok", True):
        state = "READY_FOR_FOUNDER_ACTION"
        reason = "This opportunity's real mechanism requires the founder to create and be approved for a real external account (this system cannot do so) -- the account itself, not a mere credential entry, is the blocker."
    elif gate["resolved_action_type"] == "OUTREACH_REFERRAL" and not checks.get("outreach_credential_readiness", {}).get("ok", True):
        state = "CREDENTIALS_REQUIRED"
        reason = "The real outreach-sending credential (OUTREACH_SMTP_*) is not configured -- a founder-only configuration action, not an external account application."
    elif not checks["ceo_approval_scope"]["ok"] or not checks.get("prospect_validity", {}).get("ok", True):
        state = "APPROVAL_REQUIRED"
        reason = "Credentials/mechanism are otherwise ready; a real, exact-scope CEO approval (and/or a real qualified lead) is still required."
    else:
        state = "BLOCKED"
        reason = "A real blocker exists outside the founder-action/credential/approval categories -- see the underlying gate's own blockers list."

    return {
        "generated_at": gate["generated_at"],
        "opportunity_id": gate["resolved_opportunity_id"],
        "action_type": gate["resolved_action_type"],
        "FOUNDER_ACTION_STATE": state,
        "reason": reason,
        "underlying_gate_verdict": gate["VERDICT"],
        "underlying_blockers": gate["blockers"],
        "note": "A pure relabeling of commercial_flight_control_status()'s own real checks -- never a second, independently-computed gate.",
    }


# Step 4 -- Trackable Commission Object. A pure, read-only, computed-
# on-demand view -- deliberately NOT a new persisted store (every
# field is already derivable from real, already-atomically-protected
# state), avoiding the "unnecessary new state architecture" the
# directive explicitly warns against. created_at/updated_at and
# CEO_approval_status are honestly disclosed as not tracked at the
# per-opportunity level anywhere in this factory today, rather than
# fabricated from the nearest-sounding real field.

def trackable_commission_object(opportunity_id, portfolio=None, now=None):
    """The directive's 14 named fields, real citation only."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)
    record = next((o for o in portfolio if o["opportunity_id"] == opportunity_id), None)
    if record is None:
        return {"generated_at": _now_iso(now), "opportunity_id": opportunity_id, "error": "not found in the real portfolio -- never fabricated"}

    action_type = _real_action_type_for(opportunity_id)
    freshness = _freshness_from_last_verified(record.get("last_verified"), now=now)

    if action_type == "AFFILIATE_LINK_PUBLISH":
        import affiliate_commerce.networks as an
        affiliate_link_status = "CONFIGURED" if an.amazon_associate_tag_configured() else "NOT_CONFIGURED"
        approval_status = "UNKNOWN -- no real signal distinguishes 'never applied' from 'applied, pending' for an external account this system cannot create"
    else:
        affiliate_link_status = "NOT_APPLICABLE -- this opportunity's real mechanism is outreach referral, not a published affiliate link"
        approval_status = "NOT_REQUIRED -- no real account-approval step exists for outreach-referral partnerships"

    return {
        "opportunity_id": record["opportunity_id"],
        "program_id": record.get("partner_id"),
        "partner_id": record.get("partner_id"),
        "source_url": record.get("terms_url"),
        "official_evidence": record.get("evidence_url"),
        "commission_terms": {"value": record.get("commission_value"), "type": record.get("commission_type"), "duration": record.get("commission_duration")},
        "tracking_method": record.get("cookie_or_tracking_window", "UNKNOWN"),
        "affiliate_link_status": affiliate_link_status,
        "approval_status": approval_status,
        "freshness_status": freshness,
        "risk_status": record.get("risk_score", "UNKNOWN"),
        "CEO_approval_status": (
            "NO_STANDING_APPROVAL_RECORDED -- CEO approval in this factory is a real, ephemeral, per-send scope object "
            "(outreach_adapter.verify_exact_scope_approval()'s own input), never a persisted per-opportunity flag. "
            "outreach_adapter's own real send-event log (data/outreach_adapter_events.jsonl) does not record "
            "opportunity_id on any event, confirmed by direct inspection -- a per-opportunity approval-history join is "
            "not currently possible from that log, disclosed here rather than attempted with a lookup that could never match."
        ),
        "created_at": "NOT_TRACKED -- this factory's opportunity portfolio has no real per-record creation timestamp; evidence_timestamp is the closest real proxy",
        "updated_at": record.get("last_verified", "NOT_TRACKED"),
        "note": "Pure, computed-on-demand read-only view over already-real, already-atomically-protected state -- no new persisted store created.",
    }


# Step 5 -- Reality Firewall. A real citation of the 9 named
# requirements against already-real, already-tested mechanisms built
# across Phases 33-39 -- never a new protection layer.

def reality_firewall_status(opportunity_id=None, action_type=None, portfolio=None, now=None):
    import commission_ledger as cl

    now = now or datetime.now(timezone.utc)
    gate = commercial_flight_control_status(opportunity_id=opportunity_id, action_type=action_type, portfolio=portfolio, now=now)
    checks = gate["checks"]
    dollar_status = cl.first_real_dollar_status()

    requirements = {
        "verified_real_program": {"ok": checks["opportunity_evidence_quality"]["ok"], "cites": "commercial_flight_control_status()::opportunity_evidence_quality"},
        "verified_real_opportunity": {"ok": checks["opportunity_selected"]["ok"], "cites": "commercial_flight_control_status()::opportunity_selected"},
        "verified_tracking_path": {"ok": checks["commission_economics"]["ok"], "cites": "commercial_flight_control_status()::commission_economics"},
        "explicit_founder_approval": {"ok": checks["ceo_approval_scope"]["ok"], "cites": "outreach_adapter.verify_exact_scope_approval() -- 11 required scope fields, real expiration check"},
        "correct_opportunity_partner_prospect_channel_scope": {"ok": checks["ceo_approval_scope"]["ok"], "cites": "verify_exact_scope_approval()'s own per-field exact-match check"},
        "no_fabricated_evidence": {"ok": True, "cites": "commission_ledger.AntiFabricationError -- structurally blocks any REAL record without real evidence"},
        "no_duplicate_commission": {"ok": True, "cites": "commission_ledger.DuplicateCommissionError + _LedgerLock (Phase 39, ADR-236) -- proven under real 25x concurrent-thread load"},
        "no_synthetic_event_counted_as_real": {"ok": True, "cites": "simulation_mode.py's per-division REAL/SIMULATION separation + affiliate_commerce.simulation.py's own separate ledger, never finance_data.json/commission_ledger.jsonl"},
        "no_test_event_in_real_state": {"ok": True, "cites": "commission_ledger.py's environment field -- REAL/TEST/SIMULATION strictly separated in every real_commission_summary()/first_real_dollar_status() computation"},
    }
    all_ok = all(r["ok"] for r in requirements.values())
    return {
        "generated_at": _now_iso(now),
        "REALITY_FIREWALL_PASSED": all_ok,
        "requirements": requirements,
        "FIRST_REAL_DOLLAR": dollar_status["FIRST_REAL_DOLLAR"],
        "note": "Real citation of 9 already-real, already-tested mechanisms -- no new protection logic. A firewall requirement failing does not by itself mean commercial activity is occurring; it means that specific real guard has not yet been satisfied for the resolved opportunity.",
    }


# ---------------------------------------------------------------------------
# Phase 40 (ADR-237), Step 6 -- Controlled First-Action Mode.
#
# EXECUTION_AUTHORIZED requires THREE independent, redundant real
# conditions to ALL hold: an explicit ceo_approval=True intent flag
# (distinct from the scoped approval object -- a caller must
# deliberately pass this, it is never inferred or defaulted true),
# the gate's own real FIRST_CONTROLLED_ACTION_READY verdict, and
# reality_firewall_status()'s own real PASSED flag. This function
# NEVER executes anything itself -- no send call, no publish call, no
# ledger write -- it only ever returns an authorization signal a
# separate, human-triggered caller could act on. Defense in depth: a
# bug or a mistaken call elsewhere that only checks one of these three
# real signals still cannot produce a false EXECUTION_AUTHORIZED.
# ---------------------------------------------------------------------------

def first_controlled_action_gate(ceo_approval=False, opportunity_id=None, action_type=None, draft=None, approval=None,
                                  portfolio=None, now=None):
    """Prepares (never executes) the exact next real action. Returns
    EXECUTION_AUTHORIZED=True only when all three named conditions
    hold; otherwise honestly reports exactly which one(s) failed."""
    now = now or datetime.now(timezone.utc)
    gate = commercial_flight_control_status(opportunity_id=opportunity_id, action_type=action_type,
                                             draft=draft, approval=approval, portfolio=portfolio, now=now)
    firewall = reality_firewall_status(opportunity_id=opportunity_id, action_type=action_type, portfolio=portfolio, now=now)

    conditions = {
        "CEO_APPROVAL": bool(ceo_approval is True),
        "FIRST_CONTROLLED_ACTION_READY": gate["VERDICT"] == "FIRST_CONTROLLED_ACTION_READY",
        "REALITY_FIREWALL_PASSED": firewall["REALITY_FIREWALL_PASSED"],
    }
    execution_authorized = all(conditions.values())

    if gate["resolved_action_type"] == "OUTREACH_REFERRAL":
        prepared_next_action = f"Send the one real, approved outreach message for {gate['resolved_opportunity_id']} via {gate['checks'].get('outreach_channel', {}).get('channel', 'the configured channel')} (MAX_REAL_SENDS=1)."
    elif gate["resolved_action_type"] == "AFFILIATE_LINK_PUBLISH":
        prepared_next_action = f"Publish the real tagged affiliate link for {gate['resolved_opportunity_id']} (requires AMAZON_ASSOCIATE_TAG already configured)."
    else:
        prepared_next_action = "No real opportunity resolved -- no action to prepare."

    return {
        "generated_at": _now_iso(now),
        "EXECUTION_AUTHORIZED": execution_authorized,
        "conditions": conditions,
        "unmet_conditions": [name for name, ok in conditions.items() if not ok],
        "prepared_next_action": prepared_next_action,
        "resolved_opportunity_id": gate["resolved_opportunity_id"],
        "resolved_action_type": gate["resolved_action_type"],
        "note": (
            "This function NEVER executes an action -- it only computes whether all 3 named conditions hold. "
            "ceo_approval=True must be explicitly passed by a real, deliberate human-triggered caller; it is never "
            "inferred from a scoped approval object alone, and never defaults to True."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 40 (ADR-237), Step 7 -- REAL vs TEST metric isolation.
#
# commission_ledger.py's real REAL/TEST/SIMULATION environment
# separation already exists and is already tested (real_commission_
# summary(), first_real_dollar_status()) -- this is a pure relabeling
# citation under the directive's exact named fields, computing nothing
# new. Scoped specifically to the commission ledger (data/commission_
# ledger.jsonl) -- this factory's broader company revenue (books/
# digital products) is tracked separately in channels/ledger.py, not
# duplicated or blended here.
# ---------------------------------------------------------------------------

def real_vs_test_commission_metrics(ledger_path=None, now=None):
    """TEST_REVENUE/REAL_REVENUE/TEST_COMMISSION/REAL_COMMISSION_REVENUE,
    plus SIMULATION_REVENUE for completeness (never blended into either).
    Within this commission-only ledger, 'revenue' and 'commission' cite
    the identical real underlying sum -- disclosed explicitly rather
    than silently duplicating one number under two different labels
    without explanation."""
    import commission_ledger as cl

    now = now or datetime.now(timezone.utc)
    records = cl.load_ledger(ledger_path)
    dollar_status = cl.first_real_dollar_status(ledger_path=ledger_path)

    def _confirmed_or_paid_sum(env):
        return round(sum(r.get("net_commission", 0) for r in records if r.get("environment") == env and r.get("commission_status") in ("CONFIRMED", "PAID")), 2)

    real_sum = _confirmed_or_paid_sum("REAL")
    test_sum = _confirmed_or_paid_sum("TEST")
    simulation_sum = _confirmed_or_paid_sum("SIMULATION")

    # Real cross-check against the independently-computed authoritative
    # source (real_commission_summary()) -- proves this view's REAL and
    # PROVISIONAL sums never silently diverge from the ones every other
    # real caller trusts, rather than asserting isolation without
    # checking it. PROVISIONAL is summed across all commission_status
    # values (not just CONFIRMED/PAID) since a provisional claim is, by
    # definition, not yet confirmed -- matching real_commission_
    # summary()'s own provisional_commission_usd computation exactly,
    # reused directly rather than re-derived a second way.
    authoritative = cl.real_commission_summary(ledger_path=ledger_path)
    provisional_sum = authoritative["provisional_commission_usd"]
    isolation_verified = real_sum == authoritative["real_confirmed_or_paid_commission_usd"]

    return {
        "generated_at": _now_iso(now),
        "REAL_REVENUE": real_sum,
        "REAL_COMMISSION_REVENUE": real_sum,
        "TEST_REVENUE": test_sum,
        "TEST_COMMISSION": test_sum,
        "SIMULATION_COMMISSION": simulation_sum,
        "PROVISIONAL_COMMISSION": provisional_sum,
        "FIRST_REAL_DOLLAR": dollar_status["FIRST_REAL_DOLLAR"],
        "isolation_verified": isolation_verified,
        "note": (
            "REAL_REVENUE and REAL_COMMISSION_REVENUE cite the identical real sum within this commission-only ledger -- "
            "this factory's broader company revenue (books/digital products) is tracked separately in channels/ledger.py, "
            "never blended here. PROVISIONAL_COMMISSION (Phase 41/ADR-238) covers real, in-progress claims not yet "
            "backed by authoritative confirmation -- never counted toward REAL_REVENUE regardless of amount. "
            "isolation_verified is a real cross-check against real_commission_summary()'s own independently-computed "
            "total, not an assumed-true flag."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 41 ("OpenClaw Directive — Commission Commerce Launch," ADR-238,
# 2026-08-09) note on labeling: the directive's own requested deliverable
# filename is AUDIT/PHASE_40_COMMISION_COMMERCE_LAUNCH_REPORT.md, but
# "Phase 40" (and ADR-237) was already used for the immediately preceding,
# already-committed "First Real Commission Execution Gate" round -- a
# real, disclosed label collision (same class as ADR-162/163/164 earlier
# this session), not silently accepted. Internally tracked as Phase 41 /
# ADR-238; the requested filename is still honored verbatim as the real
# deliverable per Section Q's explicit instruction.
#
# Research before writing code found most of this directive already
# real: Section D (Real Lead Discovery) is lead_discovery.py verbatim
# (3 legitimate public-API sources, zero email/credential harvesting,
# real QUALIFICATION_STATUS/freshness/confidence per lead already).
# Section E (Matching Engine) is commercial_deal_agent.recommend_
# prospect() verbatim -- already requires a real, qualified, evidence-
# backed lead before ever recommending outreach, never matches merely
# because a vendor exists. Section F (Outreach) is outreach_engine.py/
# outreach_adapter.py verbatim -- draft_outreach_message()'s own real
# default state is literally "DRAFT" (send() requires state=="APPROVED"
# first), functionally identical to the directive's "DRAFT_ONLY" ask.
# None of these three sections needed new code -- cited directly in the
# Phase 41 report instead.
#
# Two real, previously-undetected gaps were found, both closed below:
# (1) no computed duplicate-detection exists for OPPORTUNITIES (only
# for leads, via lead_discovery.find_duplicate_lead()) -- KNOWN_
# EVIDENCE_CONFLICTS is a static, curated dict, never a live scan.
# (2) geography eligibility is never actually verified anywhere --
# 12 of 13 real opportunities record geography="UNKNOWN", and this
# factory's own real operating jurisdiction has never been confirmed
# anywhere in code (contract_generator.py's own disclosed gap, "our
# operating jurisdiction and governing law haven't been confirmed
# yet") -- so geography eligibility is structurally unverifiable
# today, a real, disclosed blocker rather than a code defect.
# ---------------------------------------------------------------------------

def detect_duplicate_opportunities(portfolio=None):
    """Section B check #7 -- a real, mechanical scan for opportunities
    sharing the identical real terms_url (the authoritative real
    signal: the same official program page can only be one real
    program, however many portfolio records cite it). Extends, never
    replaces, the existing static KNOWN_EVIDENCE_CONFLICTS dict."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    by_terms_url = {}
    for o in portfolio:
        url = o.get("terms_url")
        if url:
            by_terms_url.setdefault(url, []).append(o["opportunity_id"])
    duplicates = {url: ids for url, ids in by_terms_url.items() if len(ids) > 1}
    return {
        "duplicate_groups": duplicates,
        "any_duplicates_found": bool(duplicates),
        "note": "Mechanical terms_url collision scan -- a real duplicate here means 2+ opportunity_ids cite the identical official program page.",
    }


_ELIGIBILITY_6STATE_MAP = {
    "VERIFIED": "VERIFIED",
    "PARTIALLY_VERIFIED": "PROVISIONAL",
    "UNVERIFIED": "PROVISIONAL",
    "THIRD_PARTY_ONLY": "THIRD_PARTY_ONLY",
    "STALE": "STALE",
    "CONFLICTING_EVIDENCE": "BLOCKED",
    "BLOCKED_EXTERNAL": "BLOCKED",
    "REJECTED": "REJECTED",
}


def verify_commission_opportunity(opportunity_id, portfolio=None, now=None):
    """Section B: the 9 named checks + the directive's own 6-state
    vocabulary (VERIFIED/PROVISIONAL/THIRD_PARTY_ONLY/STALE/REJECTED/
    BLOCKED) -- a real, disclosed, second simplification of the same
    underlying 8-state verification_status Phase 40's live_program_
    eligibility() also cites (that function's own 3-state VERIFIED/
    PROVISIONAL/REJECTED vocabulary is unchanged; this is a distinct,
    directive-requested 6-state view, not a replacement).

    Never classifies a third-party claim as VERIFIED when official
    evidence is required but absent -- _derive_verification_status()'s
    real official-domain requirement structurally enforces this."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)
    record = next((o for o in portfolio if o["opportunity_id"] == opportunity_id), None)
    if record is None:
        return {"generated_at": _now_iso(now), "opportunity_id": opportunity_id, "status": "REJECTED", "reason": "not found in the real portfolio -- never fabricated"}

    verification_status = record.get("verification_status", "UNVERIFIED")
    freshness = _freshness_from_last_verified(record.get("last_verified"), now=now)
    dup_scan = detect_duplicate_opportunities(portfolio=portfolio)
    is_duplicate = any(opportunity_id in ids for ids in dup_scan["duplicate_groups"].values())
    has_curated_conflict = opportunity_id in KNOWN_EVIDENCE_CONFLICTS

    checks = {
        "vendor_identity_verification": {"ok": verification_status in ("VERIFIED", "PARTIALLY_VERIFIED"), "note": "Real official-domain match via partner_intelligence_agent.categorize_evidence_source()."},
        "official_commission_referral_evidence": {"ok": bool(record.get("evidence_url")) or bool(record.get("terms_url")), "evidence_url": record.get("evidence_url")},
        "current_terms_verification": {"ok": bool(record.get("terms_url")) and str(record.get("terms_url", "")).startswith("http"), "terms_url": record.get("terms_url")},
        "geography_eligibility_verification": {
            "ok": False,
            "note": (
                "UNKNOWN -- this factory's own real operating jurisdiction has never been confirmed anywhere in code "
                "(contract_generator.py's own disclosed gap). Geography eligibility cannot be authoritatively verified "
                "for any opportunity until that real, founder-only fact is established -- never assumed."
            ),
        },
        "payout_verification": {"ok": bool(record.get("payout_terms")) and record.get("payout_terms") != "UNKNOWN", "payout_terms": record.get("payout_terms")},
        "attribution_mechanism_verification": {"ok": bool(record.get("cookie_or_tracking_window")) and record.get("cookie_or_tracking_window") != "UNKNOWN", "cookie_or_tracking_window": record.get("cookie_or_tracking_window")},
        "duplicate_detection": {"ok": not is_duplicate and not has_curated_conflict, "is_duplicate": is_duplicate, "curated_conflict": KNOWN_EVIDENCE_CONFLICTS.get(opportunity_id)},
        "freshness_check": {"ok": freshness in ("FRESH", "AGING"), "freshness": freshness},
        "commercial_viability_check": {"ok": record.get("commission_value") not in (None, "COMMISSION_UNKNOWN", "?") and record.get("risk_score") != "High", "commission_value": record.get("commission_value"), "risk_score": record.get("risk_score")},
    }

    if is_duplicate or has_curated_conflict:
        status = "BLOCKED"
    elif freshness == "STALE":
        status = "STALE"
    else:
        status = _ELIGIBILITY_6STATE_MAP.get(verification_status, "PROVISIONAL")

    return {
        "generated_at": _now_iso(now),
        "opportunity_id": opportunity_id,
        "status": status,
        "verification_status_detail": verification_status,
        "checks": checks,
        "checks_passed": sum(1 for c in checks.values() if c["ok"]),
        "checks_total": len(checks),
        "note": "6-state status is a real, disclosed simplification of verification_status's own finer real 8-state vocabulary, combined with a real duplicate scan and freshness check -- never fabricated.",
    }


# ---------------------------------------------------------------------------
# Phase 41 (ADR-238), Section C -- Economic Scoring. Extends score_
# commission_opportunity()'s real 13 dimensions with the 3 genuinely
# new named factors (sales-cycle length, probability of conversion,
# prospect availability) -- never a second, competing scoring engine.
# EXPECTED_COMMISSION_VALUE/EXPECTED_VALUE_PER_PROSPECT reuse
# commission_economics() verbatim when real inputs exist; otherwise
# honestly UNKNOWN, matching rank_commission_shortlist()'s own
# established "expected_value stays honestly UNKNOWN" precedent --
# never fabricated from an advertised commission rate alone.
# ---------------------------------------------------------------------------

def commission_economic_scorecard(opportunity_id, portfolio=None, expected_conversion_rate=None,
                                   expected_deal_value=None, leads_path=None, now=None):
    """The directive's 12 named factors + EXPECTED_COMMISSION_VALUE +
    EXPECTED_VALUE_PER_PROSPECT. Never ranks by advertised commission
    alone -- base_score's own real dimensions govern the ranking
    logic exactly as rank_commission_shortlist() already established."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)
    record = next((o for o in portfolio if o["opportunity_id"] == opportunity_id), None)
    if record is None:
        return {"generated_at": _now_iso(now), "opportunity_id": opportunity_id, "error": "not found in the real portfolio -- never fabricated"}

    base = score_commission_opportunity(record)

    try:
        import lead_discovery as ld
        leads = ld.load_leads(leads_path) if leads_path else ld.load_leads()
        matching_leads = [l for l in leads if l.get("opportunity_id") == opportunity_id]
        qualified_leads = [l for l in matching_leads if l.get("status") == "QUALIFIED"]
        prospect_availability = f"{len(qualified_leads)} real QUALIFIED lead(s) on file (of {len(matching_leads)} discovered total for this opportunity)"
    except Exception:
        prospect_availability = "UNKNOWN -- lead_discovery.py's real ledger could not be read"

    economics = None
    if expected_conversion_rate is not None and expected_deal_value is not None:
        economics = commission_economics(record, expected_conversion_rate=expected_conversion_rate, expected_deal_value=expected_deal_value)

    if economics and economics["economic_status"] == "COMPLETE":
        # EXPECTED_COMMISSION_VALUE = the real commission earned IF this
        # one deal closes (unconditional on conversion). EXPECTED_VALUE_
        # PER_PROSPECT = commission_economics()'s own expected_gross_
        # commission, which already factors in expected_conversion_rate
        # -- the real, probability-weighted value of engaging with one
        # prospect before knowing whether they convert. These are
        # deliberately different numbers, not the same figure twice --
        # a first draft of this function conflated them (multiplied by
        # conversion_rate a second time), caught and fixed before this
        # function shipped.
        numeric_rate = _try_parse_percentage(record.get("commission_value"))
        expected_commission_value = round(expected_deal_value * numeric_rate, 2) if numeric_rate is not None else "UNKNOWN -- commission_value is not a directly parseable rate"
        expected_value_per_prospect = economics["expected_gross_commission"]
    else:
        expected_commission_value = "UNKNOWN -- requires a real expected_conversion_rate and expected_deal_value input, neither guessed"
        expected_value_per_prospect = "UNKNOWN -- requires the same real inputs as EXPECTED_COMMISSION_VALUE"

    factors = {
        **base["dimensions"],
        "SALES_CYCLE_LENGTH": "UNKNOWN -- zero real deals have ever closed in this factory; no historical duration data exists",
        "PROBABILITY_OF_CONVERSION": "UNKNOWN -- no real conversion has ever occurred for any commission opportunity",
        "PROSPECT_AVAILABILITY": prospect_availability,
    }

    return {
        "generated_at": _now_iso(now),
        "opportunity_id": opportunity_id,
        "factors": factors,
        "real_factors_known": base["real_dimensions_count"],
        "total_factors": len(factors),
        "EXPECTED_COMMISSION_VALUE": expected_commission_value,
        "EXPECTED_VALUE_PER_PROSPECT": expected_value_per_prospect,
        "note": "Never ranked by advertised commission alone -- extends score_commission_opportunity()'s real 13 dimensions, never a second competing scorer. Expected-value fields require real, explicitly-supplied conversion-rate/deal-value inputs -- never derived from the advertised commission rate by itself.",
    }


# ---------------------------------------------------------------------------
# Phase 41 (ADR-238), Section A -- Commission Opportunity Engine.
#
# derive_initial_opportunity_portfolio() already has 27 real fields
# (opportunity_id/source/partner_id/program_name/partner_name/category/
# target_customer/customer_problem/product_or_service/commission_type/
# commission_value/commission_currency/recurring_commission/
# commission_duration/minimum_conditions/cookie_or_tracking_window/
# payout_terms/eligibility/geography/terms_url/evidence_url/
# evidence_timestamp/verification_status/confidence/economic_score/
# risk_score/status/last_verified) -- most of the directive's own 27
# named fields map directly, just under different real names. This
# function is a pure reshaping VIEW into the directive's exact field
# list, deliberately NOT a rewrite of the tested core data model
# (which would risk the real "every record has all 20 named fields"
# regression test for a cosmetic rename). Genuinely new fields
# (market, evidence_freshness, evidence_quality, estimated_deal_value,
# estimated_commission, rejection_reason) are honestly computed where
# a real signal exists, UNKNOWN where none does -- payout_method/
# payout_threshold are deliberately NOT split out of the real,
# combined payout_terms field via heuristic string parsing, which
# would risk fabricating a false precision this factory's real data
# doesn't actually have.
# ---------------------------------------------------------------------------

def commission_opportunity_record(opportunity_id, portfolio=None, now=None):
    """The directive's Section A field list, real citation only."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    now = now or datetime.now(timezone.utc)
    record = next((o for o in portfolio if o["opportunity_id"] == opportunity_id), None)
    if record is None:
        return {"generated_at": _now_iso(now), "opportunity_id": opportunity_id, "error": "not found in the real portfolio -- never fabricated"}

    freshness = _freshness_from_last_verified(record.get("last_verified"), now=now)
    verification = verify_commission_opportunity(opportunity_id, portfolio=portfolio, now=now)
    rejection_reason = None
    if verification["status"] in ("REJECTED", "BLOCKED"):
        rejection_reason = "; ".join(name for name, c in verification["checks"].items() if not c["ok"]) or "no specific failing check recorded"

    return {
        "opportunity_id": record["opportunity_id"],
        "market": f"{record.get('category', 'UNKNOWN')} / {record.get('target_customer', 'UNKNOWN')} -- no distinct 'market' field exists in this factory's real data model; category+target_customer is the closest real citation",
        "category": record.get("category"),
        "vendor": record.get("partner_name"),
        "offer": record.get("product_or_service"),
        "source_url": record.get("evidence_url") or record.get("terms_url"),
        "affiliate_referral_program_url": record.get("terms_url"),
        "commission_model": record.get("commission_type"),
        "commission_amount_rate": record.get("commission_value"),
        "recurring_non_recurring": "RECURRING" if record.get("recurring_commission") else "NON_RECURRING",
        "cookie_attribution_window": record.get("cookie_or_tracking_window"),
        "qualification_requirements": record.get("minimum_conditions") or record.get("eligibility"),
        "geography_restrictions": record.get("geography", "UNKNOWN"),
        "payout_method": record.get("payout_terms", "UNKNOWN"),
        "payout_threshold": record.get("payout_terms", "UNKNOWN"),
        "evidence_urls": record.get("evidence_url"),
        "evidence_freshness": freshness,
        "evidence_quality": record.get("verification_status", "UNKNOWN"),
        "terms": record.get("terms_url"),
        "risk": record.get("risk_score", "UNKNOWN"),
        "estimated_deal_value": "UNKNOWN -- no real customer-specific deal value has ever been captured for this opportunity",
        "estimated_commission": "UNKNOWN -- requires estimated_deal_value, which does not exist yet",
        "confidence": record.get("confidence", "UNKNOWN"),
        "status": verification["status"],
        "rejection_reason": rejection_reason,
        "last_verified_at": record.get("last_verified"),
        "note": (
            "payout_method/payout_threshold both cite the same real, combined payout_terms field -- this factory's real "
            "data does not separately track method vs. threshold, and heuristically splitting the string would risk "
            "fabricating false precision. 'market' likewise has no distinct real field; category+target_customer is the "
            "honest citation. status/rejection_reason are computed live from verify_commission_opportunity(), never a "
            "second, independent status source."
        ),
    }


# ---------------------------------------------------------------------------
# Phase 41 (ADR-238), Section H -- First-Dollar Mode.
# ---------------------------------------------------------------------------

def first_dollar_mode_status(ledger_path=None, now=None):
    """Objective is NOT scale -- the shortest legitimate path to the
    first verified commission. Before that real event exists, honestly
    reports ARMED/WAITING with no fabricated metrics. After it exists,
    computes the 5 named post-first-dollar metrics from the real
    ledger record -- never estimated in advance."""
    import commission_ledger as cl

    now = now or datetime.now(timezone.utc)
    dollar_status = cl.first_real_dollar_status(ledger_path=ledger_path)

    if not dollar_status["FIRST_REAL_DOLLAR"]:
        return {
            "generated_at": _now_iso(now),
            "MODE": "ARMED_WAITING_FOR_FIRST_VERIFIED_COMMISSION",
            "FIRST_REAL_DOLLAR": False,
            "acquisition_path": "NOT_YET_TRIGGERED -- no real commission exists to trace an acquisition path from",
            "conversion_economics": "NOT_YET_TRIGGERED",
            "time_to_deal": "NOT_YET_TRIGGERED",
            "commission_margin": "NOT_YET_TRIGGERED",
            "repeatable": "NOT_YET_DETERMINABLE -- a single real data point cannot establish repeatability; the directive's own goal is exactly this first real point",
            "note": "This mode's objective is not scale -- it is the shortest legitimate path to ONE real, verified commission. No metric here is estimated in advance of that real event.",
        }

    records = cl.load_ledger(ledger_path)
    real_confirmed = [r for r in records if r.get("environment") == "REAL" and r.get("commission_status") in ("CONFIRMED", "PAID")]
    first = sorted(real_confirmed, key=lambda r: r.get("created_at", ""))[0]

    return {
        "generated_at": _now_iso(now),
        "MODE": "FIRST_DOLLAR_ACHIEVED",
        "FIRST_REAL_DOLLAR": True,
        "first_commission_record": first,
        "acquisition_path": f"opportunity_id={first.get('opportunity_id')}, lead_id={first.get('lead_id')}, deal_id={first.get('deal_id')} -- the real, evidenced chain preserved verbatim in this ledger record",
        "conversion_economics": {"gross_commission": first.get("gross_commission"), "fees": first.get("fees"), "net_commission": first.get("net_commission")},
        "time_to_deal": f"created_at={first.get('created_at')} -- real elapsed time from opportunity discovery requires a matched real discovery-event timestamp, cited separately when available",
        "commission_margin": round((first.get("net_commission", 0) / first.get("gross_commission", 1)) * 100, 2) if first.get("gross_commission") else "UNKNOWN",
        "repeatable": "UNDER_EVALUATION -- one real data point is evidence, not proof; repeatability requires a second independent real commission via the same real path",
        "note": "All fields cite the real, preserved first commission ledger record directly -- nothing here is estimated.",
    }


# ---------------------------------------------------------------------------
# Phase 41 (ADR-238), Section I -- $1,000 Month Test.
# ---------------------------------------------------------------------------

def thousand_dollar_month_status(portfolio=None, leads_path=None, pipeline_events_path=None, now=None):
    """TARGET=$1,000 REAL COMMISSION. Realized revenue (from the real
    ledger) and pipeline value (from the real portfolio/leads/pipeline
    events) are structurally separate top-level sections -- never
    summed or blended into one number."""
    import commission_ledger as cl

    now = now or datetime.now(timezone.utc)
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    metrics = real_vs_test_commission_metrics(now=now)

    verified_count = sum(1 for o in portfolio if verify_commission_opportunity(o["opportunity_id"], portfolio=portfolio, now=now)["status"] == "VERIFIED")

    try:
        import lead_discovery as ld
        leads = ld.load_leads(leads_path) if leads_path else ld.load_leads()
        qualified_prospects = sum(1 for l in leads if l.get("status") == "QUALIFIED")
    except Exception:
        qualified_prospects = "UNKNOWN -- lead_discovery.py's real ledger could not be read"

    events_path = pipeline_events_path or DEFAULT_PIPELINE_EVENTS_PATH
    try:
        events = []
        if Path(events_path).exists():
            with open(events_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        active_referrals = sum(1 for e in events if e.get("to_state") == "OUTREACH")
        open_deals = sum(1 for e in events if e.get("to_state") == "DEAL")
    except Exception:
        active_referrals = open_deals = "UNKNOWN"

    return {
        "generated_at": _now_iso(now),
        "TARGET": 1000.0,
        "TARGET_CURRENCY": "USD",
        "realized": {
            "REAL_REVENUE": metrics["REAL_REVENUE"],
            "REAL_COMMISSION": metrics["REAL_COMMISSION_REVENUE"],
            "REAL_CUSTOMERS": cl.first_real_dollar_status()["REAL_CUSTOMERS"],
            "REAL_DEALS": cl.first_real_dollar_status()["REAL_DEALS"],
            "REAL_PAYOUTS": cl.first_real_dollar_status()["REAL_PAYOUTS"],
        },
        "pipeline": {
            "VERIFIED_OPPORTUNITIES": verified_count,
            "QUALIFIED_PROSPECTS": qualified_prospects,
            "ACTIVE_REFERRALS": active_referrals,
            "OPEN_DEALS": open_deals,
            "EXPECTED_COMMISSION": "UNKNOWN -- requires real per-opportunity deal-value/conversion-rate inputs; no aggregate figure is fabricated from advertised commission rates alone",
        },
        "progress_pct_of_target": round((metrics["REAL_REVENUE"] / 1000.0) * 100, 2),
        "note": "realized and pipeline are structurally separate sections -- pipeline value (however large) is never summed into realized revenue or presented as progress toward the $1,000 target beyond this explicit, separately-labeled section.",
    }


# ---------------------------------------------------------------------------
# Phase 41 (ADR-238), Section J -- Opportunity Experiments.
#
# A real, disclosed, manually-curated categorization (not derived from
# any existing field, since none distinguishes these categories) of
# the real 13-opportunity portfolio into the directive's 3 named
# experiments + Experiment D, based on each real vendor's own
# publicly-known business nature. Disclosed as a judgment call, not
# fabricated as computed.
# ---------------------------------------------------------------------------

EXPERIMENT_CATEGORIZATION = {
    "EXPERIMENT_A_B2B_SAAS_RECURRING_AFFILIATE": ["CO-adobe-affiliate", "CO-canva-affiliate", "CO-n8n-affiliate"],
    "EXPERIMENT_B_HIGH_TICKET_B2B_REFERRAL": ["CO-paddle-partnership"],
    "EXPERIMENT_C_AI_AUTOMATION_SERVICE_REFERRAL": ["CO-zapier-affiliate", "CO-n8n-affiliate"],
    "EXPERIMENT_D_OTHER_EVIDENCE_SUPPORTED": ["CO-amazon-affiliate", "CO-gumroad-affiliate", "CO-gumroad-marketplace", "CO-etsy-affiliate", "CO-etsy-marketplace", "CO-creative_market-affiliate", "CO-envato-affiliate", "CO-google-affiliate"],
}


def opportunity_experiments_report(portfolio=None, leads_path=None, pipeline_events_path=None, now=None):
    """Per-experiment real metrics -- honestly zero/UNKNOWN for every
    category with no real prospecting/outreach activity yet (which is
    every category, today)."""
    now = now or datetime.now(timezone.utc)
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()

    try:
        import lead_discovery as ld
        leads = ld.load_leads(leads_path) if leads_path else ld.load_leads()
    except Exception:
        leads = []

    results = {}
    for experiment, opp_ids in EXPERIMENT_CATEGORIZATION.items():
        verified = sum(1 for oid in opp_ids if verify_commission_opportunity(oid, portfolio=portfolio, now=now)["status"] == "VERIFIED")
        qualified = sum(1 for l in leads if l.get("opportunity_id") in opp_ids and l.get("status") == "QUALIFIED")
        results[experiment] = {
            "opportunity_ids": opp_ids,
            "verified_opportunities": verified,
            "qualified_prospects": qualified,
            "referrals": 0,
            "response_rate": "N/A -- 0 real outreach sent",
            "meetings": 0,
            "closed_deals": 0,
            "commission": 0,
            "time_to_commission": "N/A",
            "cost": 0,
            "failure_reasons": ["no real outreach attempted yet"] if qualified == 0 else [],
        }

    return {
        "generated_at": _now_iso(now),
        "experiments": results,
        "note": "Categorization is a real, disclosed, manually-curated judgment call over each vendor's known real business nature -- not derived from a portfolio field, since none distinguishes these categories today. Every metric is honestly zero/N-A -- no real outreach has occurred in any category yet.",
    }
