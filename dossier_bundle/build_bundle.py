"""OpenClaw Factory — Dossier Bundle builder (Universal Production Engine
§3/§6, 2026-07-18).

Mandatory per-product artifacts stage: every product generated must
automatically produce documentation, metadata, marketing assets, support
files, and update history. Reuses production_factory/dossier.py's real
metadata assembly and book_generator.py's real groq_chat() for
marketing/support copy — no generation logic duplicated here, only
assembled.
"""

import json
import os
import re
from datetime import datetime, timezone

import book_generator as bg
from production_factory.dossier import build_production_dossier

_CHANGELOG_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'product_changelog.jsonl'
))


def _build_documentation(spec):
    """A plain README-style assembly from already-generated components —
    no new content generation. Empty/missing components produce an
    honest, minimal doc rather than inventing filler."""
    title = spec.get("title") or "Untitled Product"
    components = spec.get("components") or []
    lines = [f"# {title}", ""]
    if spec.get("subtitle"):
        lines += [spec["subtitle"], ""]
    for c in components:
        if isinstance(c, dict):
            lines += [f"## {c.get('title', 'Untitled Section')}", "", c.get("content", "") or "", ""]
    return "\n".join(lines).strip() + "\n"


def _parse_marketing_copy(text):
    parts = re.split(r'(?m)^#{1,4}\s*(HEADLINE|DESCRIPTION|KEYWORDS)\s*#{0,4}\s*$', text, flags=re.IGNORECASE)
    fields = {"headline": "", "description": "", "keywords": ""}
    for i in range(1, len(parts), 2):
        key = parts[i].strip().lower()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if key in fields:
            fields[key] = body
    return fields


def _generate_marketing_copy(spec):
    """Groq-backed title/description/keywords — same real-generation
    discipline as lib/publisher_seo.js's generatePublisherSEO(), reusing
    book_generator.groq_chat() directly rather than bridging to JS. Never
    raises: an honest, clearly-labeled fallback replaces AI copy on a
    real Groq failure, matching every other AI content path in this
    factory."""
    title = spec.get("title") or "Untitled Product"
    niche = spec.get("niche") or spec.get("topic") or title
    system = (
        "You are the marketing/SEO copywriting agent at OpenClaw Factory. "
        "Write real, concise, conversion-focused marketplace copy for a "
        "real digital product — never generic filler."
    )
    user_prompt = (
        f"Product title: \"{title}\"\nNiche/topic: {niche}\n\n"
        "Return ONLY this exact plain-text format, no JSON, no Markdown:\n"
        "##HEADLINE##\n<one compelling sales headline, under 70 chars>\n"
        "##DESCRIPTION##\n<150-250 word marketplace description>\n"
        "##KEYWORDS##\n<8-12 comma-separated SEO keywords>"
    )
    try:
        raw = bg.groq_chat(
            system, user_prompt, max_tokens=800,
            cost_context={"niche": niche, "title": title, "product_type": "marketing_copy"},
        )
        return {"ok": True, "content": _parse_marketing_copy(raw), "source": "groq"}
    except Exception as e:
        return {
            "ok": False,
            "content": {
                "headline": title,
                "description": f"AI marketing copy generation was unavailable for this attempt ({e}).",
                "keywords": niche,
            },
            "source": "fallback",
        }


def _generate_support_copy(spec):
    """A short FAQ/troubleshooting support doc — reuses the exact same
    Groq call mechanism as marketing copy (one small, honest, real
    generation call), not a new generator."""
    title = spec.get("title") or "Untitled Product"
    niche = spec.get("niche") or spec.get("topic") or title
    system = (
        "You are the customer-support content agent at OpenClaw Factory. "
        "Write a real, useful FAQ/troubleshooting section for a digital "
        "product buyer — never generic filler."
    )
    user_prompt = (
        f"Product title: \"{title}\"\nNiche/topic: {niche}\n\n"
        "Write 4-6 real FAQ question/answer pairs a buyer of this exact "
        "product would actually ask, plain text, one pair per paragraph."
    )
    try:
        raw = bg.groq_chat(
            system, user_prompt, max_tokens=800,
            cost_context={"niche": niche, "title": title, "product_type": "support_copy"},
        )
        return {"ok": True, "content": raw, "source": "groq"}
    except Exception as e:
        return {
            "ok": False,
            "content": f"AI support content generation was unavailable for this attempt ({e}).",
            "source": "fallback",
        }


def _append_changelog(production_id, spec, generation_result, changelog_path=None):
    """Update history: one append-only line per generation, keyed by
    production_id — mirrors every other real .jsonl log this factory
    already uses (books/_generation_log.jsonl, data/decisions.jsonl).
    Logging failures must never break a successful generation, same
    discipline as book_generator._log_generation()."""
    path = changelog_path or _CHANGELOG_PATH
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entry = {
            "production_id": production_id,
            "title": spec.get("title"),
            "product_family": spec.get("product_family"),
            "published": generation_result.get("published"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        return True
    except Exception:
        return False


def build_product_dossier_bundle(spec, generation_result, decision=None, changelog_path=None):
    """Assembles the mandatory per-product artifact bundle (Universal
    Production Engine §3): documentation, metadata, marketing, support,
    update history — all keyed by the SAME production_id every other
    stage already uses.

    spec: a ProductSpecification-shaped dict whose `components` hold the
    FINAL, already-generated {"title","content"} sections (post-Content-
    Generation) — this stage never generates product documentation
    content itself, only assembles what already exists.
    generation_result: the real Asset Generation build() result (has
    production_id/file/path/pages/published/inspection/...).
    decision: optional real Decision object — when provided, metadata
    reuses production_factory.dossier.build_production_dossier()'s full
    real assembly unchanged; when omitted (e.g. a family generated
    outside the ladder/decision path), metadata is a smaller, honest
    subset built directly from spec/generation_result rather than a
    fabricated ladder/ROI/market analysis.
    """
    production_id = generation_result.get("production_id") or spec.get("production_id")

    if decision is not None:
        metadata = build_production_dossier(decision)
    else:
        metadata = {
            "production_id": production_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "niche": spec.get("niche"),
            "product_family": spec.get("product_family"),
            "pricing_strategy": {"recommended_price": generation_result.get("price")},
            "has_cover": generation_result.get("cover") is not None,
            "note": "no Decision supplied — reduced metadata, no ladder/ROI/market data available",
        }

    bundle = {
        "production_id": production_id,
        "documentation": _build_documentation(spec),
        "metadata": metadata,
        "marketing": _generate_marketing_copy(spec),
        "support": _generate_support_copy(spec),
    }
    bundle["changelog_appended"] = _append_changelog(production_id, spec, generation_result, changelog_path)
    return bundle
