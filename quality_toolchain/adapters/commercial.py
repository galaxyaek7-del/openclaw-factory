# -*- coding: utf-8 -*-
"""Isolated adapter: commercial QA (QUALITY ARCHITECTURE directive,
2026-09-02). Wraps inspectors.py::audit_commercial -- the factory's already-
real, load-bearing Commercial Auditor (profit_oracle profit score, economics/
butter-price floor, duplicate/product-history check, QUARANTINE.md prior-
rejection check) -- into the toolchain's `commercial_qa` layer as an
ADVISORY, evidence-recorded adapter.

Purpose: connect the already-real commercial gate into the toolchain without
duplicating it. Decision authority stays human; this adapter reports numeric
findings, never auto-publishes.

Contract:
  check_commercial(niche=None, price=None, title=None, platform=None,
                   page_count=None) -> dict
    - mirrors audit_commercial()'s signature; price may be int/float/str
      (audit_commercial already normalizes).
    Returns {"status", "passed", "score": "N/M", "checks": [concrete items],
             "failures": [...], "profit_score"}.

Fail-closed: an exception in the delegation resolves to status "error" and
passed=False. A missing niche/price is passed through honestly (the real
audit_commercial already treats missing economics as a failure, never a
fabricated pass).
"""


def check_commercial(niche=None, price=None, title=None, platform=None,
                     page_count=None):
    try:
        import importlib
        inspectors = importlib.import_module("inspectors")
    except Exception as e:  # noqa: BLE001 - fail closed if inspectors can't load
        return {"status": "error", "passed": False, "score": "0/0",
                "checks": [], "failures": [f"could not load inspectors: {e}"],
                "reason": "inspectors.py unavailable"}

    try:
        res = inspectors.audit_commercial(
            niche, price, title=title,
            platform=platform or "kdp_ebook", page_count=page_count,
        )
    except Exception as e:  # noqa: BLE001 - fail closed
        return {"status": "error", "passed": False, "score": "0/0",
                "checks": [], "failures": [str(e)],
                "reason": f"audit_commercial raised: {e}"}

    checks = list(res.get("checks") or [])
    failures = list(res.get("failures") or [])
    passed_count = sum(1 for c in checks if c.get("passed"))
    try:
        order = list(checks)
    except Exception:  # noqa: BLE001
        order = res.get("checks") or []

    return {
        "status": "ok",
        "passed": bool(res.get("passed")),
        "score": f"{passed_count}/{len(order)}" if order else "0/0",
        "checks": [
            {"name": c.get("name"), "passed": c.get("passed"),
             "detail": c.get("detail")}
            for c in checks
        ],
        "failures": failures,
        "profit_score": res.get("profit_score"),
        "verdict": res.get("verdict"),
        "reason": None if res.get("passed") else (
            "commercial audit reported one or more failures"),
    }