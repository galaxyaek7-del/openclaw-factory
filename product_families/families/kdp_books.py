"""kdp_books family adapter — legacy compatibility only (Packaging
Architecture Plan §2). Wraps book_generator.generate_book() unchanged;
zero new content-generation code. This is the exact function
orchestrator/engines/production.py's non-ladder-tagged branch already
calls via subprocess today — this adapter calls it in-process instead
(same pattern tests/test_product_package.py already uses successfully),
returning the identical result shape.
"""

import book_generator as bg
from .. import registry


class KdpBooksFamily:
    name = "kdp_books"

    def generate(self, spec):
        family_config = spec.get("family_config") or {}
        return bg.generate_book(
            title=spec.get("title") or "Untitled Book",
            topic=spec.get("topic") or spec.get("niche") or "",
            chapters=family_config.get("chapter_count", 8),
            audience=family_config.get("audience", "القارئ العام"),
            price=spec.get("price_hint") or 9.99,
            theme=family_config.get("theme", "blue"),
            author=spec.get("author") or "OpenClaw Press",
            output=family_config.get("output"),
        )


registry.register(KdpBooksFamily())
