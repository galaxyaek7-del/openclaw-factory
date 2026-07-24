"""Galaxy Forge — Dossier Bundle builder (Universal Production Engine
§3/§6, 2026-07-18).

Mandatory per-product artifacts stage: every product generated must
automatically produce documentation, metadata, marketing assets, support
files, and update history. Reuses production_factory/dossier.py's real
metadata assembly and book_generator.py's real groq_chat() for
marketing/support copy — no generation logic duplicated here, only
assembled.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone

import book_generator as bg
import factory_state

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
    """Real bug found live (2026-07-22, product quality pass): the model
    doesn't reliably echo the literal HEADLINE/DESCRIPTION/KEYWORDS tag
    words as their own header line — it writes a real headline as the
    header itself (e.g. "##SOC 2 Compliance Made Easy with AI##") with
    the description following as body text, and often drops the KEYWORDS
    marker line entirely. Same class of failure as
    book_generator._parse_sectioned_techdoc()'s real bug and identical
    resilience-over-strictness fix: when the strict tag match leaves
    headline/description empty, recover the model's real first header
    text as the headline and its body as the description (both genuinely
    written by the model, just under a header it invented), and fall
    back to a plausible comma-heavy final paragraph for keywords rather
    than leaving it blank."""
    parts = re.split(r'(?m)^#{1,4}\s*(HEADLINE|DESCRIPTION|KEYWORDS)\s*#{0,4}\s*$', text, flags=re.IGNORECASE)
    fields = {"headline": "", "description": "", "keywords": ""}
    for i in range(1, len(parts), 2):
        key = parts[i].strip().lower()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if key in fields:
            fields[key] = body

    if not fields["headline"] or not fields["description"]:
        loose_parts = re.split(r'(?m)^#{1,4}\s*(.+?)\s*#{0,4}\s*$', text)
        if len(loose_parts) >= 3 and loose_parts[1].strip():
            if not fields["headline"]:
                fields["headline"] = loose_parts[1].strip()
            if not fields["description"]:
                fields["description"] = loose_parts[2].strip()

    if not fields["keywords"]:
        paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
        if paragraphs:
            last = paragraphs[-1].lstrip("#").strip()
            if last.count(",") >= 3 and last.count(".") == 0:
                fields["keywords"] = last

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
        "You are the marketing/SEO copywriting agent at Galaxy Forge. "
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
        "You are the customer-support content agent at Galaxy Forge. "
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


def _count_prior_versions(production_id, changelog_path):
    """Reads the changelog BEFORE this generation's own entry is appended
    -- a real, derived count, not a separately-tracked version store. No
    production_id or no prior file -> this is the first build."""
    if not production_id or not os.path.exists(changelog_path):
        return 0
    count = 0
    try:
        with open(changelog_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("production_id") == production_id:
                    count += 1
    except OSError:
        return 0
    return count


def _next_version(production_id, changelog_path):
    """Semantic-ish version derived from real changelog history: the
    first build of a production_id is 1.0.0; each subsequent real
    regeneration for the SAME production_id (e.g. a retried/re-run
    stage) bumps the minor number. Never fabricated -- purely a count of
    real prior entries."""
    return f"1.{_count_prior_versions(production_id, changelog_path)}.0"


def _spec_hash(spec):
    """A stable fingerprint of what was actually requested -- lets a
    future reader confirm two builds used the identical specification,
    without storing the whole spec twice."""
    try:
        canonical = json.dumps(spec, sort_keys=True, ensure_ascii=False, default=str)
    except TypeError:
        canonical = str(spec)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def _build_manifest(spec, generation_result, production_id, version,
                     content_generator=None, asset_builder=None, packager=None):
    """Real record of exactly what was built and with which UPE registry
    implementations -- the "how do I reproduce or audit this exact
    build" artifact. content_generator/asset_builder/packager are
    honestly None when the caller (a Phase A family not yet routed
    through the new registries) doesn't know them -- never guessed."""
    files = [f for f in (
        generation_result.get("path"),
        (generation_result.get("cover") or {}).get("path"),
    ) if f]
    return {
        "production_id": production_id,
        "version": version,
        "product_family": spec.get("product_family"),
        "files": files,
        "content_generator": content_generator,
        "asset_builder": asset_builder,
        "packager": packager,
        "spec_hash": _spec_hash(spec),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _recovery_metadata(production_id, state_path=None):
    """Real, honest lookup of this exact product's recovery history in
    factory_state.json's pending_retries (Unified Recovery System §3) --
    never a fabricated "no issues" claim when interruption data actually
    exists, and never a per-product history invented from
    data/recovery_actions.jsonl, whose real records are factory-wide
    operator actions with no production_id field to filter by."""
    state = factory_state.load_state(state_path)
    pending = [
        r for r in (state.get("pending_retries") or [])
        if isinstance(r.get("context"), dict) and r["context"].get("production_id") == production_id
    ]
    return {
        "had_pending_retry": bool(pending),
        "pending_retries": pending,
        "factory_last_successful_checkpoint": state.get("last_successful_checkpoint"),
    }


def _append_changelog(production_id, spec, generation_result, version, changelog_path=None):
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
            "version": version,
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


def build_product_dossier_bundle(
    spec, generation_result, decision=None, changelog_path=None,
    content_generator=None, asset_builder=None, packager=None, state_path=None,
):
    """Assembles the mandatory per-product artifact bundle (Universal
    Production Engine §3/Roadmap Step 2): documentation, metadata,
    marketing, support, update history, version, build manifest, QA
    report, and recovery metadata — all keyed by the SAME production_id
    every other stage already uses.

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
    content_generator/asset_builder/packager: the UPE registry names the
    caller actually used (e.g. "groq_techdoc"/"techdoc_package"/
    "single_file") — surfaced in the build manifest for real
    reproducibility, honestly None when the caller doesn't route through
    the new registries yet.
    """
    production_id = generation_result.get("production_id") or spec.get("production_id")
    path = changelog_path or _CHANGELOG_PATH
    version = _next_version(production_id, path)

    if decision is not None:
        # Local import: production_factory.dossier imports product_families,
        # whose family adapters (automation_systems.py, Roadmap Step 2) import
        # this module back — a module-level import here would be circular.
        from production_factory.dossier import build_production_dossier
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
        "version": version,
        # Autonomous Digital Company v1, Track C (2026-07-19): honestly
        # "active" for every product today -- there is zero real per-
        # product sales data yet to ever justify "declining"/"retire".
        # The decision logic that would set this to anything else is
        # real future work (needs real sales history to evolve/retire
        # against), named here so it isn't forgotten, never guessed at.
        "lifecycle_status": "active",
        "documentation": _build_documentation(spec),
        "metadata": metadata,
        "marketing": _generate_marketing_copy(spec),
        "support": _generate_support_copy(spec),
        "build_manifest": _build_manifest(
            spec, generation_result, production_id, version,
            content_generator=content_generator, asset_builder=asset_builder, packager=packager,
        ),
        "qa_report": generation_result.get("inspection"),
        "recovery_metadata": _recovery_metadata(production_id, state_path=state_path),
    }
    bundle["changelog_appended"] = _append_changelog(production_id, spec, generation_result, version, path)
    return bundle
