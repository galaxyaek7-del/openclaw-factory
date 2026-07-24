"""knowledge_bases family adapter (Packaging Architecture Plan §2). Wraps
book_generator.generate_book_from_content() — verbatim article content
only in Phase A (that function's own contract: content is used verbatim,
never AI-generated/rewritten). A component with no real content raises
rather than fabricating a knowledge-base article — see
product_families.spec.components_to_verbatim_chapters()'s docstring for
why an AI-generation path isn't in scope here yet.

Priced as product_type="premium" (gumroad_premium band) — the closest
already-configured economics band to a curated multi-article reference
bundle; _economics_platform_for() has no "knowledge_base" entry and
would otherwise silently fall back to kdp_ebook's $6 floor, the wrong
band for this family. Revisit once real knowledge-base sales exist
(Plan §7 Phase C+).
"""

import book_generator as bg
from .. import registry
from ..spec import components_to_verbatim_chapters


class KnowledgeBasesFamily:
    name = "knowledge_bases"

    def generate(self, spec):
        family_config = spec.get("family_config") or {}
        chapters = components_to_verbatim_chapters(spec.get("components"))
        return bg.generate_book_from_content(
            title=spec.get("title") or "Untitled",
            subtitle=spec.get("subtitle") or "",
            chapters=chapters,
            price=spec.get("price_hint") or 97.0,
            theme=family_config.get("theme", "blue"),
            author=spec.get("author") or "Galaxy Forge Press",
            output=family_config.get("output"),
            product_type="premium",
        )


registry.register(KnowledgeBasesFamily())
