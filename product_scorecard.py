"""Galaxy Forge -- measurable product quality gate (Cycle 87, directive D).

WHY A COMPOSED GATE
-------------------
The Cycle 86 scorecard was written inline inside scripts/cycle86_content_gate.py
and hardcoded to the EU AI Act toolkit. That is not a gate; it is a report
about one product. A gate has to accept any product, apply the same rubric, and
return the same verdict vocabulary every time.

This module composes the checks that already exist rather than reimplementing
them:
    file_testing_engine        -> file completeness / usability   (25)
    product_content_integrity  -> accuracy and sources           (25)
    source_grounding           -> grounding of regulatory claims (part of 25)
    practical-value signals    -> customer fit                   (20)
    independent verification   -> critic + tests                 (15)
    commercial presentation    -> description accuracy           (15)

VERDICT VOCABULARY (never collapsed)
-------------------------------------
  PASS     every required dimension met, no open critical defect
  HOLD     a defect is open, or a required dimension is UNKNOWN
  BLOCKED  verification could not run; a named human action is required
  FAIL     a required dimension is definitively below threshold
  UNKNOWN  insufficient evidence to decide

The founder's rule is explicit and is encoded in decide(): a high total can
NEVER cancel a critical defect. `decide()` checks the defect list before it
looks at the score at all.

Every dimension must be backed by evidence. A dimension with no evidence is
scored UNKNOWN, which is not the same as zero and is not the same as full --
it makes the product HOLD, because unverifiable is not publishable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PASS = "PASS"
HOLD = "HOLD"
BLOCKED = "BLOCKED"
FAIL = "FAIL"
UNKNOWN = "UNKNOWN"

THRESHOLD = 90


@dataclass
class Dimension:
    name: str
    max_points: int
    status: str = UNKNOWN          # PASS | FAIL | UNKNOWN | BLOCKED
    earned: int = 0
    evidence: list[str] = field(default_factory=list)

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)


@dataclass
class Scorecard:
    product: str
    dimensions: list[Dimension] = field(default_factory=list)
    critical_defects: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(d.earned for d in self.dimensions)

    @property
    def max_total(self) -> int:
        return sum(d.max_points for d in self.dimensions)

    def decide(self) -> str:
        """
        Defects are checked BEFORE the score. A 95 with an open critical defect
        is HOLD. This is the founder's rule and it is enforced here so no
        future caller can bypass it by adding points.
        """
        if self.critical_defects:
            return HOLD
        blocked = [d.name for d in self.dimensions if d.status == BLOCKED]
        if blocked:
            return BLOCKED
        unknown = [d.name for d in self.dimensions if d.status == UNKNOWN]
        failing = [d.name for d in self.dimensions if d.status == FAIL]
        if unknown:
            return HOLD          # unverifiable is not publishable
        if failing:
            return FAIL
        if self.total < THRESHOLD:
            return HOLD
        return PASS

    def as_dict(self) -> dict:
        return {
            "product": self.product,
            "verdict": self.decide(),
            "total": self.total,
            "max": self.max_total,
            "threshold": THRESHOLD,
            "critical_defects": self.critical_defects,
            "dimensions": [
                {"name": d.name, "earned": d.earned, "max": d.max_points,
                 "status": d.status, "evidence": d.evidence}
                for d in self.dimensions
            ],
            "note": ("a high score never cancels an open critical defect; "
                     "UNKNOWN is not a pass"),
        }


# --- dimension builders ----------------------------------------------------
def dim_files(results: list) -> Dimension:
    """
    File completeness and usability, 25 points, earned proportionally to the
    fraction of files that PASS. An UNKNOWN file counts as neither earned nor
    lost -- it drags the status to UNKNOWN so the product cannot ship on it.
    """
    d = Dimension("file_completeness_and_usability", 25)
    if not results:
        d.status = UNKNOWN
        d.evidence.append("no files were tested")
        return d
    total = len(results)
    passed = sum(1 for r in results if r.status == PASS)
    unknown = sum(1 for r in results if r.status == UNKNOWN)
    failed = sum(1 for r in results if r.status == FAIL)
    d.evidence.append(f"{passed}/{total} files PASS, {failed} FAIL, {unknown} UNKNOWN")
    for r in results:
        if r.status != PASS:
            d.evidence.append(f"{Path(r.path).name if False else r.path.split(chr(92))[-1]}"
                              f": {r.status} {r.problems[:1]}")
    if unknown:
        d.status = UNKNOWN
        d.earned = round(25 * passed / total)
        return d
    d.status = PASS if failed == 0 else FAIL
    d.earned = round(25 * passed / total)
    return d


def dim_accuracy(content_result, grounding_result) -> Dimension:
    """
    Accuracy and sources, 25. A fabricated legal citation is disqualifying on
    its own; it cannot be offset by a perfect file score elsewhere.
    """
    d = Dimension("accuracy_and_sources", 25)
    critical = []
    if content_result is not None:
        critical = [f for f in content_result.findings
                    if f.severity == "CRITICAL"]
    if grounding_result is not None and grounding_result.violations:
        critical = critical or [type("V", (), {"evidence": v})()
                                for v in grounding_result.violations]

    if critical:
        d.status = FAIL
        d.earned = 2
        rules = sorted({getattr(f, "rule", "UNGROUNDED") for f in critical})
        d.evidence.append(f"{len(critical)} critical defect(s): {rules}")
        return d
    if content_result is None:
        d.status = UNKNOWN
        d.evidence.append("content was never checked")
        return d
    d.status = PASS
    d.earned = 25
    d.evidence.append("no fabricated citation, no ungrounded regulatory claim")
    return d


def dim_practical_value(word_stats: dict) -> Dimension:
    """
    Practical value and customer fit, 20. Driven by real measurements: median
    chapter length, and whether a workbook actually computes.
    """
    d = Dimension("practical_value_and_customer_fit", 20)
    median_words = word_stats.get("median_chapter_words")
    zero_formula = word_stats.get("workbooks_without_formulas", 0)
    total_wb = word_stats.get("workbooks_tested", 0)
    if median_words is None and total_wb == 0:
        d.status = UNKNOWN
        d.evidence.append("no usable value signal was measured")
        return d
    ev, score = [], 0
    if median_words is not None:
        ev.append(f"median chapter {median_words} words")
        score += min(12, round(12 * median_words / 300))
    if total_wb:
        ev.append(f"{zero_formula}/{total_wb} workbooks ship with zero formulas")
        score += round(8 * (total_wb - zero_formula) / total_wb) if total_wb else 0
    d.evidence = ev
    d.earned = score
    d.status = PASS if score >= 14 else (HOLD if score >= 8 else FAIL)
    return d


def dim_verification(test_summary: dict) -> Dimension:
    """
    Independent verification, 15. Docked for missing automated coverage AND
    for the absence of any human review -- which is a real gap, not a
    formality, for a compliance product.
    """
    d = Dimension("independent_verification_and_tests", 15)
    covered = test_summary.get("files_independently_tested", 0)
    required = test_summary.get("files_required", 0)
    human = test_summary.get("human_specialist_review", False)
    ev = [f"{covered}/{required} files independently tested"]
    if not human:
        ev.append("no qualified human specialist review")
    d.evidence = ev
    if required and covered < required:
        d.status = UNKNOWN
        d.earned = round(10 * covered / required)
        return d
    d.earned = 10 if human else 5
    d.status = HOLD if not human else PASS
    return d


def dim_presentation(page_result) -> Dimension:
    """
    Commercial presentation and description accuracy, 15. Every marketing
    claim must map to evidence inside the product. An unmatched claim is not
    a style problem; it is the defect product_claim_integrity.py exists for.
    """
    d = Dimension("commercial_presentation_and_accuracy", 15)
    if page_result is None:
        d.status = UNKNOWN
        d.evidence.append("sales page was never matched against the product")
        return d
    unmatched = page_result.get("unmatched_claims", [])
    d.evidence.append(f"{len(unmatched)} unmatched sales-page claim(s)")
    if unmatched:
        d.status = FAIL
        d.earned = max(0, 15 - 5 * len(unmatched))
        d.evidence.extend(str(c)[:80] for c in unmatched[:3])
        return d
    d.status = PASS
    d.earned = 15
    d.evidence.append("every claim matched to in-product evidence")
    return d


def build_scorecard(product: str, *, file_results, content_result,
                    grounding_result, word_stats, test_summary,
                    page_result, critical_defects=None) -> Scorecard:
    sc = Scorecard(product=product, critical_defects=list(critical_defects or []))
    sc.dimensions = [
        dim_files(file_results),
        dim_accuracy(content_result, grounding_result),
        dim_practical_value(word_stats),
        dim_verification(test_summary),
        dim_presentation(page_result),
    ]
    return sc


from pathlib import Path  # noqa: E402  (used in dim_files evidence formatting)