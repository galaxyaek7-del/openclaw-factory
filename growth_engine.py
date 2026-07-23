#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Global Growth Engine (2026-07-24).

Product Multiplication, Channel Expansion, and Compounding signals for
every real ACCEPTED opportunity. Confirmed with the founder before
building (AskUserQuestion): "validated winner" = any real ACCEPTED
decision today (many exist), not gated on a real closed sale (zero
exist) — but every candidate below explicitly discloses whether it is
market-validated (real closed-sale evidence, market_memory.py) or only
intelligence-validated (the ladder score alone), never presented as
equally proven.

Checked candidate-by-candidate against what this factory can actually
compute, reusing real functions rather than a second scoring pass:

  REAL, reused directly:
    premium_version  <- value_engine's own upgrade_potential dimension
                         (revenue_pipeline.plan.compare_ladder_variants())
    bundle_opportunities <- value_engine's own bundle_potential dimension
    api_version / saas_version <- product_families.registry's real
                         adapter status for api_products/micro_saas
                         (Universal Production Engine, honest REAL vs
                         NOT YET BUILT, never fabricated)
    subscription_version <- economics.py/channels/paddle_publisher.py's
                         real, structural billing_cycle support — a real
                         capability with zero real usage precedent yet,
                         reported as exactly that, not as a proven model

  NO REAL SOURCE ANYWHERE IN THIS FACTORY TODAY — always honestly
  {available: False, reason: ...}, never guessed:
    enterprise_version (no distinct enterprise pricing/positioning tier
                         exists beyond the "elite" ladder price band —
                         CLAUDE.md's own Path 5, VIP business services,
                         is a named but unbuilt future track),
    regional_versions / language_localized_versions (ADR-103's Global
                         Market Expansion deferral, reaffirmed twice
                         today — zero real local data connectors, zero
                         real sales, unchanged since either deferral),
    industry_specific_versions (no real industry taxonomy exists
                         anywhere in this factory — product_families is
                         about file TYPE, not customer industry),
    ai_agent_version (no distinct real product family for this — the
                         closest real analogs, ai_saas/micro_saas, are
                         reported separately above, never conflated).

Channel Expansion follows integration_registry.py's own established
pattern exactly: a real, live BaseArm is referenced from channels/
registry.py, everything else is an honest, env-var-based (or
structurally-absent) catalog entry — never a live "test connection"
call.
"""

from datetime import datetime, timezone


def _premium_candidate(upgrade_potential):
    """Normalizes value_engine's upgrade_potential (real, reused
    verbatim) into this module's {available, ...} candidate shape.
    upgrade_potential has 3 real possible shapes: value_engine._unknown()
    ({"answer": "Unknown", "reason": ...}) when no real ladder/price/
    variants exist yet, or an already-{"available": bool, ...}-shaped
    dict either way once they do — never re-scored here."""
    if not isinstance(upgrade_potential, dict):
        return {"available": False, "reason": "لا بيانات ترقية حقيقية متاحة"}
    if upgrade_potential.get("answer") == "Unknown":
        return {"available": False, "reason": upgrade_potential.get("reason")}
    return upgrade_potential


def _subscription_candidate():
    """Real structural capability check: economics.create_price()/
    channels/paddle_publisher.py already accept a real billing_cycle —
    Paddle genuinely supports recurring billing today. Zero real product
    has ever used it (all 5 real shipped products are one-time), so this
    is reported as a real, unused capability, never as a proven model."""
    return {
        "structurally_available": True,
        "real_precedent": False,
        "reason": "Paddle يدعم billing_cycle حقيقياً (channels/paddle_publisher.py::create_price) — "
                  "لكن صفر منتج حقيقي استخدمه حتى الآن؛ قدرة حقيقية غير مُختبَرة تجارياً، وليست نموذجاً مُثبَتاً",
    }


def _family_adapter_candidate(family_name):
    import product_families  # noqa: F401 — self-registers Phase A adapters
    from product_families import registry as family_registry

    adapter = family_registry.get(family_name)
    return {
        "family": family_name,
        "status": "REAL" if adapter is not None else "NOT YET BUILT",
        "reason": f"product_families.families.{family_name} مُسجَّل فعلاً" if adapter is not None
                  else "لا adapter حقيقي مُسجَّل بعد لهذه العائلة (Universal Production Engine Roadmap)",
    }


_NO_SOURCE_CANDIDATES = {
    "enterprise_version": "لا مستوى تسعير/تموضع Enterprise حقيقي متمايز عن نطاق السعر elite اليوم — مسار VIP لخدمات رجال الأعمال (المسار 5، CLAUDE.md) مُخطَّط لكن غير مبنيّ بعد",
    "regional_versions": "مؤجَّل — لا موصّلات بيانات محلية حقيقية لأي سوق إقليمي، صفر مبيعات حقيقية (ADR-103، مؤكَّد مرتين اليوم)",
    "language_localized_versions": "نفس سبب regional_versions — لا قدرة توطين لغوي حقيقية في هذا المصنع اليوم",
    "industry_specific_versions": "لا تصنيف صناعة/قطاع عميل حقيقي في هذا المصنع اليوم — product_families يصنّف نوع الملف، لا الصناعة",
    "ai_agent_version": "لا عائلة منتج حقيقية متمايزة لـ'وكيل ذكاء اصطناعي' اليوم — أقرب تشابه حقيقي هو ai_saas/micro_saas أعلاه، غير مُدمَج هنا تجنباً للخلط",
}


def evaluate_product_multiplication(niche, decisions_path=None, board_path=None, alerts_path=None,
                                     reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """Real, honest evaluation of the 10 founder-named variant types for
    one real ACCEPTED niche. Returns None (never fabricated) when this
    niche has no real ACCEPTED decision — matching value_engine.compute_
    value_profile()'s own scope."""
    import value_engine
    import market_memory

    profile = value_engine.compute_value_profile(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    if profile is None:
        return None

    market_memory_profile = market_memory.niche_commercial_profile(niche, evidence_path=evidence_path)
    market_validated = bool(market_memory_profile and market_memory_profile.get("sample_size", 0) > 0)

    dims = profile["dimensions"]
    candidates = {
        "premium_version": _premium_candidate(dims.get("upgrade_potential")),
        "bundle_opportunities": dims.get("bundle_potential"),
        "subscription_version": _subscription_candidate(),
        "api_version": _family_adapter_candidate("api_products"),
        "saas_version": _family_adapter_candidate("micro_saas"),
    }
    for name, reason in _NO_SOURCE_CANDIDATES.items():
        candidates[name] = {"available": False, "reason": reason}

    return {
        "niche": niche,
        "validation_strength": "market_validated" if market_validated else "intelligence_validated_only",
        "market_memory_sample_size": (market_memory_profile or {}).get("sample_size", 0),
        "candidates": candidates,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


# Real, live arms already referenced from channels/registry.py (Paddle,
# Gumroad, Payhip, Etsy). Everything else the founder named here follows
# integration_registry.py's exact established pattern: a real, named
# catalog entry with `configured` computed from a real environment-
# variable presence check only, or honestly `None` where no credential
# concept exists at all for this factory's current architecture (a
# single-file storefront has no separate "Direct Website" platform to
# credential, for instance).
_CHANNEL_CATALOG = [
    {"name": "GPT Store", "credential_env_var": "OPENAI_GPT_STORE_TOKEN"},
    {"name": "Enterprise Sales", "credential_env_var": None},
    {"name": "Affiliate Network", "credential_env_var": "AFFILIATE_NETWORK_API_KEY"},
    {"name": "Subscription Platform", "credential_env_var": None},
    {"name": "B2B Licensing", "credential_env_var": None},
    {"name": "White Label", "credential_env_var": None},
    {"name": "Direct Website", "credential_env_var": None},
]


def evaluate_channel_expansion():
    """Real, factory-wide (not per-niche — channels are platform-level)
    readiness check across the 10 founder-named channels. Live arms
    referenced from channels/registry.py, never re-derived; the rest an
    honest catalog entry, `configured` from a real env-var check only,
    `None` where this factory has no credential concept to check at
    all — never a live 'test connection' call."""
    import os

    try:
        import distributor  # noqa: F401 — self-registers every real, live arm
        from channels import registry as channel_registry
        live_arms = [
            {"name": arm.name, "source": "channels.registry", "configured": arm.status().value == "ready"}
            for arm in channel_registry.all_arms()
        ]
    except Exception:
        live_arms = []

    catalog_entries = []
    for c in _CHANNEL_CATALOG:
        env_var = c["credential_env_var"]
        configured = bool(os.environ.get(env_var)) if env_var else None
        catalog_entries.append({"name": c["name"], "source": "growth_engine (catalog)", "configured": configured})

    return {"live_arms": live_arms, "catalog_entries": catalog_entries, "evaluated_at": datetime.now(timezone.utc).isoformat()}


def build_growth_report(niche, decisions_path=None, board_path=None, alerts_path=None,
                         reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """The real, combined per-niche growth report: product multiplication
    candidates + factory-wide channel readiness (shared across every
    niche, since channels aren't niche-specific)."""
    multiplication = evaluate_product_multiplication(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    if multiplication is None:
        return None
    return {**multiplication, "channel_expansion": evaluate_channel_expansion()}
