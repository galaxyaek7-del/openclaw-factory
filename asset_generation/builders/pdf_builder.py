"""PDF asset builders (Universal Production Engine §3/§6, 2026-07-18) —
today's real `AssetGenerator` implementations. Wraps book_generator.py's
already-tested, already-real full generation pipelines
(generate_book()/generate_product_package()) unchanged — no new PDF
rendering, cover, inspection, or logging logic lives here.

Interface contract: build(spec) -> dict (book_generator.py's own real
result shape: success/file/path/pages/price/product_type/cover/
published/inspection/...). The two builders below cover every family
shipped so far (kdp_books uses "ai_book"; professional_templates/
digital_toolkits/knowledge_bases use "techdoc_package") — each existing
family adapter keeps calling book_generator.py directly today (zero
behavior change, per the approved Roadmap Step 1 scope); this registry
exists so a NEW family (Roadmap step 2+) has one real, swappable place
to register its own builder without touching product_families/ or
content_generation/.
"""

import book_generator as bg
from product_families.spec import components_to_sections
from .. import registry


class AiBookAssetBuilder:
    """Pairs with content_generation's "groq_book" generator."""
    name = "ai_book"

    def build(self, spec):
        """spec: the same fields kdp_books.py's adapter already passes to
        generate_book() — title/topic/niche/price_hint/author, plus
        family_config's chapter_count/audience/theme/output. Runs the
        full real pipeline: Groq content + PDF/cover render + Dual
        Inspection + Factory Memory log."""
        family_config = spec.get("family_config") or {}
        return bg.generate_book(
            title=spec.get("title") or "Untitled Book",
            topic=spec.get("topic") or spec.get("niche") or "",
            chapters=family_config.get("chapter_count", 8),
            audience=family_config.get("audience", "القارئ العام"),
            price=spec.get("price_hint") or 9.99,
            theme=family_config.get("theme", "blue"),
            author=spec.get("author") or "Galaxy Forge Press",
            output=family_config.get("output"),
        )


class TechdocPackageAssetBuilder:
    """Pairs with content_generation's "groq_techdoc" generator; also
    accepts already-written {"title","content"} components verbatim
    (same contract generate_product_package() already honors)."""
    name = "techdoc_package"

    def build(self, spec):
        """spec: the same fields digital_toolkits.py/
        professional_templates.py/knowledge_bases.py already pass —
        title/subtitle/topic/price_hint/author/components, plus
        family_config's theme/output. Runs the full real pipeline: Groq
        content (for any plain-string section) + PDF/cover render + Dual
        Inspection + Factory Memory log."""
        family_config = spec.get("family_config") or {}
        return bg.generate_product_package(
            title=spec.get("title") or "Untitled",
            subtitle=spec.get("subtitle") or "",
            topic=spec.get("topic") or spec.get("niche") or "",
            price=spec.get("price_hint") or 197.0,
            theme=family_config.get("theme", "blue"),
            author=spec.get("author") or "Galaxy Forge Press",
            output=family_config.get("output"),
            sections=components_to_sections(spec.get("components")),
            production_id=spec.get("production_id"),
        )


registry.register(AiBookAssetBuilder())
registry.register(TechdocPackageAssetBuilder())
