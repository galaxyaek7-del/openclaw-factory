#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-page founder digest of the agent packages waiting for review (2026-11-07). Read-only.

    python scripts/package_review_digest.py            # writes drafts/PACKAGES_REVIEW.md (drafts/ is git-ignored) and prints a summary

For each package in drafts/agent_packages with status AWAITING_FOUNDER_REVIEW: title, audience, the final price (the pricing agent decides,
a disagreement with the brief is shown), whether it overlaps a live product, a deterministic buyer-relevance label, and the QA verdict.
It recommends nothing and approves nothing: publication still needs the founder to name the product.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
PKG_DIR = ROOT / "drafts" / "agent_packages"
OUT = ROOT / "drafts" / "PACKAGES_REVIEW.md"


def load_packages(pkg_dir=PKG_DIR):
    out = []
    for f in sorted(Path(pkg_dir).glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(p, dict) and p.get("status") == "AWAITING_FOUNDER_REVIEW" and p.get("brief"):
            p["_file"] = f.name
            out.append(p)
    return out


def describe(p, live_titles, quality, duplicate_of):
    b, pr, ql = p.get("brief") or {}, p.get("pricing") or {}, p.get("listing") or {}
    title = ql.get("title") or b.get("title") or ""
    dup = duplicate_of(title, live_titles)
    brief_price, final = b.get("price"), pr.get("price_usd")
    return {
        "file": p.get("_file"), "title": title, "audience": (b.get("audience") or "")[:110],
        "final_price": final, "price_note": "" if brief_price == final or final is None else f"brief said {brief_price}",
        "overlap": f"{dup[0]} ({round(dup[1] * 100)}%)" if dup else "",
        "fit": quality({"niche": title, "topic": b.get("topic") or ""}),
        "qa": (p.get("qa") or {}).get("verdict"), "created": str(p.get("created_at", ""))[:10],
    }


def render(rows):
    L = ["# Packages waiting for founder review", "",
         "Read-only digest. Fit = deterministic buyer-relevance label (strong = a money or operations decision is in the topic), not demand.",
         "Nothing here is approved or published. Approve by naming the product.", "",
         "| # | Title | Audience | Price | Overlap with a live product | Fit | QA | Date |", "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        price = f"${r['final_price']}" + (f" ({r['price_note']})" if r["price_note"] else "")
        L.append(f"| {i} | {r['title']} | {r['audience']} | {price} | {r['overlap'] or '-'} | {r['fit']} | {r['qa']} | {r['created']} |")
    return "\n".join(L) + "\n"


def main():
    from golden_hunter import digital_discovery as dd
    live = dd.live_titles()
    rows = [describe(p, live, dd.quality, dd.duplicate_of) for p in load_packages()]
    rows.sort(key=lambda r: (r["overlap"] != "", r["fit"] != "strong", r["title"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rows), encoding="utf-8")
    n_ok = sum(1 for r in rows if not r["overlap"] and r["fit"] == "strong")
    sys.stdout.buffer.write(f"{len(rows)} packages; {n_ok} strong and not overlapping a live product; written to {OUT.relative_to(ROOT)}\n".encode("utf-8"))


if __name__ == "__main__":
    main()
