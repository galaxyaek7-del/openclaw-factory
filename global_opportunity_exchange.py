#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Global Opportunity Exchange (GOX) (2026-07-29) — "GLOBAL OPPORTUNITY
EXCHANGE" directive: every monitored marketplace treated as a live
asset, portfolio-value optimization (never one marketplace), and
concentration-risk detection against 4 named thresholds.

A research audit before writing any code found this directive collides
directly with facts CLAUDE.md itself already documents as a deliberate,
founder-confirmed 2026-07-23 decision: zero real local-market data
connectors exist for any country, and only 4 of the 15 named
marketplaces (etsy, gumroad, payhip, paddle) have a real registered
channel arm today. This module is, by design, the most DISCOVERY-heavy
of this session's CEO-style-directive modules -- that emptiness is the
correct, honest disclosure of this factory's real current state (4 real
channels, 0 real sale events, 3 real ACCEPTED opportunities), never
backfilled or fabricated to look more built-out than it is.

Every function here is read-only/recommend-only. Diversification
recommendations are real, mechanical citations of a real threshold
being crossed -- never a fabricated suggestion, and never auto-executed
(the Founder always approves, matching this factory's universal
recommend-only discipline)."""

from collections import Counter
from datetime import datetime, timezone

# The directive's 15 named marketplaces. Only 4 have a real registered
# channel arm today (channels/registry.py, confirmed via distributor.py's
# real self-registration import) -- mapped here exactly like growth_engine.
# py::premium_product_catalog_status()'s own _PREMIUM_CATEGORY_FAMILY
# pattern: real arm name when one exists, honestly None otherwise.
_MARKETPLACE_ARM = {
    "Amazon KDP": None,
    "Gumroad": "gumroad",
    "Etsy": "etsy",
    "Creative Market": None,
    "ThemeForest": None,
    "Envato": None,
    "AliExpress Affiliate": None,
    "Amazon Associates": None,
    "Booking Affiliate": None,
    "Travel Affiliate Networks": None,
    "Software Affiliate Programs": None,
    "AI API Marketplace": None,
    "Education Platforms": None,
    "Developer Platforms": None,
    "Enterprise B2B": None,
}

# config/economics.json's real platform keys that correspond to each
# named marketplace -- a real, independently-disclosed fact from "has a
# registered distribution arm": KDP has real commission-rate config
# (used by revenue_pipeline.plan's cost modeling) despite having no real
# arm; Etsy/Payhip/Paddle have a real arm but no economics.json entry
# (their fee handling lives elsewhere) -- never conflated.
_MARKETPLACE_ECONOMICS_PLATFORMS = {
    "Amazon KDP": ("kdp_ebook", "kdp_paperback"),
    "Gumroad": ("gumroad_digital", "gumroad_premium", "gumroad_elite"),
}

_COUNTRY_DEPENDENCY_REASON = (
    "مؤجَّل بوعي — لا موصّل بيانات سوق محلي حقيقي لأي دولة في هذا المصنع اليوم "
    "(قرار مؤكَّد من المؤسس بتاريخ 2026-07-23، موثَّق في CLAUDE.md) — Hacker News وGitHub "
    "هما المصدرين الخارجيين الحقيقيين الوحيدين، وكلاهما عالمي/إنجليزي، لا يمثّلان استخبارات سوق قُطرية حقيقية. "
    "لا حقل دولة (country) موجود في data/sales_ledger.jsonl الحقيقي -- بناء هذا المؤشر يتطلب موصّل بيانات حقيقي غير موجود بعد."
)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def marketplace_catalog():
    """The 15 named marketplaces mapped onto real registered channel
    arms (channels/registry.py) + real economics.json commission
    config -- both cited independently, never conflated. Imports
    distributor.py first (same self-registration precedent as
    founder_console.py::build_founder_queue_partial()) so every real
    arm is actually registered before checking."""
    import distributor  # noqa: F401 -- self-registers every real channel arm
    from channels import registry

    registered = {arm.name for arm in registry.all_arms()}

    catalog = {}
    for marketplace, arm_name in _MARKETPLACE_ARM.items():
        has_real_arm = arm_name is not None and arm_name in registered
        economics_platforms = _MARKETPLACE_ECONOMICS_PLATFORMS.get(marketplace, ())
        catalog[marketplace] = {
            "real_arm": arm_name if has_real_arm else None,
            "status": "REAL" if has_real_arm else "DISCOVERY",
            "reason": None if has_real_arm else f"لا قناة توزيع حقيقية مسجَّلة لـ'{marketplace}' اليوم",
            "has_real_commission_config": bool(economics_platforms),
            "economics_platforms": list(economics_platforms) or None,
        }

    # Disclosed finding: 2 of this factory's 4 real channels (payhip,
    # paddle) aren't even named in the directive's own 15-marketplace
    # list -- the founder's named list and this factory's real channel
    # set genuinely differ, worth surfacing rather than silently omitting.
    unnamed_real_arms = sorted(registered - {a for a in _MARKETPLACE_ARM.values() if a})

    return {
        "catalog": catalog,
        "real_arms_count": len(registered),
        "named_marketplaces_with_real_arm": sum(1 for c in catalog.values() if c["status"] == "REAL"),
        "real_arms_not_named_in_directive": unnamed_real_arms,
        "generated_at": _now_iso(),
    }


def product_family_distribution(decisions_path=None):
    """Real concentration check #2 (">30% one product family"): a real
    Counter over every real ACCEPTED decision's product_family field --
    the exact technique value_engine.py::_score_synergy_and_bundle()
    already established for `ladder` (swap the field, not the method)."""
    from decision_engine import ranking

    accepted = [d for d in ranking.rank_all(path=decisions_path) if d.get("status") == "ACCEPTED" and d.get("niche")]
    with_family = [d for d in accepted if d.get("product_family")]

    if not with_family:
        return {
            "answer": "NOT ENOUGH EVIDENCE",
            "reason": "لا قرار ACCEPTED حقيقي واحد يحمل product_family مسجَّل بعد",
            "total_accepted": len(accepted),
        }

    counts = Counter(d["product_family"] for d in with_family)
    total = len(with_family)
    top_family, top_count = counts.most_common(1)[0]
    return {
        "total_accepted": len(accepted),
        "total_with_product_family": total,
        "distribution": {family: {"count": count, "pct": round(100 * count / total, 1)} for family, count in counts.items()},
        "top_family": top_family,
        "top_family_pct": round(100 * top_count / total, 1),
        "generated_at": _now_iso(),
    }


def revenue_distribution(ledger_path=None):
    """Real concentration check #1 (">40% one platform"): groups every
    real logged sale event (channels/ledger.py) by its real `platform`
    field and computes real revenue %. Honestly NOT ENOUGH EVIDENCE
    when zero real sale events exist yet (this factory's real current
    state) -- never estimated from publish attempts or dry runs."""
    from channels import ledger

    by_platform = {}
    total = 0.0
    for event in ledger.read_events(event_type="sale", ledger_path=ledger_path):
        platform = event.get("platform")
        amount = ledger._extract_sale_amount(event.get("raw") or {}, platform)
        if amount is None or not platform:
            continue
        by_platform[platform] = by_platform.get(platform, 0.0) + amount
        total += amount

    if not by_platform or total <= 0:
        return {
            "answer": "NOT ENOUGH EVIDENCE",
            "reason": "لا حدث بيع حقيقي واحد مسجَّل بعد في data/sales_ledger.jsonl -- لا توزيع إيراد حقيقي لعرضه",
        }

    top_platform, top_amount = max(by_platform.items(), key=lambda kv: kv[1])
    return {
        "total_revenue_usd": round(total, 2),
        "by_platform": {p: {"revenue_usd": round(v, 2), "pct": round(100 * v / total, 1)} for p, v in by_platform.items()},
        "top_platform": top_platform,
        "top_platform_pct": round(100 * top_amount / total, 1),
        "generated_at": _now_iso(),
    }


def ai_provider_concentration(cost_log_path=None):
    """Real concentration check #4 (">20% one AI provider"): cites
    ai_capability.registry.list_providers()'s real per-provider cost
    stats verbatim. Real but structurally trivial today -- Groq is the
    only provider with any real usage, so its share is ~100% by
    definition, not yet a real diversification signal (there is no
    real alternative-provider spend to compare against)."""
    from ai_capability import registry as ai_registry

    providers = ai_registry.list_providers(cost_log_path=cost_log_path)
    real_costs = {
        p["provider"]: p["real_stats"]["total_cost_usd"]
        for p in providers
        if p.get("real_stats") and p["real_stats"].get("total_cost_usd") is not None
    }
    if not real_costs:
        return {"answer": "NOT ENOUGH EVIDENCE", "reason": "لا بيانات تكلفة حقيقية مسجَّلة لأي مزوّد ذكاء اصطناعي بعد"}

    total = sum(real_costs.values())
    top_provider, top_cost = max(real_costs.items(), key=lambda kv: kv[1])
    real_provider_count = len(real_costs)

    return {
        "real_provider_count": real_provider_count,
        "by_provider": {p: {"total_cost_usd": round(c, 6), "pct": round(100 * c / total, 1)} for p, c in real_costs.items()} if total else {},
        "top_provider": top_provider,
        "top_provider_pct": round(100 * top_cost / total, 1) if total else 100.0,
        "note": (
            f"مزوّد واحد فقط ({top_provider}) لديه استخدام حقيقي مسجَّل اليوم — هذه حقيقة واقعة، ليست بعد إشارة تنويع حقيقية حتى يوجد مزوّد ثانٍ حقيقي فعلاً مستدعى"
            if real_provider_count == 1 else None
        ),
        "generated_at": _now_iso(),
    }


def country_dependency_note():
    """Real concentration check #3 (">25% one country"): NOT a
    computation -- a permanent, real citation of this factory's own
    founder-confirmed 2026-07-23 decision (CLAUDE.md). Always returns
    the same structural DISCOVERY; never computes a percentage that
    cannot exist without a real local-market data connector this
    factory genuinely does not have."""
    return {
        "answer": "DISCOVERY", "structural": True,
        "reason": _COUNTRY_DEPENDENCY_REASON,
        "generated_at": _now_iso(),
    }


def market_health(publish_protection_state_path=None):
    """"Market Health"/"Market Saturation" for marketplaces-as-platforms
    (distinct from competitor_discovery.py's niche/product-category
    saturation, untouched here) -- cites channels.publish_protection.
    list_publish_protection_status()'s already-real per-arm state
    verbatim. Honestly empty until a real publish attempt exists for
    any arm."""
    from channels import publish_protection

    status = publish_protection.list_publish_protection_status(state_path=publish_protection_state_path)
    arms = status.get("arms") or {}
    if not arms:
        return {
            "answer": "NOT ENOUGH EVIDENCE", "reason": "لا محاولة نشر حقيقية واحدة مسجَّلة لأي قناة بعد",
            "global_emergency_stopped": (status.get("global") or {}).get("emergency_stopped", False),
        }

    by_arm = {
        arm_name: {
            "currently_allowed": record["currently_allowed"],
            "risk_score": record["risk_score"],
            "consecutive_failures": record["consecutive_failures"],
            "has_ever_published_successfully": record["has_ever_published_successfully"],
        }
        for arm_name, record in arms.items()
    }
    unhealthy_arms = [a for a, r in by_arm.items() if not r["currently_allowed"] or r["consecutive_failures"] > 0]

    return {
        "by_arm": by_arm,
        "unhealthy_arms": unhealthy_arms,
        "global_emergency_stopped": (status.get("global") or {}).get("emergency_stopped", False),
        "generated_at": _now_iso(),
    }


_CONCENTRATION_THRESHOLDS = {"platform": 40.0, "product_family": 30.0, "country": 25.0, "ai_provider": 20.0}


def _check_threshold(value_dict, pct_key, top_key, threshold):
    if "answer" in value_dict:
        return {"threshold_pct": threshold, "value_pct": None, "exceeded": value_dict["answer"], "top": None, "reason": value_dict.get("reason")}
    pct = value_dict.get(pct_key)
    return {
        "threshold_pct": threshold, "value_pct": pct,
        "exceeded": bool(pct is not None and pct > threshold),
        "top": value_dict.get(top_key), "reason": None,
    }


def concentration_risk_report(decisions_path=None, ledger_path=None, cost_log_path=None):
    """Aggregates the directive's exact 4 named thresholds. Each is
    `{threshold_pct, value_pct, exceeded, top, reason}` -- `exceeded` is
    a real boolean only when real data exists to compute it; otherwise
    it's the honest string `"NOT ENOUGH EVIDENCE"` or `"structural
    DISCOVERY"`, never a fabricated True/False."""
    revenue = revenue_distribution(ledger_path=ledger_path)
    family = product_family_distribution(decisions_path=decisions_path)
    ai_conc = ai_provider_concentration(cost_log_path=cost_log_path)
    country = country_dependency_note()

    return {
        "platform": _check_threshold(revenue, "top_platform_pct", "top_platform", _CONCENTRATION_THRESHOLDS["platform"]),
        "product_family": _check_threshold(family, "top_family_pct", "top_family", _CONCENTRATION_THRESHOLDS["product_family"]),
        "country": {
            "threshold_pct": _CONCENTRATION_THRESHOLDS["country"], "value_pct": None,
            "exceeded": "structural DISCOVERY", "top": None, "reason": country["reason"],
        },
        "ai_provider": _check_threshold(ai_conc, "top_provider_pct", "top_provider", _CONCENTRATION_THRESHOLDS["ai_provider"]),
        "generated_at": _now_iso(),
    }


def build_global_opportunity_exchange_dashboard(decisions_path=None, board_path=None, alerts_path=None,
                                                 reopen_log_path=None, evidence_path=None, timeline_path=None,
                                                 outcomes_path=None, ledger_path=None, cost_log_path=None,
                                                 publish_protection_state_path=None):
    """The one real aggregator: Global Opportunity Map, Capital Flow
    Between Markets, Market Health, Market Saturation, Opportunity
    Ranking, Revenue Distribution, Market Dependency Index, and real,
    mechanical diversification recommendations. Every field cites an
    already-real function; the real portfolio scan (value_engine.
    build_value_engine_report()) is computed exactly once."""
    import value_engine

    portfolio = value_engine.build_value_engine_report(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    catalog = marketplace_catalog()
    revenue = revenue_distribution(ledger_path=ledger_path)
    health = market_health(publish_protection_state_path=publish_protection_state_path)
    dependency_index = concentration_risk_report(decisions_path=decisions_path, ledger_path=ledger_path, cost_log_path=cost_log_path)

    profiles = portfolio["profiles"]
    opportunity_ranking = [
        {
            "niche": p["niche"],
            "priority_score": p["board_summary"]["priority_score"].get("score")
                if isinstance(p["board_summary"]["priority_score"], dict) else None,
        }
        for p in profiles
    ]

    # Real, mechanical: one line per concentration check that actually
    # crosses its real threshold, citing the real number -- never a
    # fabricated suggestion, never padded when nothing real crosses.
    diversification_recommendations = [
        {
            "dimension": dimension, "value_pct": check["value_pct"], "threshold_pct": check["threshold_pct"], "top": check["top"],
            "recommendation": f"نوّع بعيداً عن {check['top']} — تركّز {check['value_pct']}% (الحد الآمن {check['threshold_pct']}%)",
        }
        for dimension, check in dependency_index.items()
        if dimension != "generated_at" and check.get("exceeded") is True
    ]

    return {
        "global_opportunity_map": {"portfolio_size": len(profiles), "marketplace_catalog": catalog},
        "capital_flow_between_markets": revenue,
        "market_health": health,
        "market_saturation": {
            **health,
            "note": "نفس إشارة market_health الحقيقية أعلاه — لا مقياس تشبّع منفصل حقيقي لمنصّة التوزيع بعد "
                     "(تشبّع النيتش/فئة المنتج يبقى نطاق competitor_discovery.py، غير مُدمَج هنا تجنباً للخلط بين معنيي 'السوق')",
        },
        "opportunity_ranking": opportunity_ranking,
        "revenue_distribution": revenue,
        "market_dependency_index": dependency_index,
        "diversification_recommendations": diversification_recommendations,
        "founder_approval_note": "توصيات فقط — لا تنفيذ تلقائي؛ المؤسس هو الموافِق الوحيد على أي إعادة تخصيص حقيقية",
        "generated_at": _now_iso(),
    }
