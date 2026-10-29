"""Trend-to-Product: traceability, observed outcomes and dashboard state (2026-10-29).

Chain: signal (SIG-) -> opportunity (OPP-) -> specification (SPEC-) -> product
(registry internal_id) -> QA (manifest qa) -> approval (publication_approvals)
-> listing (registry url/published) -> outcome (registry sales).

Product, QA, approval, listing and sales are READ from the factory's existing
authoritative records; this module never keeps a second copy of them. A spec can
be linked only to a product that exists in data/product_registry.json.

Outcomes are labelled OBSERVED and kept apart from forecasts (price ranges,
scores). calibration_summary() compares bands with observed sales but never
changes weights by itself; with too few linked products it says so.
"""
import json
import os
from datetime import datetime, timezone

from . import ideation, records, scoring

STATE_PATH = os.path.join(records.ROOT, "data", "trend_to_product_state.json")
APPROVALS_PATH = os.path.join(records.ROOT, "data", "publication_approvals.json")
MIN_LINKED_FOR_CALIBRATION = 5
MIN_DAYS_LISTED = 30


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def link_spec_to_product(spec_id, internal_id, relation="BUILT_FROM_SPEC", note=None,
                         base_dir=None, registry=None):
    """Record that a registry product was built from (or already covers) a spec."""
    if relation not in ("BUILT_FROM_SPEC", "EXISTING_PRODUCT_COVERS"):
        raise records.RecordError(f"unknown relation {relation!r}")
    specs = ideation.latest_specs(base_dir)
    if spec_id not in specs:
        raise records.RecordError(f"unknown spec {spec_id}")
    products = {p.get("internal_id"): p for p in (registry if registry is not None
                                                   else ideation.load_registry())}
    if internal_id not in products:
        raise records.RecordError(f"{internal_id} is not in the product registry")
    rec = {"link_id": records._id("LNK", spec_id, internal_id, relation), "spec_id": spec_id,
           "opportunity_id": specs[spec_id]["opportunity_id"], "internal_id": internal_id,
           "relation": relation, "note": note, "recorded_at": records._now()}
    if rec["link_id"] not in records._index("links.jsonl", "link_id", base_dir):
        records._append("links.jsonl", rec, base_dir)
    return rec


def _qa_of(product, root):
    m = product.get("manifest")
    if not m:
        return {"status": "UNKNOWN", "reason": "no manifest path in registry"}
    doc = _read_json(os.path.join(root, m))
    if not doc or "qa" not in doc:
        return {"status": "UNKNOWN", "reason": f"no qa block in {m}"}
    qa = doc["qa"]
    parts = {k: v.get("status") for k, v in qa.items() if isinstance(v, dict) and "status" in v}
    return {"status": "PASS" if qa.get("ok") and all(s == "PASS" for s in parts.values()) else "NOT_PASS",
            "checks": parts, "manifest": m}


def _approval_of(internal_id, approvals_path):
    doc = _read_json(approvals_path) or {}
    rows = [a for a in doc.get("approvals", []) if a.get("product_id") == internal_id]
    if not rows:
        return {"status": "NONE", "reason": "no publication approval record"}
    a = rows[-1]
    return {"status": a.get("status"), "approval_id": a.get("approval_id"),
            "approved_at": a.get("approved_at")}


def trace(opportunity_id, base_dir=None, registry=None, root=None, approvals_path=None):
    root = root or records.ROOT
    ops = {o["opportunity_id"]: o for o in scoring.latest_opportunities(base_dir)}
    if opportunity_id not in ops:
        raise records.RecordError(f"unknown opportunity {opportunity_id}")
    op = ops[opportunity_id]
    specs = [s for s in ideation.latest_specs(base_dir).values() if s["opportunity_id"] == opportunity_id]
    links = [l for l in records.read_jsonl("links.jsonl", base_dir) if l["opportunity_id"] == opportunity_id]
    products = {p.get("internal_id"): p for p in (registry if registry is not None
                                                   else ideation.load_registry())}
    chain = []
    for l in links:
        p = products.get(l["internal_id"])
        if not p:
            chain.append({"link": l, "product": None, "problem": "linked product no longer in registry"})
            continue
        chain.append({
            "link": l,
            "product": {"internal_id": p["internal_id"], "title": p.get("title")},
            "qa": _qa_of(p, root),
            "approval": _approval_of(p["internal_id"], approvals_path or APPROVALS_PATH),
            "listing": {"published": p.get("published"), "url": p.get("url"),
                        "first_published_at": p.get("first_published_at")},
            "outcome": {"label": "OBSERVED", "source": "data/product_registry.json",
                        "sales_count": p.get("sales_count"), "sales_usd_cents": p.get("sales_usd_cents"),
                        "traffic": "UNKNOWN (no per-product traffic receiver, backlog B6)",
                        "refunds": "UNKNOWN (no refund record source)",
                        "net_revenue": "UNKNOWN (fees not recorded)"},
        })
    return {"opportunity": {k: op[k] for k in ("opportunity_id", "name", "format", "band",
                                                "composite", "coverage")},
            "forecast": {"price_range": op.get("price_range"), "label": "FORECAST/OBSERVED-COMPETITOR"},
            "signals": op["signal_ids"], "specs": [s["spec_id"] for s in specs], "chain": chain}


def calibration_summary(base_dir=None, registry=None, now=None):
    """Compare opportunity bands with observed sales of products linked as BUILT_FROM_SPEC."""
    now = now or datetime.now(timezone.utc)
    products = {p.get("internal_id"): p for p in (registry if registry is not None
                                                   else ideation.load_registry())}
    ops = {o["opportunity_id"]: o for o in scoring.latest_opportunities(base_dir)}
    rows = []
    for l in records.read_jsonl("links.jsonl", base_dir):
        if l["relation"] != "BUILT_FROM_SPEC":
            continue
        p = products.get(l["internal_id"])
        if not p or not p.get("first_published_at"):
            continue
        try:
            days = (now - datetime.fromisoformat(p["first_published_at"].replace("Z", "+00:00"))).days
        except ValueError:
            continue
        if days < MIN_DAYS_LISTED:
            continue
        rows.append({"internal_id": p["internal_id"], "band": ops.get(l["opportunity_id"], {}).get("band"),
                     "days_listed": days, "sales_count": p.get("sales_count") or 0})
    if len(rows) < MIN_LINKED_FOR_CALIBRATION:
        return {"status": "NOT_ENOUGH_DATA", "eligible": len(rows),
                "needed": MIN_LINKED_FOR_CALIBRATION,
                "note": f"needs {MIN_LINKED_FOR_CALIBRATION} spec-built products listed >= "
                        f"{MIN_DAYS_LISTED} days; weights are not changed automatically"}
    by_band = {}
    for r in rows:
        b = by_band.setdefault(r["band"], {"products": 0, "with_sale": 0})
        b["products"] += 1
        b["with_sale"] += 1 if r["sales_count"] > 0 else 0
    return {"status": "OBSERVED", "by_band": by_band, "rows": rows,
            "note": "observed comparison for founder review; weights are not changed automatically"}


def build_state(base_dir=None, registry=None, now=None):
    now = now or datetime.now(timezone.utc)
    sources = records.read_jsonl("sources.jsonl", base_dir)
    signals = records.read_jsonl("signals.jsonl", base_dir)
    specs = list(ideation.latest_specs(base_dir).values())
    links = records.read_jsonl("links.jsonl", base_dir)
    ranked = scoring.rank(base_dir)
    dates = sorted(s["accessed_on"] for s in sources)
    newest_age = (now.date() - datetime.strptime(dates[-1], "%Y-%m-%d").date()).days if dates else None
    by_type = {}
    for s in sources:
        by_type[s["source_type"]] = by_type.get(s["source_type"], 0) + 1
    blockers = []
    for o in ranked:
        if o["band"] in ("INSUFFICIENT_EVIDENCE", "BLOCKED_RIGHTS"):
            blockers.append(f"{o['name']}: {o['band']}")
    for s in specs:
        for b in s.get("blockers", []) + s.get("reviews", []):
            blockers.append(f"{s['title']}: {b}")
    return {
        "schema": "trend_to_product_state/1",
        "generated_at": now.isoformat(),
        "evidence_freshness": {"newest_access": dates[-1] if dates else None,
                               "oldest_access": dates[0] if dates else None,
                               "newest_age_days": newest_age},
        "counts": {"sources": len(sources), "signals": len(signals), "opportunities": len(ranked),
                   "specs": len(specs), "product_links": len(links)},
        "evidence_quality": by_type,
        "signals_counting_as_sales": sum(1 for s in signals if s.get("counts_as_sales_evidence")),
        "platform_policy": {k: {"api_configured": v["api_configured"], "max_use": v["max_use"],
                                "rule": v["rule"]} for k, v in records.PLATFORM_POLICY.items()
                            if k != "_default"},
        "opportunities": [{
            "opportunity_id": o["opportunity_id"], "name": o["name"], "format": o["format"],
            "t1_arm": o["t1_arm"], "band": o["band"], "composite": o["composite"],
            "coverage": o["coverage"], "rights": o["rights"]["status"],
            "price_range": o.get("price_range"), "missing_evidence": o["missing_evidence"],
            "dimensions": {k: v["score"] for k, v in o["dimensions"].items()},
        } for o in ranked],
        "specs": [{"spec_id": s["spec_id"], "title": s["title"], "status": s["status"],
                   "duplication": s["duplication"]["verdict"],
                   "duplicates": [m["internal_id"] for m in s["duplication"]["matches"][:3]],
                   "blockers": s.get("blockers", []), "reviews": s.get("reviews", [])} for s in specs],
        "calibration": calibration_summary(base_dir, registry, now),
        "blockers": blockers,
        "live_publish": "disabled: listing drafts carry publish_allowed=false; publication needs "
                        "founder approval and the platform write gate",
    }


def write_state(path=None, base_dir=None, registry=None, now=None):
    doc = build_state(base_dir, registry, now)
    path = path or STATE_PATH
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return doc
