"""professional_templates family adapter (Packaging Architecture Plan §2).
Wraps book_generator.generate_product_package() unchanged — real Groq
content generation per component (ai_generate_techdoc_content(), ADR-077),
honest fallback on failure, priced against the gumroad_elite band via
generate_product_package()'s own _economics_platform_for("techdoc").
"""

import book_generator as bg
from .. import registry
from ..spec import components_to_sections


class ProfessionalTemplatesFamily:
    name = "professional_templates"

    def generate(self, spec):
        family_config = spec.get("family_config") or {}
        return bg.generate_product_package(
            title=spec.get("title") or "Untitled",
            subtitle=spec.get("subtitle") or "",
            topic=spec.get("topic") or spec.get("niche") or "",
            price=spec.get("price_hint") or 197.0,
            theme=family_config.get("theme", "blue"),
            author=spec.get("author") or "OpenClaw Press",
            output=family_config.get("output"),
            sections=components_to_sections(spec.get("components")),
            production_id=spec.get("production_id"),
        )


registry.register(ProfessionalTemplatesFamily())
