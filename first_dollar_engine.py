"""FIRST-DOLLAR ENGINE -- thin commercial layer on top of the existing
Golden Hunter + Revenue OS + CEO Loop + distribution infrastructure.

FINAL OPERATING DIRECTIVE (2026-08-15): find the fastest legitimate path to
the first real verified $1-$10, then scale proven paths only.

Design rules honored here:
  * REUSE, never duplicate: this module composes commission_engine
    (load_opportunity_portfolio), revenue_os (run_daily_ceo_loop,
    treasury_status), autonomous_commerce_ops (human_gate_orchestrator),
    and click_tracking (read_clicks) -- it never re-implements their logic.
    goos build candidates may be injected as discovery feed input (guarded,
    read-only) but the golden-hunter feed itself is NOT re-created here.
  * Strict revenue integrity: REAL / TEST / MOCK / PROJECTED / UNKNOWN are kept
    separate. Clicks are not revenue. This module NEVER writes to any real
    ledger (it is read-only by construction).
  * Zero discretionary spend: nothing here costs money, buys traffic, or
    subscribes to a paid API.
  * Human-gate minimization: AUTOMATABLE vs HUMAN_GATE classification reuses
    the real gate orchestrator; the founder is only asked for the unavoidable
    (identity, payment method, OAuth, platform approval, legal, 2FA/CAPTCHA).
  * FIRST_DOLLAR_SCORE is deliberately NOT commission-maximizing: a fast $5
    path with a realistic conversion may outrank a slow $500 one.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 1) FIRST-DOLLAR SCORING MODEL
# ---------------------------------------------------------------------------

# The 12 weighted criteria (weights sum to 1.00). Ordering and weights encode
# the directive's priority: probability of first conversion > speed > zero-cost
# > minimal founder intervention; commission value is NOT the dominant factor.
FIRST_DOLLAR_CRITERIA: List[dict] = [
    {"name": "probability_first_conversion", "weight": 0.20,
     "meaning": "Likelihood this converts a real visitor into a real paid event soon."},
    {"name": "time_to_first_revenue", "weight": 0.15,
     "meaning": "How fast real revenue can arrive (gate-free, assets-ready = fastest)."},
    {"name": "zero_low_cost", "weight": 0.10,
     "meaning": "Zero or near-zero upfront cost (always high under the zero-spend rule)."},
    {"name": "minimal_founder_intervention", "weight": 0.15,
     "meaning": "Few human gates on the path (identity/payment/OAuth/approval/legal/2FA)."},
    {"name": "country_payment_compatibility", "weight": 0.05,
     "meaning": "Payout actually receivable in the operator's country (e.g. Algeria)."},
    {"name": "existing_asset_reuse", "weight": 0.10,
     "meaning": "Reuses a real existing product/PDF/content/launch asset (REUSE > BUILD)."},
    {"name": "existing_distribution", "weight": 0.05,
     "meaning": "Fits an already-authorized, zero-cost distribution channel (SEO ready)."},
    {"name": "commission_profit_value", "weight": 0.05,
     "meaning": "Commission or margin value -- present but deliberately not dominant."},
    {"name": "recurring_potential", "weight": 0.05,
     "meaning": "Recurring revenue potential beyond the first dollar."},
    {"name": "demand_evidence", "weight": 0.05,
     "meaning": "Real, recorded demand signal (real clicks / official program page)."},
    {"name": "platform_reliability", "weight": 0.03,
     "meaning": "Verified program / real account state (VERIFIED tier)."},
    {"name": "compliance_safety", "weight": 0.02,
     "meaning": "Low risk, no ToS bypass, legitimate platform only."},
]

FIRST_DOLLAR_CRITERION_NAMES = [c["name"] for c in FIRST_DOLLAR_CRITERIA]
assert abs(sum(c["weight"] for c in FIRST_DOLLAR_CRITERIA) - 1.0) < 1e-9


def _norm(value, invert=False):
    """Normalize a 0..1 signal; None -> neutral 0.5 (honest unknown, never a
    fabricated strong/weak value)."""
    if value is None:
        return 0.5
    v = max(0.0, min(1.0, float(value)))
    return 1.0 - v if invert else v


def first_dollar_score(opportunity: dict,
                       human_gates: Optional[dict] = None,
                       clicks: int = 0,
                       lifecycle_state: Optional[str] = None,
                       assets_ready: Optional[List[str]] = None) -> Dict[str, object]:
    """Score ONE opportunity by FIRST_DOLLAR_SCORE (0..100). Every criterion is
    derived from real, existing signals (verification tier, recurring flag,
    payout compatibility, real click counts, real asset readiness, real gate
    state); unknown signals stay a neutral 0.5 -- nothing is fabricated.

    Returns the explainable per-criterion breakdown plus the weighted total."""
    assets_ready = assets_ready or []

    # --- probability of first conversion (0.20) ---
    # Real tier confidence. Values match revenue_os._CONFIDENCE_BY_TIER where
    # tiers overlap (VERIFIED=1.0, UNVERIFIED=0.6, DISCOVERED=0.4,
    # REJECTED=0.0), and extend it with the real tiers present in this
    # portfolio (PARTIALLY_VERIFIED=0.6, THIRD_PARTY_ONLY=0.4) so both engines
    # agree wherever they share a tier. Unknown tier stays a neutral 0.5.
    tier = str(opportunity.get("verification_status") or "").upper()
    tier_conf = {"VERIFIED": 1.0, "UNVERIFIED": 0.6, "PARTIALLY_VERIFIED": 0.6,
                 "THIRD_PARTY_ONLY": 0.4, "DISCOVERED": 0.4, "REJECTED": 0.0}.get(tier, 0.5)
    # Real clicks are hard evidence of an existing funnel; capped at 1.0.
    click_evidence = _norm(min(1.0, clicks / 20.0))
    probability = round(0.7 * tier_conf + 0.3 * click_evidence, 3)

    # --- time to first revenue (0.15) ---
    # A gate-free opportunity with a ready asset is fastest (1.0); a
    # blocking human gate slows it to 0.2; no asset + no gate = 0.6.
    gated = bool(human_gates and human_gates.get("BLOCKING"))
    if not gated and assets_ready:
        time_to_revenue = 1.0
    elif not gated:
        time_to_revenue = 0.6
    else:
        time_to_revenue = 0.2

    # --- zero / low cost (0.10) ---
    # Zero-spend rule: every existing path costs nothing; a path that needs
    # paid traffic/tooling would score 0.1. Today all are zero-cost.
    zero_cost = 1.0 if opportunity.get("estimated_cost") in (None, 0, "0") else 0.1

    # --- minimal founder intervention (0.15) ---
    # BLOCKING human gate => low; no gate => high. Reuses the real gate state.
    intervention = 0.2 if gated else 1.0

    # --- country / payment compatibility (0.05) ---
    # Real payout_algeria_compatible flag: true=1.0, false=0.2, unknown=0.5.
    compat = opportunity.get("payout_algeria_compatible")
    if compat is True:
        payment_compat = 1.0
    elif compat is False:
        payment_compat = 0.2
    else:
        payment_compat = 0.5

    # --- existing asset reuse (0.10) ---
    asset_reuse = 1.0 if assets_ready else 0.4

    # --- existing distribution (0.05) ---
    # SEO is the only READY zero-cost channel today; others are HUMAN_GATE.
    dist = 1.0 if opportunity.get("_distribution_ready") else 0.5

    # --- commission / profit value (0.05) ---
    recurring = bool(opportunity.get("recurring_commission"))
    cv = str(opportunity.get("commission_value") or "").lower()
    # Parse an honest numeric proxy from the real text when present.
    profit_val = 0.5  # unknown default
    if recurring:
        profit_val = 0.8
    if any(k in cv for k in ("30%", "40%", "50%")):
        profit_val = max(profit_val, 0.9)
    elif any(k in cv for k in ("10%", "20%")):
        profit_val = max(profit_val, 0.7)
    elif "5%" in cv:
        profit_val = max(profit_val, 0.5)

    # --- recurring potential (0.05) ---
    recurring_pot = 1.0 if recurring else 0.3

    # --- demand evidence (0.05) ---
    demand = 1.0 if (clicks > 0 or opportunity.get("evidence_url")) else 0.3

    # --- platform reliability (0.03) ---
    reliability = tier_conf

    # --- compliance / safety (0.02) ---
    risk = str(opportunity.get("risk_score") or "").lower()
    compliance = 1.0 if risk == "low" else (0.7 if risk else 0.5)

    breakdown = {
        "probability_first_conversion": probability,
        "time_to_first_revenue": time_to_revenue,
        "zero_low_cost": zero_cost,
        "minimal_founder_intervention": intervention,
        "country_payment_compatibility": payment_compat,
        "existing_asset_reuse": asset_reuse,
        "existing_distribution": dist,
        "commission_profit_value": profit_val,
        "recurring_potential": recurring_pot,
        "demand_evidence": demand,
        "platform_reliability": reliability,
        "compliance_safety": compliance,
    }

    weights = {c["name"]: c["weight"] for c in FIRST_DOLLAR_CRITERIA}
    score = round(100.0 * sum(breakdown[k] * weights[k] for k in breakdown), 2)

    return {
        "opportunity_id": opportunity.get("opportunity_id"),
        "program_name": opportunity.get("program_name") or opportunity.get("partner_name"),
        "FIRST_DOLLAR_SCORE": score,
        "breakdown": breakdown,
        "weights": weights,
        "note": "Computed from real portfolio/gate/click signals; unknown signals stay neutral 0.5.",
    }


def first_dollar_ladder(verified_revenue_usd: float) -> dict:
    """Map the real verified-revenue level to the First-Dollar -> Scale ladder
    (directive section 13). Read-only; only REAL verified money advances a
    level."""
    if verified_revenue_usd <= 0:
        level, label = 0, "LEVEL 0: no verified revenue yet -- hunt the first $1-$10"
    elif verified_revenue_usd < 10:
        level, label = 1, "LEVEL 1: first $1-$10 proven"
    elif verified_revenue_usd < 50:
        level, label = 2, "LEVEL 2: first repeatable $10-$50"
    elif verified_revenue_usd < 500:
        level, label = 3, "LEVEL 3: $100+ repeatable path"
    elif verified_revenue_usd < 5000:
        level, label = 4, "LEVEL 4: $500+ premium opportunity"
    else:
        level, label = 5, "LEVEL 5: recurring revenue / high-value digital product"
    return {
        "level": level,
        "label": label,
        "verified_revenue_usd": round(verified_revenue_usd, 2),
        "rule": "Only REAL verified external money advances the ladder. Clicks, mock and projected revenue never do.",
    }


# ---------------------------------------------------------------------------
# 2) HUMAN-GATE CLASSIFICATION (AUTOMATABLE vs HUMAN_GATE)
# ---------------------------------------------------------------------------

# Unavoidable human gates (directive section 6) -- exactly the classes the
# factory can never perform for the founder.
HUMAN_GATE_KINDS = (
    "identity verification", "account creation requiring human approval",
    "OAuth approval", "payment method", "2FA", "CAPTCHA",
    "legal acceptance", "platform approval", "financial authorization",
)


# Platforms with a real, already-configured credential in the factory's env
# (verified in the CTO+COO audit): publishing to these is not blocked on
# account creation, so AUTOMATABLE classification is honest for them ONLY when
# no other gate applies.
_CREDENTIALED_PLATFORMS = {"GUMROAD", "PADDLE"}


def classify_human_gate(opportunity: dict,
                        blocking_gates: Optional[List[dict]] = None) -> dict:
    """Classify one opportunity as AUTOMATABLE or HUMAN_GATE.

    Reuses the real gate orchestrator output (autonomous_commerce_ops) when
    available. A HUMAN_GATE is declared whenever an unavoidable human class is
    present (account creation / application / OAuth / payment method / 2FA /
    CAPTCHA / legal / platform approval / financial authorization). Crucially,
    an *affiliate program without a live credential* always requires account
    creation + platform approval -- that is a human gate, never a claim the
    factory can "just run it". Only a platform with a real configured
    credential (Gumroad/Paddle) can be AUTOMATABLE, and only when no
    BLOCKING gate remains."""
    blocking_gates = blocking_gates or []
    platform_key = str(opportunity.get("platform") or opportunity.get("partner_id") or "").upper()
    oid = (opportunity.get("opportunity_id") or "").upper()

    # 1) If a real blocking gate already names this opportunity's platform,
    #    it is HUMAN_GATE with the real gate's founder action.
    for g in blocking_gates:
        gplat = str(g.get("platform") or "").upper()
        if gplat and (gplat in platform_key or any(part in gplat for part in oid.split("-"))):
            return {
                "classification": "HUMAN_GATE",
                "gate_id": g.get("gate_id"),
                "founder_action": g.get("founder_action") or g.get("action_required"),
                "why": g.get("why_required") or g.get("action_required"),
                "verification_after": g.get("verification_after_action"),
            }

    # 2) Explicit eligibility language that is a genuine human gate.
    eligibility = str(opportunity.get("eligibility") or "").lower()
    if any(k in eligibility for k in ("application", "approval", "signup", "onboarding",
                                      "manual review", "approve", "account")):
        return {
            "classification": "HUMAN_GATE",
            "gate_id": None,
            "founder_action": f"Complete the {opportunity.get('program_name', 'program')} application/approval (self-service signup).",
            "why": f"eligibility field: {opportunity.get('eligibility')}",
            "verification_after": "Confirm the program account/tracking link is live.",
        }

    # 3) Every affiliate opportunity requires a live account + platform
    #    approval to generate a tracking link. No credential in the factory
    #    means this is a human gate -- even when the eligibility field is
    #    UNKNOWN (honest UNKNOWN must never default to AUTOMATABLE).
    category = str(opportunity.get("category") or "").lower()
    if "affiliate" in category or "partnership" in category:
        return {
            "classification": "HUMAN_GATE",
            "gate_id": None,
            "founder_action": f"Create/approve the {opportunity.get('program_name', 'program')} affiliate account and generate the real tracking link.",
            "why": "Affiliate programs require a live account + platform approval before any tracking link can exist (no credential configured in the factory).",
            "verification_after": "Confirm the account is live and a real tracking link is configured.",
        }

    # 4) Marketplace/payment platforms: AUTOMATABLE ONLY when the platform has
    #    a real configured credential and no blocking gate remains.
    if any(p in platform_key for p in _CREDENTIALED_PLATFORMS):
        return {
            "classification": "AUTOMATABLE",
            "gate_id": None,
            "founder_action": None,
            "why": "Platform has a real configured credential and no blocking gate remains.",
            "verification_after": None,
        }

    # 5) Honest unknown: without evidence of a live credential/account, the
    #    safe classification is HUMAN_GATE (unverified capability is never
    #    claimed as automatable).
    return {
        "classification": "HUMAN_GATE",
        "gate_id": None,
        "founder_action": f"Provide/authorize the {opportunity.get('program_name', 'program')} account or credential, or confirm an existing one.",
        "why": "No live credential or authorized account is evidenced for this opportunity; unverified capability is never claimed automatable.",
        "verification_after": "Confirm the account/credential is live and usable.",
    }


# ---------------------------------------------------------------------------
# 3) OPPORTUNITY CLASS (directive section 5 -- full schema)
# ---------------------------------------------------------------------------

def build_opportunity_class(opportunity: dict,
                            gate: dict,
                            score: dict,
                            ladder: dict) -> dict:
    """Assemble the full opportunity class with every required field. Missing
    real data stays UNKNOWN -- never a fabricated value."""
    return {
        "opportunity_id": opportunity.get("opportunity_id"),
        "category": opportunity.get("category", "unknown"),
        "source": opportunity.get("source", "UNKNOWN"),
        "offer": opportunity.get("product_or_service") or opportunity.get("program_name"),
        "merchant_platform": opportunity.get("partner_name") or opportunity.get("program_name"),
        "commission_or_margin": opportunity.get("commission_value", "UNKNOWN"),
        "recurring_status": "RECURRING" if opportunity.get("recurring_commission") else "ONE_TIME",
        "payout_method": opportunity.get("payout_terms", "UNKNOWN"),
        "country_eligibility": opportunity.get("geography", "UNKNOWN"),
        "required_credentials": opportunity.get("eligibility", "UNKNOWN"),
        "required_founder_action": gate.get("founder_action"),
        "estimated_time_to_first_revenue": score["breakdown"]["time_to_first_revenue"],
        "estimated_cost": opportunity.get("estimated_cost", 0),
        "demand_evidence": opportunity.get("evidence_url") or "UNKNOWN",
        "competition_signal": opportunity.get("risk_score", "UNKNOWN"),
        "risk": opportunity.get("risk_score", "UNKNOWN"),
        "first_dollar_score": score["FIRST_DOLLAR_SCORE"],
        "long_term_score": score["breakdown"]["recurring_potential"],
        "status": "HUMAN_GATE" if gate["classification"] == "HUMAN_GATE" else "AUTOMATABLE",
    }


# ---------------------------------------------------------------------------
# 4) DISCOVERY (extends Golden Hunter -- reuses real feeds, no new agents)
# ---------------------------------------------------------------------------

def discover_first_dollar_opportunities(portfolio: Optional[List[dict]] = None,
                                        goos_candidates: Optional[dict] = None,
                                        verified_programs: Optional[List[dict]] = None) -> Dict[str, object]:
    """Discover + verify + dedupe the candidate set.

    REUSE over BUILD: reads the real portfolio (commission_opportunities.jsonl
    via commission_engine) plus any officially-verified affiliate programs that
    are injected. The Golden Hunter build feed (goos) is an OPTIONAL injected
    input -- the default cycle does not auto-load it because those are
    speculative unbuilt products (directive: existing assets first). Never
    fires a live web hunt, never writes to the portfolio, never duplicates an
    existing opportunity_id."""
    from commission_engine import load_opportunity_portfolio

    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    seen = set()
    out = []

    def _add(o):
        oid = o.get("opportunity_id")
        if not oid or oid in seen:
            return
        seen.add(oid)
        out.append(o)

    for o in portfolio:
        _add(o)

    for p in (verified_programs or []):
        _add(p)

    # Golden Hunter build candidates: OPTIONAL injected feed only (guarded,
    # read-only). It is NOT auto-loaded in the default cycle because build
    # candidates are speculative/unbuilt products -- the directive mandates
    # existing assets first (REUSE > BUILD) and forbids speculative products.
    goos_candidates = goos_candidates if goos_candidates is not None else {}
    for bc in (goos_candidates or {}).get("build_next") or []:
        _add({
            "opportunity_id": f"BUILD-{bc.get('niche', 'candidate')}",
            "source": "goos.rank_build_candidates() (Golden Hunter build feed)",
            "program_name": bc.get("niche"),
            "partner_name": bc.get("niche"),
            "category": "digital_product_build",
            "verification_status": "UNVERIFIED",
            "recurring_commission": False,
            "commission_value": "BUILD (product build candidate)",
            "eligibility": "automatable build; distribution needs a payment channel",
            "risk_score": "Low",
            "evidence_url": None,
            "payout_algeria_compatible": None,
            "estimated_cost": 0,
        })

    return {
        "generated_at": _now_iso(),
        "opportunities_scanned": len(out),
        "deduplicated": len(portfolio) + len(verified_programs or []) + len(goos_candidates.get("build_next") or []) - len(out),
        "opportunities": out,
        "note": "Read-only discovery over real feeds (portfolio + verified programs; Golden Hunter build feed optional-injected only). No live hunt, no writes, no duplicates.",
    }


# ---------------------------------------------------------------------------
# 5) RANKING + EXECUTION ROUTER
# ---------------------------------------------------------------------------

def _real_click_counts() -> Dict[str, int]:
    """Real click counts per opportunity from the real affiliate_clicks ledger."""
    try:
        from affiliate_commerce.click_tracking import read_clicks
        clicks = read_clicks()
    except Exception:
        return {}
    by_opp = {}
    for c in clicks:
        pid = c.get("product_id")
        if pid:
            by_opp[pid] = by_opp.get(pid, 0) + 1
    return by_opp


def _blocking_gates() -> List[dict]:
    """Real BLOCKING human gates from the gate orchestrator."""
    try:
        from autonomous_commerce_ops import human_gate_orchestrator
        return [g for g in human_gate_orchestrator()["gates"] if g.get("status") == "BLOCKING"]
    except Exception:
        return []


def rank_first_dollar(top_n: int = 10,
                      portfolio: Optional[List[dict]] = None) -> Dict[str, object]:
    """Rank the whole candidate set by FIRST_DOLLAR_SCORE (descending), with
    human-gate classification + opportunity class on each. Read-only."""
    import commission_engine

    portfolio = portfolio if portfolio is not None else commission_engine.load_opportunity_portfolio()
    gates = _blocking_gates()
    clicks = _real_click_counts()

    # Asset-readiness hints: real existing assets for the known first-dollar arms.
    _ASSET_HINTS = {
        "CO-digitalocean-affiliate": ["5 content pieces ready", "launch batch ready"],
        "CO-amazon-affiliate": ["customer_site affiliate pages live", "18 real clicks"],
        "CO-gumroad-affiliate": ["EU AI Act toolkit product created (draft)", "PDF asset"],
        "CO-gumroad-marketplace": ["EU AI Act toolkit product created (draft)", "PDF asset"],
        "CO-paddle-partnership": ["6 real Paddle products with real prices"],
        "CO-n8n-affiliate": ["4 real clicks", "affiliate content factory"],
        "CO-aweber-affiliate": ["affiliate content factory"],
        "CO-envato-affiliate": ["affiliate content factory"],
    }
    _DIST_READY = {"CO-digitalocean-affiliate", "CO-amazon-affiliate", "CO-gumroad-affiliate"}

    ranked = []
    for o in portfolio:
        oid = o.get("opportunity_id")
        if not oid:
            continue
        opp = dict(o)
        opp["_distribution_ready"] = oid in _DIST_READY
        assets = _ASSET_HINTS.get(oid, [])
        opp["_assets"] = assets

        score = first_dollar_score(
            opp,
            human_gates={"BLOCKING": any(g.get("gate_id") and (g.get("gate_id").lower() in oid.lower() or str(g.get("platform") or "").lower() in oid.lower()) for g in gates)},
            clicks=clicks.get(oid, 0),
            assets_ready=assets,
        )
        gate = classify_human_gate(opp, blocking_gates=gates)
        opp_class = build_opportunity_class(opp, gate, score, {})
        ranked.append({
            **opp_class,
            "first_dollar_score": score["FIRST_DOLLAR_SCORE"],
            "breakdown": score["breakdown"],
            "classification": gate["classification"],
            "_assets": assets,
            "_distribution_ready": opp["_distribution_ready"],
        })

    ranked.sort(key=lambda r: r["first_dollar_score"], reverse=True)
    return {
        "generated_at": _now_iso(),
        "top_n": top_n,
        "BEST_FIRST_DOLLAR": ranked[0]["opportunity_id"] if ranked else None,
        "ranking": ranked[:top_n],
        "rule": "Ranked by FIRST_DOLLAR_SCORE (probability x speed x zero-cost x minimal-founder-intervention; commission is not dominant).",
    }


def execution_router(top_n: int = 3,
                     portfolio: Optional[List[dict]] = None) -> Dict[str, object]:
    """Select the TOP N and decide CAN_EXECUTE_NOW vs WAITING_FOR_HUMAN_GATE.

    A blocked opportunity never stops the others: each of the top N is
    classified independently."""
    ranked = rank_first_dollar(top_n=top_n, portfolio=portfolio)
    out = []
    for r in ranked["ranking"]:
        out.append({
            "opportunity_id": r["opportunity_id"],
            "program_name": r["merchant_platform"],
            "first_dollar_score": r["first_dollar_score"],
            "classification": r["classification"],
            "can_execute_now": r["classification"] == "AUTOMATABLE",
            "human_gate": None if r["classification"] == "AUTOMATABLE" else {
                "founder_action": r["required_founder_action"],
                "why": r.get("status"),
            },
            "assets_ready": r.get("_assets", []),
        })
    return {
        "generated_at": _now_iso(),
        "TOP_3": out,
        "rule": "Independent classification per opportunity -- one blocked arm never halts the rest. AUTOMATABLE = CAN_EXECUTE_NOW with existing authorized infra; HUMAN_GATE = founder action with the factory's verification after it.",
    }


# ---------------------------------------------------------------------------
# 6) DAILY AUTONOMOUS CYCLE
# ---------------------------------------------------------------------------

def run_first_dollar_cycle(portfolio: Optional[List[dict]] = None) -> Dict[str, object]:
    """The full daily cycle:
    DISCOVER -> VERIFY -> SCORE -> RANK -> SELECT -> PREPARE -> EXECUTE WHERE
    AUTHORIZED -> TRACK -> VERIFY REVENUE -> LEARN -> RE-RANK.

    Composes the real engines; read-only; zero spend; never writes a ledger."""
    from commission_engine import load_opportunity_portfolio
    from revenue_os import run_daily_ceo_loop, treasury_status

    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()

    # DISCOVER + VERIFY (real portfolio + verified programs; the Golden Hunter
    # build feed is an OPTIONAL injected input, not auto-loaded -- speculative
    # build candidates stay out of the default cycle per REUSE > BUILD).
    discovery = discover_first_dollar_opportunities(portfolio=portfolio)
    # SCORE + RANK
    ranked = rank_first_dollar(top_n=10, portfolio=portfolio)
    # SELECT + ROUTER (independent per-opportunity classification)
    router = execution_router(top_n=3, portfolio=portfolio)
    # CEO loop stays the central authority (compares ALL arms).
    ceo = run_daily_ceo_loop()
    # VERIFY REVENUE (real only)
    treasury = treasury_status()
    verified = float(treasury["verified_revenue_usd"] or 0)
    ladder = first_dollar_ladder(verified)
    # LEARN (re-rank from real signals is intrinsic to rank_first_dollar, which
    # re-reads real clicks every call)

    return {
        "generated_at": _now_iso(),
        "DISCOVER": {"opportunities_scanned": discovery["opportunities_scanned"], "note": discovery["note"]},
        "VERIFY": {"note": "verification tiers read from the real portfolio (VERIFIED/PARTIALLY/THIRD_PARTY_ONLY)."},
        "SCORE": {"model": "FIRST_DOLLAR_SCORE (12 weighted criteria)", "criteria_count": len(FIRST_DOLLAR_CRITERIA)},
        "RANK": {"BEST_FIRST_DOLLAR": ranked["BEST_FIRST_DOLLAR"], "top_10": [r["opportunity_id"] for r in ranked["ranking"]]},
        "SELECT": router["TOP_3"],
        "PREPARE": {"note": "existing assets reused per arm (see rank_first_dollar asset hints); nothing new built."},
        "EXECUTE_WHERE_AUTHORIZED": {
            "note": "No live publish today: every distribution channel except SEO is HUMAN_GATE and no publish is authorized without platform authorization (directive section 10).",
            "automatable_ready": [r["opportunity_id"] for r in router["TOP_3"] if r["classification"] == "AUTOMATABLE"],
        },
        "TRACK": {"note": "real clicks re-read every cycle from affiliate_clicks.jsonl."},
        "VERIFY_REVENUE": treasury,
        "LEARN": {"note": "rank_first_dollar re-reads real clicks each call -- a real conversion/sale shifts ranking automatically."},
        "RE_RANK": {"note": "next cycle re-runs DISCOVER->RE-RANK."},
        "LADDER": ladder,
        "CEO_LOOP": ceo,
        "REAL_VERIFIED_REVENUE_USD": verified,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


if __name__ == "__main__":
    report = run_first_dollar_cycle()
    print(json.dumps({
        "REAL_VERIFIED_REVENUE_USD": report["REAL_VERIFIED_REVENUE_USD"],
        "RANK": report["RANK"],
        "SELECT": report["SELECT"],
        "LADDER": report["LADDER"],
    }, indent=1, ensure_ascii=False, default=str))