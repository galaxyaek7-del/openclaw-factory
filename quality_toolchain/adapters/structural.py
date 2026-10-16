# -*- coding: utf-8 -*-
"""Isolated adapter: structural QA (QUALITY ARCHITECTURE directive,
2026-09-02). Two real, deterministic layers combined into one advisory gate
for the toolchain's `structural_qa` layer:

  1. content_markers: a real scan for forgotten placeholders / unfinished
     / machine-rendered text that must not ship -- [TBD], lorem ipsum, bare
     bracket shells, "todo"/"fixme", repeated boilerplate markers, stray
     markdown fences, etc. Produces a numeric hits list (never a vague
     "good/bad" verdict).
  2. pdf_integrity (optional): delegates to inspectors.py::inspect_technical
     ONLY when a real pdf_path is supplied. That is the factory's already-
     real, load-bearing PDF structural gate (pypdf parse, page count, empty
     pages, cover, Arabic shaping). Advisory here, as everywhere in the
     toolchain.

Purposes: close the QUALITY ARCHITECTURE "structural_qa: completeness / no
forgotten placeholders / proper formatting" criterion with a real scanner;
connect the already-real inspectors.py gate without duplicating it.

Contract:
  check_structural(product_text=None, product_chapters=None, pdf_path=None,
                   min_pages=None) -> dict
    - product_text: concatenated product text to scan for markers (required
      for the marker scan; missing -> markers reported UNVERIFIED).
    - product_chapters: alternative to product_text (joined).
    - pdf_path: optional real PDF file for the inspectors.py pass.
    Returns {"status", "passed", "score": "N/M", "markers": [found items],
              "pdf": {...} or None, "findings": [concrete notes]}.

Fail-closed: an exception in the marker scan or the pdf delegation resolves
to status "error" and passed=False. An unverifiable markers scan (no text)
never becomes a clean pass -- it reports unverified and sets advisory
REVIEW, the established toolchain fail-safe.
"""

import os

# Concrete, disclosed marker patterns (deterministic, phrase-list discipline
# matching executive_quality_gate.py's own content scans). Each is a regex.
_MARKER_PATTERNS = {
    "placeholder_bracket": r"(?i)\[TBD\]|\[todo\]|\[fixme\]|\[insert[^\]]*\]|\[placeholder[^\]]*\]",
    "lorem_ipsum": r"(?i)\b(lorem\s+ipsum|dolor\s+sit)\b",
    "unresolved_angle": r"<insert\s+[^>]+>|<add\s+[^>]+>|<<[^>]+>>",
    "stray_markdown_fence": r"(?m)^```$|^~~~$",
    "stray_template_tag": r"(?i)\{\{\s*[a-z_]+\s*\}\}",
    "repeated_boilerplate_block": r"(?s)(.{200,}?)(\1){2,}",
}


def _to_text(product_text, product_chapters):
    if isinstance(product_text, str) and product_text.strip():
        return product_text
    if isinstance(product_chapters, list):
        parts = []
        for c in product_chapters:
            if isinstance(c, dict) and c.get("content"):
                parts.append(str(c["content"]))
            elif isinstance(c, str):
                parts.append(c)
        return "\n".join(parts)
    if isinstance(product_chapters, str):
        return product_chapters
    return ""


def _find_markers(text):
    import re
    found = []
    for kind, pat in _MARKER_PATTERNS.items():
        try:
            matches = list(re.findall(pat, text))
        except Exception:  # noqa: BLE001 - never crash the gate on a bad pattern
            continue
        if matches:
            found.append({"kind": kind, "count": len(matches)})
    return found


def check_structural(product_text=None, product_chapters=None, pdf_path=None,
                     min_pages=None, checks=("content_markers", "pdf_integrity")):
    text = _to_text(product_text, product_chapters)
    ver = {"status": "ok", "passed": True, "score": None, "markers": [],
           "pdf": None, "findings": [], "reason": None, "unverified": []}
    attempted = []
    passed = []

    if "content_markers" in checks:
        attempted.append("content_markers")
        if not text.strip():
            ver["unverified"].append("content_markers")
            ver["findings"].append("content_markers: no product text supplied -> UNVERIFIED")
        else:
            markers = _find_markers(text)
            ver["markers"] = markers
            if markers:
                detail = "; ".join(f"{m['kind']} x{m['count']}" for m in markers)
                ver["findings"].append(f"content_markers: {len(markers)} marker type(s) found: {detail}")
                ver["passed"] = False
            else:
                passed.append("content_markers")
                ver["findings"].append("content_markers: no placeholder/machine-marker patterns found")

    if "pdf_integrity" in checks:
        attempted.append("pdf_integrity")
        if not pdf_path:
            ver["unverified"].append("pdf_integrity")
            ver["findings"].append("pdf_integrity: no pdf_path supplied -> UNVERIFIED")
        else:
            try:
                import importlib
                inspectors = importlib.import_module("inspectors")
                res = inspectors.inspect_technical(
                    pdf_path, min_pages=min_pages or 1,
                )
                ver["pdf"] = {
                    "passed": res.get("passed"),
                    "severity": res.get("severity"),
                    "checks_count": len(res.get("checks") or []),
                    "failures": res.get("failures") or [],
                }
                if not res.get("passed"):
                    ver["passed"] = False
                    ver["findings"].append(
                        "pdf_integrity: " + "; ".join(res.get("failures") or ["failed"]))
                else:
                    passed.append("pdf_integrity")
                    ver["findings"].append(f"pdf_integrity: {len(res.get('checks') or [])} checks passed")
            except Exception as e:  # noqa: BLE001 - fail closed
                ver["passed"] = False
                ver["findings"].append(f"pdf_integrity: error -> {e}")

    ver["score"] = f"{len(passed)}/{len(attempted)}" if attempted else "0/0"
    if ver["unverified"] and ver["passed"]:
        ver["verdict"] = "REVIEW"
        ver["reason"] = "some structural checks are UNVERIFIED (missing input); advisory REVIEW"
    elif not ver["passed"]:
        ver["reason"] = "one or more structural checks reported findings/failure"
    elif attempted:
        ver["reason"] = "all structural checks passed"
    return ver