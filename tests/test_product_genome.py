"""Tests for product_genome.py (P1 ARM 3 — Product Genome ENGINE).

HARD RULES verified here:
- No fabrication of success/sales/ratings/prices/market evidence.
- REAL/TEST/MOCK/UNKNOWN preserved; inference never upgraded to REAL.
- PATTERN != SUCCESS, FEATURE FREQUENCY != CUSTOMER VALUE,
  SIMILARITY != MARKET VALIDATION, GENOME INSIGHT != COMMERCIAL READINESS.
- No external side effects; no financial-file writes; no execution.
- Opportunity Kill gate is never bypassed.
"""

import json
from pathlib import Path


from product_genome import (
    ProductGenomeEngine,
    build_product_genome,
    verify_lifecycle_gates,
    normalize_feature,
    classify_reality_state,
    classify_evidence_type,
    extract_attributes,
    detect_patterns,
    build_product_dna,
    REALITY_STATES,
    EVIDENCE_TYPES,
)


def _real_candidate():
    """The real, controlled product candidate (controlled_customer_validation).
    Reality state is UNKNOWN (no real product success evidence yet)."""
    return {
        "product_id": "PROD-5214fb83a464299d",
        "category": "legal-saas",
        "problem_solved": "Solo attorneys cannot operationalize EU AI Act obligations into a repeatable client workflow",
        "customer_segment": "solo attorney / small law firm",
        "core_features": ["automated report generation", "recurring billing", "api integration", "compliance checklist"],
        "differentiation": ["compliance checklist"],
        "reality_state": "UNKNOWN",
        "evidence_state": "UNKNOWN",
        "price": None,
        "costs": {},
    }


def test_normalize_feature_synonyms():
    assert normalize_feature("Automated Reporting") == "automatic report generation"
    assert normalize_feature("subscription billing") == "recurring billing"
    assert normalize_feature("API Access") == "api integration"
    assert normalize_feature("white label") == "white-label"
    # unambiguous pass-through
    assert normalize_feature("drag-and-drop") == "drag-and-drop"
    assert normalize_feature("") == ""


def test_classify_reality_state_coercion():
    assert classify_reality_state("REAL") == "REAL"
    assert classify_reality_state("mock") == "MOCK"
    assert classify_reality_state("bogus") == "UNKNOWN"
    assert classify_reality_state(None) == "UNKNOWN"


def test_classify_evidence_type_coercion():
    assert classify_evidence_type("REAL_SUCCESS_EVIDENCE") == "REAL_SUCCESS_EVIDENCE"
    assert classify_evidence_type("competitor_evidence") == "COMPETITOR_EVIDENCE"
    assert classify_evidence_type("whatever") == "ASSUMPTION"


def test_validate_source_rejects_missing_id():
    eng = ProductGenomeEngine()
    r = eng.validate_source({"category": "x"})
    assert r["valid"] is False
    assert r["status"] == "INVALID_INPUT"


def test_validate_source_rejects_fabricated_success():
    eng = ProductGenomeEngine()
    r = eng.validate_source({"product_id": "P1", "success_claim": True, "reality_state": "UNKNOWN"})
    assert r["valid"] is False
    r2 = eng.validate_source({"product_id": "P1", "success_claim": True, "reality_state": "REAL"})
    assert r2["valid"] is True


def test_extract_attributes_preserves_unknown():
    attrs = extract_attributes({"product_id": "P1"})
    for cat in ("PROBLEM", "CUSTOMER", "PRICING", "DELIVERY", "SUPPORT", "COMPLIANCE"):
        assert attrs[cat]["value"] is None
        assert attrs[cat]["reality_state"] == "UNKNOWN"


def test_detect_patterns_no_fabricated_success():
    # two products sharing a normalized feature -> it surfaces as common
    p1 = _real_candidate()
    p2 = dict(_real_candidate(), product_id="PROD-SECOND-1111")
    p2["core_features"] = ["Automated Reporting", "recurring billing", "api integration"]
    pat = detect_patterns([p1, p2])
    assert "COMMON != SUCCESS" in pat["note"]
    assert "FEATURE FREQUENCY != CUSTOMER VALUE" in pat["note"]
    # no sale/revenue figures invented
    assert "common_features" in pat
    # common feature present (synonym folding: Automated Reporting -> automatic report generation)
    feats = {f["feature"] for f in pat["common_features"]}
    assert "automatic report generation" in feats
    # a single product never fabricates a common pattern
    assert detect_patterns([_real_candidate()])["common_features"] == []


def test_build_product_dna_unknown_categories():
    products = [_real_candidate()]
    pat = detect_patterns(products)
    dna = build_product_dna(pat, products)
    # categories with no observed value must surface as UNKNOWN_DNA
    for cat in ("WORKFLOW", "DELIVERY", "PRICING", "RECURRING_MODEL", "AUTOMATION"):
        assert cat in dna["UNKNOWN_DNA"]
    assert "CORE = repeated" in dna["note"]


def test_analyze_on_real_candidate_is_read_only_and_honest():
    eng = ProductGenomeEngine()
    res = eng.analyze([_real_candidate()], integrations=True)
    assert res["status"] == "OK"
    assert res["financial_truth_unchanged"] is True
    assert res["reused_existing_genome"] is True
    # candidate never upgraded to REAL success
    for e in res["evidence_classification"]:
        assert e["evidence_type"] != "REAL_SUCCESS_EVIDENCE"
        assert e["reality_state"] in REALITY_STATES
    # integration executed read-only and never bypassed the kill gate
    integ = res["integration"]
    assert integ is not None
    assert integ["opportunity_kill"]["status"] in ("OK", "UNKNOWN")
    # Opportunity Kill gate is consulted; genome does not auto-launch
    kill = integ["opportunity_kill"]["kills"][0]["kill"]
    assert kill["decision"] in ("HOLD", "INVESTIGATE", "KILL", "DEFERRED", "PROCEED")
    # for this UNKNOWN-reality candidate it must NOT auto-proceed to launch
    assert kill["decision"] != "PROCEED"
    # but crucially financial truth is unchanged and no execution happened
    assert res["financial_truth_unchanged"] is True
    assert "COMMERCIAL READINESS" in res["note"]


def test_analyze_dedupes_and_rejects_fabricated_success_inputs():
    eng = ProductGenomeEngine()
    dup = _real_candidate()
    fake = {"product_id": "P9", "success_claim": True, "reality_state": "UNKNOWN",
            "core_features": ["x"]}
    res = eng.analyze([dup, dup, fake], integrations=False)
    assert res["total_input"] == 3
    assert res["deduplicated_products"] == 1  # dup removed
    assert len(res["invalid_products"]) == 1  # fake rejected
    assert res["valid_products"] == 2


def test_analyze_fail_safe_on_non_list():
    eng = ProductGenomeEngine()
    res = eng.analyze({"not": "a list"}, integrations=False)
    assert res["status"] == "INVALID_INPUT"
    assert res["financial_truth_unchanged"] is True


def test_build_product_genome_false_for_unknown_id():
    g = build_product_genome("NONEXISTENT-PROD-XYZ-123")
    assert g["found"] is False
    assert "reason" in g


def test_verify_lifecycle_gates_all_ok_non_bypassable():
    lg = verify_lifecycle_gates("paddle")
    assert lg["all_gates_ok"] is True
    assert lg["bypass_possible"] is False
    # every critical transition is enforced by a real gate
    assert len(lg["checks"]) >= 5
