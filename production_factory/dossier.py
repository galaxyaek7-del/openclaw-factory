"""
Production Dossier builder (Phase 7) — see package docstring for the
full mapping of every section to the existing component it reuses.
"""

from datetime import datetime, timezone

import channels.etsy_arm  # noqa: F401,E402 — self-registers
import channels.gumroad_arm  # noqa: F401,E402
import channels.payhip_arm  # noqa: F401,E402
import channels.paddle_arm  # noqa: F401,E402 — ADR-077: was missing (real
# drift found in ENGINEERING_ASSESSMENT_20260718.md) since paddle_arm.py
# was added this session (ADR-065/074) — _publishing_checklist() below
# reports on whatever channels.registry actually has, so this dossier
# builder reported an incomplete publishing checklist without it.
import profit_oracle
from channels import registry as channel_registry

import product_families  # noqa: F401,E402 — self-registers Phase A family adapters
from product_families import registry as family_registry
from product_families.mapping import ALL_PRODUCT_FAMILIES

from revenue_pipeline import plan as plan_module

# Real check names already run by inspectors.py's Dual Inspection system
# (inspect_technical()/audit_commercial()) -- listed here as a checklist
# template, never re-implemented.
QUALITY_CHECKLIST = [
    "pdf_exists", "pdf_file_size", "pdf_not_corrupt", "pdf_page_count",
    "pdf_page_dimensions_sane", "pdf_no_empty_pages",
    "cover_exists", "cover_opens", "cover_dimensions",
    "cover_70_20_10_zone", "cover_title_bigger_than_author",
    "arabic_shaping_available",
    "profit_score", "butter_price", "not_duplicate", "not_previously_rejected",
]

# The real, fixed set of artifacts book_generator.py/cover_designer_v2.py
# actually produce today -- not an aspirational list.
ASSET_CHECKLIST = [
    "PDF manuscript (book_generator.py)",
    "Cover design (cover_designer_v2.py)",
    "SEO metadata: title/description/keywords (lib/publisher_seo.js)",
]


def make_production_id(decision):
    """Derived from the Decision's own already-deterministic decision_id
    (ADR-050) -- not a new ID scheme."""
    return f"PROD-{decision['decision_id']}"


def _product_type_capability():
    """Honest, not aspirational (Packaging Architecture Plan §4.6,
    2026-07-18): data-driven off product_families.registry, not a
    hardcoded dict — a family reports REAL only once its adapter module
    actually exists and self-registered on import; declaring a new family
    module updates this automatically, with zero edit here."""
    capability = {}
    for name in ALL_PRODUCT_FAMILIES:
        adapter = family_registry.get(name)
        capability[name] = (
            f"REAL — product_families.families.{name}"
            if adapter is not None
            else "NOT YET BUILT — no adapter registered yet (Packaging Architecture Plan §7 roadmap)"
        )
    return capability


def _market_positioning(snapshot):
    return {
        "demand_pattern": snapshot.get("demand_pattern"),
        "competitors": snapshot.get("competitors"),
        "opportunity_gap": snapshot.get("opportunity_gap"),
        "customer_pain_reason": (snapshot.get("customer_pain") or {}).get("reason"),
    }


def _customer_profile(niche):
    niche_lower = niche.lower()
    matched = [q for q in profit_oracle.SUBNICHE_QUALIFIERS if q in niche_lower]
    if matched:
        return {
            "maturity": "REAL",
            "audience_qualifier": matched[0],
            "source": "profit_oracle.SUBNICHE_QUALIFIERS keyword match",
        }
    return {
        "maturity": "DISCOVERY",
        "reason": "لا مؤهِّل جمهور حقيقي مطابق في نص النيتش — لا بيانات استبيان/تحليلات عملاء موجودة بأي حال",
    }


def _publishing_checklist():
    return [{"platform": arm.name, "status": arm.status().value} for arm in channel_registry.all_arms()]


def _pre_production_verification(decision, roi_info):
    snapshot = decision.get("evaluation_snapshot") or {}
    confidence = snapshot.get("confidence") or {}
    risk = snapshot.get("risk") or {}
    execution = (snapshot.get("dimension_scores") or {}).get("execution") or {}
    ready_platforms = [c["platform"] for c in _publishing_checklist() if c["status"] == "ready"]

    return {
        "evidence_quality": {
            "score": confidence.get("score"), "level": confidence.get("level"), "note": confidence.get("note"),
        },
        "market_readiness": {
            "ready_platforms": ready_platforms,
            "market_ready": len(ready_platforms) > 0,
        },
        "production_feasibility": {
            "execution_score": execution.get("normalized_score"),
            "explanation": execution.get("explanation"),
        },
        "expected_roi": roi_info,
        "risk_level": {"score": risk.get("score"), "level": risk.get("level"), "notes": risk.get("notes")},
        "all_checks_passed": bool(
            decision.get("opportunity_score_accepted")
            and risk.get("level") == "low"
            and len(ready_platforms) > 0
        ),
    }


def build_production_dossier(decision):
    niche = decision["niche"]
    snapshot = decision.get("evaluation_snapshot") or {}
    production_plan = plan_module.build_production_plan(decision)
    cost_info = plan_module.estimate_production_cost()
    roi_info = plan_module.estimate_roi(
        production_plan["recommended_price"],
        cost_info.get("estimated_cost_usd") if cost_info.get("maturity") == "REAL" else None,
        platform=production_plan.get("economics_platform", production_plan["recommended_platform"]),
    )

    return {
        "production_id": make_production_id(decision),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "niche": niche,
        "product_specification": production_plan,
        "market_positioning": _market_positioning(snapshot),
        "customer_profile": _customer_profile(niche),
        "pricing_strategy": {
            "recommended_price": production_plan["recommended_price"],
            "butter_price_book": profit_oracle.butter_price(niche, product_type="book"),
            "note": production_plan["pricing_note"],
        },
        "asset_checklist": ASSET_CHECKLIST,
        "quality_checklist": QUALITY_CHECKLIST,
        "publishing_checklist": _publishing_checklist(),
        "success_metrics": {"production_cost": cost_info, "expected_roi": roi_info},
        "product_type_capability": _product_type_capability(),
        "pre_production_verification": _pre_production_verification(decision, roi_info),
    }
