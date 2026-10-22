"""spreadsheet_systems family -- a real workbook, not a PDF about one.

Replaces (2026-10-22) an untracked, never-imported manifest that routed this
family through content_generator="groq_techdoc" + asset_builder=
"techdoc_package": six LLM-written prose sections ("Sheet Structure &
Formulas", ...) rendered to a PDF. Registered as written, it would have sold
a description of a spreadsheet as the spreadsheet.

The deliverable is now the .xlsx itself, built by asset_generation's
xlsx_workbook builder from a declared workbook_spec (same format as the
cohort builders' workbook.json). No spec, no product: nothing is invented.
A companion guide, when wanted, is a separate techdoc product or a verbatim
component -- never a substitute for the workbook.
"""
from ..manifest import ProductManifest, register as register_manifest
from .. import registry

MANIFEST = ProductManifest(
    product_id="spreadsheet_systems",
    family="spreadsheet_systems",
    category="productivity_system",
    content_generator="none",
    asset_builder="xlsx_workbook",
    packager="single_file",
    default_sections=[],
    qa_profile={"file_type": "xlsx", "min_formulas": 1, "economics_platform": "gumroad_digital"},
    publishing_profile={"product_type": "spreadsheet"},
    pricing_strategy={"price_hint": 39.0, "platform_band": "digital"},
    supported_marketplaces=["gumroad", "etsy"],
    recovery_policy={},
)


class SpreadsheetSystemsFamily:
    name = "spreadsheet_systems"
    manifest = MANIFEST

    def generate(self, spec):
        from asset_generation import registry as asset_registry
        from product_packaging import registry as packaging_registry

        builder = asset_registry.get(MANIFEST.asset_builder)
        result = builder.build(spec)
        if not result.get("success"):
            return {**result, "success": False, "package": None}
        package = packaging_registry.get(MANIFEST.packager).package(spec, result)
        return {**result, "package": package}


register_manifest(MANIFEST)
registry.register(SpreadsheetSystemsFamily())
