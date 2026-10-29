"""Trend-to-Product: cross-arm product formats, specifications, duplication check
and listing drafts (2026-10-29).

FORMATS describes what this factory can actually build and verify today, per
format, citing the existing pipeline it would reuse. Effort and maintenance are
DERIVED from that (an existing, tested pipeline -> lower effort) and say so; they
are not market data.

Nothing here publishes, prices or schedules anything. A listing draft carries
publish_allowed=False and must go through the existing publication approval
(data/publication_approvals.json) and the platform write gate like every other
product.
"""
import json
import os
import re

from . import records

REGISTRY_PATH = os.path.join(records.ROOT, "data", "product_registry.json")

# effort/maintenance: 1 (hard / heavy upkeep) .. 5 (easy / static). verification
# says how technical correctness is checked and whether this factory can do it.
FORMATS = {
    "guide_printable": {
        "label": "Original digital guide or printable (PDF)",
        "t1_arm": "digital_products",
        "pipeline": ["book_generator.py", "inspectors.py", "pdf_layout_inspector.py"],
        "verification": "page/text inspection and layout check (existing); facts need cited sources",
        "verifiable_here": True,
        "effort": 4, "effort_basis": "existing PDF pipeline and Dual Inspection",
        "maintenance": 4, "maintenance_basis": "static unless it cites rules that change",
    },
    "craft_pattern": {
        "label": "Original crochet/craft pattern",
        "t1_arm": "digital_products",
        "pipeline": [],
        "verification": "stitch counts per row can be checked by code; gauge, drape, fit and "
                        "whether the finished piece looks as pictured need a physical test make",
        "verifiable_here": False,
        "effort": 1, "effort_basis": "no pattern pipeline; physical test make is not available here",
        "maintenance": 4, "maintenance_basis": "static once tested; errata from buyers",
    },
    "excel_tool": {
        "label": "Excel calculator or business tracker",
        "t1_arm": "digital_products",
        "pipeline": ["books/_batch14_src", "native_workbook_qa.py", "workbook_upgrader.py"],
        "verification": "independent formula recomputation (batch 14: 872 checks) and workbook QA",
        "verifiable_here": True,
        "effort": 4, "effort_basis": "batch 13-15 workbook pipeline with independent checks",
        "maintenance": 3, "maintenance_basis": "fee/tax tables inside a calculator go out of date",
    },
    "notion_template": {
        "label": "Notion template",
        "t1_arm": "digital_products",
        "pipeline": ["_gen_notion_drafts.py"],
        "verification": "structure can be specified here; duplicating and testing it needs a Notion "
                        "workspace session (no Notion delivery pipeline is built)",
        "verifiable_here": False,
        "effort": 2, "effort_basis": "draft generator only; no tested Notion delivery path",
        "maintenance": 4, "maintenance_basis": "static template",
    },
    "research_data_tool": {
        "label": "Research product or data-driven tool",
        "t1_arm": "research_data_services",
        "pipeline": ["source_grounding.py"],
        "verification": "every figure needs a cited, dated source; data provenance card required",
        "verifiable_here": True,
        "effort": 2, "effort_basis": "grounding exists; no packaged dataset format yet (backlog B20)",
        "maintenance": 2, "maintenance_basis": "data goes stale; needs scheduled refresh",
    },
    "kids_education": {
        "label": "Children's educational material / media product",
        "t1_arm": "childrens_media_studio",
        "pipeline": ["kids_studio/"],
        "verification": "age-appropriateness and content review by a person; voices/font undecided",
        "verifiable_here": False,
        "effort": 2, "effort_basis": "studio produces an animatic only; founder decisions pending (B25)",
        "maintenance": 4, "maintenance_basis": "static once released",
    },
    "service_micro_b2b": {
        "label": "Productized service or micro-B2B tool",
        "t1_arm": "micro_b2b",
        "pipeline": ["services/spreadsheet_normalization/"],
        "verification": "fixture-based tests of the delivery engine",
        "verifiable_here": True,
        "effort": 2, "effort_basis": "one delivery engine exists; any service needs customer contact, "
                                     "which requires founder authorisation",
        "maintenance": 2, "maintenance_basis": "ongoing delivery and support",
    },
}

SPEC_FIELDS = ("title", "target_customer", "problem_statement", "value_proposition",
               "differentiation", "deliverables", "acceptance_tests", "price_range")

_STOP = set("a an and or the for of to with in on by your you my our from as at is are be "
            "pdf printable template templates excel notion kit pack tool tools tracker planner "
            "workbook guide digital download sheet sheets spreadsheet & -".split())


# Words that name the same subject or buyer. Title-word overlap alone missed that
# "Handmade Order Costing & Pricing Workbook" competes with B14-005 "Etsy &
# Shopify Product Profit Calculator" (found 2026-10-29); concepts catch that.
CONCEPTS = {
    "c:pricing": {"price", "prices", "pricing", "profit", "profitability", "margin", "margins",
                  "costing", "markup", "breakeven"},
    "c:online_seller": {"etsy", "shopify", "handmade", "maker", "makers", "seller", "sellers",
                        "crafter", "crafters", "marketplace"},
    "c:reading": {"reading", "book", "books", "reader", "readers"},
    "c:content": {"content", "social", "posting", "posts", "instagram", "pinterest"},
    "c:crochet": {"crochet", "knitting", "yarn", "amigurumi", "stitch"},
    "c:miniature": {"miniature", "miniatures", "dollhouse"},
}
_TO_CONCEPT = {w: c for c, words in CONCEPTS.items() for w in words}


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOP and len(t) > 2}


def _concepts(tokens):
    return {_TO_CONCEPT[t] for t in tokens if t in _TO_CONCEPT}


def load_registry(path=None):
    try:
        with open(path or REGISTRY_PATH, encoding="utf-8") as f:
            return json.load(f).get("products", [])
    except (OSError, ValueError):
        return []


def duplication_check(title, keywords=(), registry=None, registry_path=None):
    """Compare an idea with every product in the authoritative registry.

    Disclosed heuristic over registry titles, not a semantic judgement:
      title-word Jaccard >= 0.5                 DUPLICATE (same product exists)
      Jaccard >= 0.25, or >= 3 shared words,
      or >= 2 shared subject concepts           CANNIBALIZATION (same buyer and job)
    The idea's title alone is compared for concepts (keywords add words only), so
    a long problem statement cannot match everything.
    """
    products = registry if registry is not None else load_registry(registry_path)
    mine = _tokens(title) | _tokens(" ".join(keywords))
    mine_c = _concepts(_tokens(title))
    hits = []
    for p in products:
        theirs = _tokens(p.get("title"))
        if not mine or not theirs:
            continue
        j = len(mine & theirs) / len(mine | theirs)
        overlap = sorted(mine & theirs)
        shared_c = sorted(mine_c & _concepts(theirs))
        if j >= 0.25 or len(overlap) >= 3 or len(shared_c) >= 2:
            hits.append({"internal_id": p.get("internal_id"), "title": p.get("title"),
                         "published": p.get("published"), "similarity": round(j, 2),
                         "shared_terms": overlap, "shared_concepts": shared_c,
                         "verdict": "DUPLICATE" if j >= 0.5 else "CANNIBALIZATION"})
    hits.sort(key=lambda h: (-h["similarity"], -len(h["shared_concepts"])))
    verdict = "DUPLICATE" if any(h["verdict"] == "DUPLICATE" for h in hits) else (
        "CANNIBALIZATION" if hits else "NONE_FOUND")
    return {"verdict": verdict, "matches": hits[:10], "compared": len(products),
            "method": "content-word Jaccard over registry titles (heuristic)"}


def price_range_from_signals(signals):
    """Aggregate PRICE_OBSERVATION signals. Returns UNKNOWN when none exist."""
    obs = [s for s in signals if s["signal_type"] == "PRICE_OBSERVATION" and s.get("value")]
    usd = [s for s in obs if s["value"].get("currency") == "USD"]
    if not usd:
        return {"status": "UNKNOWN", "reason": "no USD price observations recorded",
                "signal_ids": [s["signal_id"] for s in obs]}
    lows = [s["value"]["low"] for s in usd]
    highs = [s["value"]["high"] for s in usd]
    medians = [s["value"]["median"] for s in usd if s["value"].get("median") is not None]
    return {"status": "OBSERVED_RANGE", "currency": "USD", "low": min(lows), "high": max(highs),
            "medians": medians, "signal_ids": [s["signal_id"] for s in usd],
            "note": "observed list prices of competing listings; not sales and not our price"}


def build_spec(opportunity, format_key, title, target_customer, problem_statement,
               value_proposition, differentiation, deliverables, acceptance_tests,
               proposed_price_usd=None, registry=None, base_dir=None):
    """Create a product specification linked to an opportunity. Validates fields,
    runs the duplication check and attaches the evidence-based price range."""
    if format_key not in FORMATS:
        raise records.RecordError(f"unknown format {format_key!r}")
    fmt = FORMATS[format_key]
    sigs = records.signals_for(signal_ids=opportunity.get("signal_ids", []), base_dir=base_dir)
    price = price_range_from_signals(sigs)
    spec = {
        "spec_id": records._id("SPEC", opportunity["opportunity_id"], format_key, title),
        "opportunity_id": opportunity["opportunity_id"],
        "format": format_key, "format_label": fmt["label"], "t1_arm": fmt["t1_arm"],
        "title": title, "target_customer": target_customer,
        "problem_statement": problem_statement, "value_proposition": value_proposition,
        "differentiation": differentiation, "deliverables": list(deliverables or []),
        "acceptance_tests": list(acceptance_tests or []),
        "price_range": price,
        "proposed_price_usd": proposed_price_usd,
        "price_basis": ("within observed competing range" if price["status"] == "OBSERVED_RANGE"
                        and proposed_price_usd is not None
                        and price["low"] <= proposed_price_usd <= price["high"]
                        else "outside or without observed range: needs founder review"
                        if proposed_price_usd is not None else "no price proposed"),
        "pipeline": fmt["pipeline"], "verification": fmt["verification"],
        "verifiable_here": fmt["verifiable_here"],
        "duplication": duplication_check(title, [problem_statement], registry=registry),
        "status": "SPEC_DRAFT", "recorded_at": records._now(),
    }
    missing = [f for f in SPEC_FIELDS if f != "price_range" and not spec.get(f)]
    if missing:
        raise records.RecordError(f"specification incomplete: {missing}")
    blockers = []
    if not fmt["verifiable_here"]:
        blockers.append("technical correctness cannot be fully verified with this factory's tools: "
                        + fmt["verification"])
    if spec["duplication"]["verdict"] == "DUPLICATE":
        blockers.append("duplicates an existing product: "
                        + spec["duplication"]["matches"][0]["internal_id"])
    reviews = []
    if spec["duplication"]["verdict"] == "CANNIBALIZATION":
        reviews.append("would compete with our own product(s): "
                       + ", ".join(m["internal_id"] for m in spec["duplication"]["matches"][:3])
                       + " -- founder decides: differentiate, bundle, or drop")
    spec["blockers"] = blockers
    spec["reviews"] = reviews
    spec["status"] = "SPEC_BLOCKED" if blockers else ("SPEC_REVIEW" if reviews else "SPEC_DRAFT")
    # Append-only: a re-run that changes the verdict adds a newer record; readers
    # take the latest record per spec_id (latest_specs), history is kept.
    prev = latest_specs(base_dir).get(spec["spec_id"])
    if not prev or (prev.get("status"), prev.get("duplication", {}).get("verdict")) != (
            spec["status"], spec["duplication"]["verdict"]):
        records._append("specs.jsonl", spec, base_dir)
    return spec


def latest_specs(base_dir=None):
    out = {}
    for r in records.read_jsonl("specs.jsonl", base_dir):
        out[r["spec_id"]] = r
    return out


def listing_draft(spec, description, tags, contents, support):
    """Draft listing copy for founder review. Never published from here."""
    text = " ".join([spec["title"], description, " ".join(contents)])
    urgency = None
    try:
        import executive_quality_gate as eqg
        urgency = eqg.check_fake_urgency_risk([{"content": text}])
    except Exception:
        urgency = {"status": "UNKNOWN"}
    problems = []
    if urgency.get("status") == "FAIL":
        problems.append("fake urgency wording: " + ", ".join(urgency.get("evidence") or []))
    if len(tags) > 13:
        problems.append("more than 13 tags")
    return {
        "spec_id": spec["spec_id"], "title": spec["title"][:100], "description": description,
        "keywords_tags": list(tags)[:13], "contents": list(contents), "support": support,
        "proposed_price_usd": spec.get("proposed_price_usd"),
        "pricing_evidence": spec["price_range"],
        "status": "DRAFT_NOT_PUBLISHED", "publish_allowed": False,
        "requires": ["product built from this spec and passing its acceptance tests",
                     "rights check PASS", "founder publication approval",
                     "platform write gate"],
        "problems": problems,
    }
