"""Groq-backed content generators (Universal Production Engine §3/§6,
2026-07-18) — today's real `ContentGenerator` implementations. Thin
wrappers over book_generator.py's already-tested, content-only functions
(ai_generate_book_content()/ai_generate_techdoc_content() + their honest
fallbacks) — no new Groq prompting logic, no new fallback logic.

Interface contract: generate(request) -> dict. The dict's exact shape is
a contract between one ContentGenerator and its paired Asset Generator
(book content stays book_data-shaped for create_ai_book(); techdoc
content stays components-shaped for generate_product_package()'s own
section assembly) — the call contract (one method, one dict in, one
dict out, never raises) is what's uniform and swappable, matching how
book_generator.py's own two content paths already differ in shape today.

Swapping either of these for a future AI model means registering a new
generator under the SAME name (e.g. "groq_book") with the SAME output
shape — every downstream Asset Generator keeps working unchanged.
"""

import book_generator as bg
from .. import registry


class GroqBookContentGenerator:
    """Pairs with asset_generation's pdf_builder "ai_book" implementation."""
    name = "groq_book"

    def generate(self, request):
        """request: {"title", "topic", "chapter_count" (default 8),
        "audience" (default "القارئ العام")}. Returns the real book_data
        shape create_ai_book() expects: {"subtitle","introduction",
        "chapters","conclusion"}. Falls back to honest, clearly-labeled
        placeholder content on a real Groq failure — never raises,
        matching generate_book()'s own existing discipline."""
        title = request.get("title", "Untitled Book")
        topic = request.get("topic") or title
        chapters = request.get("chapter_count", 8)
        audience = request.get("audience", "القارئ العام")
        try:
            return bg.ai_generate_book_content(title, topic, chapters, audience)
        except Exception:
            return bg._fallback_book_content(title, topic, chapters, audience)


class GroqTechdocContentGenerator:
    """Pairs with asset_generation's pdf_builder "techdoc" implementation."""
    name = "groq_techdoc"

    def generate(self, request):
        """request: {"title", "topic", "section_titles": [str, ...]}.
        Returns {"components": [{"title","content"}, ...]} — the same
        shape generate_product_package() already assembles from
        ai_generate_techdoc_content()'s real output. Falls back to
        honest, clearly-labeled placeholder content on a real Groq
        failure — never raises."""
        title = request.get("title", "Untitled")
        topic = request.get("topic") or title
        section_titles = request.get("section_titles") or []
        try:
            generated = bg.ai_generate_techdoc_content(title, topic, section_titles)
        except Exception:
            generated = bg._fallback_techdoc_content(topic, section_titles)
        return {"components": generated}


registry.register(GroqBookContentGenerator())
registry.register(GroqTechdocContentGenerator())
