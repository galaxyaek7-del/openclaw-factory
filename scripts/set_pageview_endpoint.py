"""BKL-002 helper: point gf-pageview.js on the experiment pages at a public
page-view receiver (Phase 5, 2026-10-16).

gf-pageview.js posts to same-origin /api/page-view unless a page carries
    <meta name="gf-pageview-endpoint" content="https://...">
On GitHub Pages same-origin is a 404, so no visit has ever been recorded.
Once the founder has an approved public HTTPS receiver, run:

    python scripts/set_pageview_endpoint.py --endpoint https://host/api/page-view            # dry run
    python scripts/set_pageview_endpoint.py --endpoint https://host/api/page-view --apply    # edits pages

Scope: only pages that carry the EXP-C81-001 campaign tag (--scope all for every
page that loads gf-pageview.js). Idempotent: an existing tag is replaced, never
duplicated. --remove takes the tag out again (rollback).

The receiver must answer the browser's CORS preflight for
https://galaxyaek7-del.github.io, because the beacon is a cross-origin JSON
POST. server.js currently sets cors({origin: false}), so pointing pages at it
without that change would still record nothing. This script cannot check the
receiver; it only edits the pages, and nothing is live until a push.
"""
import argparse
import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "customer_site")
CAMPAIGN = "utm_campaign=etsy_suspension_cluster"
META_RE = re.compile(r'[ \t]*<meta name="gf-pageview-endpoint" content="[^"]*">\r?\n?')


def _read(path, newline=None):
    with open(path, encoding="utf-8", newline=newline) as fh:
        return fh.read()


def target_pages(site=SITE, scope="experiment"):
    out = []
    for name in sorted(os.listdir(site)):
        if not name.endswith(".html"):
            continue
        html = _read(os.path.join(site, name))
        if "gf-pageview.js" not in html:
            continue
        if scope == "all" or CAMPAIGN in html:
            out.append(name)
    return out


def validate(endpoint):
    u = urlparse(endpoint or "")
    if u.scheme != "https" or not u.netloc:
        return "endpoint must be an absolute https:// URL"
    if u.hostname in ("localhost", "127.0.0.1", "::1") or (u.hostname or "").endswith(".local"):
        return "endpoint must be publicly reachable, not a local address"
    if '"' in endpoint or "<" in endpoint or ">" in endpoint:
        return "endpoint contains characters not allowed in an HTML attribute"
    return None


def edit(html, endpoint=None):
    """Return html with the tag set to endpoint (or removed when None)."""
    html = META_RE.sub("", html)
    if endpoint is None:
        return html
    tag = f'<meta name="gf-pageview-endpoint" content="{endpoint}">\n'
    m = re.search(r"<head[^>]*>\r?\n?", html, re.I)
    if not m:
        raise ValueError("no <head> element")
    return html[:m.end()] + tag + html[m.end():]


def run(endpoint=None, apply=False, remove=False, site=SITE, scope="experiment"):
    if not remove:
        err = validate(endpoint)
        if err:
            return {"ok": False, "error": err}
    changed = []
    for name in target_pages(site, scope):
        path = os.path.join(site, name)
        before = _read(path, newline="")
        after = edit(before, None if remove else endpoint)
        if after != before:
            changed.append(name)
            if apply:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(after)
    return {"ok": True, "applied": apply, "pages_changed": changed,
            "note": "nothing is live until commit + push; receiver must allow CORS from galaxyaek7-del.github.io"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--endpoint")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--scope", choices=("experiment", "all"), default="experiment")
    a = ap.parse_args(argv)
    r = run(a.endpoint, a.apply, a.remove, scope=a.scope)
    print(r)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
