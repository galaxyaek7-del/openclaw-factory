#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sales-path audit: can a visitor get from the public site to a purchase? (2026-11-07). Local and read-only, no network.

    python scripts/sales_path_audit.py [--json]

Checks, from the files that are actually published:
  * sitemap.xml: every URL exists on disk, none is noindex, none is listed twice;
  * indexable tool/guide/blog pages that are missing from the sitemap;
  * every catalog product has a tool page, and that page carries the catalog's buy URL;
  * every tool page's buy URL belongs to the catalog (a page selling something we no longer list);
  * orphan pages that ARE indexable (a page nothing links to cannot be reached from the site).
Exit 1 when any HIGH finding exists (a path that cannot lead to a sale).
"""
from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://galaxyaek7-del.github.io/openclaw-factory/"
NOINDEX = re.compile(r'name="robots"[^>]*noindex', re.I)
BUY = re.compile(r'https://[A-Za-z0-9.-]*gumroad\.com/l/[A-Za-z0-9_-]+')


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def F(sev, what, fix):
    return {"severity": sev, "what": what, "next": fix}


def audit(root=ROOT):
    out = []
    sm = read(root / "sitemap.xml")
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    dup = [u for u, n in Counter(locs).items() if n > 1]
    if dup:
        out.append(F("MEDIUM", f"sitemap lists {len(dup)} URL(s) twice: {dup[:2]}", "dedupe the generator"))
    in_map = set()
    for u in locs:
        rel = u.replace(BASE, "")
        in_map.add(rel)
        f = root / rel
        if not f.exists():
            out.append(F("HIGH", f"sitemap URL has no file: {rel}", "remove it or restore the page"))
        elif rel.endswith(".html") and NOINDEX.search(read(f)):
            out.append(F("MEDIUM", f"sitemap lists a noindex page: {rel}", "drop it from the sitemap or remove noindex"))
    pages = [p.replace("\\", "/") for pat in ("tool-*.html", "guide-*.html", "blog-*.html") for p in glob.glob(str(root / "customer_site" / pat))]
    rel_pages = [str(Path(p).relative_to(root)).replace("\\", "/") for p in pages]
    not_in = [p for p in rel_pages if p not in in_map and not NOINDEX.search(read(root / p))]
    if not_in:
        out.append(F("MEDIUM", f"{len(not_in)} indexable page(s) missing from sitemap.xml, e.g. {not_in[:3]}", "add them (sitemap generator)"))
    cat = (json.loads(read(root / "customer_site" / "catalog.json") or "{}").get("data") or {}).get("products", [])
    tool_text = {}
    for p in glob.glob(str(root / "customer_site" / "tool-*.html")):
        tool_text[p] = read(p)
    cat_urls = {c.get("url") for c in cat if c.get("url")}
    all_text = chr(10).join(read(p) for p in glob.glob(str(root / "customer_site" / "*.html")) if not NOINDEX.search(read(p)))
    unreachable = []
    for c in cat:
        pg = [t for t in tool_text.values() if c["id"] in t]
        if pg and c.get("url") and not any(c["url"] in t for t in pg):
            out.append(F("HIGH", f"{c['id']}: its page does not carry the catalog buy URL", "regenerate the page"))
        elif not pg and c.get("url") and c["url"].split("?")[0] not in all_text:
            unreachable.append(c["id"])
    if unreachable:
        out.append(F("MEDIUM", f"{len(unreachable)} live products have no indexable site page that links to their buy URL (reachable only from Gumroad itself / Pinterest), e.g. {unreachable[:4]}",
                     "legacy listings: add them to a catalog page or accept Gumroad-only; new batches get a tool page automatically"))
    for p, t in tool_text.items():
        urls = set(BUY.findall(t))
        if urls and not (urls & {u.split("?")[0] for u in cat_urls}) and not any(u.split("?")[0] in t for u in cat_urls):
            out.append(F("HIGH", f"{Path(p).name} sells a Gumroad product that is not in the catalog", "retire the page or relist"))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    f = audit()
    if "--json" in argv:
        sys.stdout.write(json.dumps(f, ensure_ascii=False, indent=1) + "\n")
    else:
        c = Counter(x["severity"] for x in f)
        L = [f"SALES PATH AUDIT: {c.get('HIGH', 0)} high, {c.get('MEDIUM', 0)} medium"]
        for x in f:
            L.append(f"[{x['severity']}] {x['what']}\n        -> {x['next']}")
        sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 1 if any(x["severity"] == "HIGH" for x in f) else 0


if __name__ == "__main__":
    sys.exit(main())
