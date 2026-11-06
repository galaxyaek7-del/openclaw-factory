#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Public-site readiness audit for a company that sells to the whole world (2026-11-06). Read-only.

    python scripts/global_readiness_audit.py            # summary
    python scripts/global_readiness_audit.py --json     # everything, with the offending files

Checks (all on customer_site/, the only public surface):
  LANG       every page declares a language (<html lang>)
  TRUST_LINK every public page reaches the Trust Center (privacy, terms, refunds) with one click
  LINKS      internal links (href/src without a scheme) point at files that exist
  SITEMAP    every public page is in sitemap.xml
  LANGUAGES  how many pages exist per language (a fact for the localisation plan, not a pass/fail)
Pages under trust/ are the policies themselves; `noindex` pages are skipped. Nothing is written.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "customer_site"
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/"
HREF = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#?][^"']*)["']""", re.I)
LANG = re.compile(r"<html[^>]*\blang\s*=\s*[\"']([^\"']+)", re.I)
TRUST_HREF = re.compile(r"""href\s*=\s*["'](?:\./)?(?:\.\./)?trust/(?:index|privacy-policy|terms-of-service|refund-policy)\.html""", re.I)


def public_pages(site=SITE):
    out = []
    for p in sorted(site.glob("*.html")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"<meta[^>]+name=[\"']robots[\"'][^>]*noindex", text, re.I):
            continue
        out.append((p, text))
    return out


def internal_targets(text):
    for m in HREF.finditer(text):
        u = m.group(1).strip()
        if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|\{|<|\$|data:)", u, re.I) or "{{" in u or "${" in u:
            continue
        yield unquote(urlparse(u).path)


def sitemap_urls(path=SITEMAP):
    try:
        return set(re.findall(r"<loc>([^<]+)</loc>", Path(path).read_text(encoding="utf-8")))
    except OSError:
        return set()


def run(site=SITE, sitemap=SITEMAP, base=BASE):
    pages = public_pages(site)
    smap = sitemap_urls(sitemap)
    no_lang, no_trust, not_in_map, broken = [], [], [], []
    langs = Counter()
    for p, text in pages:
        m = LANG.search(text)
        if not m:
            no_lang.append(p.name)
        else:
            langs[m.group(1).split("-")[0].lower()] += 1
        if not TRUST_HREF.search(text):
            no_trust.append(p.name)
        if base + p.name not in smap:
            not_in_map.append(p.name)
        for t in set(internal_targets(text)):
            if t and not (p.parent / t).exists() and not (site / t.lstrip("/")).exists():
                broken.append(f"{p.name} -> {t}")
    drafts = sorted(q.name for q in (site / "trust").glob("*.html") if "DRAFT" in q.read_text(encoding="utf-8", errors="ignore")[:6000])         if (site / "trust").is_dir() else []
    # Linking every page to policies that are still marked "DRAFT TEMPLATE - NOT LEGALLY REVIEWED" with
    # "[FOUNDER INPUT REQUIRED]" placeholders would send visitors to unfinished legal text: so a missing link is a
    # consequence of an open founder/legal decision, not a code defect, and the audit says which it is.
    return {"pages": len(pages), "languages": dict(langs), "no_lang": no_lang, "no_trust_link": no_trust,
            "trust_pages_still_draft": drafts,
            "no_trust_link_blocker": "legal pages are DRAFT: finish and review them (founder + lawyer), then link them" if drafts else None,
            "not_in_sitemap": not_in_map, "broken_internal_links": broken}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    r = run()
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(json.dumps({"pages": r["pages"], "languages": r["languages"], "no_lang": len(r["no_lang"]),
                          "no_trust_link": len(r["no_trust_link"]), "trust_pages_still_draft": len(r["trust_pages_still_draft"]), "not_in_sitemap": len(r["not_in_sitemap"]),
                          "broken_internal_links": len(r["broken_internal_links"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
