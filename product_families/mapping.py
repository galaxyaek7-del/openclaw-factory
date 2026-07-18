"""OpenClaw Factory — ladder rank -> default product_family mapping
(Packaging Architecture Plan §1).

`ladder` (profit_oracle.py's Strategic Production Priority Ladder rank)
answers "how much should we prioritize/pay for this opportunity."
`product_family` answers "what kind of file do we actually build." A
ladder rank does not dictate exactly one family — this table is only the
DEFAULT used when Discovery/Validation didn't set an explicit family; an
explicit family always wins.

This mapping is a judgment call, not derived from real sales data (no
family has ever shipped) — flagged explicitly in the Packaging
Architecture Plan §7 Risk 3. The founder should revisit it once real
production experience exists.
"""

# The full 9-family taxonomy (Packaging Architecture Plan §2) — used by
# production_factory/dossier.py's _product_type_capability() to report
# REAL vs NOT YET BUILT for every family, not just the 4 with a Phase A
# adapter. Order matches the plan's own numbering (KDP last = legacy).
#
# "automation_packs" was renamed to "automation_systems" (Universal
# Production Engine Roadmap Step 2, 2026-07-18) the moment a real adapter
# was actually built under that name — the UPE architecture plan had
# already adopted "automation_systems" as canonical wording; this is where
# that rename actually lands in code, not just in planning docs.
ALL_PRODUCT_FAMILIES = (
    "ai_saas", "professional_templates", "digital_toolkits", "notion_systems",
    "spreadsheet_systems", "prompt_libraries", "automation_systems",
    "knowledge_bases", "kdp_books",
)

DEFAULT_FAMILY_BY_LADDER = {
    "ai_saas": "ai_saas",
    "b2b_systems": "automation_systems",
    "automation_tools": "automation_systems",
    "reusable_assets": "professional_templates",
    "educational": "knowledge_bases",
    "kdp_books": "kdp_books",
}


def resolve_product_family(ladder, explicit_family=None):
    """An explicit family always wins over the default table. With no
    explicit family and an unrecognized/missing ladder, returns None —
    same "don't guess" discipline as the rest of this factory; the caller
    (orchestrator/engines/production.py) must handle None by falling back
    to its own existing behavior, never by inventing a family."""
    if explicit_family:
        return explicit_family
    return DEFAULT_FAMILY_BY_LADDER.get(ladder)
