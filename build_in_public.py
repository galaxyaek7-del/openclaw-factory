#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Build in Public / Marketing Arm (2026-07-24).

Founder decision (2026-07-24): "Build in Public" is OpenClaw's official
marketing strategy — directly closing the "Marketing readiness: NOT
READY" finding from the same day's Production Readiness Certification.

Three real deliverables, reusing already-built infrastructure:

  1. build_weekly_progress_report() — real, pure aggregation over
     decision_engine/production_blueprint/finance data. Zero AI cost,
     zero fabrication: English, honest numbers only, explicit "0" when
     nothing real happened this week rather than padding.
  2. draft_adr_post() — reuses ai_capability.orchestrator.generate()
     (ADR-104's real multi-model dispatch) to turn one real ADR file
     into an accessible public post draft. A real AI-generated draft,
     never auto-published — always written to a real pending-review
     file and queued via Telegram for the founder's own approval.
  3. queue_draft_for_approval() — reuses channels/telegram_direct.py's
     already-real, already-live send_telegram_message() directly,
     never a second Telegram integration. Arabic notification text
     (matching this factory's established Telegram convention since
     2026-07-18), pointing at the real English draft file for review.

Nothing here auto-publishes anything. "Prepare a public GitHub repo
structure" is built as real local files under public_site/ — creating
or pushing an actual public GitHub repository is a real, hard-to-
reverse, publicly-visible action requiring the founder's own explicit
action, not taken here.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DRAFTS_DIR = _FACTORY_ROOT / "drafts" / "pending_review"


def build_weekly_progress_report(days=7, decisions_path=None, ledger_path=None):
    """Real, English, honest-numbers-only weekly progress report — no
    hype language, no fabricated momentum. Every count is a real,
    already-computed signal: real decisions.jsonl entries within the
    window (scored/accepted/rejected), real production_blueprint
    lifecycle evidence (products moved forward), real finance_data.json
    sales within the window."""
    from decision_engine import ranking
    from channels import ledger

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    all_decisions = ranking.rank_all(path=decisions_path)

    def _in_window(d):
        ts = d.get("decided_at")
        if not ts:
            return False
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return False
        return dt >= cutoff

    recent = [d for d in all_decisions if _in_window(d)]
    scored = len(recent)
    accepted = sum(1 for d in recent if d.get("status") == "ACCEPTED")
    rejected = sum(1 for d in recent if d.get("status") == "REJECTED")
    deferred = scored - accepted - rejected

    sale_events = list(ledger.read_events(event_type="sale", ledger_path=ledger_path))
    real_revenue_this_week = 0.0
    for event in sale_events:
        ts = event.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt >= cutoff:
            amount = ledger._extract_sale_amount(event.get("raw") or {}, event.get("platform"))
            if amount:
                real_revenue_this_week += amount

    lines = [
        f"# OpenClaw — Weekly Progress Report",
        f"**Window:** last {days} days, ending {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "All numbers below are real counts from this factory's own real, timestamped records. "
        "No projections, no rounding up, no marketing language.",
        "",
        f"- Opportunities scored: **{scored}**",
        f"- Accepted: **{accepted}**",
        f"- Rejected: **{rejected}**",
        f"- Deferred / pending: **{deferred}**",
        f"- Real revenue recorded this week: **${real_revenue_this_week:.2f}**"
        + (" (zero real sales this week)" if real_revenue_this_week == 0 else ""),
        "",
    ]
    if scored == 0:
        lines.append("No new opportunities were scored this week.")

    return {
        "report_markdown": "\n".join(lines),
        "scored": scored, "accepted": accepted, "rejected": rejected, "deferred": deferred,
        "real_revenue_this_week": round(real_revenue_this_week, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def draft_adr_post(adr_path):
    """Real AI-generated public post draft from one real ADR file.
    Reuses ai_capability.orchestrator.generate() (ADR-104) directly —
    never a second content-generation path. Returns the real draft
    text; never writes or publishes anything itself (see
    queue_draft_for_approval() for that)."""
    from ai_capability import orchestrator as ai_orchestrator

    adr_path = Path(adr_path)
    adr_text = adr_path.read_text(encoding="utf-8")

    system_prompt = (
        "You are helping a solo founder turn an internal engineering decision record (ADR) "
        "into a short, honest public 'build in public' post. Rules: only state what the ADR "
        "itself actually says — never invent metrics, dates, or outcomes not in the source. "
        "No hype adjectives. Plain, direct English. 150-300 words. End with what's real vs. "
        "what's still a known gap, if the ADR discloses one."
    )
    user_prompt = f"Turn this ADR into a public build-in-public post:\n\n{adr_text[:6000]}"

    result = ai_orchestrator.generate("marketing_copy", system_prompt, user_prompt)
    return {
        "source_adr": str(adr_path.name),
        "draft_text": result["content"],
        "provider": result["provider"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def queue_draft_for_approval(draft_type, title, content_markdown, telegram_summary_arabic, drafts_dir=None, env_path=None):
    """Writes the real draft to a real pending-review file (never
    auto-published) and sends a real Arabic Telegram notification
    pointing at it — reuses channels/telegram_direct.py's already-live
    send_telegram_message() directly, never a second Telegram
    integration."""
    from channels import telegram_direct

    directory = Path(drafts_dir) if drafts_dir else DRAFTS_DIR
    directory.mkdir(parents=True, exist_ok=True)

    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in title.lower())[:60]
    filename = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_{draft_type}_{slug}.md"
    filepath = directory / filename
    filepath.write_text(content_markdown, encoding="utf-8")

    telegram_result = telegram_direct.send_telegram_message(
        f"{telegram_summary_arabic}\n\n📄 {filename}", env_path=env_path,
    )

    return {
        "draft_path": str(filepath), "filename": filename,
        "telegram": telegram_result,
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


def approve_draft(filename, drafts_dir=None, approved_dir=None):
    """Moves a real draft from drafts/pending_review/ to drafts/approved/
    once the founder has approved it (2026-07-24, via Telegram reply) --
    the file's content is already the final text; this only marks it
    approved and ready. No auto-posting integration exists for any real
    public channel today, so "final publishable" means ready for the
    founder to post manually, not an automated publish."""
    pending = Path(drafts_dir) if drafts_dir else DRAFTS_DIR
    approved = Path(approved_dir) if approved_dir else (_FACTORY_ROOT / "drafts" / "approved")
    approved.mkdir(parents=True, exist_ok=True)

    src = pending / filename
    if not src.exists():
        return {"approved": False, "path": None, "error": f"{filename} not found in {pending}"}

    dest = approved / filename
    dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    src.unlink()
    return {"approved": True, "path": str(dest), "approved_at": datetime.now(timezone.utc).isoformat()}


def publish_approved_draft(filename, title, approved_dir=None, public_site_dir=None):
    """Copies one real approved draft (drafts/approved/) into
    public_site/posts/ as a real, publishable file -- never touches the
    source approved file. `title` is supplied by the caller rather than
    re-derived, since draft_adr_post()'s AI output sometimes leaves its
    own source filename as a leftover '# adr-106-....md' heading; that
    artifact line is stripped here if present, the real approved body is
    otherwise reused verbatim."""
    approved = Path(approved_dir) if approved_dir else (_FACTORY_ROOT / "drafts" / "approved")
    posts_dir = (Path(public_site_dir) if public_site_dir else (_FACTORY_ROOT / "public_site")) / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)

    src = approved / filename
    if not src.exists():
        return {"published": False, "path": None, "error": f"{filename} not found in {approved}"}

    lines = src.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# ") and lines[0].strip().endswith(".md"):
        lines = lines[1:]
    body = "\n".join(lines).strip()

    slug = filename.rsplit(".", 1)[0]
    dest = posts_dir / f"{slug}.md"
    dest.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    return {"published": True, "path": str(dest), "slug": slug}


def _post_title(post_path):
    """First H1 line of a real published post file, falling back to the
    filename if the file has no heading (should not happen in practice,
    since publish_approved_draft() always writes one)."""
    for line in post_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return post_path.stem


def build_public_site_structure(output_dir=None):
    """Real, local scaffolding for a future public GitHub repo — never
    creates or pushes an actual public repository (a real, hard-to-
    reverse, publicly-visible action outside this function's scope).
    Product catalog reused verbatim from data/paddle_products.json —
    the real, only products this factory has ever priced and listed.
    Lists real posts already published under public_site/posts/ (see
    publish_approved_draft()) if any exist yet — never fabricates a
    post list when none has been published."""
    output = Path(output_dir) if output_dir else (_FACTORY_ROOT / "public_site")
    output.mkdir(parents=True, exist_ok=True)

    products_path = _FACTORY_ROOT / "data" / "paddle_products.json"
    products = json.loads(products_path.read_text(encoding="utf-8")) if products_path.exists() else []

    posts_dir = output / "posts"
    post_files = sorted(posts_dir.glob("*.md")) if posts_dir.exists() else []

    posts_section_md = ""
    posts_section_html = "<p>No posts published yet — check back soon.</p>"
    if post_files:
        posts_section_md = "\n## Posts\n\n" + "\n".join(
            f"- [{_post_title(p)}](posts/{p.name})" for p in post_files
        ) + "\n"
        posts_section_html = "<ul>\n" + "\n".join(
            f'<li><a href="posts/{p.name}">{_post_title(p)}</a></li>' for p in post_files
        ) + "\n</ul>"

    follow_note = (
        "This repository is updated as the factory operates — weekly progress reports and "
        "engineering decision posts land here as they happen, not on a fixed schedule. "
        "Watch or star this repo to follow along."
    )

    readme = (
        "# OpenClaw\n\n"
        "OpenClaw is a solo-founder digital investment company, built and operated in the open. "
        "This repository documents the real engineering decisions, real products, and real "
        "commercial evidence behind it — including the parts that don't work yet.\n\n"
        "## Real products, real prices\n\n"
        + "\n".join(f"- **{p['title']}** — ${p['price']:.2f}" for p in products)
        + "\n\n## Build in public\n\n"
        "Weekly progress reports and engineering decision records (ADRs) are published here as "
        "they happen — honest numbers, no hype.\n"
        + posts_section_md
        + f"\n## Follow the build\n\n{follow_note}\n"
    )
    (output / "README.md").write_text(readme, encoding="utf-8")

    html_rows = "\n".join(
        f'<tr><td>{p["title"]}</td><td>${p["price"]:.2f}</td></tr>' for p in products
    )
    index_html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>OpenClaw</title></head>
<body>
<h1>OpenClaw</h1>
<p>A solo-founder digital investment company, built and operated in the open.</p>
<h2>Products</h2>
<table>{html_rows}</table>
<h2>Posts</h2>
{posts_section_html}
<h2>Follow the build</h2>
<p>{follow_note}</p>
</body></html>
"""
    (output / "index.html").write_text(index_html, encoding="utf-8")
    (output / "products.json").write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "output_dir": str(output),
        "files_written": ["README.md", "index.html", "products.json"],
        "real_product_count": len(products),
        "real_post_count": len(post_files),
    }
