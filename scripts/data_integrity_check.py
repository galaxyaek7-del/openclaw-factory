#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data integrity check for the flat-file store (2026-11-06). Read-only.

    python scripts/data_integrity_check.py          # human summary, exit 1 on NEW corruption
    python scripts/data_integrity_check.py --json

The factory has no database: data/*.json, data/*.jsonl, config/*.json are the store. This parses all of them (BOM and UTF-16 tolerated)
and compares unparseable files with config/data_integrity_known.json, the list of historical files found broken on 2026-11-06 that no
live code reads (STABILITY_REPORT L1). A file outside that list that stops parsing is NEW corruption: exit 1. Nothing is deleted or moved.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWN = ROOT / "config" / "data_integrity_known.json"


def parse_json_bytes(b):
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return json.loads(b.decode(enc))
        except (UnicodeError, ValueError):
            continue
    raise ValueError("unparseable")


def scan(root=ROOT):
    bad_json, bad_jsonl = [], {}
    patterns = [("data", "*.json"), ("config", "*.json")]
    for d, pat in patterns:
        for f in sorted((root / d).glob(pat)):
            try:
                parse_json_bytes(f.read_bytes())
            except (ValueError, OSError):
                bad_json.append(f.relative_to(root).as_posix())
    for f in sorted((root / "data").glob("*.jsonl")):
        n = 0
        try:
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line:
                    try:
                        json.loads(line)
                    except ValueError:
                        n += 1
        except OSError:
            continue
        if n:
            bad_jsonl[f.relative_to(root).as_posix()] = n
    return bad_json, bad_jsonl


def compare(bad_json, bad_jsonl, known):
    kj, kl = set(known.get("json", [])), known.get("jsonl", {})
    new_json = [f for f in bad_json if f not in kj]
    # a known JSONL may keep its old bad lines but must not gain more
    new_jsonl = {f: n for f, n in bad_jsonl.items() if f not in kl or n > kl[f]}
    return new_json, new_jsonl


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    bj, bl = scan()
    try:
        known = json.loads(KNOWN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        known = {"json": [], "jsonl": {}}
    nj, nl = compare(bj, bl, known)
    res = {"unparseable_json": len(bj), "jsonl_with_bad_lines": len(bl), "known_baseline": bool(known.get("json") or known.get("jsonl")),
           "new_corrupt_json": nj, "new_or_grown_jsonl": nl}
    if "--json" in argv:
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    else:
        sys.stdout.write(f"integrity: {len(bj)} unparseable json, {len(bl)} jsonl with bad lines; NEW: {nj or 'none'} {nl or ''}\n")
    return 1 if (nj or nl) else 0


if __name__ == "__main__":
    sys.exit(main())
