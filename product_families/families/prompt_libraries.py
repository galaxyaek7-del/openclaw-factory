"""prompt_libraries family definition — Product Manifest for AI prompt libraries.
"""
from ..manifest import ProductManifest
from ..generic_adapter import register_manifest_driven_family

DEFAULT_PROMPT_SECTIONS = [
    "Prompt Library Overview",
    "Prompt Categories & Use Cases",
    "Prompt Engineering Guide",
    "Customization & Variables",
    "Best Practices & Tips",
    "Updates & Expansion",
]

MANIFEST = ProductManifest(
    product_id="prompt_libraries",
    family="prompt_libraries",
    category="ai_asset",
    content_generator="groq_techdoc",
    asset_builder="techdoc_package",
    packager="single_file",
    default_sections=DEFAULT_PROMPT_SECTIONS,
    qa_profile={"min_pages": 4, "economics_platform": "gumroad_digital"},
    publishing_profile={"product_type": "techdoc"},
    pricing_strategy={"price_hint": 29.0, "platform_band": "digital"},
    supported_marketplaces=["gumroad", "etsy"],
    recovery_policy={"content_retry_task": "groq_generation"},
)

register_manifest_driven_family(MANIFEST)
