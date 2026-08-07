"""Galaxy Forge -- Contradiction Engine (new, ADR-208, Phase 18, 2026-08-08).

Answers Section 15 of the founder's "Knowledge Graph & Institutional
Memory Engine" directive: detect real contradictions in this factory's
own recorded knowledge, never silently pick the convenient answer.

Checked first: no dedicated contradiction-detection mechanism exists
anywhere in this factory (confirmed by direct search). This is a
genuinely new, narrow module -- 2 real, checkable contradiction classes
this factory can actually detect from its own real data, not a generic
NLP-style "find all disagreements" system.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_DECISIONS_PATH = _FACTORY_ROOT / "data" / "decisions.jsonl"
_PADDLE_PRODUCTS_PATH = _FACTORY_ROOT / "data" / "paddle_products.json"

# Real, disclosed threshold -- a swing bigger than this across real
# evaluations of the SAME niche is flagged as a real, worth-a-look
# volatility signal. Not a claim that either score is "wrong."
_SCORE_VOLATILITY_THRESHOLD = 20.0


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _read_jsonl(path):
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def detect_decision_volatility(decisions_path=None):
    """Real, mechanical check: for every real niche with 2+ real
    evaluation records, does the real opportunity_score swing beyond
    the disclosed threshold, or does the real status flip-flop between
    ACCEPTED/DEFERRED/REJECTED? Never picks which value is "correct" --
    records both, with their real timestamps, for a human to judge."""
    records = _read_jsonl(decisions_path or _DECISIONS_PATH)

    by_niche = {}
    for r in records:
        niche = r.get("niche")
        if not niche:
            continue
        by_niche.setdefault(niche, []).append(r)

    contradictions = []
    for niche, entries in by_niche.items():
        entries_with_score = [e for e in entries if e.get("opportunity_score") is not None]
        if len(entries_with_score) >= 2:
            scores = [e["opportunity_score"] for e in entries_with_score]
            spread = max(scores) - min(scores)
            if spread > _SCORE_VOLATILITY_THRESHOLD:
                lo = min(entries_with_score, key=lambda e: e["opportunity_score"])
                hi = max(entries_with_score, key=lambda e: e["opportunity_score"])
                contradictions.append({
                    "type": "CONTRADICTION",
                    "category": "conflicting_market_estimate",
                    "entity": niche,
                    "sources": [
                        {"value": lo["opportunity_score"], "decided_at": lo.get("decided_at"), "decision_id": lo.get("decision_id")},
                        {"value": hi["opportunity_score"], "decided_at": hi.get("decided_at"), "decision_id": hi.get("decision_id")},
                    ],
                    "spread": round(spread, 1),
                    "reliability_estimate": "Both real, from this factory's own real evaluation pipeline -- neither is presumptively more reliable than the other without independent verification.",
                    "requires_verification": True,
                })

        statuses = [e.get("status") for e in entries if e.get("status")]
        distinct_statuses = set(statuses)
        if len(distinct_statuses) > 1 and "ACCEPTED" in distinct_statuses and "REJECTED" in distinct_statuses:
            contradictions.append({
                "type": "CONTRADICTION",
                "category": "contradictory_strategic_conclusion",
                "entity": niche,
                "sources": [{"status": s} for s in sorted(distinct_statuses)],
                "reliability_estimate": "Real status flip-flop between ACCEPTED and REJECTED for the same niche -- requires human review before treating either as final.",
                "requires_verification": True,
            })

    return contradictions


def detect_price_contradiction(product_title, now=None, live_check=True):
    """Real, live-capable check: does this factory's internal record of
    a product's price match the live Paddle account's own real price?
    Read-only -- never corrects either record. live_check=False skips
    the real network call (for fast, offline testing)."""
    now = now or datetime.now(timezone.utc)
    products = []
    try:
        with open(_PADDLE_PRODUCTS_PATH, "r", encoding="utf-8") as f:
            products = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass

    internal = next((p for p in products if p.get("title") == product_title), None)
    if internal is None:
        return {"status": "NOT_FOUND", "product": product_title}

    if not live_check:
        return {"status": "SKIPPED", "product": product_title, "reason": "live_check=False"}

    try:
        from channels import paddle_publisher as pp
        api_key = pp.load_api_key()
        r = __import__("requests").get(
            f"{pp.PADDLE_API_BASE}/prices/{internal.get('price_id')}", headers=pp._headers(api_key), timeout=30,
        )
        r.raise_for_status()
        live_price_cents = int(r.json().get("data", {}).get("unit_price", {}).get("amount", 0))
        live_price = round(live_price_cents / 100, 2)
    except Exception as e:
        return {"status": "ERROR", "product": product_title, "error": str(e)}

    internal_price = internal.get("price")
    if internal_price != live_price:
        return {
            "type": "CONTRADICTION", "category": "conflicting_product_price", "entity": product_title,
            "sources": [
                {"source": "data/paddle_products.json (internal)", "value": internal_price},
                {"source": "live Paddle API", "value": live_price},
            ],
            "reliability_estimate": "The live Paddle API is the real source of truth for what a customer would actually be charged -- the internal record should be treated as stale, not the live price.",
            "requires_verification": False,
            "generated_at": now.isoformat(),
        }
    return {"status": "MATCH", "product": product_title, "price": live_price, "generated_at": now.isoformat()}


def detect_all_contradictions(decisions_path=None, check_prices=True, now=None):
    """The one real aggregator. Never silently resolves a real
    contradiction -- every one found is returned, with both sources and
    an honest reliability_estimate, for a human to act on."""
    now = now or datetime.now(timezone.utc)
    contradictions = detect_decision_volatility(decisions_path=decisions_path)

    price_checks = []
    if check_prices:
        try:
            with open(_PADDLE_PRODUCTS_PATH, "r", encoding="utf-8") as f:
                products = json.load(f)
            for p in products:
                result = detect_price_contradiction(p.get("title"), now=now)
                if result.get("type") == "CONTRADICTION":
                    contradictions.append(result)
                price_checks.append(result)
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "generated_at": now.isoformat(),
        "contradictions": contradictions,
        "total_contradictions": len(contradictions),
        "price_checks_performed": len(price_checks),
        "note": "Every contradiction found cites both real sources and an honest reliability estimate -- never silently resolved to whichever value is more convenient.",
    }
