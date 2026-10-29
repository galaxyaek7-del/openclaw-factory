"""Trend-to-Product: explainable, advisory opportunity scoring (2026-10-29).

Nine dimensions, each scored 0..5 (5 = most favourable) or left as None with the
reason it could not be scored. No dimension is ever filled from a default. The
composite is a weighted mean of the scored dimensions only, reported together
with its evidence coverage; below MIN_COVERAGE, or without any demand evidence,
the band is INSUFFICIENT_EVIDENCE and no composite is given.

Every result carries advisory=True and publication_decision=None: a ranking is
input to a founder decision, never a publication decision.

Scoring definitions (the "basis" field of each dimension repeats them):
  demand_evidence        demand signals weighted by source strength. Search
                         interest is an index of interest, not of purchases.
  competition            listing counts (>=100k -> 1, >=10k -> 2, >=1k -> 3,
                         >=100 -> 4, else 5); free alternatives lower it by 1.
  problem_severity       distinct questions stating the problem (1-2:1, 3-9:2, 10-29:3,
                         30-99:4, 100+:5), else a recorded assessment.
  differentiation        recorded assessment only (INFERRED); never computed.
  production_effort      from ideation.FORMATS (existing pipeline -> easier).
  distribution           channel facts recorded in DISTRIBUTION_FACTS.
  rights_risk            rights.check_rights status: PASS 5, REVIEW 2, BLOCK 0.
  payment_feasibility    PAYMENT_FACTS; no channel scores 5 before a first sale.
  maintenance            from ideation.FORMATS.
"""
from . import ideation, records, rights

WEIGHTS = {
    "demand_evidence": 3, "competition": 2, "problem_severity": 2, "differentiation": 2,
    "production_effort": 1, "distribution": 1, "rights_risk": 2, "payment_feasibility": 1,
    "maintenance": 1,
}
MIN_COVERAGE = 0.6

# Facts about this factory's channels, 2026-10-29 (OBSERVED: product registry,
# distribution dashboard, revenue_truth). Restated, not inferred.
DISTRIBUTION_FACTS = {
    "gumroad_download": (4, "Gumroad account live with 102 published listings; site pages exist; "
                            "Pinterest queue blocked on a missing board"),
    "notion_via_gumroad": (3, "can be sold as a Gumroad download of a duplicate link; no Notion "
                              "marketplace account"),
    "service": (1, "needs customer contact, which requires founder authorisation"),
    "media": (2, "children's media has no released channel yet"),
}
PAYMENT_FACTS = {
    "gumroad": (4, "Gumroad checkout live; no sale yet, so payment is not verified end to end"),
    "none": (1, "no live checkout for this format"),
}
FORMAT_CHANNEL = {
    "guide_printable": ("gumroad_download", "gumroad"),
    "craft_pattern": ("gumroad_download", "gumroad"),
    "excel_tool": ("gumroad_download", "gumroad"),
    "notion_template": ("notion_via_gumroad", "gumroad"),
    "research_data_tool": ("gumroad_download", "gumroad"),
    "kids_education": ("media", "none"),
    "service_micro_b2b": ("service", "none"),
}


def _dim(score, basis, label, signal_ids=(), missing=None):
    return {"score": score, "basis": basis, "label": label,
            "signal_ids": list(signal_ids), "missing": missing}


def _demand(sigs):
    d = [s for s in sigs if s["signal_type"] in records.DEMAND_SIGNALS]
    if not d:
        return _dim(None, "no demand signals recorded", "UNKNOWN",
                    missing="search interest, trend direction or repeated customer problems")
    total = sum(s["evidence_weight"] for s in d)
    score = round(min(5.0, total * 2), 2)
    return _dim(score, f"{len(d)} demand signal(s), source-weighted sum {total:.2f} x2, capped at 5; "
                       "interest, not purchases", "DERIVED", [s["signal_id"] for s in d])


def _competition(sigs):
    dens = [s for s in sigs if s["signal_type"] == "COMPETITION_DENSITY"
            and isinstance(s.get("value"), dict) and s["value"].get("listings") is not None]
    fmts = [s for s in sigs if s["signal_type"] == "COMPETING_FORMAT"]
    free = any((s.get("value") or {}).get("free_alternatives") for s in fmts)
    if not dens and not fmts:
        return _dim(None, "no competition observations", "UNKNOWN",
                    missing="listing counts or competing formats")
    if dens:
        n = max(s["value"]["listings"] for s in dens)
        score = 1 if n >= 100000 else 2 if n >= 10000 else 3 if n >= 1000 else 4 if n >= 100 else 5
        basis = f"{n:,} listings observed"
    else:
        score, basis = 3, "competing formats observed, no listing count (mid score, disclosed)"
    if free:
        score = max(0, score - 1)
        basis += "; free alternatives exist (-1)"
    return _dim(score, basis, "DERIVED", [s["signal_id"] for s in dens + fmts])


def _assessed(name, assessments, sigs=None):
    if sigs:
        p = [s for s in sigs if s["signal_type"] == "CUSTOMER_PROBLEM"]
        counted = [s for s in p if isinstance(s.get("value"), dict) and s["value"].get("question_count")]
        if counted:
            n = max(s["value"]["question_count"] for s in counted)
            score = 1 if n <= 2 else 2 if n <= 9 else 3 if n <= 29 else 4 if n <= 99 else 5
            return _dim(score, f"{n} distinct questions stating the problem (bands 1-2:1, 3-9:2, 10-29:3, "
                               "30-99:4, 100+:5); a stated problem, not purchase intent", "DERIVED",
                        [s["signal_id"] for s in counted])
        if p:
            score = min(5, 1 + len(p))
            return _dim(score, f"{len(p)} recorded customer-problem signal(s)", "DERIVED",
                        [s["signal_id"] for s in p])
    a = (assessments or {}).get(name)
    if not a or a.get("score") is None or not a.get("basis"):
        return _dim(None, "no evidence or recorded assessment", "UNKNOWN",
                    missing=f"{name}: needs a recorded assessment with its basis")
    if a.get("label") not in ("INFERRED", "ESTIMATED", "DERIVED"):
        return _dim(None, "assessment without an evidence label", "UNKNOWN",
                    missing=f"{name}: label must be INFERRED, ESTIMATED or DERIVED")
    return _dim(max(0, min(5, a["score"])), a["basis"], a["label"], a.get("signal_ids", ()))


def score_opportunity(format_key, sigs, assessments=None, rights_result=None):
    fmt = ideation.FORMATS.get(format_key)
    if not fmt:
        raise records.RecordError(f"unknown format {format_key!r}")
    chan, pay = FORMAT_CHANNEL[format_key]
    rr = rights_result or rights.check_rights()
    rights_score = {"PASS": 5, "REVIEW": 2, "BLOCK": 0}[rr["status"]]
    dims = {
        "demand_evidence": _demand(sigs),
        "competition": _competition(sigs),
        "problem_severity": _assessed("problem_severity", assessments, sigs),
        "differentiation": _assessed("differentiation", assessments),
        "production_effort": _dim(fmt["effort"], fmt["effort_basis"], "DERIVED"),
        "distribution": _dim(DISTRIBUTION_FACTS[chan][0], DISTRIBUTION_FACTS[chan][1], "OBSERVED"),
        "rights_risk": _dim(rights_score, f"rights check {rr['status']}"
                            + ("" if rr.get("findings") else f" ({rr.get('note')})"), "DERIVED"),
        "payment_feasibility": _dim(PAYMENT_FACTS[pay][0], PAYMENT_FACTS[pay][1], "OBSERVED"),
        "maintenance": _dim(fmt["maintenance"], fmt["maintenance_basis"], "DERIVED"),
    }
    scored = {k: v for k, v in dims.items() if v["score"] is not None}
    total_w = sum(WEIGHTS.values())
    cov = round(sum(WEIGHTS[k] for k in scored) / total_w, 2)
    missing = [v["missing"] for v in dims.values() if v["missing"]]
    if dims["demand_evidence"]["score"] is None or cov < MIN_COVERAGE:
        composite, band = None, "INSUFFICIENT_EVIDENCE"
    else:
        composite = round(sum(v["score"] * WEIGHTS[k] for k, v in scored.items())
                          / sum(WEIGHTS[k] for k in scored), 2)
        band = "STRONG" if composite >= 3.8 else "MODERATE" if composite >= 2.8 else "WEAK"
    if rr["status"] == "BLOCK":
        band = "BLOCKED_RIGHTS"
    return {
        "dimensions": dims, "weights": WEIGHTS, "coverage": cov, "composite": composite,
        "band": band, "missing_evidence": missing, "rights": rr,
        "advisory": True, "publication_decision": None,
        "note": "advisory ranking; composite over scored dimensions only; search interest is not sales",
    }


def record_opportunity(name, topic, format_key, signal_ids, assessments=None, assets=None,
                       idea_text=None, base_dir=None):
    """Score and store one candidate opportunity (one topic x one format)."""
    sigs = records.signals_for(signal_ids=signal_ids, base_dir=base_dir)
    if len(sigs) != len(set(signal_ids)):
        raise records.RecordError("unknown signal id(s) cited")
    rr = rights.check_rights(assets, idea_text)
    result = score_opportunity(format_key, sigs, assessments, rr)
    rec = {
        "opportunity_id": records._id("OPP", topic, format_key, name),
        "name": name, "topic": topic, "format": format_key,
        "t1_arm": ideation.FORMATS[format_key]["t1_arm"],
        "signal_ids": list(signal_ids), "assessments": assessments or {},
        "price_range": ideation.price_range_from_signals(sigs),
        "status": "EVALUATED", "recorded_at": records._now(), **result,
    }
    records._append("opportunities.jsonl", rec, base_dir)
    return rec


def latest_opportunities(base_dir=None):
    """Latest record per opportunity id (re-scoring appends; history is kept)."""
    latest = {}
    for r in records.read_jsonl("opportunities.jsonl", base_dir):
        latest[r["opportunity_id"]] = r
    return list(latest.values())


def rank(base_dir=None):
    ops = latest_opportunities(base_dir)
    order = {"STRONG": 0, "MODERATE": 1, "WEAK": 2, "INSUFFICIENT_EVIDENCE": 3, "BLOCKED_RIGHTS": 4}
    return sorted(ops, key=lambda o: (order.get(o["band"], 9), -(o["composite"] or 0), -o["coverage"]))
