# -*- coding: utf-8 -*-
"""Distinctiveness NORMALIZATION layer (FOUNDER APPROVED 2026-09-02).

Purpose: contamination_ratio is the PRIMARY distinctiveness signal for long-text
reuse detection. A measured false-positive was recorded on the real-product
benchmark: comparing a long flagship product against small near-empty template
siblings inflated contamination because their token set was dominated by shared
factory-standard TOC/chapter boilerplate. This module removes or DISCOUNTS that
known boilerplate BEFORE the contamination/jaccard token sets are formed, so the
scoring reflects substantive content reuse rather than shared template chrome.

Hard rules honored verbatim from the founder decision:
  - This layer ONLY removes *known, declared* boilerplate/templates — NEVER
    arbitrary text merely to improve a score.
  - The rules are EXPLICIT, VERSIONED, TESTABLE, AUDITABLE, PRODUCT-TYPE AWARE.
  - Every removal is auditable: the returned record reports exactly what tokens
    were removed from each side and why, so nothing happens invisibly.

Contract:
  normalize_tokens(tokens:set[str], product_type:str|None, version:str=None)
      -> {"tokens": set[str], "removed": [ {token-ish evidence} ],
          "rule_name", "rule_version", "product_type",
          "removed_count", "kept_count"}

  discounted vs hard-removed:
    - removed_tokens   : tokens explicitly declared as boilerplate are dropped
                         from BOTH candidate and reference token sets (shared
                         count is recomputed without them).
    - NOTE: we report both the raw (un-normalized) contamination and the
      normalized contamination so the auditor can always see the effect.
"""
import re

NORMALIZATION_VERSION = "1.0.0"


# Factory-standard structural boilerplate tokens observed in the real-product
# benchmark reference PDFs (shared TOC / chapter skeleton / template chrome).
# These are EXPLICIT, NOT arbitrary: each entry is a concrete token (or a very
# narrow, deliberate phrase regex) that appeared in real factory reference
# products' standardized skeleton. Derived from the real-product benchmark
# boilerplate diagnostic (tokens shared by >=2 of the 6 real references).
# Derivation: DERIVED.
DEFAULT_BOILERPLATE_TOKENS = {
    "table", "of", "contents", "what", "s", "inside", "chapter",
    "overview", "getting", "started", "feature", "reference", "setup",
    "configuration", "faq", "troubleshooting", "support", "next", "steps",
    "the", "a", "an", "this", "and", "for", "with", "that", "to", "in",
}

# Product-type aware: additional boilerplate is fine to declare per product type.
# Empty by default; audience shall be extended explicitly + versioned.
_PRODUCT_TYPE_EXTRA = {}


def _boilerplate_for(product_type):
    """FK policy: base boilerplate + product-type-specific extra tokens (never
    arbitrary; defined explicitly and versioned)."""
    return DEFAULT_BOILERPLATE_TOKENS | set(_PRODUCT_TYPE_EXTRA.get(product_type or "", ()))


def normalize_tokens(tokens, product_type=None, rule_version=None):
    """Return the normalized token set plus an auditable removal record.

    Discount strategy: tokens in the declared boilerplate set are HARD-removed
    (they carry no distinctiveness information because they are factory
    standard chrome). To stay honest and auditable, we do NOT invent a
    heuristic; we only strip an explicit, versioned whitelist of boilerplate
    and we REPORT exactly what was stripped."""
    version = rule_version or NORMALIZATION_VERSION
    boiler = _boilerplate_for(product_type)
    removed = sorted(tokens & boiler)
    kept = tokens - boiler
    removed_evidence = [
        {"token": t, "why": "factory_standard_boilerplate",
         "rule_version": version, "product_type": product_type or "unknown"}
        for t in removed
    ]
    return {
        "tokens": kept,
        "removed": removed_evidence,
        "rule_name": "factory_standard_boilerplate_discount",
        "rule_version": version,
        "product_type": product_type or "unknown",
        "removed_count": len(removed),
        "kept_count": len(kept),
    }


def audit_report(candidate_tokens, reference_tokens, product_type=None,
                 rule_version=None):
    """Produce an auditable snapshot used by the distinctiveness adapter:
    before/after counts + removed-token evidence, so normalization is never
    invisible. Returns a dict suitable for inclusion in a verdict record."""
    cand_norm = normalize_tokens(candidate_tokens, product_type, rule_version)
    ref_norm = normalize_tokens(reference_tokens, product_type, rule_version)
    return {
        "normalization_version": cand_norm["rule_version"],
        "product_type": cand_norm["product_type"],
        "candidate": {
            "raw_count": len(candidate_tokens),
            "normalized_count": len(cand_norm["tokens"]),
            "removed_evidence": cand_norm["removed"][:200],
        },
        "reference": {
            "raw_count": len(reference_tokens),
            "normalized_count": len(ref_norm["tokens"]),
            "removed_evidence": ref_norm["removed"][:200],
        },
    }