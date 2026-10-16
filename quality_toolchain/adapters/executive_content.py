# -*- coding: utf-8 -*-
"""Isolated adapter: executive content gate (QUALITY ARCHITECTURE directive,
2026-09-02). Wraps executive_quality_gate.py's four REJECT_IF_FAIL
deterministic content checks -- content_neutrality_risk, copyright_
trademark_risk, fake_urgency_risk, brand_reputation_risk -- so the Quality
Toolchain's `content_qa` layer surfaces the factory's already-real, already-
tested executive content gate with a numeric hits list per criterion.

Purpose: connect the REAL executive content checks into the toolchain as an
ADVISORY, evidence-recorded adapter (founder-approved CONNECT scope). The
decision authority always stays human; this adapter never blocks production
on its own, it only records measured results + concrete findings.

Contract:
  check_executive_content(product_chapters, checks=None) -> dict
    - product_chapters: list of {"content": ...} chapter dicts (the exact
      shape executive_quality_gate.py's content checks already consume), OR
      a plain string (wrapped into a single chapter for convenience).
    - checks: optional explicit list of check-function names to run; defaults
      to the four REJECT_IF_FAIL content checks.
    - Returns {"status", "passed", "checks": [ {name, status, evidence,
      hits} ], "score": N/M, "failure_hits": {check: [phrases]}}. `passed` is
      True iff every run check returned PASS; UNKNOWN checks (no content)
      never count as pass and are reported as "unverified", never silently
      excluded.

Fail-closed: any exception resolves to status "error" and passed=False,
matching the toolchain's gate.py contract. Imported lazily so the toolchain
layer never hard-depends on executive_quality_gate being importable at
import time.
"""

REJECT_IF_FAIL_CONTENT_CHECKS = (
    "check_content_neutrality_risk",
    "check_copyright_trademark_risk",
    "check_fake_urgency_risk",
    "check_brand_reputation_risk",
)


def _to_chapters(product_chapters):
    """Normalize input: already-list-of-dicts stays; a plain string becomes a
    single chapter dict; empty/None becomes empty list (no content -> each
    check honestly returns UNKNOWN, never a fabricated pass)."""
    if isinstance(product_chapters, str):
        return [{"content": product_chapters}]
    if isinstance(product_chapters, list):
        return [c for c in product_chapters if isinstance(c, dict)]
    return []


def _status_to_failed(status):
    """executive_quality_gate status -> toolchain pass/fail mapping.
    Only an explicit PASS contributes a pass; FAIL fails; UNKNOWN/INFO are
    reported as unverified (never count as a pass, never a definite fail)."""
    return {"PASS": False, "FAIL": True}.get(status, None)


def check_executive_content(product_chapters, checks=None):
    import importlib
    eqg = importlib.import_module("executive_quality_gate")

    names = list(checks or REJECT_IF_FAIL_CONTENT_CHECKS)
    chapters = _to_chapters(product_chapters)

    ver = {"status": "ok", "passed": True, "checks": [], "score": None,
           "failure_hits": {}, "unverified": [], "reason": None}
    passed_count = 0
    attempted = 0

    for name in names:
        fn = getattr(eqg, name, None)
        if fn is None:
            ver["checks"].append({"name": name, "status": "error",
                                  "evidence": None, "hits": [],
                                  "reason": "unknown check name"})
            attempted += 1
            continue
        attempted += 1
        try:
            res = fn(chapters)
        except Exception as e:  # noqa: BLE001 - fail closed
            ver["checks"].append({"name": name, "status": "error",
                                  "evidence": None, "hits": [],
                                  "reason": str(e)})
            continue
        status = res.get("status", "UNKNOWN")
        evidence = res.get("evidence") or []
        hits = [h for h in evidence if isinstance(h, str)]
        failed = _status_to_failed(status)
        ver["checks"].append({
            "name": name, "status": status,
            "evidence": evidence, "hits": hits,
            "reason": res.get("reason"),
        })
        if status == "PASS":
            passed_count += 1
        elif failed:
            ver["failure_hits"][name] = hits
            ver["passed"] = False
        else:
            ver["unverified"].append(name)

    ver["score"] = f"{passed_count}/{attempted}" if attempted else "0/0"
    if ver["failure_hits"]:
        ver["reason"] = "one or more executive content checks reported FAIL"
    elif ver["unverified"]:
        ver["reason"] = "some executive content checks are UNKNOWN (no content)"
        # An unverified check never becomes a clean pass -- advisory REVIEW.
        ver["passed"] = False
        ver["verdict"] = "REVIEW"
    elif attempted:
        ver["reason"] = "all executive content checks passed"
    return ver