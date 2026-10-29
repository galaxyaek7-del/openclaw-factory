"""Add (or remove) the Cloudflare Web Analytics beacon on every customer_site page.

Prepared 2026-10-29, not applied. The public site is served by GitHub Pages,
which records no visits and cannot receive the factory's own page-view POST.
Cloudflare Web Analytics is free, needs no DNS change for a site it does not
proxy ("manual setup"), sets no cookies, and is reported per page that renders
its script. It needs an account in the founder's name; this script only edits
the pages once the founder has the site token from that account.

    python scripts/set_cloudflare_analytics.py --token <32-hex site token>            # dry run
    python scripts/set_cloudflare_analytics.py --token <token> --apply                # edit pages
    python scripts/set_cloudflare_analytics.py --remove --apply                       # rollback

Copy the token (not the whole snippet) from the dashboard's manual setup. The
snippet markup has changed between Cloudflare doc versions; if the dashboard
shows a different tag shape, compare it with SNIPPET below before applying.
Idempotent: an existing Cloudflare beacon is replaced, never duplicated. Each
file keeps its bytes and line endings except for that one line. Nothing is
measured until the change is pushed, and nothing here proves receipt: the
first visit seen in the Cloudflare dashboard does.

The page's own gf-pageview.js beacon is left alone; it still needs a receiver
of its own (scripts/set_pageview_endpoint.py).
"""
import argparse
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "customer_site")
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
SNIPPET = ("<script defer src=\"https://static.cloudflareinsights.com/beacon.min.js\" "
           "data-cf-beacon='{\"token\": \"%s\"}'></script>")
EXISTING = re.compile(rb"[ \t]*<script[^>]*static\.cloudflareinsights\.com/beacon\.min\.js[^>]*></script>\r?\n?")


def pages(site=SITE):
    return sorted(glob.glob(os.path.join(site, "**", "*.html"), recursive=True))


def edit(raw, token=None):
    """raw with any Cloudflare beacon removed and, when token is given, one
    inserted before </head>. None when a token is given and there is no </head>."""
    out = EXISTING.sub(b"", raw)
    if token is None:
        return out
    i = out.find(b"</head>")
    if i < 0:
        return None
    nl = b"\r\n" if b"\r\n" in out else b"\n"
    return out[:i] + (SNIPPET % token).encode("ascii") + nl + out[i:]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--token", help="Cloudflare Web Analytics site token (32 hex characters)")
    g.add_argument("--remove", action="store_true", help="take the beacon out of every page")
    ap.add_argument("--apply", action="store_true", help="write the change (default: dry run)")
    ap.add_argument("--site", default=SITE)
    args = ap.parse_args(argv)
    token = None
    if args.token is not None:
        token = args.token.strip().lower()
        if not TOKEN_RE.match(token):
            print("refused: the token must be 32 hexadecimal characters (the site token, not an API token)")
            return 2
    changed = skipped = 0
    for p in pages(args.site):
        with open(p, "rb") as fh:
            raw = fh.read()
        new = edit(raw, token)
        if new is None:
            skipped += 1
            print("SKIP (no </head>): " + os.path.relpath(p, args.site))
            continue
        if new == raw:
            continue
        changed += 1
        if args.apply:
            with open(p, "wb") as fh:
                fh.write(new)
    verb = "changed" if args.apply else "would change"
    print("%s %d page(s), skipped %d%s" % (verb, changed, skipped, "" if args.apply else " (dry run; --apply to write)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
