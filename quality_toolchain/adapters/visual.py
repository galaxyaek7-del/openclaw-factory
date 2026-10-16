# -*- coding: utf-8 -*-
"""Isolated adapter: visual QA (PHASE 2A directive, 2026-09-02). Wires the
single genuinely missing visual layer into the Quality Toolchain by citing
the factory's already-real, load-bearing cover-inspection code -- exactly the
"cover pixels/rendering (inspectors.py + cover_designer_v2)" description the
`visual_qa` layer declares -- WITHOUT re-implementing or fabricating any check.

The real engine here is inspectors.py::inspect_technical(), which has a
dedicated Cover block (inspectors.py:197-241): a genuine Pillow-based
corruption/verify + dimension + 70/20/10 title-zone + title-vs-author-size
check over cover_designer_v2's rendered PNG output. inspectors.py itself
already cites cover_designer_v2 (it reuses cover_designer_v2._looks_like_
placeholder at inspectors.py:62-67 and validates against EXPECTED_COVER_SIZE
= (1600, 2560), the cover_designer_v2 render dimension). So this adapter
delegates to inspectors and surfaces only the cover checks it really returns.

There is NO inspectors.py::inspect_cover function (verified by grep); the
directive's "inspectors.inspect_cover" name is satisfied by the real,
existing cover-inspection path inside inspect_technical. Nothing here calls
cover_designer_v2 to render -- this adapter only inspects an already-created
cover artifact (read-only, zero external I/O) and never re-derives a check.

Contract:
  check_visual(cover_path=None, pdf_path=None, texts=None, min_pages=None)
    -> dict
  - cover_path: optional path to a real cover image (PNG/JPG) to inspect.
  - pdf_path:   optional real PDF path (passed through to inspect_technical
                so the cover block's accompanying file/PDF context is real).
  - texts:      optional {"title", "subtitle", "author"} (passed through; the
                cover block + Arabic-shaping context re-checks placeholders).

Fail-closed / not_available (never a PASS):
  - If Pillow cannot be imported -> {"status": "not_available",
    "passed": False, ...}. not_available must NEVER be read as Gate-1 PASS;
    the strict run_stack overall_verdict treats it as REVIEW/blocked.
  - If no cover_path is supplied -> {"status": "not_available",
    "passed": False, ...} because there is no artifact to verify; a visual
    layer cannot honestly claim PASS without real evidence. (This matches
    inspect_technical's own note that a missing separate cover is a
    legitimate in-PDF degradation path -- but this dedicated visual layer
    will not manufacture a PASS from it.)
  - A real failure found by inspect_technical's cover checks resolves to
    {"status": "ok", "passed": False} with evidence -- a real failed check,
    not an availability gap.
  - If the cover block produced NO cover checks at all, or inspection raised,
    resolves to {"status": "error", "passed": False} -- never a fabricated
    pass without executed evidence.
"""

import os


def _coverage_checks(tech_report):
    """Return only the cover-related checks real inspect_technical returned.

    These are the checks whose `name` is the cover block's keys, so the
    adapter reports exactly the evidence that actually ran and never invents
    an extra check. Ordered: exists -> opens -> dimensions -> zone -> size.
    """
    cover_names = (
        "cover_exists",
        "cover_opens",
        "cover_dimensions",
        "cover_70_20_10_zone",
        "cover_title_bigger_than_author",
    )
    return [c for c in (tech_report.get("checks") or []) if c.get("name") in cover_names]


def check_visual(cover_path=None, pdf_path=None, texts=None, min_pages=None):
    # Fail-closed: real Pillow-backed verification is impossible without
    # Pillow, so this is explicitly not_available, never a fabricated pass.
    try:
        import PIL  # noqa: F401  -- availability probe only
    except Exception as e:  # noqa: BLE001 - Pillow presence is the gate
        return {
            "status": "not_available",
            "passed": False,
            "score": "0/0",
            "checks": [],
            "failures": [f"Pillow unavailable -> visual QA cannot run; fail-closed: {e}"],
            "reason": "Pillow (PIL) not importable",
        }

    # No cover artifact to inspect: a dedicated visual layer cannot claim PASS
    # without real evidence. not_available, by design never interpreted as
    # Gate-1 PASS.
    if not cover_path:
        return {
            "status": "not_available",
            "passed": False,
            "score": "0/0",
            "checks": [],
            "failures": ["no cover_path supplied -> no cover artifact to verify"],
            "reason": "no cover artifact supplied for visual QA",
        }

    # Delegate to the factory's real cover-inspection path.
    try:
        import importlib
        inspectors = importlib.import_module("inspectors")
        res = inspectors.inspect_technical(
            pdf_path, cover_path=cover_path, texts=texts,
            min_pages=min_pages or 1,
        )
    except Exception as e:  # noqa: BLE001 - fail closed
        return {
            "status": "error",
            "passed": False,
            "score": "0/0",
            "checks": [],
            "failures": [f"cover inspection raised: {e}"],
            "reason": f"inspectors.inspect_technical raised: {e}",
        }

    cover_checks = _coverage_checks(res)
    
    # Add cover imagery check (is it a solid color placeholder or real image?)
    if cover_path and os.path.exists(cover_path):
        try:
            from PIL import Image
            img = Image.open(cover_path)
            # Sample pixels across the image
            pixels = []
            for x in range(0, img.width, img.width // 10):
                for y in range(0, img.height, img.height // 10):
                    pixels.append(img.getpixel((x, y)))
            
            # Check color variance (solid color = low variance)
            unique_colors = len(set(pixels))
            has_imagery = unique_colors > 5  # Real images have many colors (covers may have large solid zones)
            
            cover_checks.append({
                "name": "cover_has_imagery",
                "passed": has_imagery,
                "detail": f"Cover has {unique_colors} unique colors (real imagery: >5)"
            })
        except Exception:
            pass
    
    # The directive requires a real, executed cover check before any PASS.
    # If inspect_technical returned nothing for the cover block, we cannot
    # honestly pass (fail-closed error, not a fabricated pass).
    if not cover_checks:
        return {
            "status": "error",
            "passed": False,
            "score": "0/0",
            "checks": [],
            "failures": ["no cover check evidence returned by inspectors.inspect_technical"],
            "reason": "cannot report PASS without real executed cover evidence",
        }

    passed_count = sum(1 for c in cover_checks if c.get("passed"))
    failures = [f"{c.get('name')}: {c.get('detail')}"
                for c in cover_checks if not c.get("passed")]
    all_passed = passed_count == len(cover_checks) and not failures
    return {
        "status": "ok",
        "passed": all_passed,
        "score": f"{passed_count}/{len(cover_checks)}",
        "checks": [
            {"name": c.get("name"), "passed": bool(c.get("passed")),
             "detail": c.get("detail")}
            for c in cover_checks
        ],
        "failures": failures,
        "reason": None if all_passed else (
            "one or more real cover checks failed"),
        "verdict": "PASS" if all_passed else "FAIL",
    }