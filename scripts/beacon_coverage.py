#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Which public pages load the visit-counter file, and which load it twice? (2026-11-07). Local, read-only.

    python scripts/beacon_coverage.py [--json]

A page that does not load assets/gf-pageview.js can never be counted (a blind spot); a page that loads it twice would double-count every
visit (duplicate pageviews). noindex pages are reported separately: they are not part of the public funnel. Exit 1 when an indexable
page is missing the file or loads it more than once.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOINDEX = re.compile(r'name="robots"[^>]*noindex', re.I)


def scan(root=ROOT):
    out = {"pages": 0, "once": 0, "missing": [], "duplicate": [], "noindex_missing": []}
    for f in sorted((root / "customer_site").rglob("*.html")):
        t = f.read_text(encoding="utf-8", errors="ignore")
        rel = f.relative_to(root).as_posix()
        out["pages"] += 1
        n = len(re.findall(r"gf-pageview\.js", t))
        if n == 1:
            out["once"] += 1
        elif n > 1:
            out["duplicate"].append(rel)
        elif NOINDEX.search(t):
            out["noindex_missing"].append(rel)
        else:
            out["missing"].append(rel)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    r = scan()
    if "--json" in argv:
        sys.stdout.write(json.dumps(r, ensure_ascii=False, indent=1) + "\n")
    else:
        sys.stdout.buffer.write((f"BEACON COVERAGE: {r['pages']} pages, {r['once']} load the counter once, {len(r['duplicate'])} twice, "
                                 f"{len(r['missing'])} indexable pages without it, {len(r['noindex_missing'])} noindex pages without it\n"
                                 + "".join(f"  MISSING {p}\n" for p in r["missing"][:15])
                                 + "".join(f"  DUPLICATE {p}\n" for p in r["duplicate"][:15])).encode("utf-8"))
    return 1 if r["missing"] or r["duplicate"] else 0


if __name__ == "__main__":
    sys.exit(main())
