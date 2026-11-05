#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — affiliate content prep (autonomous, publish-gated correctly).

For the top-3 QUALIFIED programs by AFFILIATE_PRIORITY_SCORE:
- builds deterministic 5-piece content packs (affiliate_content_factory,
  verified_usage=False, disclosure forced) -> affiliate_content/<asset>.json
- renders 2 informational HTML pages to customer_site/affiliate/ with the
  mandatory disclosure banner and NO affiliate links (none approved yet;
  link slots explicitly marked pending). Publishing to our own static site
  is the authorized channel #1; external posting stays founder-gated.
Idempotent: skips assets already prepared. Never fabricates usage/reviews.
"""
import html
import json
from datetime import datetime, timezone
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent
OUT_CONTENT = FACTORY_DIR / "affiliate_content"
OUT_SITE = FACTORY_DIR / "customer_site" / "affiliate"

DISCLOSURE = ("This page may contain affiliate links. If you purchase through "
              "a qualifying link, we may receive a commission at no additional "
              "cost to you. Link slots on this page are pending program approval.")

ANGLE = {
    "CO-digitalocean-affiliate": ("cloud hosting for side projects",
                                  "developers choosing their first VPS"),
    "CO-brevo-affiliate": ("email marketing for small business",
                           "owners comparing newsletter tools"),
    "CO-n8n-affiliate": ("workflow automation without enterprise budget",
                         "operators automating repetitive work"),
}


def _packs_for(factory, AffiliateContentInput):
    from affiliate import priority as P
    ranked = [s for s in P.rank_all()["ranked"] if s["status"] == "QUALIFIED"][:3]
    made = []
    OUT_CONTENT.mkdir(parents=True, exist_ok=True)
    import affiliate.registry as R
    by_id = {o.get("opportunity_id"): o for o in R.load_opportunities()}
    for s in ranked:
        asset_id = "AFF-" + s["opportunity_id"].replace("CO-", "").replace("-affiliate", "").upper() + "-001"
        dest = OUT_CONTENT / f"{asset_id}.json"
        if dest.exists():
            made.append({"asset_id": asset_id, "status": "EXISTS"})
            continue
        o = by_id.get(s["opportunity_id"], {})
        angle, audience = ANGLE.get(s["opportunity_id"], ("business software", "small teams"))
        inp_arg = AffiliateContentInput(
            opportunity_id=s["opportunity_id"], program_name=s["program_name"],
            product_category=str(o.get("category", "business software")),
            solves_problem=angle, target_audience=audience,
            commission_disclosure=str(o.get("commission_value", "see program terms")),
            verified_usage=False, audience_angle=angle)
        pieces = factory.build_affiliate_content(inp_arg)
        rendered = factory.render_all_formats(inp_arg)
        dest.write_text(json.dumps({
            "asset_id": asset_id, "opportunity_id": s["opportunity_id"],
            "program_name": s["program_name"], "priority_score": s["score"],
            "verified_usage": False, "disclosure": DISCLOSURE,
            "affiliate_link": "PENDING_APPROVAL",
            "pieces": [{"kind": p.format, "title": p.title, "body": p.body,
                        "cta": p.cta, "disclosure": p.disclosure} for p in pieces],
            "rendered": rendered,
            "prepared_at": datetime.now(timezone.utc).isoformat(),
            "status": "DRAFT_AWAITS_FOUNDER_PUBLISH"}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        made.append({"asset_id": asset_id, "status": "CREATED"})
    return made


HTML_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Galaxy Forge Guides</title>
<meta name="description" content="{desc}">
<style>body{{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;line-height:1.6}} .disc{{background:#fff8e1;border:1px solid #e0c36a;padding:.75rem;border-radius:6px;font-size:.9rem}} h1{{font-size:1.6rem}}</style>
</head><body>
<div class="disc">{disclosure}</div>
<h1>{title}</h1>
<p><em>Galaxy Forge informational guide. We have no paid relationship shown on this page yet — affiliate link slots are pending program approval.</em></p>
{body}
<p><a href="/site/">Back to Galaxy Forge</a></p>
</body></html>"""


def _render_pages():
    from affiliate_content_factory import render_all_formats  # noqa (ensures module present)
    pages = []
    OUT_SITE.mkdir(parents=True, exist_ok=True)
    for asset_file in sorted(OUT_CONTENT.glob("AFF-*.json"))[:2]:
        pack = json.loads(asset_file.read_text(encoding="utf-8"))
        pieces = pack.get("pieces", [])
        if not pieces:
            continue
        title = pack["program_name"] + " — independent informational guide"
        sections = []
        for p in pieces:
            paras = "".join(f"<p>{html.escape(q)}</p>"
                            for q in str(p.get("body", "")).split("\n") if q.strip())
            sections.append(f"<h2>{html.escape(p.get('kind', '').title())}: "
                            f"{html.escape(p.get('title', ''))}</h2>{paras}")
        body_html = "\n".join(sections)
        page = OUT_SITE / f"{asset_file.stem.lower().replace('_', '-')}.html"
        page.write_text(HTML_SHELL.format(
            title=html.escape(title),
            desc=html.escape(f"Independent informational guide: {pack['program_name']}."),
            disclosure=html.escape(DISCLOSURE), body=body_html), encoding="utf-8")
        pages.append({"asset_id": pack["asset_id"], "page": str(page.relative_to(FACTORY_DIR)),
                      "status": "PUBLISHED_ON_OWN_SITE"})
    return pages


def main():
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    import affiliate_content_factory as F
    packs = _packs_for(F, F.AffiliateContentInput)
    pages = _render_pages()
    print(json.dumps({"packs": packs, "pages": pages}, ensure_ascii=False))


if __name__ == "__main__":
    main()
