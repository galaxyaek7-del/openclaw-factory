"""Galaxy Forge -- Commercial Control Center (new, ADR-202, 2026-08-07).

Answers Phase 12 Section 1 (the CEO revenue dashboard) and Section 18
(the Global Commercial Score) of the founder's "Global Commercial
Revenue Operating System" directive.

Research before writing this module found every real revenue signal it
needed already exists, scattered: channels/ledger.py::revenue_trend()
and reconcile_ledger_to_finance() (real sales trend + finance_data.json
sync), finance_data.json's own totals/byLadder (real, currently $1
because of one known smoke-test record, filtered out below the same way
ceo_home.py already does), customer_pipeline.py::funnel_conversion_
summary() (real conversion), affiliate_commerce/click_tracking.py (real
click volume, currently zero), goos.py's own disclosed CAC/CLV gap.
This module's real job is aggregation and honest tiering -- never a new
source of revenue truth, and never a field promoted to ACTUAL without a
real, cited source.

ACTUAL / ESTIMATED / PROJECTED (the directive's own required tiers):
  ACTUAL     -- a real, already-recorded number from a real ledger.
  ESTIMATED  -- a real, disclosed model applied to real inputs (today,
                only affiliate_commerce/simulation.py's simulated
                conversions -- explicitly never merged into ACTUAL revenue).
  PROJECTED  -- a forward-looking forecast. Honestly empty today:
                strategic_intelligence_core.py::evaluate_strategic_horizons()
                already reports every horizon "NOT ENOUGH EVIDENCE" --
                this factory has no real forecasting model to cite.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
_TEST_RECORD_MARKER = "DELETE-ME"

_LADDER_TO_REVENUE_CATEGORY = {
    # Real, disclosed mapping -- this factory's own Strategic Production
    # Priority Ladder ranks (profit_oracle.py::LADDER_RANKS) are the only
    # real per-sale categorization that exists; there is no independent
    # "subscription/licensing/enterprise/partnership" tag anywhere in
    # finance_data.json's real sale records. ai_saas/b2b_systems are the
    # closest real proxy for recurring/enterprise-shaped revenue --
    # disclosed as a proxy, never presented as a distinct real measurement.
    "ai_saas": "subscription_revenue_proxy",
    "b2b_systems": "enterprise_revenue_proxy",
}


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _real_sales(finance_path=None):
    finance = _read_json(Path(finance_path) if finance_path else _FINANCE_PATH, {})
    return [s for s in finance.get("sales", []) if _TEST_RECORD_MARKER not in str(s.get("product", ""))], finance


def revenue_snapshot(now=None, finance_path=None, ledger_path=None):
    """Section 1's full named line-item set, each tagged ACTUAL/ESTIMATED/
    PROJECTED explicitly -- never displayed without its tier."""
    now = now or datetime.now(timezone.utc)
    sales, finance = _real_sales(finance_path)

    today_str = now.strftime("%Y-%m-%d")
    week_start = (now - __import__("datetime").timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    month_start = now.strftime("%Y-%m-01")

    total_revenue = round(sum(float(s.get("amount", 0)) for s in sales), 2)
    revenue_today = round(sum(float(s.get("amount", 0)) for s in sales if s.get("date") == today_str), 2)
    revenue_this_week = round(sum(float(s.get("amount", 0)) for s in sales if s.get("date", "") >= week_start), 2)
    revenue_this_month = round(sum(float(s.get("amount", 0)) for s in sales if s.get("date", "") >= month_start), 2)

    by_product = {}
    for s in sales:
        by_product[s.get("product", "Unknown")] = round(by_product.get(s.get("product", "Unknown"), 0) + float(s.get("amount", 0)), 2)

    # Recomputed from the DELETE-ME-filtered `sales` list directly --
    # NEVER from finance_data.json's own totalPaddle/byLadder fields,
    # which are written by reconcile_ledger_to_finance()/server.js
    # against the UNFILTERED sales list and would silently re-include
    # the real "contract-test-ladder-DELETE-ME" smoke-test record (a
    # real bug caught live while writing this module -- total_revenue_usd
    # correctly reported $0 while revenue_by_platform still reported the
    # test record's $150 before this fix).
    by_platform = {"KDP": 0, "Etsy": 0, "Gumroad": 0, "Paddle": 0}
    for s in sales:
        platform = s.get("platform")
        if platform in by_platform:
            by_platform[platform] = round(by_platform[platform] + float(s.get("amount", 0)), 2)

    by_ladder = {}
    for s in sales:
        rank = s.get("ladder") or "kdp_books"
        by_ladder[rank] = round(by_ladder.get(rank, 0) + float(s.get("amount", 0)), 2)
    revenue_by_category = {
        _LADDER_TO_REVENUE_CATEGORY.get(k, k): v for k, v in by_ladder.items()
    }

    import channels.ledger as ledger
    trend = ledger.revenue_trend(now=now, ledger_path=ledger_path)

    import customer_pipeline
    conversion = customer_pipeline.funnel_conversion_summary()

    fees = _real_fees_if_ready()
    refunds_note = "0 -- no real refund event has ever been recorded in this factory (no real refunds endpoint is called by any arm today, see channels/base_arm.py::retrieve_refunds())"

    net_revenue = None
    net_revenue_note = "Unknown -- requires both a real revenue figure and real fee data; fee data is only available while a Paddle-ready arm can be queried live"
    if fees.get("status") == "OK":
        total_fees = round(sum((f.get("fee_usd") or 0) for f in fees.get("fees", [])), 2)
        net_revenue = round(total_revenue - total_fees, 2)
        net_revenue_note = "revenue - real Paddle transaction fees (refunds are honestly $0, no real refund event exists)"

    affiliate = _real_affiliate_summary()

    return {
        "generated_at": now.isoformat(),
        "ACTUAL": {
            "total_revenue_usd": total_revenue,
            "revenue_today_usd": revenue_today,
            "revenue_this_week_usd": revenue_this_week,
            "revenue_this_month_usd": revenue_this_month,
            "mrr_usd": 0, "mrr_note": "No real recurring/subscription billing has ever executed in this factory -- honestly $0, not Unknown.",
            "arr_usd": 0, "arr_note": "Same as MRR -- $0 real recurring revenue exists to annualize.",
            "refunds_usd": 0, "refunds_note": refunds_note,
            "fees": fees,
            "net_revenue_usd": net_revenue, "net_revenue_note": net_revenue_note,
            "affiliate_revenue_usd": affiliate["actual_revenue_usd"], "affiliate_revenue_note": affiliate["note"],
            "commission_revenue_usd": affiliate["actual_revenue_usd"], "commission_revenue_note": "Same real source as affiliate_revenue -- this factory has no separate real commission stream today.",
            "product_revenue_usd": total_revenue,
            "subscription_revenue_usd": revenue_by_category.get("subscription_revenue_proxy", 0), "subscription_revenue_note": "Proxy via the ai_saas ladder rank, not a real distinct subscription-billing measurement -- see module docstring.",
            "licensing_revenue_usd": 0, "licensing_revenue_note": "No real ladder rank or sale record maps to licensing today -- honestly $0/no signal, not fabricated.",
            "enterprise_revenue_usd": revenue_by_category.get("enterprise_revenue_proxy", 0), "enterprise_revenue_note": "Proxy via the b2b_systems ladder rank -- see module docstring.",
            "partnership_revenue_usd": 0, "partnership_revenue_note": "business_development.py's real pipeline has 0 platforms past PREPARATION -- no real partnership revenue exists yet.",
            "revenue_by_platform": by_platform,
            "revenue_by_product": by_product,
            "revenue_by_country": {"status": "UNKNOWN", "reason": "No arm in this factory extracts a real customer-country field from any platform response today -- never invented per Section 4's own attribution rule."},
            "conversion": conversion,
            "customer_acquisition_cost": {"status": "NOT_ARCHITECTED", "reason": "No real CAC computation exists anywhere in this factory -- confirmed by direct search, same disclosed gap goos.py already carries for the sibling CLV dimension."},
            "customer_lifetime_value": {"status": "PROXY_ONLY", "reason": "goos.py::DIMENSION_SOURCES['customer_lifetime_value'] -- executive_quality_gate.check_customer_retention_potential() is a real proxy signal, never a real dollar CLV figure."},
        },
        "ESTIMATED": _real_estimated_tier(),
        "PROJECTED": {
            "status": "NOT_AVAILABLE",
            "reason": "strategic_intelligence_core.py::evaluate_strategic_horizons() reports every real horizon (30d/90d/1y/3y/10y) as 'NOT ENOUGH EVIDENCE' -- this factory has no real forecasting model to cite for a projected revenue figure.",
        },
        "revenue_trend": trend,
    }


def _real_fees_if_ready():
    """Real, live Paddle fee data when the Paddle arm is actually ready --
    never a second, competing fee-estimation function. Fails safely to
    an honest gap on any error, never raises."""
    try:
        import channels.paddle_arm
        from channels import registry
        arm = registry.get("paddle")
        if arm is None:
            return {"status": "NOT_IMPLEMENTED", "reason": "paddle arm not registered"}
        return arm.retrieve_fees()
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def _real_affiliate_summary():
    try:
        from affiliate_commerce import click_tracking
        summary = click_tracking.click_summary()
        return {
            "actual_revenue_usd": 0,
            "real_clicks": summary.get("total_clicks", 0),
            "note": "affiliate_commerce/click_tracking.py -- real click count, $0 real commission revenue (no confirmed conversion has ever happened; AMAZON_ASSOCIATE_TAG remains unset).",
        }
    except Exception:
        return {"actual_revenue_usd": 0, "real_clicks": 0, "note": "affiliate_commerce click ledger not available."}


def _real_estimated_tier():
    """ESTIMATED tier: affiliate_commerce/simulation.py's disclosed,
    labeled simulation (ADR-153) -- a real model over real click volume,
    explicitly never merged into ACTUAL revenue above."""
    try:
        from affiliate_commerce import simulation
        report = simulation.simulation_funnel_report()
        return {
            "affiliate_estimated_commission_usd": report.get("total_simulated_commission_usd", 0),
            "assumptions": {
                "conversion_rate_used": report.get("conversion_rate_used"),
                "commission_rate_used": report.get("commission_rate_used"),
            },
            "note": "SIMULATION MODE (ADR-153) -- modeled over real click volume using disclosed assumed rates, never real revenue. Never blended into the ACTUAL tier above.",
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


# ── SECTION 18 — GLOBAL COMMERCIAL SCORE ──
# Same honest-exclusion averaging discipline as commercial_readiness.py
# (ADR-181/200) and executive_score.py before it: average only the
# dimensions with a real computed value this call, never force-average
# in a missing signal as a stand-in.

def global_commercial_score(now=None, finance_path=None):
    now = now or datetime.now(timezone.utc)
    snapshot = revenue_snapshot(now=now, finance_path=finance_path)

    dimensions = {}

    trend = snapshot["revenue_trend"]
    dimensions["revenue_growth"] = {
        "score": None, "source": "not_computed_this_call",
        "reason": trend.get("note") or "recent_7d_revenue_usd is real but $0 -- no real growth trend to score yet",
    }

    total_rev = snapshot["ACTUAL"]["total_revenue_usd"]
    dimensions["net_revenue"] = {
        "score": 0.0 if total_rev == 0 else None,
        "source": "channels/ledger.py + finance_data.json (real, DELETE-ME-filtered)",
        "reason": "0 real revenue recorded" if total_rev == 0 else "not_computed_this_call",
    }

    dimensions["recurring_revenue"] = {"score": 0.0, "source": "real: mrr_usd/arr_usd are honestly $0", "reason": "no real recurring billing has ever executed"}

    try:
        import resilience_monitor
        resilience = resilience_monitor.assess_resilience()
        rscore = resilience.get("resilience_score")
        if isinstance(rscore, (int, float)):
            dimensions["commercial_reliability"] = {"score": rscore, "source": "resilience_monitor.py::assess_resilience()"}
        else:
            dimensions["commercial_reliability"] = {"score": None, "source": "not_computed_this_call", "reason": str(rscore)}
    except Exception as e:
        dimensions["commercial_reliability"] = {"score": None, "source": "not_computed_this_call", "reason": str(e)}

    try:
        import global_opportunity_exchange as gox
        concentration = gox.product_family_distribution()
        families = concentration.get("distribution", {}) if isinstance(concentration, dict) else {}
        real_family_count = len([k for k, v in families.items() if v])
        dimensions["platform_diversification"] = {
            "score": min(100.0, real_family_count * 25.0) if real_family_count else 0.0,
            "source": "global_opportunity_exchange.py::product_family_distribution() -- a real Counter over ACCEPTED decisions, used here as a diversification proxy",
        }
    except Exception as e:
        dimensions["platform_diversification"] = {"score": None, "source": "not_computed_this_call", "reason": str(e)}

    affiliate = snapshot["ACTUAL"]["affiliate_revenue_usd"]
    dimensions["affiliate_revenue"] = {"score": 0.0 if affiliate == 0 else None, "source": "affiliate_commerce/click_tracking.py (real)", "reason": "0 real affiliate revenue" if affiliate == 0 else "not_computed_this_call"}

    dimensions["partnership_revenue"] = {"score": 0.0, "source": "business_development.py's real pipeline (real)", "reason": "0 platforms past PREPARATION stage"}

    conversion = snapshot["ACTUAL"]["conversion"]
    if isinstance(conversion, dict) and conversion.get("conversions"):
        avg_conv = round(sum(c["conversion_pct"] for c in conversion["conversions"]) / len(conversion["conversions"]), 1)
        dimensions["conversion"] = {"score": avg_conv, "source": "customer_pipeline.py::funnel_conversion_summary() (real)"}
    else:
        dimensions["conversion"] = {"score": None, "source": "not_computed_this_call", "reason": conversion.get("reason") if isinstance(conversion, dict) else "Unknown"}

    dimensions["customer_retention"] = {
        "score": None, "source": "not_computed_this_call",
        "reason": "No real per-customer repeat-purchase measurement exists yet -- 0 real customers to measure retention against.",
    }

    dimensions["data_quality"] = {
        "score": None, "source": "not_computed_this_call",
        "reason": "trust_audit.py's report is real but qualitative (no numeric score field) -- see trust_audit.build_trust_audit_report() directly rather than a fabricated number here.",
    }

    scored = [d["score"] for d in dimensions.values() if isinstance(d.get("score"), (int, float))]
    overall = round(sum(scored) / len(scored), 1) if scored else None

    return {
        "generated_at": now.isoformat(),
        "overall": overall,
        "overall_note": f"Average of {len(scored)}/{len(dimensions)} dimensions with a real computed value this call -- never force-averaged." if overall is not None else "No dimension had a real computed score this call.",
        "dimensions": dimensions,
    }


# ── SECTION 19 — COMMERCIAL COMMANDS ──
# The directive's own 10 example CEO questions, each routed to a real,
# already-built function -- never a natural-language model call that
# could paraphrase or invent an answer. "Every answer must contain
# evidence and timestamped data where applicable" (directive's own
# words) -- every handler below returns {answer, evidence, timestamp}.

def _answer(answer, evidence, now):
    return {"answer": answer, "evidence": evidence, "timestamp": now.isoformat()}


def _cmd_todays_revenue(now):
    snap = revenue_snapshot(now=now)
    return _answer(snap["ACTUAL"]["revenue_today_usd"], "commercial_control_center.revenue_snapshot()['ACTUAL']['revenue_today_usd']", now)


def _cmd_highest_net_margin_product(now):
    return _answer(
        {"status": "INSUFFICIENT_DATA"},
        "product_master_catalog.py's cost_usd field is honestly NOT_TRACKED per product -- data/ai_cost_log.jsonl records real AI spend company-wide only, never attributed to a single product. Net margin cannot be computed per-product without a real cost figure.",
        now,
    )


def _cmd_best_platform_for_customers(now):
    return _answer(
        {"status": "INSUFFICIENT_DATA"},
        "No real per-platform CAC/LTV computation exists anywhere in this factory (see revenue_snapshot()['ACTUAL']['customer_acquisition_cost']) -- cannot rank platforms by customer quality without it.",
        now,
    )


def _cmd_biggest_revenue_leak(now):
    try:
        import capital_allocation_engine as cae
        result = cae.opportunity_cost()
        return _answer(result, "capital_allocation_engine.py::opportunity_cost() -- real citation of ACCEPTED opportunities ranked below a higher-scoring alternative", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


def _cmd_active_affiliate_programs(now):
    try:
        import business_development as bd
        result = bd.top_affiliate_opportunities()
        return _answer(result, "business_development.py::top_affiliate_opportunities() (real, WebSearch-evidenced registry)", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


def _cmd_highest_value_partnership(now):
    try:
        import business_development as bd
        opportunities = bd.top_partnership_opportunities(n=1)
        return _answer(opportunities[0] if opportunities else None, "business_development.py::top_partnership_opportunities(n=1)", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


def _cmd_products_to_stop_promoting(now):
    try:
        import strategic_intelligence_core as sic
        brief = sic.build_executive_brief()
        return _answer(brief.get("products_to_pause"), "strategic_intelligence_core.py::build_executive_brief()['products_to_pause'] (real scheduler 'stop' bucket)", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


def _cmd_which_market_next(now):
    try:
        import market_domination_engine as mde
        result = mde.REGIONAL_COVERAGE
        return _answer(result, "market_domination_engine.py::REGIONAL_COVERAGE -- honest per-region real-connector coverage, not a fabricated recommendation", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


def _cmd_reconcile_this_month(now):
    try:
        import commercial_reconciliation as recon
        result = recon.reconcile_all(now=now)
        return _answer(result, "commercial_reconciliation.py::reconcile_all()", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


def _cmd_failed_commercial_operations(now):
    try:
        import channels.ledger as ledger_module
        failures = [e for e in ledger_module.read_events(event_type="publish_attempt") if e.get("ok") is False]
        return _answer(failures[-20:], "channels/ledger.py::read_events(event_type='publish_attempt') filtered to ok=False, most recent 20", now)
    except Exception as e:
        return _answer({"status": "ERROR"}, str(e), now)


COMMERCIAL_COMMANDS = {
    "show me today's revenue": _cmd_todays_revenue,
    "which product has the highest net margin": _cmd_highest_net_margin_product,
    "which platform generates the best customers": _cmd_best_platform_for_customers,
    "find our biggest revenue leak": _cmd_biggest_revenue_leak,
    "show me all active affiliate programs": _cmd_active_affiliate_programs,
    "find the highest-value partnership": _cmd_highest_value_partnership,
    "which products should we stop promoting": _cmd_products_to_stop_promoting,
    "which market should we enter next": _cmd_which_market_next,
    "reconcile this month's revenue": _cmd_reconcile_this_month,
    "show me all failed commercial operations": _cmd_failed_commercial_operations,
}


# ── SECTION 13 — CEO DAILY COMMERCIAL BRIEF ──
# The directive's own 12 named fields, each a real citation over
# functions already built in this round + business_development.py/
# capital_allocation_engine.py -- computes revenue_snapshot() and
# assess_commercial_alerts() exactly once, threads them through every
# field that needs them (same discipline company_pulse()/executive_
# brain.py already established for this class of aggregator).

def commercial_daily_brief(now=None):
    now = now or datetime.now(timezone.utc)
    snap = revenue_snapshot(now=now)
    actual = snap["ACTUAL"]

    best_product = max(actual["revenue_by_product"].items(), key=lambda kv: kv[1], default=None) if any(actual["revenue_by_product"].values()) else None
    best_platform = max(actual["revenue_by_platform"].items(), key=lambda kv: kv[1], default=None) if any(actual["revenue_by_platform"].values()) else None

    try:
        import commercial_alerts
        alerts = commercial_alerts.assess_commercial_alerts(now=now)
        active = alerts["active_alerts"]
        biggest_risk = max(active, key=lambda f: _SEVERITY_RANK.get(f["severity"], 0)) if active else None
    except Exception as e:
        biggest_risk = {"status": "ERROR", "error": str(e)}

    try:
        import business_development as bd
        top_partnership = bd.top_partnership_opportunities(n=1)
        top_affiliate = bd.top_affiliate_opportunities(n=1)
    except Exception as e:
        top_partnership, top_affiliate = [], []

    try:
        import capital_allocation_engine as cae
        revenue_leak = cae.opportunity_cost()
    except Exception as e:
        revenue_leak = {"status": "ERROR", "error": str(e)}

    try:
        import goos
        top_opportunity = goos.rank_build_candidates(top_n=1)
    except Exception as e:
        top_opportunity = {"status": "ERROR", "error": str(e)}

    recommended_action = "No active commercial risk and $0 real revenue -- the recommended action is unchanged from this factory's own standing Golden Rule: focus on the first real dollar (clear Paddle's account-onboarding gate) before any further commercial expansion."
    if biggest_risk and isinstance(biggest_risk, dict) and biggest_risk.get("severity") in ("critical", "emergency"):
        recommended_action = f"Address the {biggest_risk['severity']} finding in '{biggest_risk['area']}' first: {biggest_risk['detail']}"

    return {
        "generated_at": now.isoformat(),
        "revenue_usd": actual["total_revenue_usd"],
        "net_revenue_usd": actual["net_revenue_usd"],
        "best_product": {"name": best_product[0], "revenue_usd": best_product[1]} if best_product else {"status": "NO_REAL_REVENUE_YET"},
        "best_platform": {"name": best_platform[0], "revenue_usd": best_platform[1]} if best_platform else {"status": "NO_REAL_REVENUE_YET"},
        "best_market": actual["revenue_by_country"],
        "best_acquisition_channel": {"status": "INSUFFICIENT_DATA", "reason": "No real per-channel CAC/conversion data exists -- see revenue_snapshot()['ACTUAL']['customer_acquisition_cost']."},
        "top_opportunity": top_opportunity,
        "top_partnership": top_partnership[0] if top_partnership else None,
        "top_affiliate_opportunity": top_affiliate[0] if top_affiliate else None,
        "biggest_commercial_risk": biggest_risk or {"status": "NO_ACTIVE_RISK"},
        "biggest_revenue_leak": revenue_leak,
        "recommended_action": recommended_action,
    }


_SEVERITY_RANK = {"informational": 0, "warning": 1, "critical": 2, "emergency": 3}


def answer_commercial_command(command_text, now=None):
    """Case-insensitive exact match against the directive's own 10 named
    example commands -- never a fuzzy/LLM interpretation that could
    silently answer a different question than the one actually asked."""
    now = now or datetime.now(timezone.utc)
    key = command_text.strip().lower().rstrip(".?")
    handler = COMMERCIAL_COMMANDS.get(key)
    if handler is None:
        return _answer(
            {"status": "UNRECOGNIZED_COMMAND"},
            f"'{command_text}' does not match any of the {len(COMMERCIAL_COMMANDS)} known commercial commands. See commercial_control_center.COMMERCIAL_COMMANDS for the exact supported phrasings.",
            now,
        )
    return handler(now)
