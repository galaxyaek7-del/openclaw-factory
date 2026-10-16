# -*- coding: utf-8 -*-
"""Isolated adapter: Arabic readability (OSMAN metric) via the `textstat`
Python package.

Purpose (Gap 1): measure Arabic text readability/comprehensibility as a proxy
for the Arabic-naturalness pain documented in MARKET_VALIDATION_PROMPT_PACK
_REPORT.md (users complained of confusing/machine-translated Arabic output).

Contract:
  check_readability(text) -> dict:
      {"passed", "score", "threshold_info", "status", "took_ms"}

  - passed  : score >= configured readability threshold (higher osman score =
               easier/more readable; see OSMAN/Arabic readability semantics).
  - score   : the raw OSMAN readability number from textstat.osman(text).
  - status  : "ok" | "not_available" (textstat missing) | "error" |
              "invalid_input"
  - Failure (not_available/error/invalid_input) ALWAYS yields passed=False —
    a disabled/absent tool must never become a silent PASS.

This adapter is deliberately thin and holds no policy: thresholds come from
the caller/config, and it never writes evidence or makes product decisions.

Windows: textstat is pure Python and confirmed working on this box for
Arabic input (OBSERVED this session).
"""

import time

_ARABIC_RE = None


def _has_arabic(text):
    global _ARABIC_RE
    if _ARABIC_RE is None:
        import re
        _ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
    return bool(_ARABIC_RE.search(str(text or "")))


def _get_osman_fn():
    import textstat
    if not hasattr(textstat, "osman"):
        raise AttributeError("textstat has no osman() (OSMAN Arabic readability)")
    return textstat.osman


def check_readability(text, min_osman_score=None):
    """Return a gate-shaped verdict. Default threshold: a low bar chosen so
    the checker is a *signal*, not a live gate, unless/until benchmark data
    justifies a stricter bar (see FACTORY_QUALITY_TOOLCHAIN_REPORT). Engine
    code treats passed=False as 'readability below bar' and records it; it
    does not auto-reject unless the owning gate so decides."""
    started = time.time()
    if min_osman_score is None:
        # Benchmark-calibrated default (2026-09-02): on the controlled Arabic
        # corpus, threshold 55 gives precision 1.0 / recall 1.0 separating
        # dense (OSMAN ~46-52) from natural (~84-93) texts. 40.0 was measurably
        # too low (recall 0.0) and is intentionally not the default anymore.
        min_osman_score = 55.0

    if not _has_arabic(text):
        return {"passed": True, "score": None, "threshold_info": "no_arabic_text",
                "status": "not_applicable", "took_ms": int((time.time() - started) * 1000)}

    try:
        score = _get_osman_fn()(str(text))
    except Exception as e:
        return {"passed": False, "score": None, "threshold_info": f"error:{e}",
                "status": "error", "took_ms": int((time.time() - started) * 1000)}

    score = float(score)
    passed = score >= min_osman_score
    return {
        "passed": passed,
        "score": score,
        "threshold_info": f"osman_score>=@{min_osman_score:.1f}",
        "status": "ok",
        "took_ms": int((time.time() - started) * 1000),
    }