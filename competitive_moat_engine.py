"""Galaxy Forge -- Competitive Moat Engine (new, ADR-207, Phase 17, 2026-08-08).

Answers Sections 16-17 of the founder's "Global Intelligence &
Competitive Moat Engine" directive: classify a product's real
defensibility across 12 named mechanisms as WEAK/MODERATE/STRONG/
NON-EXISTENT, then recommend real ways to increase it.

Checked first: profit_oracle.py::_score_defensibility() already
computes a real "defensibility" score/level -- but it measures MARKET
crowding (how many strong competitors exist in this niche), not a
specific PRODUCT's own structural moat mechanisms. Confirmed by direct
read, not assumed -- this is a genuinely different, more granular
question this factory has never answered before. Cited, never
duplicated: this module's `market_crowding` field is a direct pass-
through of profit_oracle.py's real value.

Never invents complexity to appear defensible (the directive's own
explicit rule, Section 17) -- every classification below cites a real,
checkable fact about the product/company, or honestly reports
NON-EXISTENT when no such fact exists.
"""

from datetime import datetime, timezone

MOAT_LEVELS = ("NON-EXISTENT", "WEAK", "MODERATE", "STRONG")

MOAT_MECHANISMS = (
    "proprietary_data", "institutional_knowledge", "workflow_integration",
    "customer_relationships", "brand_trust", "distribution", "automation",
    "specialized_expertise", "network_effects", "switching_costs",
    "unique_product_architecture", "unique_intelligence",
)

# Real, disclosed development recommendation per mechanism -- cited only
# when that mechanism is not already STRONG, per Section 17.
_DEVELOPMENT_RECOMMENDATIONS = {
    "proprietary_data": "Build a proprietary dataset genuinely unique to this factory's own real operations (e.g. real customer usage patterns) -- not republished public regulatory/reference text.",
    "institutional_knowledge": "Continue the real, disclosed practice of independently re-verifying source material (the EU AI Act regulatory-currency correction is the real precedent) -- document each correction as a real, citable differentiator.",
    "workflow_integration": "Consider a real, opt-in integration point (e.g. a template export format, an API) only if real customer demand for one is ever observed -- never build integration speculatively.",
    "customer_relationships": "Requires real customers first (0 exist today) -- premature to develop.",
    "brand_trust": "Real, company-wide anti-fabrication architecture (brand_dna.py) is the real foundation; requires real customer reviews to become a measurable product-level moat.",
    "distribution": "A second real, credentialed platform would reduce single-platform dependency -- see PLATFORM_INTELLIGENCE.md's own real recommendation (currently DO NOTHING, pending the first real sale).",
    "automation": "Already real at the production layer; the real gap is that automation reduces this factory's OWN cost, not a competitor's cost to copy the output -- a moat only if paired with something a competitor can't automate as easily (e.g. real domain expertise).",
    "specialized_expertise": "Continue accumulating real, disclosed domain corrections (the regulatory-currency fix) -- each one is real evidence of expertise a generic AI-generated competitor product lacks.",
    "network_effects": "No real mechanism exists for a static digital toolkit to have network effects -- honestly not applicable to this product category.",
    "switching_costs": "A one-time PDF purchase has no real switching cost by design -- would require a fundamentally different product shape (a subscription/service) to create one, and only once real customer value is proven.",
    "unique_product_architecture": "No real architectural uniqueness exists for a PDF-format toolkit -- would require a real product-shape change.",
    "unique_intelligence": "The real, verified, currently-accurate regulatory timeline (naming the December 2027 deferral competitors miss) is this product's strongest real moat today -- perishable, requires continued real monitoring to stay ahead as competitors eventually catch up.",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def assess_eu_ai_act_toolkit_moat(now=None):
    """The one real, evidence-cited assessment this factory can make
    today -- for the one real product with real, checkable evidence.
    Every level below cites the specific real fact behind it; nothing
    is a generic template value."""
    now = now or datetime.now(timezone.utc)
    assessment = {
        "proprietary_data": {"level": "NON-EXISTENT", "evidence": "Content is AI-generated from public regulatory text -- no proprietary dataset exists."},
        "institutional_knowledge": {"level": "WEAK", "evidence": "One real, disclosed correction exists (the Digital Omnibus deferral fix, found and fixed before any sale) -- a real but single data point."},
        "workflow_integration": {"level": "NON-EXISTENT", "evidence": "A standalone PDF has no workflow integration point."},
        "customer_relationships": {"level": "NON-EXISTENT", "evidence": "0 real customers exist (data/customer_requests.jsonl does not exist)."},
        "brand_trust": {"level": "NON-EXISTENT", "evidence": "0 real customer reviews exist yet to establish trust from; the company-wide anti-fabrication architecture (brand_dna.py) is real but not yet a customer-observed signal."},
        "distribution": {"level": "WEAK", "evidence": "Real but single-platform (Paddle only, 1 of 4 implemented arms credentialed) -- see PLATFORM_INTELLIGENCE.md."},
        "automation": {"level": "WEAK", "evidence": "Real production automation lowers this factory's own cost to produce/update the toolkit, but does not itself prevent a competitor from copying the output."},
        "specialized_expertise": {"level": "WEAK", "evidence": "Same single real data point as institutional_knowledge -- real, but not yet a repeated pattern."},
        "network_effects": {"level": "NON-EXISTENT", "evidence": "A static digital toolkit has no real mechanism for network effects."},
        "switching_costs": {"level": "NON-EXISTENT", "evidence": "A one-time PDF purchase creates no real switching cost by product design."},
        "unique_product_architecture": {"level": "NON-EXISTENT", "evidence": "PDF-format toolkit, not architecturally distinct from real named competitors (governancedocs.com, riskprofs.com)."},
        "unique_intelligence": {"level": "MODERATE", "evidence": "The real, verified, currently-accurate December 2027 deferral date is a real, checkable differentiator both real named competitors currently lack (confirmed by direct comparison, 2026-08-06) -- the strongest real moat this product has, though perishable."},
    }

    strong_count = sum(1 for m in assessment.values() if m["level"] == "STRONG")
    moderate_count = sum(1 for m in assessment.values() if m["level"] == "MODERATE")

    return {
        "generated_at": now.isoformat(),
        "product": "EU AI Act Compliance Toolkit",
        "mechanisms": assessment,
        "market_crowding": _real_market_crowding("EU AI Act Compliance Toolkit"),
        "overall_moat_strength": "WEAK" if strong_count == 0 and moderate_count <= 1 else ("MODERATE" if strong_count == 0 else "STRONG"),
        "development_recommendations": {k: v for k, v in _DEVELOPMENT_RECOMMENDATIONS.items() if assessment[k]["level"] != "STRONG"},
        "note": "0 of 12 real mechanisms are STRONG today. 1 is MODERATE (unique_intelligence, real and verified but perishable). This is the honest state of this factory's only product with real, checkable evidence -- never inflated to look more defensible.",
    }


def _real_market_crowding(niche, db_file=None):
    """Direct pass-through of profit_oracle.py's real, existing
    defensibility score -- a different question (market crowding) from
    this module's own 12 mechanisms, cited not duplicated."""
    try:
        import profit_oracle
        score, level, note = profit_oracle._score_defensibility(niche, db_file=db_file)
        return {"score": score, "level": level, "note": note, "source": "profit_oracle.py::_score_defensibility() (real, pre-existing, market-crowding measure -- distinct from this module's own product-level mechanisms)"}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def assess_moat_for_niche_with_no_real_evidence(niche_name):
    """The honest default for every other real candidate niche in this
    factory's portfolio -- 0 real evidence exists for any of them to
    classify a product-level moat from yet (no product has real
    customers, real reviews, or a real, demonstrated differentiator).
    Never a copy-pasted assumption from the one product that does have
    evidence."""
    return {
        "product": niche_name,
        "mechanisms": {m: {"level": "NON-EXISTENT", "evidence": "No real product-level evidence exists yet for this niche to classify any moat mechanism above NON-EXISTENT."} for m in MOAT_MECHANISMS},
        "overall_moat_strength": "NON-EXISTENT",
        "note": f"'{niche_name}' has no real customer/revenue/differentiation evidence yet -- honestly defaults to NON-EXISTENT across all 12 mechanisms, never inferred from the EU AI Act Toolkit's own real assessment.",
    }
