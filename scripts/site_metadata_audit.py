"""Read-only metadata and link audit for customer_site/ (Cycle 103).

Reproducible replacement for hand-counted claims such as "75 pages audited,
missing canonical repaired, duplicate Open Graph removed". For every
customer_site/*.html it checks:

  ENCODING        not valid UTF-8, or a UTF-16 BOM
  CHARSET         no <meta charset>
  TITLE           not exactly one non-empty <title>
  CANONICAL       not exactly one canonical link, or it does not point at
                  this page's own public URL
  CANONICAL_DUP   the same canonical URL on two pages
  OG_DUP          an og:* / twitter:* property declared more than once
  OG_URL          og:url present but different from the canonical
  OG_IMAGE        og:image present but not an absolute https URL
  TWITTER         og:title present but no twitter:card
  BROKEN_LINK     a relative href/src to a file that does not exist
  SITEMAP_MISSING an indexable page absent from sitemap.xml
  SITEMAP_DEAD    a sitemap <loc> whose file does not exist
  SITEMAP_NOINDEX a sitemap <loc> whose own page says noindex (a
                  contradictory signal: the sitemap asks for the page to be
                  indexed while the page asks not to be)
  DRAFT_BUY_LINK  a page that calls itself DRAFT/planned/coming soon but
                  carries a Gumroad buy link

Optionally (``--unlisted id1,id2``) it also flags links to Gumroad product
ids known to be unpublished or withdrawn (UNLISTED_LINK).

It reads files only; it never edits, fetches or publishes anything.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DIR = os.path.join(ROOT, "customer_site")
SITEMAP = os.path.join(ROOT, "sitemap.xml")
BASE_URL = "https://galaxyaek7-del.github.io/openclaw-factory/customer_site/"

_DRAFT_RE = re.compile(r"\b(DRAFT|coming soon|not yet listed|\(planned\))", re.I)
_GUMROAD_ID_RE = re.compile(r"gumroad\.com/l/([A-Za-z0-9_-]+)")


class _Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles: list[str] = []
        self._in_title = False
        self.canonicals: list[str] = []
        self.meta_props: list[tuple[str, str]] = []
        self.charset = False
        self.links: list[str] = []
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
            self.titles.append("")
        elif tag == "link" and "canonical" in a.get("rel", "").lower().split():
            self.canonicals.append(a.get("href", ""))
        elif tag == "meta":
            if "charset" in a or a.get("http-equiv", "").lower() == "content-type":
                self.charset = True
            key = a.get("property") or a.get("name") or ""
            if key.startswith(("og:", "twitter:")):
                self.meta_props.append((key, a.get("content", "")))
            if a.get("name", "").lower() == "robots" and "noindex" in a.get("content", "").lower():
                self.noindex = True
        for attr in ("href", "src"):
            if attr in a and tag in ("a", "link", "script", "img", "source"):
                self.links.append(a[attr])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.titles:
            self.titles[-1] += data


def _is_relative(url: str) -> bool:
    return bool(url) and not re.match(r"^([a-z][a-z0-9+.-]*:|//|#)", url, re.I)


def audit_page(path: str, site_dir: str, base_url: str, unlisted: set[str]) -> tuple[list[dict], dict]:
    name = os.path.relpath(path, site_dir).replace(os.sep, "/")
    page_dir = os.path.dirname(path)
    findings: list[dict] = []

    def add(kind, detail):
        findings.append({"page": name, "kind": kind, "detail": detail})

    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        add("ENCODING", "UTF-16 BOM")
        text = raw.decode("utf-16", errors="replace")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            add("ENCODING", f"not valid UTF-8 at byte {exc.start}")
            text = raw.decode("utf-8", errors="replace")

    c = _Collector()
    c.feed(text)
    if not c.charset:
        add("CHARSET", "no <meta charset>")
    titles = [t.strip() for t in c.titles]
    if len(titles) != 1 or not titles[0]:
        add("TITLE", f"{len(titles)} <title> element(s)")
    expected = base_url + name
    if len(c.canonicals) != 1:
        add("CANONICAL", f"{len(c.canonicals)} canonical link(s)")
    elif c.canonicals[0] != expected:
        add("CANONICAL", f"points at {c.canonicals[0]}")
    counts = Counter(k for k, _ in c.meta_props)
    for key, n in sorted(counts.items()):
        if n > 1:
            add("OG_DUP", f"{key} x{n}")
    props = dict(c.meta_props)
    if "og:url" in props and c.canonicals and props["og:url"] != c.canonicals[0]:
        add("OG_URL", f"og:url {props['og:url']} != canonical")
    if "og:image" in props and not props["og:image"].startswith("https://"):
        add("OG_IMAGE", props["og:image"] or "(empty)")
    if "og:title" in props and "twitter:card" not in props:
        add("TWITTER", "og:title without twitter:card")
    for link in c.links:
        if not _is_relative(link):
            continue
        target = link.split("#", 1)[0].split("?", 1)[0]
        if target and not os.path.exists(os.path.normpath(os.path.join(page_dir, target))):
            add("BROKEN_LINK", link)
    ids = set(_GUMROAD_ID_RE.findall(text))
    visible = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S | re.I)
    visible = re.sub(r"<[^>]+>", " ", visible)
    if ids and _DRAFT_RE.search(visible):
        add("DRAFT_BUY_LINK", ", ".join(sorted(ids)))
    for pid in sorted(ids & unlisted):
        add("UNLISTED_LINK", pid)
    meta = {"canonical": c.canonicals[0] if len(c.canonicals) == 1 else None, "noindex": c.noindex}
    return findings, meta


def audit_site(site_dir: str = SITE_DIR, sitemap: str = SITEMAP, base_url: str = BASE_URL,
               unlisted: set[str] | None = None) -> dict:
    unlisted = unlisted or set()
    pages: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(site_dir):
        for f in filenames:
            if f.endswith(".html"):
                pages.append(os.path.relpath(os.path.join(dirpath, f), site_dir).replace(os.sep, "/"))
    pages.sort()
    findings: list[dict] = []
    canon_pages: dict[str, list[str]] = defaultdict(list)
    indexable: set[str] = set()
    noindex_pages: set[str] = set()
    for name in pages:
        f, meta = audit_page(os.path.join(site_dir, *name.split("/")), site_dir, base_url, unlisted)
        findings += f
        if meta["canonical"]:
            canon_pages[meta["canonical"]].append(name)
        if not meta["noindex"]:
            indexable.add(name)
        else:
            noindex_pages.add(name)
    for url, names in canon_pages.items():
        if len(names) > 1:
            findings.append({"page": ", ".join(names), "kind": "CANONICAL_DUP", "detail": url})
    if os.path.exists(sitemap):
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", open(sitemap, encoding="utf-8-sig").read())
        in_map = {u[len(base_url):] for u in locs if u.startswith(base_url)}
        for name in sorted(in_map):
            if not os.path.exists(os.path.join(site_dir, name)):
                findings.append({"page": name, "kind": "SITEMAP_DEAD", "detail": "listed but missing"})
        for name in sorted(indexable - in_map):
            findings.append({"page": name, "kind": "SITEMAP_MISSING", "detail": "indexable page not in sitemap"})
        for name in sorted(in_map & noindex_pages):
            findings.append({"page": name, "kind": "SITEMAP_NOINDEX",
                             "detail": "listed in sitemap but the page itself says noindex"})
    return {
        "pages": len(pages),
        "findings": findings,
        "by_kind": dict(Counter(f["kind"] for f in findings)),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--unlisted", default="", help="comma-separated Gumroad ids known to be unpublished")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    report = audit_site(unlisted={x for x in args.unlisted.split(",") if x})
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for f in report["findings"]:
            print(f"{f['kind']:16} {f['page']} :: {f['detail']}")
        print(json.dumps({"pages": report["pages"], "by_kind": report["by_kind"]}))
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
