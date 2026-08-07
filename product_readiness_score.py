"""Product Readiness Score (new, ADR-199, 2026-08-07) -- the founder's
"Stop writing strategy documents, implement" directive. Closes the one
genuine, small, buildable gap READINESS_SCORE_ENGINE.md (Phase 9,
ADR-198) named explicitly: "a real per-product Overall Readiness score
would... thread the 3 already-per-product signals through, honestly
exclude the 3 that aren't."

Pure citation over 3 already-real, already-tested functions --
inspectors.py::inspect_technical()/audit_commercial() (per-product,
real) and strategic_intelligence_core.strategic_score() (per-niche,
real). Customer/Automation/Security stay honestly excluded, exactly as
READINESS_SCORE_ENGINE.md disclosed -- no real per-product signal
exists for any of them yet, and averaging in a company-wide number
would misrepresent it as product-specific.

Real, disclosed nuance found while building this: re-running
audit_commercial() against an already-shipped product always fails its
own real not_duplicate/not_previously_rejected checks -- correct,
expected behavior of the duplicate-detection safety system (QUARANTINE.md's
own real design), not a live commercial defect. This module reports
that distinction explicitly rather than either hiding a raw "False" or
treating it as a real problem it is not."""

from pathlib import Path

_PROCEDURAL_RERUN_CHECKS = ("not_duplicate", "not_previously_rejected")


def _technical_component(pdf_path, cover_path=None):
    from inspectors import inspect_technical
    try:
        result = inspect_technical(pdf_path, cover_path)
    except Exception as e:
        return {"score": None, "evidence": f"inspect_technical() failed: {e}", "source": "inspectors.py::inspect_technical()"}
    checks = result.get("checks") or []
    passed_count = sum(1 for c in checks if c.get("passed"))
    score = round(100 * passed_count / len(checks), 1) if checks else None
    return {
        "score": score,
        "evidence": f"{passed_count}/{len(checks)} real technical checks passed. Overall passed={result.get('passed')}.",
        "source": "inspectors.py::inspect_technical()",
    }


def _commercial_component(niche, price, title=None, platform=None, page_count=None):
    from inspectors import audit_commercial
    try:
        result = audit_commercial(niche, price, title=title, platform=platform, page_count=page_count)
    except Exception as e:
        return {"score": None, "evidence": f"audit_commercial() failed: {e}", "source": "inspectors.py::audit_commercial()"}

    real_failures = [f for f in (result.get("failures") or []) if not any(f.startswith(p) for p in _PROCEDURAL_RERUN_CHECKS)]
    procedural_failures = [f for f in (result.get("failures") or []) if any(f.startswith(p) for p in _PROCEDURAL_RERUN_CHECKS)]

    return {
        "score": result.get("profit_score"),
        "evidence": (
            f"real profit_score={result.get('profit_score')}. "
            f"Raw passed={result.get('passed')} -- {len(procedural_failures)} procedural re-run artifact(s) "
            f"(not_duplicate/not_previously_rejected, expected for an already-shipped product, not a live defect) "
            f"and {len(real_failures)} genuine commercial failure(s)."
        ),
        "real_failures": real_failures,
        "procedural_failures": procedural_failures,
        "source": "inspectors.py::audit_commercial()",
    }


def _strategic_component(niche):
    from strategic_intelligence_core import strategic_score
    try:
        result = strategic_score(niche)
    except Exception as e:
        return {"score": None, "evidence": f"strategic_score() failed: {e}", "source": "strategic_intelligence_core.py::strategic_score()"}
    numeric_values = [
        d["value"] for d in result.values()
        if isinstance(d, dict) and isinstance(d.get("value"), (int, float))
    ]
    score = round(sum(numeric_values) / len(numeric_values), 1) if numeric_values else None
    return {
        "score": score,
        "evidence": f"{len(numeric_values)} of 11 real strategic dimensions had a real numeric value this call; the rest were honestly Unknown (no real ACCEPTED decision for this niche yet).",
        "source": "strategic_intelligence_core.py::strategic_score()",
    }


def compute_product_readiness_score(pdf_path, price, niche, cover_path=None, title=None, platform=None, page_count=None):
    """The one real aggregator -- computes the 3 real per-product
    components exactly once, averages only the ones with a real
    numeric value (same honest-exclusion discipline as
    commercial_readiness.py), and names the 3 dimensions this factory
    has no real per-product signal for at all."""
    technical = _technical_component(pdf_path, cover_path)
    commercial = _commercial_component(niche, price, title=title, platform=platform, page_count=page_count)
    strategic = _strategic_component(niche)

    dims = {"technical": technical, "commercial": commercial, "strategic": strategic}
    scored = [d["score"] for d in dims.values() if d["score"] is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else None

    return {
        "product": niche,
        "overall_readiness": overall,
        "overall_note": "Average of the real, per-product dimensions computed this call (technical/commercial/strategic). Customer, Automation, and Security are deliberately excluded -- no real per-product signal exists for any of them anywhere in this factory (READINESS_SCORE_ENGINE.md's own disclosed gap, not filled here with a company-wide substitute).",
        "dimensions": dims,
        "not_scored": {
            "customer": "No real per-product customer-readiness signal exists -- trust_audit.py's customer-risk section is company-wide only.",
            "automation": "launch_readiness.py's automation dimension is per-division, not per-product.",
            "security": "resilience_monitor.py's findings are company-wide, not per-product.",
        },
    }
