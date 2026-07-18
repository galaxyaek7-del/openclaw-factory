"""OpenClaw Factory — common Product Specification (Packaging Architecture
Plan §3).

The single structured-JSON shape every family adapter's generate(spec)
receives, and every downstream stage (QA/Packaging/Metadata/Pricing)
could consume identically regardless of which family produced it.
Generalizes the `chapters`/`sections` pattern book_generator.py already
proved: a plain-string component means "generate this"; a
{"title","content"} dict means "use verbatim, never regenerated."
"""


def build_product_specification(
    niche, product_family, production_id=None, ladder=None, title=None,
    subtitle="", topic=None, author="OpenClaw Factory", language="ar",
    price_hint=None, economics_platform=None, recommended_platform=None,
    components=None, family_config=None,
):
    return {
        "production_id": production_id,
        "niche": niche,
        "product_family": product_family,
        "ladder": ladder,
        "title": title or niche,
        "subtitle": subtitle,
        "topic": topic or niche,
        "author": author,
        "language": language,
        "price_hint": price_hint,
        "economics_platform": economics_platform,
        "recommended_platform": recommended_platform,
        "components": components or [],
        "family_config": family_config or {},
    }


def components_to_sections(components):
    """Translates `components` into book_generator.generate_product_package()'s
    `sections` param shape: a plain string title -> AI-generate (via its own
    already-tested ai_generate_techdoc_content()); a {"title","content"}
    dict -> used verbatim. Never invents content itself — purely a shape
    translation. Returns None for an empty/missing list so the caller can
    fall through to generate_product_package()'s own default section
    skeleton (DEFAULT_TECHDOC_SECTIONS), unchanged."""
    if not components:
        return None
    sections = []
    for c in components:
        if isinstance(c, dict) and c.get("content"):
            sections.append({"title": c.get("title") or "Untitled Section", "content": c["content"]})
        elif isinstance(c, dict):
            sections.append(c.get("title") or "Untitled Section")
        else:
            sections.append(str(c))
    return sections


def components_to_verbatim_chapters(components):
    """Translates `components` into generate_book_from_content()'s
    `chapters` param — verbatim content only, no AI-generation path (Phase
    A limitation: knowledge_bases has no content-generation code of its
    own yet, see families/knowledge_bases.py). Raises ValueError if any
    component lacks real content — never silently fabricates a knowledge-
    base article, same "no duplicated logic, no silent fallback"
    discipline as the rest of this pipeline."""
    chapters = []
    for c in components or []:
        if not isinstance(c, dict) or not c.get("content"):
            raise ValueError(
                "knowledge_bases family requires verbatim content for every "
                "component in Phase A (no AI-generation path yet) — got a "
                "component with no content"
            )
        chapters.append({"title": c.get("title") or "Untitled Section", "content": c["content"]})
    return chapters
