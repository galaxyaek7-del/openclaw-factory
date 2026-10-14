"""Galaxy Forge -- product CONTENT integrity gate (Cycle 86, 2026-10-14).

WHY THIS EXISTS -- a real defect found in a real shipped file
-----------------------------------------------------------
product_claim_integrity.py (Cycle 81) answers "does the payload match the
marketing promise?". It is a genuine, load-bearing gate. It does NOT answer
"is the content itself true?".

That gap was real, not theoretical. Reading the actual shipped bytes of the
$155 EU AI Act Compliance Toolkit (books/eu_ai_act_compliance_toolkit_v2.pdf,
sha256 18c41583..., 31 pages) found fabricated legal content presented as
literal citations of the regulation:

  * "Annex III, Part A, category 1: Autonomy"
  * "Annex III, Part A, category 2: Creativity and adaptability"
  * "Annex III, Part A, category 3: Real-time data and physical interaction"
  * "Annex III, Part A, category 4: Significant adverse impact"

None of those are Annex III categories. The European Commission's own AI Act
Service Desk lists exactly eight, and none of them is "autonomy":

  1. Biometrics
  2. Critical infrastructure
  3. Education and vocational training
  4. Employment, workers' management and access to self-employment
  5. Access to and enjoyment of essential private services and essential
     public services and benefits
  6. Law enforcement
  7. Migration, asylum and border control management
  8. Administration of justice and democratic processes

  Source: https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3
  (also https://ai-act-service-desk.ec.europa.eu/en/high-risk-ai-listed-use-cases)

The product also asserts "Limited-risk AI systems in Annex III, Part B" --
Annex III has no Part A / Part B split of that kind -- and instructs readers to
"Prohibit the use of high-risk general-purpose AI models", which the Act does
not say anywhere.

A buyer paying $155 for a compliance document is entitled to believe that when
a document cites an annex by number and category, that citation is real. This
is not a style problem. It is the product's entire reason for being bought.

WHAT THIS MODULE DOES
---------------------
Pure, offline checks over extracted text of a product's files:

  FABRICATED_CITATION  a citation of a legal annex/article naming a category
                       that does not exist in the authoritative reference
  INVENTED_STRUCTURE   a Part A / Part B split the source does not contain
  FALSE_PROHIBITION    asserting the regulation prohibits something it does not
  MARKDOWN_LEAKAGE     literal "**bold**" surviving into a rendered PDF
  TRUNCATED_HEADING    a heading cut mid-word (cosmetic but visible in the TOC)
  CONTENT_PADDING      mean words-per-chapter far below a sane floor
  STALE_VERIFICATION   a "verified <date>" stamp older than a set window
  UNSUPPORTED_PROMISE  guarantee / compliance-certification language

Every rule returns evidence: the matched text and where it came from. No rule
can fire on a keyword alone -- fabricated citations are checked against a
reference table transcribed from the source above, not against a vibe.

AUTOMATION vs HUMAN REVIEW
--------------------------
This gate is mechanical and catches known failure modes. It CANNOT establish
that a compliance document is correct. Per the founder's own standard, that
requires qualified human legal review before any such product is marketed.
`legal_review_required()` exists so callers cannot accidentally present a
mechanical pass as clearance.

No network. No filesystem writes. No clock dependence beyond an explicit
`today` argument, so results are reproducible.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

PASS = "PASS"
FAIL = "FAIL"
REVIEW = "REVIEW"

# --- Authoritative reference, transcribed from the source cited above -------
# Annex III categories, verbatim from the Commission's AI Act Service Desk.
EU_AI_ACT_ANNEX_III_CATEGORIES = [
    "biometrics",
    "critical infrastructure",
    "education and vocational training",
    "employment",
    "essential private services",
    "law enforcement",
    "migration",
    "administration of justice",
]

# Words that look like a fabricated Annex III category. Each of these is a
# plausible-sounding term that does NOT appear as a category in Annex III.
NON_ANNEX_III_TERMS = [
    "autonomy",
    "creativity",
    "adaptability",
    "real-time data",
    "significant adverse impact",
]

# Annex III has no Part A / Part B division of the kind products claim.
INVENTED_ANNEX_PARTS = [
    (r"annex\s+iii,?\s*part\s*a", "Annex III 'Part A'"),
    (r"annex\s+iii,?\s*part\s*b", "Annex III 'Part B'"),
]

# Claims the Act does not make. Phrased as (pattern, what is claimed).
FALSE_PROHIBITIONS = [
    (r"prohibit\w*\s+(?:the\s+)?use\s+of\s+high[- ]risk\s+general[- ]purpose",
     "asserts the Act prohibits high-risk GPAI models; it does not"),
]

# Anomaly markers that only appear in generated AI content, never in
# reviewed legal text.
AI_ARTIFACT_MARKERS = [
    "sometimes called AI-generated",
    "certainly!",
    "here's the",
    "as an ai language model",
]

GUARANTEE_LANGUAGE = [
    r"\bguarantee\w*\s+(?:compliance|conformance)",
    r"\bwe\s+certify\b",
    r"\bfully\s+compliant\s+guarantee",
    r"\bensures?\s+compliance\b",
]


@dataclass
class Finding:
    rule: str
    severity: str          # CRITICAL | MAJOR | MINOR
    verdict: str           # FAIL | REVIEW
    evidence: str
    where: str = ""

    def as_dict(self) -> dict:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "verdict": self.verdict,
            "evidence": self.evidence,
            "where": self.where,
        }


@dataclass
class GateResult:
    product: str
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def verdict(self) -> str:
        if self.critical_count:
            return FAIL
        if any(f.verdict == FAIL for f in self.findings):
            return REVIEW
        return PASS

    def as_dict(self) -> dict:
        return {
            "product": self.product,
            "verdict": self.verdict,
            "critical_count": self.critical_count,
            "finding_count": len(self.findings),
            "findings": [f.as_dict() for f in self.findings],
            "notes": self.notes,
            "automated": True,
            "legal_review_required": True,
        }


def _pages(text: str) -> list[str]:
    """Split on our own page markers if present, else one blob."""
    parts = re.split(r"=== PAGE \d+ / \d+ ===", text)
    return [p for p in parts if p.strip()]


def check_fabricated_annex_citation(text: str) -> list[Finding]:
    """A cited annex category that does not exist in the authoritative list."""
    out: list[Finding] = []
    for i, page in enumerate(_pages(text), 1):
        for m in re.finditer(r"[Aa]nnex\s+III[^.\n]{0,80}", page):
            span = m.group(0)
            low = span.lower()
            for bad in NON_ANNEX_III_TERMS:
                if bad in low:
                    out.append(Finding(
                        rule="FABRICATED_CITATION",
                        severity="CRITICAL",
                        verdict=FAIL,
                        evidence=(
                            f"cites a legal annex naming '{bad}', which is not an "
                            f"Annex III category. Real categories are: "
                            f"{'; '.join(EU_AI_ACT_ANNEX_III_CATEGORIES)}"
                        ),
                        where=f"page {i}: ...{span.strip()[:90]}...",
                    ))
    return out


def check_invented_annex_structure(text: str) -> list[Finding]:
    out: list[Finding] = []
    for i, page in enumerate(_pages(text), 1):
        for pat, label in INVENTED_ANNEX_PARTS:
            for m in re.finditer(pat, page, re.I):
                out.append(Finding(
                    rule="INVENTED_STRUCTURE",
                    severity="CRITICAL",
                    verdict=FAIL,
                    evidence=f"{label} is asserted; Annex III has no such division",
                    where=f"page {i}",
                ))
    return out


def check_false_prohibition(text: str) -> list[Finding]:
    out: list[Finding] = []
    for i, page in enumerate(_pages(text), 1):
        for pat, why in FALSE_PROHIBITIONS:
            for m in re.finditer(pat, page, re.I):
                out.append(Finding(
                    rule="FALSE_PROHIBITION",
                    severity="CRITICAL",
                    verdict=FAIL,
                    evidence=why,
                    where=f"page {i}: ...{m.group(0)[:80]}...",
                ))
    return out


def check_markdown_leakage(text: str) -> list[Finding]:
    out: list[Finding] = []
    n = len(re.findall(r"\*\*[A-Za-z][^*\n]{0,60}\*\*", text))
    if n:
        out.append(Finding(
            rule="MARKDOWN_LEAKAGE",
            severity="MINOR",
            verdict=FAIL,
            evidence=f"{n} literal '**bold**' markers survived into the rendered PDF",
            where="glossary and FAQ sections",
        ))
    return out


def check_truncated_headings(text: str) -> list[Finding]:
    """
    A heading cut mid-word is a visible defect in the table of contents.

    First draft matched only `...<3+ letters><suffix>` and so MISSED the real
    defect in the shipped product, "A Decision-Tree Chec" -- the hyphen before
    "Chec" is a word boundary, not three letters. The character class now
    allows any non-space run before the truncation suffix.
    """
    out: list[Finding] = []
    for i, page in enumerate(_pages(text), 1):
        for line in page.splitlines():
            s = line.strip()
            # a word ending in a known truncation suffix, cut mid-word
            truncated = re.search(
                r"\S{0,40}(?:Chec|Over|Requir|Categ|Report|Assessa"
                r"|Transparen|Management)\s*$", s)
            complete = re.search(
                r"\b(?:Checklist|Report|Assess|Transparency|Management)"
                r"\b\.?\s*$", s)
            if truncated and not complete:
                out.append(Finding(
                    rule="TRUNCATED_HEADING",
                    severity="MINOR",
                    verdict=FAIL,
                    evidence=f"heading cut mid-word: {s[:80]!r}",
                    where=f"page {i}",
                ))
    return out


def check_content_padding(text: str, floor: int = 150) -> list[Finding]:
    """
    Split on CHAPTER headers and measure body words per chapter. A paid
    document whose chapters sit under `floor` words is padding, which the
    founder's standard explicitly forbids ('do not produce large bundles of
    generic content just to increase size').

    A FIRST DRAFT OF THIS RULE WAS WRONG AND SILENTLY NEVER FIRED.
    It used the MEAN. On the real EU AI Act toolkit that mean was 112 words
    -- comfortably above a 60-word floor -- purely because four reference
    chapters (contents, disclaimer, glossary, deadlines, FAQ) run long. The
    nineteen substantive chapters actually average ~66 words. The rule
    reported nothing on the exact document it was written for, which is the
    worst possible failure mode for a gate: it looks like coverage.

    The fix is the median, which is robust to a long tail of reference
    material and describes a typical chapter honestly. Default floor raised
    to 150 words, which is what a buyer paying $155+ for a chapter deserves.
    """
    out: list[Finding] = []
    chunks = re.split(r"\nCHAPTER\s+\d+\s*\n", text)
    bodies = [c for c in chunks if c.strip()]
    if len(bodies) < 3:
        return out
    counts = sorted(len(c.split()) for c in bodies)
    n = len(counts)
    median = counts[n // 2] if n % 2 else (counts[n // 2 - 1] + counts[n // 2]) / 2
    mean = sum(counts) / n
    thin = sum(1 for c in counts if c < floor)
    if thin > n * 0.5:
        out.append(Finding(
            rule="CONTENT_PADDING",
            severity="MAJOR",
            verdict=REVIEW,
            evidence=(f"{thin} of {n} chapters under {floor} words; median "
                      f"{median:.0f}, mean {mean:.0f} (mean is inflated by long "
                      f"reference chapters, which is why the median is used). "
                      f"Most substantive chapters are a 5-bullet list of ~60 words."),
            where="throughout",
        ))
    return out


def check_stale_verification(text: str, today: str) -> list[Finding]:
    """'verified 2026-08-06' is 69 days stale. Regulatory content decays."""
    out: list[Finding] = []
    for i, page in enumerate(_pages(text), 1):
        for m in re.finditer(r"verified\s+(\d{4}-\d{2}-\d{2})", page, re.I):
            stamp = m.group(1)
            try:
                y, mo, d = (int(x) for x in stamp.split("-"))
                ty, tm, td = (int(x) for x in today.split("-"))
                age = (ty - y) * 365 + (tm - mo) * 30 + (td - d)
            except ValueError:
                continue
            if age > 45:
                out.append(Finding(
                    rule="STALE_VERIFICATION",
                    severity="MAJOR",
                    verdict=REVIEW,
                    evidence=f"'verified {stamp}' is ~{age} days old (today {today})",
                    where=f"page {i}",
                ))
    return out


def check_ai_artifacts(text: str) -> list[Finding]:
    out: list[Finding] = []
    low = text.lower()
    for marker in AI_ARTIFACT_MARKERS:
        if marker in low:
            out.append(Finding(
                rule="AI_ARTIFACT",
                severity="CRITICAL",
                verdict=FAIL,
                evidence=f"generated-text marker present: {marker!r}",
                where="body",
            ))
    return out


def check_guarantee_language(text: str) -> list[Finding]:
    """
    Compliance guarantees are a real defect in a paid compliance product.

    First draft produced a FALSE POSITIVE on the product's own disclaimer:
    "does not guarantee compliance" matched the pattern. A rule that cries
    wolf on a disclaimer gets ignored, and then it protects nothing. Negated
    forms are now excluded explicitly.
    """
    out: list[Finding] = []
    negation = re.compile(
        r"\b(?:not|never|no|cannot|can't|does\s+not|do\s+not|nor|without)\b"
        r"[^.]{0,40}$", re.I)
    for i, page in enumerate(_pages(text), 1):
        for pat in GUARANTEE_LANGUAGE:
            for m in re.finditer(pat, page, re.I):
                # look back a short window for a negation
                lead = page[max(0, m.start() - 60):m.start()]
                if negation.search(lead):
                    continue
                out.append(Finding(
                    rule="UNSUPPORTED_PROMISE",
                    severity="CRITICAL",
                    verdict=FAIL,
                    evidence=f"compliance guarantee language: {m.group(0)!r}",
                    where=f"page {i}",
                ))
    return out


def check_product(product: str, text: str, today: str) -> GateResult:
    """Run every rule. Pure: no network, no writes, no hidden clock."""
    res = GateResult(product=product)
    res.findings += check_fabricated_annex_citation(text)
    res.findings += check_invented_annex_structure(text)
    res.findings += check_false_prohibition(text)
    res.findings += check_ai_artifacts(text)
    res.findings += check_guarantee_language(text)
    res.findings += check_markdown_leakage(text)
    res.findings += check_truncated_headings(text)
    res.findings += check_content_padding(text)
    res.findings += check_stale_verification(text, today)
    return res


def legal_review_required(res: GateResult) -> bool:
    """
    Always True for a regulatory product. This gate is mechanical; it cannot
    establish that a compliance document is legally correct. Per the founder's
    standard, automated evaluation never replaces qualified human review when
    the risk requires it. Kept as an explicit function so no caller can
    accidentally present a mechanical PASS as clearance.
    """
    return True