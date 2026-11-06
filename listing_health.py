#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Storefront health guard: what a buyer can see wrong on a live listing (2026-11-06). Read-only.

One Gumroad list call already returns name, description, tags, price, cover and published state for every product, so
this needs no extra request. It exists because a manual scan found, on 2026-11-06, nine live descriptions with corrupted
characters and two live listings with the same title that no automatic check had noticed.

Findings (severity): PAYABLE_ZERO (CRITICAL: a published listing at price 0 takes any amount), PLACEHOLDER_TEXT (HIGH),
TEST_OR_WITHDRAWN_NAME (HIGH), MOJIBAKE (HIGH), DUPLICATE_TITLE (MEDIUM), SHORT_DESCRIPTION (MEDIUM), NO_COVER (MEDIUM),
FEW_TAGS (LOW). Deliberately NOT checked: "has a file". The list endpoint shows `file_info` empty for multi-file
products (two healthy listings read as file-less), so file presence is left to the weekly delivery audit, which reads each product.

    python listing_health.py --once      # loop step: one list call a day, writes data/listing_health.json
    python listing_health.py --now       # same, ignoring the once-a-day gate
"""
from __future__ import annotations

import collections
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "listing_health.json"
STATE = ROOT / "data" / "listing_health_state.json"
SEVERITY = {"PAYABLE_ZERO": "CRITICAL", "PLACEHOLDER_TEXT": "HIGH", "TEST_OR_WITHDRAWN_NAME": "HIGH", "MOJIBAKE": "HIGH",
            "DUPLICATE_TITLE": "MEDIUM", "SHORT_DESCRIPTION": "MEDIUM", "NO_COVER": "MEDIUM", "FEW_TAGS": "LOW"}
_TAIL = "\u0080-ÿŒœŠšŸŽžƒˆ˜–-›€™"
MOJIBAKE = re.compile("[ÂÃâð][" + _TAIL + "]{1,3}")
TEST_NAME = re.compile(r"do not buy|delete me|\[unavailable\]|^\s*test\b|\bplaceholder\b|\bAPI TEST\b", re.I)
PLACEHOLDER = re.compile(r"\[FOUNDER[^\]]*\]|\bTODO\b|lorem ipsum|\bXXX+\b|\[INSERT[^\]]*\]", re.I)
MIN_DESCRIPTION = 200


def _slug(p):
    return (p.get("short_url") or "").rstrip("/").rsplit("/", 1)[-1]


def assess(products):
    """products: the raw list returned by Gumroad's GET /v2/products. -> list of findings (published listings only,
    except duplicates which also need both published)."""
    live = [p for p in products if p.get("published") and not p.get("deleted")]
    out = []

    def add(p, kind, detail):
        out.append({"slug": _slug(p), "name": (p.get("name") or "")[:70], "kind": kind, "severity": SEVERITY[kind], "detail": detail})

    titles = collections.Counter((p.get("name") or "").strip().lower() for p in live)
    for p in live:
        name, desc = p.get("name") or "", p.get("description") or ""
        if int(p.get("price") or 0) == 0:
            add(p, "PAYABLE_ZERO", "published at price 0: a buyer can pay any amount")
        if TEST_NAME.search(name):
            add(p, "TEST_OR_WITHDRAWN_NAME", "the title marks it as a test or withdrawn listing")
        m = PLACEHOLDER.search(desc)
        if m:
            add(p, "PLACEHOLDER_TEXT", f"description contains {m.group()!r}")
        n_bad = len(MOJIBAKE.findall(name + " " + desc))
        if n_bad:
            add(p, "MOJIBAKE", f"{n_bad} corrupted character sequence(s) in the public text")
        if titles[name.strip().lower()] > 1:
            add(p, "DUPLICATE_TITLE", "another live listing has the same title")
        if len(desc) < MIN_DESCRIPTION:
            add(p, "SHORT_DESCRIPTION", f"{len(desc)} characters")
        if not p.get("preview_url"):
            add(p, "NO_COVER", "no cover image")
        if len(p.get("tags") or []) < 3:
            add(p, "FEW_TAGS", f"{len(p.get('tags') or [])} tag(s)")
    return out


def summarize(findings, total_live):
    by = collections.Counter(f["severity"] for f in findings)
    return {"live_listings": total_live, "findings": len(findings), "by_severity": dict(by),
            "needs_action": by.get("CRITICAL", 0) + by.get("HIGH", 0)}


def run_once(today=None, now=None, products=None, out=OUT, state=STATE, force=False):
    today = today or datetime.now(timezone.utc).date().isoformat()
    try:
        last = json.loads(Path(state).read_text(encoding="utf-8")).get("last_day")
    except (OSError, ValueError):
        last = None
    if last == today and not force:
        return {"action": "none", "detail": f"listing health already checked for {today}"}
    if products is None:
        sys.path.insert(0, str(ROOT))
        from channels import gumroad_publisher as gp
        products = gp.list_products(gp.load_token())  # read-only GET /v2/products
    findings = assess(products)
    live = sum(1 for p in products if p.get("published") and not p.get("deleted"))
    s = summarize(findings, live)
    doc = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "summary": s, "findings": findings}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(out) + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, out)
    tmp = Path(str(state) + ".tmp")
    tmp.write_text(json.dumps({"last_day": today}), encoding="utf-8")
    os.replace(tmp, state)
    return {"action": "findings" if s["needs_action"] else "ok",
            "detail": f"{live} live listings, {s['findings']} finding(s), {s['needs_action']} critical/high"}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        r = run_once(force="--now" in argv)
    except Exception as e:  # noqa: BLE001  reported to the loop, never thrown
        r = {"action": "failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
    sys.stdout.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
