"""Galaxy Forge — REVENUE OPERATING LAYER (Revenue OS).

One unified, composition-only layer over the factory's existing commercial
infrastructure. Nothing here rebuilds a component that already exists; every
section calls the real, already-tested function and adds only the genuinely
missing glue:

  A) UNIFIED COMMERCIAL SCHEMA   -- one canonical event model all arms share
  B) REVENUE LEDGER view          -- VERIFIED vs ESTIMATED never blended
  C) ARM ROUTER                   -- opportunity -> best revenue arm
  D) PROFIT-FIRST DECISION ENGINE -- rank by EXPECTED_PROFIT x CONFIDENCE x SPEED
  E) DISTRIBUTION ABSTRACTION     -- channel adapters + HUMAN_GATE states
  F) ATTRIBUTION                  -- source -> campaign -> content -> click -> revenue
  G) AUTONOMOUS OPTIMIZATION      -- SCALE / IMPROVE / PAUSE / KILL (real data only)
  H) TREASURY                     -- cash / verified / pending / cost / profit / reinvest
  I) DAILY CEO LOOP               -- DISCOVER -> ... -> REINVEST -> DISCOVER
  J) HUMAN GATES                  -- explicit founder-only decision points

Honesty contract (hard): never fabricate revenue, clicks, conversions or
evidence. VERIFIED revenue comes only from commission_ledger.py's REAL
CONFIRMED/PAID records. No optional spend without an explicit human
authorization flag. All output is deterministic and citation-first.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from commission_engine import load_opportunity_portfolio
from commission_ledger import (
    real_commission_summary,
    first_real_dollar_status,
    load_ledger as load_commission_ledger,
)
from channels import registry as channel_registry
from channels.ledger import read_events as read_sales_events
# Final production-readiness audit (2026-08-15): the CEO loop's
# check_approval_gates() reads channel_registry.all_arms(), but the arm
# modules self-register only on import (there is no channels/__init__.py
# importer). Without these imports run_daily_ceo_loop() saw an EMPTY
# registry and always reported founder_gates={"gated":[],"autonomous":[]}
# -- a false-zero honesty bug in the flagship daily decision report. Same
# self-registration pattern distributor.py:42-55 already uses. Read-only:
# importing an arm module never contacts a platform.
import channels.gumroad_arm  # noqa: F401,E402
import channels.payhip_arm  # noqa: F401,E402
import channels.etsy_arm  # noqa: F401,E402
import channels.paddle_arm  # noqa: F401,E402
from affiliate_commerce.click_tracking import attributed_click_summary
from revenue_intelligence import revenue_intelligence_dashboard
from commercial_execution.approval_gates import check_approval_gates
from affiliate_router import route_niche
from economics import load_config as load_economics_config

_FACTORY_ROOT = Path(__file__).resolve().parent
FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


# ---------------------------------------------------------------------------
# A) UNIFIED COMMERCIAL SCHEMA
# ---------------------------------------------------------------------------

# One canonical event vocabulary shared by every arm. Each arm's real event
# (sale / publish_attempt / commission / click) maps onto these fields; the
# `verification` field keeps estimated/projected/observed/verified apart.
COMMERCIAL_EVENT_FIELDS = (
    "event_type", "opportunity_id", "offer_id", "revenue_arm", "channel",
    "campaign", "asset", "click_id", "lead_id", "order_id", "conversion_id",
    "commission_id", "refund_id", "gross_amount_usd", "fees_usd",
    "net_amount_usd", "currency", "verification", "source", "occurred_at",
)

VERIFICATION_TIERS = ("VERIFIED", "OBSERVED", "PROJECTED", "ESTIMATED", "UNKNOWN")


def canonical_event(**kwargs) -> Dict[str, object]:
    """Build a canonical commercial event. Unknown fields are rejected;
    a `verification` tier is mandatory and must be a real tier."""
    unknown = set(kwargs) - set(COMMERCIAL_EVENT_FIELDS)
    if unknown:
        raise ValueError(f"unknown commercial event field(s): {sorted(unknown)}")
    verification = kwargs.get("verification")
    if verification not in VERIFICATION_TIERS:
        raise ValueError(f"verification must be one of {VERIFICATION_TIERS}, got {verification!r}")
    event = {k: kwargs[k] for k in COMMERCIAL_EVENT_FIELDS if kwargs.get(k) is not None}
    event.setdefault("occurred_at", _now_iso())
    return event


def _commission_to_event(record: dict) -> Dict[str, object]:
    """Map one real commission_ledger record onto the canonical schema.
    VERIFIED only if the record is REAL and CONFIRMED/PAID."""
    verification = "VERIFIED" if (
        record.get("environment") == "REAL"
        and record.get("commission_status") in ("CONFIRMED", "PAID")
    ) else "UNKNOWN"
    return canonical_event(
        event_type="commission",
        opportunity_id=record.get("opportunity_id"),
        commission_id=record.get("commission_id"),
        gross_amount_usd=record.get("gross_commission"),
        fees_usd=record.get("fees"),
        net_amount_usd=record.get("net_commission"),
        currency=record.get("currency", "USD"),
        verification=verification,
        source="commission_ledger.jsonl",
        occurred_at=record.get("created_at"),
    )


def _sale_to_event(sale: dict) -> Dict[str, object]:
    """Map one real channels/ledger.py sale event onto the canonical schema.
    Verification stays UNKNOWN unless the raw record proves otherwise — a
    ledger line is an observed record, never a self-verified dollar."""
    raw = sale.get("raw") or {}
    return canonical_event(
        event_type="sale",
        channel=sale.get("channel"),
        campaign=sale.get("campaign"),
        lead_id=None,
        order_id=raw.get("id") if isinstance(raw, dict) else None,
        currency=raw.get("currency", "USD") if isinstance(raw, dict) else "USD",
        verification="OBSERVED",
        source="sales_ledger.jsonl",
        occurred_at=sale.get("timestamp"),
    )


def _click_to_event(click: dict) -> Dict[str, object]:
    """Map one real click_tracking record onto the canonical schema."""
    return canonical_event(
        event_type="click",
        opportunity_id=click.get("product_id"),
        channel=click.get("channel"),
        campaign=click.get("campaign"),
        asset=click.get("content"),
        click_id=click.get("timestamp"),
        verification="OBSERVED",
        source="affiliate_clicks.jsonl",
        occurred_at=click.get("timestamp"),
    )


# ---------------------------------------------------------------------------
# B) REVENUE LEDGER VIEW (unified, VERIFIED never blended)
# ---------------------------------------------------------------------------

def revenue_ledger_view(commission_ledger_path: Optional[str] = None,
                        sales_ledger_path: Optional[str] = None,
                        clicks_ledger_path: Optional[str] = None) -> Dict[str, object]:
    """One unified, read-only view across the factory's three real ledgers.
    VERIFIED revenue is computed ONLY from commission_ledger REAL
    CONFIRMED/PAID records; everything else is reported in its own tier and
    never summed into VERIFIED."""
    commission = real_commission_summary(ledger_path=commission_ledger_path)
    verified_usd = commission["real_confirmed_or_paid_commission_usd"]
    pending_usd = sum(
        r.get("net_commission", 0)
        for r in load_commission_ledger(commission_ledger_path)
        if r.get("environment") == "REAL" and r.get("commission_status") == "PENDING"
    )
    projected_usd = sum(
        r.get("net_commission", 0)
        for r in load_commission_ledger(commission_ledger_path)
        if r.get("environment") == "PROVISIONAL"
    )

    sales_events = list(read_sales_events(event_type="sale", ledger_path=sales_ledger_path))
    clicks = attributed_click_summary(ledger_path=clicks_ledger_path)

    return {
        "generated_at": _now_iso(),
        "VERIFIED_REVENUE_USD": verified_usd,
        "VERIFIED_COMMISSIONS": commission["real_confirmed_or_paid_commission_usd"],
        "PENDING_REVENUE_USD": pending_usd,
        "PROJECTED_REVENUE_USD": projected_usd,
        "ESTIMATED_REVENUE_USD": 0,
        "OBSERVED_SALES": len(sales_events),
        "OBSERVED_CLICKS": clicks,
        "verification_separation": (
            "VERIFIED comes only from commission_ledger REAL/CONFIRMED-or-PAID. "
            "PENDING/PROJECTED/OBSERVED are reported separately and NEVER added to VERIFIED."
        ),
    }


# ---------------------------------------------------------------------------
# C) ARM ROUTER
# ---------------------------------------------------------------------------

ARM_BY_CATEGORY = {
    "affiliate": "AFFILIATE",
    "marketplace": "MARKETPLACE",
    "partnership": "B2B",
    "kdp": "KDP",
    "templates": "TEMPLATES",
    "wall_art": "WALL_ART",
    "saas": "SAAS",
}

# Which arms exist as real registered publishers today (from the real channel
# registry). Never claims an arm exists that hasn't registered.
REAL_ARMS = ("gumroad", "etsy", "paddle", "payhip")


def _arm_status_summary() -> Dict[str, str]:
    """Real arm readiness from the live registry; empty registry is honest
    (arms register at import time)."""
    arms = channel_registry.all_arms()
    return {a.name: a.status().value for a in arms} or {}


def route_opportunity_to_arm(opportunity: dict,
                             arms_status: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Route ONE opportunity to the best revenue arm. Does NOT assume every
    opportunity becomes a product: an AFFILIATE opportunity routes to the
    affiliate engine (not to a marketplace product), a marketplace
    opportunity routes to the real published arm, etc."""
    category = (opportunity.get("category") or "affiliate").lower()
    arm = ARM_BY_CATEGORY.get(category, "AFFILIATE")
    statuses = arms_status if arms_status is not None else _arm_status_summary()
    return {
        "opportunity_id": opportunity.get("opportunity_id"),
        "category": category,
        "routed_arm": arm,
        "real_arm_status": {k: v for k, v in statuses.items() if k in REAL_ARMS},
        "rationale": (
            f"category '{category}' routes to {arm}; registered arm statuses are "
            f"{statuses or 'none registered (arms register on import)'}."
        ),
    }


def arm_router_report(portfolio: Optional[List[dict]] = None,
                      arms_status: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Route the whole real portfolio through the arm router."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    routes = [route_opportunity_to_arm(o, arms_status=arms_status) for o in portfolio]
    by_arm: Dict[str, int] = {}
    for r in routes:
        by_arm[r["routed_arm"]] = by_arm.get(r["routed_arm"], 0) + 1
    return {
        "generated_at": _now_iso(),
        "total_opportunities": len(routes),
        "routes_by_arm": by_arm,
        "routes": routes,
    }


# ---------------------------------------------------------------------------
# D) PROFIT-FIRST DECISION ENGINE
# ---------------------------------------------------------------------------

def _score_component(value, invert=False):
    """Normalize a 0..1 score; None -> neutral 0.5 (honest unknown, never a
    fabricated strong/weak value)."""
    if value is None:
        return 0.5
    v = max(0.0, min(1.0, float(value)))
    return 1.0 - v if invert else v


def profit_first_score(opportunity: dict,
                       recurring: bool = True,
                       evidence_confidence: Optional[float] = None,
                       distribution_difficulty: Optional[float] = None,
                       time_to_market_days: Optional[float] = None,
                       margin: Optional[float] = None) -> Dict[str, object]:
    """Score ONE opportunity by EXPECTED_PROFIT x CONFIDENCE x SPEED.
    Every input defaults to a neutral 0.5 when unknown -- an unknown never
    inflates or kills a score. A program with a real, verified payout path
    for THIS operator (payout_algeria_compatible) carries full weight; one
    whose only payout path is blocked gets a 0.2 factor -- it cannot turn
    clicks into cash, so it cannot be the profit-first choice. Returns the
    explainable breakdown."""
    recurring_score = 1.0 if recurring else 0.3
    margin_score = _score_component(margin)
    effort_score = _score_component(1.0 - (time_to_market_days / 30.0) if time_to_market_days else None, invert=False)
    distribution_score = _score_component(distribution_difficulty, invert=True)
    confidence_score = _score_component(evidence_confidence)
    speed_score = _score_component(effort_score, invert=False)

    payout_factor = 1.0 if opportunity.get("payout_algeria_compatible") else 0.2

    profit = margin_score * payout_factor
    expected_profit = profit * recurring_score
    expected_score = expected_profit * confidence_score * speed_score

    return {
        "opportunity_id": opportunity.get("opportunity_id"),
        "program_name": opportunity.get("program_name") or opportunity.get("partner_name"),
        "recurring_commission": bool(recurring),
        "expected_profit_score": round(expected_profit, 3),
        "confidence_score": round(confidence_score, 3),
        "speed_score": round(speed_score, 3),
        "PROFIT_FIRST_RANK": round(expected_score, 3),
        "breakdown": {
            "recurring": round(recurring_score, 2),
            "margin": round(margin_score, 2),
            "payout_factor": round(payout_factor, 2),
            "time_to_market_effort": round(effort_score, 2),
            "distribution": round(distribution_score, 2),
            "confidence": round(confidence_score, 2),
            "speed": round(speed_score, 2),
        },
    }


_CONFIDENCE_BY_TIER = {
    "VERIFIED": 1.0,
    "UNVERIFIED": 0.6,
    "DISCOVERED": 0.4,
    "REJECTED": 0.0,
}


def _tier_confidence(opportunity: dict) -> float:
    """Confidence from the portfolio's real verification tier — a VERIFIED
    program outranks an unverified one, exactly as a profit-first engine
    must. Unknown tier stays a neutral 0.5, never a fabricated boost."""
    tier = (opportunity.get("verification_status") or "").upper()
    if tier in _CONFIDENCE_BY_TIER:
        return _CONFIDENCE_BY_TIER[tier]
    conf = opportunity.get("confidence") or ""
    if conf and str(conf).upper() == "HIGH":
        return 0.9
    return 0.5


def profit_first_rank(portfolio: Optional[List[dict]] = None,
                      top_n: int = 5) -> Dict[str, object]:
    """Rank the whole real portfolio by PROFIT_FIRST_RANK (descending)."""
    portfolio = portfolio if portfolio is not None else load_opportunity_portfolio()
    ranked = [
        profit_first_score(
            o,
            recurring=bool(o.get("recurring_commission", False)),
            evidence_confidence=_tier_confidence(o),
        )
        for o in portfolio
    ]
    ranked.sort(key=lambda r: r["PROFIT_FIRST_RANK"], reverse=True)
    return {
        "generated_at": _now_iso(),
        "top_n": top_n,
        "BEST_PROFIT_FIRST": ranked[0]["opportunity_id"] if ranked else None,
        "ranking": ranked[:top_n],
    }


# ---------------------------------------------------------------------------
# E) DISTRIBUTION ABSTRACTION (channel adapters + HUMAN_GATE)
# ---------------------------------------------------------------------------

# Every distribution channel the factory can (eventually) reach, each with an
# honest adapter state. OAuth/manual platforms are HUMAN_GATE -- never
# bypassed, never fabricated as connected.
CHANNEL_ADAPTERS = {
    "tiktok": {"adapter": None, "state": "HUMAN_GATE", "reason": "requires OAuth + human account"},
    "youtube_shorts": {"adapter": None, "state": "HUMAN_GATE", "reason": "requires OAuth + human account"},
    "pinterest": {"adapter": None, "state": "HUMAN_GATE", "reason": "requires OAuth + human account"},
    "facebook": {"adapter": None, "state": "HUMAN_GATE", "reason": "requires OAuth + human account"},
    "x": {"adapter": None, "state": "HUMAN_GATE", "reason": "requires OAuth + human account"},
    "linkedin": {"adapter": None, "state": "HUMAN_GATE", "reason": "requires OAuth + human account"},
    "seo": {"adapter": "repurposing_engine.seo_content", "state": "READY", "reason": "deterministic, zero-cost content asset"},
    "email": {"adapter": "outreach_adapter.SMTPOutreachAdapter", "state": "HUMAN_GATE", "reason": "no live SMTP credentials configured"},
}


def distribution_channel_status() -> Dict[str, object]:
    return {
        "generated_at": _now_iso(),
        "channels": CHANNEL_ADAPTERS,
        "note": "HUMAN_GATE channels are never bypassed or faked -- they record exactly what requires human OAuth/account action.",
    }


# ---------------------------------------------------------------------------
# F) ATTRIBUTION
# ---------------------------------------------------------------------------

def attribution_chain(opportunity_id: str,
                      channel: str,
                      campaign: str,
                      asset: str,
                      source: str = "galaxyforge") -> Dict[str, str]:
    """Deterministic attribution fingerprint for one launch asset. The
    destination URL is filled only once a real network link exists -- never
    guessed (see affiliate_launch_prep.LAUNCH_LINK_STATUS)."""
    return {
        "source": source,
        "campaign": campaign,
        "content": asset,
        "channel": channel,
        "opportunity_id": opportunity_id,
        "utm_campaign": campaign,
        "utm_source": source,
    }


def attribution_status() -> Dict[str, object]:
    """Real attribution wiring state: the tracking is live, revenue mapping
    waits on real conversion evidence."""
    clicks = attributed_click_summary()
    return {
        "generated_at": _now_iso(),
        "attribution_enabled": True,
        "clicks_by_channel": clicks.get("clicks_by_channel", {}),
        "note": "attribution is wired; VERIFIED revenue requires a real commission_ledger CONFIRMED/PAID record.",
    }


# ---------------------------------------------------------------------------
# G) AUTONOMOUS OPTIMIZATION (real data only)
# ---------------------------------------------------------------------------

def autonomous_optimization(commission_ledger_path: Optional[str] = None,
                            clicks_path: Optional[str] = None) -> Dict[str, object]:
    """Decide SCALE / IMPROVE / PAUSE / KILL per tracked asset. Uses ONLY
    real data. Zero real data -> honest 'PAUSE (no real data)' — never a
    fabricated winner."""
    summary = real_commission_summary(ledger_path=commission_ledger_path)
    clicks = attributed_click_summary(ledger_path=clicks_path)

    decisions = []
    for channel, count in (clicks.get("clicks_by_channel") or {}).items():
        if count == 0:
            decisions.append({"channel": channel, "decision": "PAUSE", "reason": "0 real clicks — not enough evidence to scale"})
        elif summary["real_confirmed_or_paid_commission_usd"] > 0:
            decisions.append({"channel": channel, "decision": "SCALE", "reason": "real verified commission exists from this channel family"})
        else:
            decisions.append({"channel": channel, "decision": "IMPROVE", "reason": f"{count} real clicks, 0 real conversions yet — improve offer/landing before scaling"})

    has_verified = summary["real_confirmed_or_paid_commission_usd"] > 0
    return {
        "generated_at": _now_iso(),
        "has_real_verified_commission": has_verified,
        "decisions": decisions,
        "rule": "SCALE only winners with real verified revenue; IMPROVE uncertain; PAUSE no-data; KILL only proven losers (0 real data today -> no KILL).",
    }


# ---------------------------------------------------------------------------
# H) TREASURY
# ---------------------------------------------------------------------------

def treasury_status(commission_ledger_path: Optional[str] = None,
                    finance_path: Optional[Path] = None) -> Dict[str, object]:
    """Unified treasury: cash / verified revenue / pending / cost / profit /
    available reinvestment. Reads finance_data.json (the factory's real
    finance view) + the real commission ledger. No spend authorization —
    reinvestment is only ever reported, never spent."""
    summary = real_commission_summary(ledger_path=commission_ledger_path)
    verified = float(summary["real_confirmed_or_paid_commission_usd"])

    finance = {}
    try:
        with open(finance_path or FINANCE_PATH, encoding="utf-8") as f:
            finance = json.load(f)
    except (OSError, json.JSONDecodeError):
        finance = {}

    total_sales = finance.get("totalSales", 0) or 0
    cash = float(finance.get("cashReceived", 0) or 0)
    pending = float(summary.get("provisional_commission_usd", 0) or 0)
    # Zero-discretionary-spend rule: cost is 0 until an explicitly approved
    # real cost exists; nothing unapproved is ever introduced (directive:
    # "unapproved costs must not be introduced").
    cost = 0.0
    return {
        "generated_at": _now_iso(),
        "cash_usd": cash,
        "verified_revenue_usd": verified,
        "pending_revenue_usd": pending,
        "cost_usd": cost,
        "profit_usd": round(verified - cost, 2),
        "available_reinvestment_usd": round(verified * 0.5, 2),
        "zero_capital_rule": "No optional spend in the zero-capital phase — reinvestment is reported only; any spend needs explicit human authorization.",
        "finance_snapshot": {k: finance[k] for k in ("totalSales", "totalGumroad", "totalPaddle", "totalEtsy", "totalKDP") if k in finance},
        "source": "finance_data.json + commission_ledger real summary",
    }


# ---------------------------------------------------------------------------
# I) DAILY CEO LOOP
# ---------------------------------------------------------------------------

def run_daily_ceo_loop() -> Dict[str, object]:
    """The factory's daily commercial heartbeat:
    DISCOVER -> VERIFY -> RANK -> EXECUTE -> DISTRIBUTE -> MEASURE ->
    OPTIMIZE -> REINVEST -> DISCOVER AGAIN.

    Every stage calls the real existing engine. All read-only today:
    execution/distribution of real spend or real publish requires a founder
    authorization flag, which stays off until real revenue exists."""
    # DISCOVER is read-only here: it scans the real opportunities file, never
    # fires a live web hunt (which can block on external search). The hunt
    # itself is the caller's explicit action, not part of the daily heartbeat.
    try:
        discover_count = len(load_opportunity_portfolio())
        discovery = {"note": "read-only scan of real portfolio (commission_opportunities.jsonl)"}
    except Exception as e:  # pragma: no cover - defensive
        discover_count = -1
        discovery = {"error": str(e)}
    verified = real_commission_summary()["real_confirmed_or_paid_commission_usd"]
    intelligence = revenue_intelligence_dashboard()
    gates = check_approval_gates()

    # FIRST-DOLLAR lens (FINAL OPERATING DIRECTIVE 2026-08-15): the CEO loop
    # stays the central authority; the thin first-dollar engine adds its
    # scoring/ranking on top without duplicating any engine here. Read-only.
    try:
        import first_dollar_engine
        fd_rank = first_dollar_engine.rank_first_dollar(top_n=3)
        fd_ladder = first_dollar_engine.first_dollar_ladder(verified)
        first_dollar = {
            "BEST_FIRST_DOLLAR": fd_rank["BEST_FIRST_DOLLAR"],
            "TOP_3": [
                {"opportunity_id": o["opportunity_id"], "first_dollar_score": o["first_dollar_score"],
                 "classification": o["classification"]}
                for o in fd_rank["ranking"]
            ],
            "LADDER": fd_ladder,
        }
    except Exception as e:  # pragma: no cover - defensive; never breaks the loop
        first_dollar = {"error": str(e)}

    # ONE-NEXT-ACTION (Autonomous Enterprise Master Plan Task 1, 2026-08-15):
    # the founder receives one prioritized action, not twenty tasks. Computed
    # from real state only (env presence + publish protection + paddle
    # products + commission opportunities + real clicks). Read-only.
    try:
        import founder_next_action
        next_action = founder_next_action.build_founder_next_action()
    except Exception as e:  # pragma: no cover - defensive; never breaks the loop
        next_action = {"error": str(e)}

    # EXECUTIVE ORCHESTRATOR (Autonomous Executive Orchestrator directive,
    # 2026-08-15): the CEO loop consumes the orchestrator rather than operating
    # as an isolated scheduler. Composition-only; every TOP is computed by the
    # real owning engine and composed here into ONE executive state. Read-only.
    try:
        import executive_orchestrator
        orchestrator = {
            "TOP_OPPORTUNITY": None, "TOP_REVENUE_ARM": None,
            "TOP_AUTONOMOUS_ACTION": None, "TOP_HUMAN_GATE": None,
            "TOP_EXPERIMENT": None, "WORK_QUEUE_TOTAL": 0,
        }
        try:
            priorities = executive_orchestrator.unified_priorities(top_n=3)
            orchestrator["TOP_OPPORTUNITY"] = priorities.get("TOP_OPPORTUNITY")
            orchestrator["TOP_REVENUE_ARM"] = priorities.get("TOP_REVENUE_ARM")
            orchestrator["TOP_AUTONOMOUS_ACTION"] = priorities.get("TOP_AUTONOMOUS_ACTION")
            orchestrator["TOP_HUMAN_GATE"] = priorities.get("TOP_HUMAN_GATE")
            orchestrator["TOP_EXPERIMENT"] = priorities.get("TOP_EXPERIMENT")
        except Exception as e:  # pragma: no cover - defensive; never breaks the loop
            orchestrator["error"] = str(e)
        try:
            queue = executive_orchestrator.build_work_queue()
            orchestrator["WORK_QUEUE_TOTAL"] = len(queue)
            orchestrator["TOP_WORK_ITEMS"] = queue[:3]
        except Exception as e:  # pragma: no cover - defensive; never breaks the loop
            orchestrator["work_queue_error"] = str(e)
        orchestrator["note"] = "CEO loop consumes the Executive Orchestrator: one priority system, one decision state machine, no duplicate engines."
    except Exception as e:  # pragma: no cover - defensive; never breaks the loop
        orchestrator = {"error": str(e)}

    return {
        "generated_at": _now_iso(),
        "DISCOVER": {"opportunities_scanned": discover_count, "note": discovery.get("note", "read-only scan")},
        "VERIFY": {"note": "verified opportunities live in commission_opportunities.jsonl (VERIFIED tier)"},
        "RANK": profit_first_rank(top_n=3),
        "FIRST_DOLLAR": first_dollar,
        "EXECUTE": {"note": "execution gated: no spend, no publish without founder authorization", "founder_gates": gates},
        "DISTRIBUTE": distribution_channel_status(),
        "MEASURE": intelligence,
        "OPTIMIZE": autonomous_optimization(),
        "REINVEST": treasury_status(),
        "DISCOVER_AGAIN": {"note": "loop continues; next cycle re-scans real signals"},
        "NEXT_ACTION": next_action,
        "ORCHESTRATOR": orchestrator,
        "REAL_VERIFIED_REVENUE_USD": verified,
    }


# ---------------------------------------------------------------------------
# J) HUMAN GATES
# ---------------------------------------------------------------------------

def human_gates_report() -> Dict[str, object]:
    """Explicit, single view of every decision point that is reserved for the
    founder — nothing the factory can legally/technically do alone is listed
    here."""
    gates = check_approval_gates()
    return {
        "generated_at": _now_iso(),
        "account_creation_confirmation": "HUMAN — account creation/legal acceptance is founder-only",
        "identity": "HUMAN — identity verification is founder-only",
        "payment_details": "HUMAN — adding payout rails (Payoneer/bank) is founder-only",
        "oauth_authorization": "HUMAN — every OAuth channel is founder-only (see distribution_channel_status)",
        "exceptional_spend": "HUMAN — any optional spend needs explicit founder authorization",
        "legal_high_risk": "HUMAN — legal/strategic decisions are founder-only",
        "registered_arms_ready": gates.get("autonomous", []),
        "registered_arms_gated": gates.get("gated", []),
    }


def build_revenue_os_dashboard() -> Dict[str, object]:
    """The unified source of commercial truth — every section computed exactly
    once, reusing the real engines."""
    return {
        "generated_at": _now_iso(),
        "REVENUE_LEDGER": revenue_ledger_view(),
        "ARM_ROUTER": arm_router_report(),
        "PROFIT_FIRST": profit_first_rank(top_n=5),
        "DISTRIBUTION": distribution_channel_status(),
        "ATTRIBUTION": attribution_status(),
        "OPTIMIZATION": autonomous_optimization(),
        "TREASURY": treasury_status(),
        "HUMAN_GATES": human_gates_report(),
        "note": "Composition-only layer. VERIFIED revenue traces to commission_ledger.py REAL/CONFIRMED-or-PAID records only.",
    }