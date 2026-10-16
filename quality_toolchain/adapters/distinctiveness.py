# -*- coding: utf-8 -*-
"""Isolated adapter: measured distinctiveness of a product text vs. one or
more reference texts ("free documented alternative" packs, competitors).

Purpose (Gap 2): prove a newly generated product's text is genuinely
distinctive from already-documented free packs listed in MARKET_VALIDATION
_PROMPT_PACK_REPORT / QUALITY_TOOLING_OPTIONS_REPORT, rather than an
unstructured re-arrangement of the same content.

Method (pure Python stdlib, deterministic, Windows-clean):
  - document overlap = Jaccard index over normalized word sets between the
    candidate and each reference.
  - longest-common-substring proximity = length of the longest shared
    character n-gram run / length of the candidate, as a *structural*
    reuse guard (Jaccard alone misses contiguous copy-paste inside longer
    texts).

Contract:
  check_distinctiveness(candidate, references, max_overlap=0.5,
                        max_lcs_ratio=0.25) -> dict with status/result.

  - status "ok" -> structure {"overlaps": [ {ref_label, jaccard, lcs_ratio} ],
                              "max_overlap", "max_lcs_ratio", "passed"}
      passed True  iff all overlaps <= max_overlap AND all lcs_ratio
                   <= max_lcs_ratio
      passed False iff any reference exceeds either guard
  - references may be a list of strings OR list of {label, text}.
  - empty references -> passed True with overlap=0 (nothing to compare
    against; the caller decides whether that is enough).

Fail-closed: any exception resolves to status "error" and passed=False.
"""

import re
import time

from .. import normalization as _norm


def _tokens(text):
    return set(re.findall(r"[^\W0-9_]+", str(text).lower()))


def _ngrams(text, n=3):
    s = re.sub(r"\s+", "", str(text).lower())
    return set(s[i:i + n] for i in range(len(s) - n + 1)) if len(s) >= n else set()


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _contamination_ratio(candidate_tokens, reference_tokens):
    """DERIVED additive signal (does not affect `passed`): fraction of the
    reference's own token set that also appears in the candidate. Unlike the
    Jaccard-overlap (which is diluted by a long candidate's many extra
    tokens), this cost-amplifier is not diluted by candidate length, so it
    better catches a long near-duplicate that embeds/reorders much of a short
    reference. Reported as evidence only; not used in the pass/fail gate."""
    if not reference_tokens:
        return 0.0
    return len(candidate_tokens & reference_tokens) / len(reference_tokens)


def _lcs_ratio(candidate, reference):
    """Structural copy-paste guard: fraction of candidate's length covered by
    the longest character substring shared with the reference (lower is more
    distinctive). Uses difflib.SequenceMatcher over the two strings."""
    import difflib
    c = str(candidate)
    if not c:
        return 0.0
    sm = difflib.SequenceMatcher(None, c, str(reference), autojunk=False)
    longest = 0
    for a0, _, a1 in sm.get_matching_blocks():
        longest = max(longest, a1 - a0)
    return longest / len(c)


def check_distinctiveness(candidate, references, max_overlap=0.5,
                          max_lcs_ratio=0.25, max_contamination=0.5,
                          paths_to_avoid=None, enable_lcs=True,
                          max_lcs_chars=20000, lcs_timeout_s=None,
                          normalize=True, product_type=None,
                          norm_version=None):
    """Measured distinctiveness of a candidate vs references.

    FOUNDER-APPROVED roles (2026-09-02):
      PRIMARY distinctiveness signal for long-text reuse detection =
      contamination_ratio (not diluted by candidate length).
      SECONDARY / comparative = Jaccard overlap.
      LCS ratio = structural copy-paste guard, NOT part of the cheap default
      pass decision for long products.

    Fail-safe on unavailable/expensive secondary detectors:
      - If enable_lcs=False, OR the candidate/reference exceed max_lcs_chars
        (expensive LCS on long text, observed 63.65s on a 20,951-char product),
        OR LCS exceeds lcs_timeout_s, then LCS is NOT computed.
      - In that case `lcs_unavailable=True` and `lcs_reason` explains why.
      - A timeout/unavailable LCS NEVER yields an automatic QUALITY PASS:
        `passed` is set based ONLY on the checks that actually ran (jaccard +
        contamination), and a top-level `verdict` is emitted as
        "REVIEW" (not a clean pass) whenever the structural guard could not
        run. Callers must treat `passed=True` with `lcs_unavailable=True` +
        `verdict="REVIEW"` as ADVISORY ONLY, never as proof of clean quality.

    Normalization:
      - normalize=True discounts declared factory-standard boilerplate from
        both candidate and reference token sets before contamination/jaccard
        (see normalization.py). Removals are auditable and versioned.
      - A separate `normalization_audit` field reports what was removed.
        Raw (un-normalized) contamination is always kept alongside.

    Returns: dict with status/result, additive fields for the new roles.
    """
    try:
        if references is None:
            references = []
        normalized = []
        for i, ref in enumerate(references):
            if isinstance(ref, dict):
                normalized.append((ref.get("label", f"ref{i}"), ref.get("text", "")))
            else:
                normalized.append((f"ref{i}", str(ref)))

        cand_tokens = _tokens(candidate)
        cand_ngrams = _ngrams(candidate)
        normalization_audit = None
        if normalize:
            cand_norm = _norm.normalize_tokens(cand_tokens, product_type, norm_version)
            cand_tokens = cand_norm["tokens"]
            cand_ngrams = cand_ngrams & cand_norm["tokens"] if cand_ngrams else cand_ngrams
            normalization_audit = _norm.audit_report(
                cand_tokens, set(), product_type, norm_version)

        overlaps = []
        cand_len = len(str(candidate))
        for label, text in normalized:
            ref_tokens = _tokens(text)
            ref_ngrams = _ngrams(text)
            if normalize:
                ref_norm = _norm.normalize_tokens(ref_tokens, product_type, norm_version)
                ref_tokens = ref_norm["tokens"]
                ref_ngrams = ref_ngrams & ref_norm["tokens"] if ref_ngrams else ref_ngrams
                if normalization_audit is not None:
                    normalization_audit["reference"].setdefault("raw_count", len(ref_tokens))
            ref_len = len(str(text))
            jac = max(
                _jaccard(cand_tokens, ref_tokens),
                _jaccard(cand_ngrams, ref_ngrams),
            )
            # LCS is the expensive guard. Guard it by size + timeout.
            lcs = None
            lcs_reason = None
            size_ok = (max_lcs_chars is None) or (
                cand_len + ref_len <= max_lcs_chars)
            if enable_lcs and size_ok:
                try:
                    if lcs_timeout_s:
                        start = time.time()
                        lcs = _lcs_ratio(candidate, text)
                        if time.time() - start > lcs_timeout_s:
                            lcs = None
                            lcs_reason = f"lcs_timeout>{lcs_timeout_s}s"
                    else:
                        lcs = _lcs_ratio(candidate, text)
                except Exception as e:  # noqa: BLE001
                    lcs = None
                    lcs_reason = f"lcs_error:{e}"
            elif enable_lcs and max_lcs_chars is not None and \
                    cand_len + ref_len > max_lcs_chars:
                lcs_reason = f"lcs_skipped_size>{max_lcs_chars}chars"
            elif not enable_lcs:
                lcs_reason = "lcs_disabled"

            contam_raw = _contamination_ratio(cand_tokens, ref_tokens)
            contam_norm = contam_raw
            overlaps.append({"ref": label, "jaccard": round(jac, 4),
                             "lcs_ratio": None if lcs is None else round(lcs, 4),
                             "lcs_unavailable": lcs is None,
                             "lcs_reason": lcs_reason,
                             "contamination_ratio": round(contam_norm, 4),
                             "contamination_ratio_raw": round(contam_raw, 4)})

        if not normalized:
            return {"status": "ok", "passed": True, "max_overlap": 0.0,
                    "max_lcs_ratio": 0.0, "max_contamination": 0.0,
                    "lcs_unavailable": False, "overlaps": [],
                    "verdict": "PASS" if enable_lcs else "REVIEW",
                    "normalization_audit": normalization_audit,
                    "signal_roles": {
                        "primary": "contamination_ratio",
                        "secondary": "jaccard",
                        "structural_guard": "lcs_ratio",
                    },
                    "threshold_info": "no_references"}

        max_o = max(o["jaccard"] for o in overlaps)
        max_l = max((o["lcs_ratio"] for o in overlaps if o["lcs_ratio"] is not None),
                    default=0.0)
        max_c = max(o["contamination_ratio"] for o in overlaps)
        max_c_raw = max(o["contamination_ratio_raw"] for o in overlaps)
        any_lcs_unavailable = any(o["lcs_unavailable"] for o in overlaps)
        ran_lcs = [o for o in overlaps if o["lcs_ratio"] is not None]

        # PRIMARY distinctiveness = contamination_ratio (long-text reuse).
        primary_pass = max_c <= max_contamination
        # SECONDARY / comparative = Jaccard overlap.
        secondary_pass = max_o <= max_overlap
        # Structural LCS guard: a measured ratio above cap is a definite
        # rejection signal. Unavailable LCS is NOT a pass and NOT a fail — it
        # means "structural cleanliness is NOT confirmed".
        structural_pass = bool(ran_lcs) and all(
            o["lcs_ratio"] <= max_lcs_ratio for o in ran_lcs
        ) if ran_lcs else False
        structural_confirmed = bool(ran_lcs) and structural_pass

        # FOUNDER RULE: lcs_unavailable / timeout / failure MUST NEVER become a
        # QUALITY PASS. `passed` therefore requires primary + secondary AND a
        # CONFIRMED clean structural guard. If LCS did not run (disabled, size
        # limit, or timeout), structural cleanliness is unconfirmed, so `passed`
        # is False and the verdict is REVIEW (advisory) — never an automatic
        # clean pass from an unavailable detector.
        passed = primary_pass and secondary_pass and structural_confirmed

        if any_lcs_unavailable:
            verdict = "REVIEW"          # structural guard unavailable
        elif not (primary_pass and secondary_pass):
            verdict = "REVIEW"          # measurable distinctiveness failure
        elif not structural_confirmed and ran_lcs and not structural_pass:
            verdict = "REVIEW"          # measured structural failure
        else:
            verdict = "PASS"            # all confirmed checks passed with the
                                        # structural guard present

        checks = {
            "primary_contamination": primary_pass,
            "secondary_jaccard": secondary_pass,
            "structural_lcs": structural_pass if ran_lcs else None,
        }
        return {"status": "ok", "passed": passed,
                "checks": checks,
                "max_overlap": round(max_o, 4),
                "max_lcs_ratio": round(max_l, 4),
                "max_contamination": round(max_c, 4),
                "max_contamination_raw": round(max_c_raw, 4),
                "lcs_unavailable": any_lcs_unavailable,
                "lcs_reasons": sorted({o["lcs_reason"] for o in overlaps if o["lcs_reason"]}),
                "primary_signal": {"name": "contamination_ratio",
                                   "value": round(max_c, 4), "passed": primary_pass},
                "secondary_signal": {"name": "jaccard",
                                     "value": round(max_o, 4), "passed": secondary_pass},
                "signal_roles": {
                    "primary": "contamination_ratio",
                    "secondary": "jaccard",
                    "structural_guard": "lcs_ratio",
                },
                "verdict": verdict,
                "advisory": verdict == "REVIEW",
                "normalization_audit": normalization_audit,
                "overlaps": overlaps,
                "threshold_info": (
                    f"max_overlap<={max_overlap},max_lcs<={max_lcs_ratio}"
                    f",max_contamination<={max_contamination}; "
                    f"CALIBRATED FOR THE AVAILABLE BENCHMARK, NOT A UNIVERSAL "
                    f"QUALITY THRESHOLD")}
    except Exception as e:
        return {"status": "error", "passed": False,
                "threshold_info": f"error:{e}", "overlaps": []}