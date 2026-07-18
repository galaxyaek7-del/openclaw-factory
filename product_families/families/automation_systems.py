"""automation_systems family definition (Universal Production Engine
Roadmap Step 3, 2026-07-18) — a Product Manifest, not a bespoke adapter
class. Roadmap Step 2 built this family as a hand-written
AutomationSystemsFamily class; Step 3's Product Definition Registry
proved that same pipeline shape is entirely reusable, so this family now
needs only a manifest + one registration call — the concrete
"configuration, not code" template for every family after it.

Real, distinct content shape: a business-automation-system product's own
section skeleton (not a renamed copy of professional_templates/
digital_toolkits, which share this same underlying PDF engine but with
the generic techdoc skeleton).
"""

from ..manifest import ProductManifest
from ..generic_adapter import register_manifest_driven_family

DEFAULT_AUTOMATION_SECTIONS = [
    "System Overview",
    "Workflow Architecture",
    "Setup & Integration Guide",
    "Automation Triggers & Logic",
    "Maintenance & Troubleshooting",
    "ROI & Time Savings",
]

MANIFEST = ProductManifest(
    product_id="automation_systems",
    family="automation_systems",
    category="b2b_automation_system",
    content_generator="groq_techdoc",
    asset_builder="techdoc_package",
    packager="single_file",
    default_sections=DEFAULT_AUTOMATION_SECTIONS,
    qa_profile={"min_pages": 4, "economics_platform": "gumroad_elite"},
    publishing_profile={"product_type": "techdoc"},
    pricing_strategy={"price_hint": 197.0, "platform_band": "elite"},
    supported_marketplaces=["paddle", "gumroad"],
    recovery_policy={"content_retry_task": "groq_generation"},
)

register_manifest_driven_family(MANIFEST)
