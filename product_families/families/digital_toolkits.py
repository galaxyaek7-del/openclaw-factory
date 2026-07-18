"""digital_toolkits family definition (Universal Production Engine
Roadmap Step 3, 2026-07-18) — a Product Manifest, converted from
Roadmap Step 1's direct book_generator.generate_product_package() call
to the Product Definition Registry's generic pipeline. Same underlying
real engine as professional_templates (Packaging Architecture Plan §2's
own original note: "a distinct family name today, not distinct
generation logic") — a distinct manifest entry, not distinct code.
"""

from ..manifest import ProductManifest
from ..generic_adapter import register_manifest_driven_family

MANIFEST = ProductManifest(
    product_id="digital_toolkits",
    family="digital_toolkits",
    category="digital_toolkit_package",
    content_generator="groq_techdoc",
    asset_builder="techdoc_package",
    packager="single_file",
    default_sections=[],  # no family-specific skeleton yet — falls to generate_product_package()'s own DEFAULT_TECHDOC_SECTIONS when no components are supplied
    qa_profile={"min_pages": 4, "economics_platform": "gumroad_elite"},
    publishing_profile={"product_type": "techdoc"},
    pricing_strategy={"price_hint": 197.0, "platform_band": "elite"},
    supported_marketplaces=["paddle", "gumroad"],
    recovery_policy={"content_retry_task": "groq_generation"},
)

register_manifest_driven_family(MANIFEST)
