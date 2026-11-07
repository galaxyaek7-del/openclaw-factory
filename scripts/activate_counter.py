#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Turn on the GoatCounter visit counter once the founder has created the (free) GoatCounter site (2026-11-07).

    python scripts/activate_counter.py <code> [--dry-run]     # <code> = the part before .goatcounter.com

Only writes the public site code into customer_site/assets/gf-pageview.js (the constant GF_COUNTER_CODE). It never creates an account and
handles no password: the code is a public subdomain name that ends up in the page source anyway. Idempotent; refuses anything that is not
a plain lowercase name. After it, publish through the normal site path (scripts/auto_publish_site.py runs every loop tick).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "customer_site" / "assets" / "gf-pageview.js"
CODE_RE = re.compile(r"^[a-z0-9-]{2,40}$")
LINE_RE = re.compile(r"(var GF_COUNTER_CODE = ')([^']*)(';)")


def apply(code, path=TARGET, dry_run=False):
    code = (code or "").strip().lower()
    if code.endswith(".goatcounter.com"):
        code = code[: -len(".goatcounter.com")]
    if not CODE_RE.match(code):
        return {"ok": False, "detail": "the code must be 2-40 characters of a-z, 0-9 and '-' (just the name before .goatcounter.com)"}
    raw = Path(path).read_bytes().decode("utf-8")
    m = LINE_RE.search(raw)
    if not m:
        return {"ok": False, "detail": "GF_COUNTER_CODE line not found in gf-pageview.js"}
    if m.group(2) == code:
        return {"ok": True, "changed": False, "detail": f"already set to {code}"}
    new = raw[: m.start(2)] + code + raw[m.end(2):]
    if not dry_run:
        Path(path).write_bytes(new.encode("utf-8"))  # same line endings: only the quoted value changes
    return {"ok": True, "changed": True, "detail": f"GF_COUNTER_CODE '{m.group(2)}' -> '{code}'" + (" (dry run)" if dry_run else ""),
            "endpoint": f"https://{code}.goatcounter.com/count"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if not a.startswith("--")]
    r = apply(args[0] if args else "", dry_run="--dry-run" in argv)
    sys.stdout.buffer.write((str(r) + "\n").encode("utf-8"))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
