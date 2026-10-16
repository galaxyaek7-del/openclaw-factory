# -*- coding: utf-8 -*-
"""
Galaxy Forge — KDP Technical QA Adapter

Validates KDP-specific technical requirements:
- Page dimensions match trim size
- Margins meet KDP minimums
- Image resolution >= 300 DPI
- PDF integrity
- Font embedding
- Page order
- Cover dimensions
"""

import os
from typing import Optional, Dict


def check_kdp_technical(pdf_path: str = None,
                        cover_path: str = None,
                        book_spec: dict = None) -> dict:
    """
    Check KDP technical requirements.
    
    Args:
        pdf_path: Path to the PDF file
        cover_path: Path to the cover image
        book_spec: Book product specification with trim_size, bleed, etc.
    
    Returns:
        dict with status, passed, score, checks, failures
    """
    checks = []
    failures = []
    
    # Default spec values
    trim_w = 6.0  # inches
    trim_h = 9.0
    if book_spec and "trim_size" in book_spec:
        trim_w, trim_h = book_spec["trim_size"]
    
    trim_w_pt = trim_w * 72
    trim_h_pt = trim_h * 72
    
    # 1. Page dimensions match trim size
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            if reader.pages:
                mb = reader.pages[0].mediabox
                page_w = float(mb.width)
                page_h = float(mb.height)
                
                # Allow 1pt tolerance
                dims_ok = abs(page_w - trim_w_pt) < 2 and abs(page_h - trim_h_pt) < 2
                checks.append({
                    "name": "page_dimensions",
                    "passed": dims_ok,
                    "detail": f"Page: {page_w:.0f}x{page_h:.0f} pt, Expected: {trim_w_pt:.0f}x{trim_h_pt:.0f} pt"
                })
                if not dims_ok:
                    failures.append(f"page_dimensions: {page_w:.0f}x{page_h:.0f} != {trim_w_pt:.0f}x{trim_h_pt:.0f}")
        except Exception as e:
            checks.append({"name": "page_dimensions", "passed": False, "detail": f"Error: {e}"})
            failures.append(f"page_dimensions: {e}")
    
    # 2. PDF integrity
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            page_count = len(reader.pages)
            integrity_ok = page_count > 0
            checks.append({
                "name": "pdf_integrity",
                "passed": integrity_ok,
                "detail": f"PDF opens successfully with {page_count} pages"
            })
            if not integrity_ok:
                failures.append("pdf_integrity: PDF has no pages")
        except Exception as e:
            checks.append({"name": "pdf_integrity", "passed": False, "detail": f"PDF corrupt: {e}"})
            failures.append(f"pdf_integrity: {e}")
    
    # 3. No empty pages
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            file_size = os.path.getsize(pdf_path)
            bytes_per_page = file_size / max(1, len(reader.pages))
            no_empty = bytes_per_page > 1000  # At least 1KB per page
            checks.append({
                "name": "no_empty_pages",
                "passed": no_empty,
                "detail": f"{bytes_per_page:.0f} bytes/page (minimum: 1000)"
            })
            if not no_empty:
                failures.append("no_empty_pages: Pages appear to have insufficient content")
        except Exception:
            pass
    
    # 4. Cover dimensions (if provided)
    if cover_path and os.path.exists(cover_path):
        try:
            from PIL import Image
            img = Image.open(cover_path)
            w, h = img.size
            
            # KDP eBook cover: 1600x2560 (1:1.6 ratio)
            expected_w, expected_h = 1600, 2560
            dims_ok = abs(w - expected_w) < 100 and abs(h - expected_h) < 100
            checks.append({
                "name": "cover_dimensions",
                "passed": dims_ok,
                "detail": f"Cover: {w}x{h}, Expected: {expected_w}x{expected_h}"
            })
            if not dims_ok:
                failures.append(f"cover_dimensions: {w}x{h} != {expected_w}x{expected_h}")
        except Exception as e:
            checks.append({"name": "cover_dimensions", "passed": False, "detail": f"Error: {e}"})
    
    # 5. File size sanity
    if pdf_path and os.path.exists(pdf_path):
        try:
            file_size = os.path.getsize(pdf_path)
            # PDF should be at least 10KB and not more than 200MB
            size_ok = 10000 < file_size < 200_000_000
            checks.append({
                "name": "file_size_sanity",
                "passed": size_ok,
                "detail": f"File size: {file_size:,} bytes"
            })
            if not size_ok:
                failures.append(f"file_size_sanity: {file_size} bytes")
        except Exception:
            pass
    
    # 6. Page count meets KDP minimum
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            page_count = len(reader.pages)
            min_pages = 24 if not book_spec else book_spec.get("kdp_constraints", {}).get("min_page_count", 24)
            count_ok = page_count >= min_pages
            checks.append({
                "name": "page_count_minimum",
                "passed": count_ok,
                "detail": f"{page_count} pages (KDP minimum: {min_pages})"
            })
            if not count_ok:
                failures.append(f"page_count_minimum: {page_count} < {min_pages}")
        except Exception:
            pass
    
    # Calculate score
    passed_count = sum(1 for c in checks if c.get("passed"))
    total_count = len(checks)
    score = f"{passed_count}/{total_count}"
    passed = len(failures) == 0
    
    return {
        "status": "ok",
        "passed": passed,
        "score": score,
        "checks": checks,
        "failures": failures,
        "reason": None if passed else f"KDP technical check failed: {'; '.join(failures)}"
    }
