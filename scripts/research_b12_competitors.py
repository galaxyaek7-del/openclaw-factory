"""Record real B12-001 competitors (founder directive 2026-10-17, Mission 6).

B12-001 ("Freelancer Rate & Raise Calculator", $29) is blocked by the Quality
Enforcer's Layer 3: no sourced competitor price and no recorded proof of
payment. This tool records competitors the FOUNDER found and checked by hand.
It fetches nothing and invents nothing.

How to use
  1. Search Gumroad Discover (and the wider web) for similar products, e.g.
     "freelance rate calculator", "hourly rate calculator spreadsheet".
  2. Add each real product below with record_competitor(name, url, price).
  3. Run:  python scripts/research_b12_competitors.py

What it does with them
  * keeps only entries with an http(s) URL and a positive price;
  * writes data/evidence/b12_competitors.json (evidence_type REAL,
    verified_by Founder);
  * prints the DynamicPricer recommendation (recommendation only) and the
    Quality Enforcer's new verdict for B12-001.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "evidence" / "b12_competitors.json"
MIN_COMPETITORS = 3


def record_competitor(name: str, url: str, price: float, notes: str = "") -> dict:
    return {"name": name, "url": url, "price": price, "notes": notes,
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "evidence_type": "REAL", "verified_by": "Founder"}


# Founder fills these after a research session. Leave empty until checked.
COMPETITORS = [
    # record_competitor(name="Example Product", url="https://example.gumroad.com/l/xxx", price=39),
]


def validate(entries):
    ok, rejected = [], []
    for c in entries:
        url, price = c.get("url"), c.get("price")
        if not (isinstance(url, str) and url.startswith(("http://", "https://"))):
            rejected.append({**c, "rejected": "no http(s) URL"})
        elif not (isinstance(price, (int, float)) and not isinstance(price, bool) and price > 0):
            rejected.append({**c, "rejected": "price must be a positive number"})
        else:
            ok.append(c)
    return ok, rejected


def run(entries, out=OUT, inspect=True):
    ok, rejected = validate(entries)
    if not ok:
        return {"saved": False, "valid": 0, "rejected": rejected,
                "action": ["Search gumroad.com/discover for similar products",
                           "Add at least 3 with record_competitor(name, url, price)",
                           "Run this script again"]}
    report = {"product": "B12-001",
              "research_date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "competitors": ok, "rejected": rejected,
              "ready_for_pricing": len(ok) >= MIN_COMPETITORS}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    result = {"saved": True, "path": str(out), "valid": len(ok), "rejected": rejected,
              "ready_for_pricing": report["ready_for_pricing"]}
    if inspect:
        sys.path.insert(0, str(ROOT))
        from src.pricing.dynamic_pricer import DynamicPricer
        result["price_recommendation"] = DynamicPricer().calculate_optimal_price(
            [c["price"] for c in ok], [c["url"] for c in ok], product_cost=0)
        sys.path.insert(0, str(ROOT / "src" / "quality"))
        import quality_enforcer as Q
        prod = json.loads((ROOT / "data" / "product_batch_12.json").read_text(encoding="utf-8"))["products"][0]
        comps = [{"name": c["name"], "url": c["url"], "price_usd": c["price"]} for c in ok]
        r = Q.inspect(dict(prod, competitors=comps, niche="freelancer rate calculator"),
                      stage="pre_production", report_dir=ROOT / "reports" / "B12-001" / "inspections")
        result["quality_verdict"] = r["verdict"]
        result["quality_reasons"] = r["reasons"]
    return result


if __name__ == "__main__":
    res = run(COMPETITORS)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res["saved"] else 1)
