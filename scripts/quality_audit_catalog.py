"""Master Sprint A5 (2026-10-17): run the 3-layer Quality Enforcer over every
published Gumroad listing.

Sources, all read-only:
  * Gumroad list_products GET: name, price (cents), description, published.
  * data/cycle88_catalog_reconciliation.json: listing id -> local product file
    (a name-overlap match made in Cycle 88; its `match_overlap` is reported).
  * data/catalog.json: audience (`target_buyer`) and `problem`, which exist for
    only some listings. Nothing is inferred for the rest: those listings come
    out BLOCKED_MISSING_DATA on Layer 1, which is the true state.
  * market_evidence.get_payment_evidence(niche) via the enforcer (Layer 3).

Writes reports/quality/full_audit_76.json and the per-product inspection
reports. Changes nothing on Gumroad.

    python scripts/quality_audit_catalog.py               # live read
    python scripts/quality_audit_catalog.py --from-file products.json
"""
import argparse
import html
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "quality"))
import quality_enforcer as Q  # noqa: E402

OUT = ROOT / "reports" / "quality" / "full_audit_76.json"
INSPECTIONS = ROOT / "reports" / "quality" / "inspections" / "catalog_audit"


def _text(desc):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", desc or ""))).strip()


def build_product(listing, c88, cat):
    rec = c88.get(listing.get("id")) or {}
    meta = cat.get(listing.get("id")) or {}
    local = rec.get("local_file")
    files = []
    if local:
        p = ROOT / local.replace("\\", "/")
        if p.exists():
            files.append(str(p))
    price = listing.get("price")
    return {
        "id": listing.get("id"), "title": listing.get("name"),
        "price": price / 100 if isinstance(price, (int, float)) else None,
        "audience": meta.get("target_buyer"), "problem": meta.get("problem"),
        "outcome": _text(listing.get("description"))[:2000],
        "competitors": meta.get("competitors") or [],
        "files": files,
        "_local_file_recorded": local, "_match_overlap": rec.get("match_overlap"),
    }


def run(listings, c88, cat, inspection_dir=INSPECTIONS):
    rows = []
    for l in listings:
        if l.get("deleted") or not l.get("published"):
            continue
        prod = build_product(l, c88, cat)
        r = Q.inspect(prod, stage="full", report_dir=inspection_dir)
        lay = r["layers"]
        rows.append({
            "product_id": prod["id"], "title": prod["title"], "price_usd": prod["price"],
            "verdict": r["verdict"], "reasons": r["reasons"],
            "core_value": lay["core_value"]["score"], "content_quality": lay["content_quality"]["score"],
            "market_reality": lay["market_reality"]["score"],
            "content_checks": lay["content_quality"].get("checks"),
            "depth": (lay["content_quality"].get("detail") or {}).get("depth"),
            "local_file": prod["_local_file_recorded"], "local_file_present": bool(prod["files"]),
            "match_overlap": prod["_match_overlap"],
            # Cycle 88 matched listings to local files by shared title words.
            # Two shared words is weak (seen: "SOC 2 Guide" -> an accounting
            # PDF), so findings on those rows describe the local file only.
            "match_confidence": ("NONE" if not prod["files"] else
                                 "LOW" if (prod["_match_overlap"] or 0) <= 2 else "MEDIUM"),
            "report_path": str(Path(r["report_path"]).relative_to(ROOT)),
        })
    by_verdict = Counter(r["verdict"] for r in rows)
    content_scored = [r for r in rows if r["content_quality"] is not None]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Gumroad list_products (read-only GET) + cycle88 file map + catalog.json facts",
        "audited": len(rows), "by_verdict": dict(by_verdict),
        "layer_coverage": {
            "core_value_scored": sum(r["core_value"] is not None for r in rows),
            "content_quality_scored": len(content_scored),
            "market_reality_scored": sum(r["market_reality"] is not None for r in rows),
        },
        "content_quality": {
            "passed": sum(r["content_quality"] >= Q.THRESHOLDS["content_quality"] for r in content_scored),
            "failed": sum(r["content_quality"] < Q.THRESHOLDS["content_quality"] for r in content_scored),
            "no_local_file": sum(not r["local_file_present"] for r in rows),
            "depth_insufficient": sum(1 for r in content_scored if r["content_checks"] and not r["content_checks"]["depth_sufficient"]),
            "depth_insufficient_medium_confidence_match": sum(
                1 for r in content_scored if r["match_confidence"] == "MEDIUM"
                and r["content_checks"] and not r["content_checks"]["depth_sufficient"]),
            "files_failing_existing_file_tester": [r["title"] for r in content_scored
                                                   if r["content_checks"] and not r["content_checks"]["files_open_cleanly"]],
        },
        "limits": [
            "Layer 2 judges the LOCAL file Cycle 88 matched to each listing. The Gumroad API exposes no "
            "download of the delivered file, so a bundle listing may deliver more than the matched file.",
            "Depth rule: words >= price x 100 for text formats (founder directive). Spreadsheets: >= 2 sheets and >= 5 formulas.",
        ],
        "note": ("APPROVED requires every layer. Layer 3 needs sourced competitor prices or recorded "
                 "proof of payment; none exist for these listings, so no listing can be APPROVED today. "
                 "That is a data gap, reported as BLOCKED_MISSING_DATA, not a judgement of the product."),
        "rows": sorted(rows, key=lambda r: (r["content_quality"] is None, r["content_quality"] or 0, r["title"] or "")),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file")
    a = ap.parse_args(argv)
    if a.from_file:
        listings = json.loads(Path(a.from_file).read_text(encoding="utf-8"))
    else:
        from channels import gumroad_publisher as gp
        listings = gp.list_products(gp.load_token())
    c88 = {p["id"]: p for p in json.loads((ROOT / "data/cycle88_catalog_reconciliation.json").read_text(encoding="utf-8"))["products"]}
    cat = {p["id"]: p for p in json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8"))["products"]}
    report = run(listings, c88, cat)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
