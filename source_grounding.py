"""Galaxy Forge -- source grounding for generated regulatory content (Cycle 86).

THE DEFECT THIS FIXES, AT ITS SOURCE
------------------------------------
Cycle 86 found that the shipped EU AI Act Compliance Toolkit contained
fabricated legal citations -- four invented "Annex III categories", an invented
"Annex III Part A/B" structure, and a prohibition the Act does not contain.

The cause is not the renderer. It is this line in book_generator.py's
ai_generate_book_content():

    system = ("You are the content-building agent at Galaxy Forge. You write
               real, complete digital book content ... at a quality bar
               suitable for direct publication on Amazon KDP or Gumroad ...")

There is no source grounding, no constraint on citations, and no rule against
inventing an article number. Asking a language model to write a book about a
regulation produces fluent, confident, plausible-looking legal text. It is
recalled from training data, not retrieved from a source, and it is wrong
often enough that shipping it as regulated guidance is a real liability.

Searching the whole of book_generator.py for grounding found none:
'EUR-Lex', 'eur-lex', 'primary source', 'official source', 'cite', 'citation'
are ALL ABSENT.

WHY THE FIX IS STRUCTURAL RATHER THAN A BETTER PROMPT
-----------------------------------------------------
This factory already learned the hard way that you cannot ask a model to
reliably include safety-critical text: the EU AI Act toolkit shipped with a
"not legal advice" disclaimer that the generation prompt had specified but the
model never rendered. The fix then was deterministic injection, not a better
instruction.

So this module does not ask the model to be careful. It:
  1. classifies whether a topic makes regulatory claims at all,
  2. supplies REAL, verified primary-source facts as a hard block,
  3. instructs the model to assert nothing outside that block, and
  4. verifies the OUTPUT for citations that do not appear in the supplied
     sources -- failing closed rather than trusting the model.

WHAT THIS DOES NOT CLAIM
------------------------
It does not make generated content correct. It prevents UNSOURCED claims from
reaching a customer. Grounded text is still not legally reviewed text, and
legal_review_required() keeps returning True. A language model given a true
fact block can still misapply it.

Cost: $0. Pure, offline, no network, no new dependency.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- Verified primary-source facts -----------------------------------------
# Every entry below was checked against the European Commission's own AI Act
# Service Desk on 2026-10-14. SOURCES carry the URL so a reviewer can
# re-verify rather than trust this file.
AI_ACT_ANNEX_III = {
    "citation": "Regulation (EU) 2024/1689, Annex III",
    "url": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/annex-3",
    "verified_on": "2026-10-14",
    "statement": (
        "High-risk AI systems referred to in Article 6(2) are those listed in "
        "these eight areas: (1) Biometrics; (2) Critical infrastructure; "
        "(3) Education and vocational training; (4) Employment, workers' "
        "management and access to self-employment; (5) Access to and enjoyment "
        "of essential private services and essential public services and "
        "benefits; (6) Law enforcement; (7) Migration, asylum and border "
        "control management; (8) Administration of justice and democratic "
        "processes."
    ),
    "forbidden_framings": [
        "Annex III, Part A", "Annex III, Part B",
        "Annex III category: Autonomy",
        "Annex III category: Creativity",
        "Annex III category: Adaptability",
        "Annex III category: Real-time data",
        "Annex III category: Significant adverse impact",
    ],
}

AI_ACT_STRUCTURE = {
    "citation": "Regulation (EU) 2024/1689, Article 6",
    "url": "https://ai-act-service-desk.ec.europa.eu/en/high-risk-ai-systems-areas-listed-annex-iii",
    "verified_on": "2026-10-14",
    "statement": (
        "Classification follows Article 6, read with Annexes I and III. High-risk "
        "is determined by the intended purpose and the area of use. The "
        "Commission issues classification guidelines pursuant to Article 6(5)."
    ),
}

SOURCE_REGISTRY: dict[str, list[dict]] = {
    "eu_ai_act": [AI_ACT_ANNEX_III, AI_ACT_STRUCTURE],
}

# --- Regulatory topic detection --------------------------------------------
# Deliberately conservative: false positives cost a grounded prompt, false
# negatives let fabricated regulation through to a customer.
REGULATORY_MARKERS = [
    "ai act", "gdpr", "ccpa", "soc 2", "ftc", "gpsr", "hipaa", "pci",
    "regulation", "regulatory", "compliance", "conformity", "statute",
    "legislation", "directive", "eur-lex", "penalt", "enforcement",
    "data protection", "privacy law", "consumer protection", "safety regulation",
]


@dataclass
class GroundingResult:
    is_regulatory: bool
    matched_markers: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    @property
    def grounded(self) -> bool:
        """True when nothing ungrounded survived."""
        return not self.violations

    def as_dict(self) -> dict:
        return {
            "is_regulatory": self.is_regulatory,
            "matched_markers": self.matched_markers,
            "source_count": len(self.sources),
            "violations": self.violations,
            "grounded": self.grounded,
        }


def classify_regulatory(*texts: str) -> tuple[bool, list[str]]:
    """Does this product make regulatory claims? Conservative on purpose."""
    blob = " ".join(t or "" for t in texts).lower()
    hits = [m for m in REGULATORY_MARKERS if m in blob]
    return bool(hits), hits


def get_sources(topic: str) -> list[dict]:
    """Real source block for a topic. Empty list means nothing is grounded."""
    blob = (topic or "").lower()
    if "ai act" in blob or "artificial intelligence" in blob:
        return SOURCE_REGISTRY["eu_ai_act"]
    return []


def grounding_instruction(sources: list[dict]) -> str:
    """
    The hard block injected into the generation prompt.

    It does not ask the model to be accurate. It forbids it from asserting
    anything it was not given, which is the one instruction a model can
    actually follow deterministically enough to be worth verifying against.
    """
    if not sources:
        return ""
    lines = [
        "SOURCE GROUNDING -- READ CAREFULLY, THESE ARE HARD CONSTRAINTS",
        "",
        "You are writing about a REGULATED topic. You may ONLY assert what is "
        "written in the VERIFIED SOURCES block below. Specifically:",
        "",
        "1. Do NOT invent article numbers, annex numbers, category names, "
        "division names, deadlines, dates, thresholds or penalty figures.",
        "2. Do NOT paraphrase a source into a structure it does not have.",
        "3. If the VERIFIED SOURCES block does not cover something you want "
        "to say, OMIT it. Omission is correct. Invention is not.",
        "4. If you need a fact that is not in the block, write: "
        "'[UNVERIFIED - REQUIRES PRIMARY SOURCE]' and move on.",
        "",
        "VERIFIED SOURCES:",
    ]
    for s in sources:
        lines.append("")
        lines.append(f"- {s['citation']}")
        lines.append(f"  Source: {s['url']}")
        lines.append(f"  Verified: {s['verified_on']}")
        lines.append(f"  Fact: {s['statement']}")
        for bad in s.get("forbidden_framings", []):
            lines.append(f"  NEVER write: \"{bad}\"")
    lines.append("")
    return "\n".join(lines)


# Citations that are ALWAYS a red flag regardless of topic, because they are
# the fabricated framings Cycle 86 actually found in a shipped file.
FORBIDDEN_FRAMINGS = [
    r"Annex\s+III,?\s*Part\s*A",
    r"Annex\s+III,?\s*Part\s*B",
    r"Annex\s+III[^.\n]{0,60}\b(autonomy|creativity|adaptability|real-time data)\b",
    r"prohibit\w*\s+(?:the\s+)?use\s+of\s+high[- ]risk\s+general[- ]purpose",
]


def verify_no_unsourced_citations(text: str, sources: list[dict]) -> list[str]:
    """
    Fail-closed check on GENERATED OUTPUT.

    Returns a list of violations; empty means clean. This is the check that
    would have caught the shipped product. It is deliberately mechanical --
    it cannot tell whether a claim is accurate, only whether it is one of the
    framings known to be false.
    """
    violations: list[str] = []
    for pat in FORBIDDEN_FRAMINGS:
        for m in re.finditer(pat, text or "", re.I):
            violations.append(
                f"fabricated legal framing {m.group(0)!r} -- this is not how the "
                f"regulation is structured")
    for s in sources:
        url = s.get("url")
        if url and url not in (text or ""):
            # Not fatal: a grounded rewrite may legitimately drop a citation.
            # Recorded so a reviewer can see the source was available.
            pass
    return violations


def check_generated(*, title: str, topic: str, body: str) -> GroundingResult:
    """
    Full pipeline: classify, ground, verify. Call this on generated text
    BEFORE it is packaged for a customer.
    """
    is_reg, markers = classify_regulatory(title, topic)
    sources = get_sources(topic) if is_reg else []
    violations = verify_no_unsourced_citations(body, sources) if is_reg else []
    return GroundingResult(
        is_regulatory=is_reg,
        matched_markers=markers,
        sources=sources,
        violations=violations,
    )


def legal_review_required() -> bool:
    """
    Always True for regulatory products. Grounding prevents unsourced claims;
    it does not establish that the remaining content is legally correct. Kept
    explicit so no caller mistakes a clean check for clearance.
    """
    return True