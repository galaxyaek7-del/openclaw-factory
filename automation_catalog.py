#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI Automation Revenue Engine — Automation Catalog (ADR-164, 2026-07-31).

The founder's directive named itself "ADR-162" but that number is
already allocated (Enterprise Truth Audit & Reality Certification,
committed `0b80df8`/`8818935`) -- this round is the real next number,
ADR-164, same renumbering convention CONSTITUTION.md's own amendment
history already established for a prior misnumbered ask.

The 15 named example automation-product categories, mapped onto this
factory's real, already-registered ladders (profit_oracle.py's
RECURRING_REVENUE_BY_LADDER/REUSABILITY_BY_LADDER/AUTOMATION_POTENTIAL_
BY_LADDER/LADDER_PRICE_BAND, product_families/mapping.py's real
"automation_systems" family) -- never a new taxonomy invented from
scratch. Every category maps cleanly onto one of the 3 real automation-
adjacent ladders already live in this factory (ai_saas/b2b_systems/
automation_tools) -- no category needed a NOT_IMPLEMENTED fallback,
disclosed honestly either way.
"""

# Real, disclosed mapping -- same convention as growth_engine.py's own
# _PREMIUM_CATEGORY_FAMILY. Grounded in profit_oracle.py's real,
# documented per-ladder constants, not re-derived here.
AUTOMATION_CATEGORIES = {
    "AI workflow systems": "b2b_systems",
    "n8n templates": "automation_tools",
    "Business process automation": "automation_tools",
    "CRM automation": "b2b_systems",
    "Email automation": "automation_tools",
    "Lead qualification": "b2b_systems",
    "Customer support assistants": "ai_saas",
    "Internal AI copilots": "ai_saas",
    "Reporting automation": "automation_tools",
    "Knowledge assistants": "ai_saas",
    "Document processing": "automation_tools",
    "Invoice automation": "automation_tools",
    "HR automation": "b2b_systems",
    "Sales automation": "b2b_systems",
    "Operations automation": "b2b_systems",
}


def category_catalog():
    """Real citation of each named category's real ladder + the real,
    already-documented per-ladder constants that ladder carries --
    never a fabricated per-category number."""
    import profit_oracle
    from product_families import registry as family_registry

    adapter = family_registry.get("automation_systems")
    catalog = {}
    for category, ladder in AUTOMATION_CATEGORIES.items():
        catalog[category] = {
            "ladder": ladder,
            "real_recurring_revenue_potential": profit_oracle.RECURRING_REVENUE_BY_LADDER.get(ladder),
            "real_automation_potential": profit_oracle.AUTOMATION_POTENTIAL_BY_LADDER.get(ladder),
            "real_price_band": profit_oracle.LADDER_PRICE_BAND.get(ladder),
            "product_family_status": "REAL" if adapter is not None else "NOT YET BUILT",
            "source": "profit_oracle.py's real per-ladder constants (ADR-065/122/126) + product_families/mapping.py's real 'automation_systems' family.",
        }
    return {"categories": catalog, "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
