"""List (and with --apply, fix) customer_site pages that load no page-view beacon.

Dry run by default: an earlier version wrote on every invocation, including
`--help`, treated pages that load assets/gf-pageview.js as missing a beacon
(the file name has no "page-view" in it), inserted the old inline beacon that
swallows failures, and rewrote line endings. 2026-10-29: it now recognises
gf-pageview.js, inserts that script (the observable beacon), keeps each file's
bytes and line endings except for the one inserted line, and writes only with
--apply.

    python scripts/fix_missing_beacons.py            # list pages without a beacon
    python scripts/fix_missing_beacons.py --apply    # add <script src="assets/gf-pageview.js" defer>

Nothing is measured until the pages point at a receiver that exists
(scripts/set_pageview_endpoint.py) and the change is pushed.
"""
import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = b'<script src="assets/gf-pageview.js" defer></script>'


def has_beacon(raw):
    # Only gf-pageview.js counts (2026-11-07): the old inline /api/page-view beacon posts to a server GitHub Pages does not have, so a
    # page that carries only that one is invisible to the hosted counter.
    return b"gf-pageview.js" in raw


def missing(site):
    out = []
    for p in sorted(glob.glob(os.path.join(site, "*.html"))):
        with open(p, "rb") as fh:
            raw = fh.read()
        if b'noindex' in raw and b'name="robots"' in raw:
            continue  # not part of the public funnel: never counted on purpose (2026-11-07)
        if not has_beacon(raw):
            out.append((p, raw))
    return out


def insert(raw):
    """raw with the tag before the first </head>, or None when there is none."""
    i = raw.find(b"</head>")
    if i < 0:
        return None
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    return raw[:i] + TAG + nl + raw[i:]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the change (default: list only)")
    ap.add_argument("--site", default=os.path.join(ROOT, "customer_site"))
    args = ap.parse_args(argv)
    pages = missing(args.site)
    for p, raw in pages:
        new = insert(raw)
        name = os.path.basename(p)
        if new is None:
            print("SKIP (no </head>): " + name)
            continue
        if args.apply:
            with open(p, "wb") as fh:
                fh.write(new)
        print(("added: " if args.apply else "would add: ") + name)
    print("%d page(s) without a beacon%s" % (len(pages), "" if args.apply else " (dry run; --apply to write)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
