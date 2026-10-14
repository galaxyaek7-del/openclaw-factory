"""Cycle 85: internal link graph of the public customer_site.

61 URLs sit in sitemap.xml and the GitHub Pages deployment is live, but a page
that nothing links to is effectively invisible to both a reader and a crawler.
This maps real internal href= navigation so "we published content" can never be
mistaken for "a visitor can reach it".
"""
import collections
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HREF = re.compile(r'href="([^"]+)"', re.I)

pages = {os.path.basename(p) for p in glob.glob("customer_site/*.html")}
out = collections.defaultdict(set)
inbound = collections.defaultdict(set)

for p in glob.glob("customer_site/*.html"):
    b = os.path.basename(p)
    h = open(p, encoding="utf-8", errors="replace").read()
    for m in HREF.finditer(h):
        t = m.group(1).split("#")[0].split("?")[0]
        if not t or t.startswith(("http", "mailto:", "javascript:", "/")):
            continue
        name = os.path.basename(t)
        if name in pages and name != b:
            out[b].add(name)
            inbound[name].add(b)

print(f"customer_site pages           : {len(pages)}")
orphans = sorted(f for f in pages if not inbound.get(f))
print(f"pages with ZERO inbound links  : {len(orphans)}")
for o in orphans:
    print("   ORPHAN", o)
print()
print(f"index.html links internally to : {len(out.get('index.html', ()))} pages")
for n in sorted(out.get("index.html", ())):
    print("   ->", n)
print()
sales = [p for p in pages if "etsy" in p.lower()]
print("Etsy-related pages and their inbound link count:")
for p in sorted(sales):
    print(f"   {len(inbound.get(p, ())):>2} inbound  {p}")