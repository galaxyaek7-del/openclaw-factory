"""digital_toolkits family adapter (Packaging Architecture Plan §2). Same
underlying real engine as professional_templates in Phase A
(generate_product_package()) — a distinct family name today, not distinct
generation logic; Pricing/QA differentiation between the two is later
scope (Plan §7 Phase C+), not invented here ahead of real evidence.
"""

import book_generator as bg
from .. import registry
from ..spec import components_to_sections


class DigitalToolkitsFamily:
    name = "digital_toolkits"

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


registry.register(DigitalToolkitsFamily())
