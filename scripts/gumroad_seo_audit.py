"""Gumroad listing SEO audit (founder directive 2026-10-16, Mission 5).

Scores every Gumroad listing on what helps it get found and chosen: title
length, description depth, tags, price sanity, cover image, category.

Built on the fields the Gumroad API actually returns (observed 2026-10-17 via
the existing read-only list_products GET): `price` is in CENTS (7900 = $79),
tags are `tags`, covers are `covers` / `thumbnail_url` / `preview_url`,
category is `taxonomy_id`. A field the API did not return is reported as
"unknown" and never penalised as if it were empty.

Read-only. One GET (list_products). Writes only its own report.

    python scripts/gumroad_seo_audit.py            # live read, writes data/seo/gumroad_seo_audit.json
    python scripts/gumroad_seo_audit.py --from-file products.json
"""
import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "data", "seo", "gumroad_seo_audit.json")


def _text(description):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", description or ""))).strip()


def audit_product_seo(p: dict) -> dict:
    issues, score = [], 100
    title = p.get("name") or ""
    if len(title) < 20:
        issues.append("Title too short (<20 chars)")
        score -= 15
    if len(title) > 60:
        issues.append("Title too long (>60 chars)")
        score -= 5

    desc = _text(p.get("description"))
    if len(desc) < 200:
        issues.append("Description too short (<200 chars of text)")
        score -= 20
    elif len(desc) < 500:
        issues.append("Description could be longer (<500 chars of text)")
        score -= 10

    if "tags" in p:
        tags = p.get("tags") or []
        if len(tags) < 5:
            issues.append(f"Only {len(tags)} tags (need 5+)")
            score -= 15
    else:
        tags = None

    price_usd = (p["price"] / 100) if isinstance(p.get("price"), (int, float)) else None
    if price_usd == 0:
        issues.append("Free product - no revenue")
    elif price_usd is not None and price_usd < 5:
        issues.append("Price very low (<$5)")
        score -= 5

    has_cover = bool(p.get("covers") or p.get("thumbnail_url") or p.get("preview_url") or p.get("main_cover_id"))
    if not has_cover:
        issues.append("No cover image")
        score -= 20

    if "taxonomy_id" in p and not p.get("taxonomy_id"):
        issues.append("No category (taxonomy) set - matters for Gumroad Discover")
        score -= 5

    score = max(0, score)
    return {
        "product_id": p.get("id"), "name": title, "url": p.get("short_url"),
        "published": p.get("published"), "price_usd": price_usd,
        "tags": tags, "description_chars": len(desc), "has_cover": has_cover,
        "seo_score": score, "issues": issues,
        "priority": "HIGH" if score < 60 else "MEDIUM" if score < 80 else "LOW",
    }


def run(products):
    rows = sorted((audit_product_seo(p) for p in products if not p.get("deleted")),
                  key=lambda r: (r["seo_score"], r["name"]))
    pub = [r for r in rows if r["published"]]
    issue_counts = {}
    for r in pub:
        for i in r["issues"]:
            key = re.sub(r"\d+", "N", i)
            issue_counts[key] = issue_counts.get(key, 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Gumroad API list_products (read-only GET)",
        "products": len(rows), "published": len(pub),
        "by_priority": {k: sum(1 for r in pub if r["priority"] == k) for k in ("HIGH", "MEDIUM", "LOW")},
        "average_score_published": round(sum(r["seo_score"] for r in pub) / len(pub), 1) if pub else None,
        "issue_counts_published": dict(sorted(issue_counts.items(), key=lambda kv: -kv[1])),
        "rows": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gumroad listing SEO audit (read-only)")
    ap.add_argument("--from-file")
    a = ap.parse_args(argv)
    if a.from_file:
        with open(a.from_file, encoding="utf-8") as fh:
            products = json.load(fh)
    else:
        sys.path.insert(0, ROOT)
        from channels import gumroad_publisher as gp
        products = gp.list_products(gp.load_token())
    report = run(products)
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
