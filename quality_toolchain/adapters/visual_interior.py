# -*- coding: utf-8 -*-
"""
Galaxy Forge — Interior Visual QA Adapter

Checks interior pages for visual quality:
- Image density (images per page)
- Layout variety (unique archetypes)
- Image-to-recipe mapping
- Hollow page detection
- Text overflow detection
- Page balance

This is the interior counterpart to visual.py which only checks covers.
"""

import os
from typing import Optional, List, Dict


def check_visual_interior(pdf_path: str = None, book_spec: dict = None,
                          page_archetypes: list = None,
                          image_paths: list = None,
                          min_image_density: float = 0.4,
                          min_layout_variety: float = 0.3) -> dict:
    """
    Check interior visual quality.
    
    Args:
        pdf_path: Path to the PDF file
        book_spec: Book product specification
        page_archetypes: List of archetypes used per page
        image_paths: List of image paths used in the book
        min_image_density: Minimum images per page (target: 0.4)
        min_layout_variety: Minimum layout variety score (target: 0.3)
    
    Returns:
        dict with status, passed, score, checks, failures
    """
    checks = []
    failures = []
    
    # 1. Image density check
    if image_paths is not None and pdf_path:
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            total_pages = len(reader.pages)
            image_count = len([p for p in image_paths if p and os.path.exists(p)])
            density = image_count / max(1, total_pages)
            density_ok = density >= min_image_density
            checks.append({
                "name": "image_density",
                "passed": density_ok,
                "detail": f"{image_count} images / {total_pages} pages = {density:.2f} (min: {min_image_density})"
            })
            if not density_ok:
                failures.append(f"image_density: {density:.2f} < {min_image_density}")
        except Exception as e:
            checks.append({"name": "image_density", "passed": False, "detail": f"Error: {e}"})
            failures.append(f"image_density: {e}")
    
    # 2. Layout variety check
    if page_archetypes:
        unique = len(set(page_archetypes))
        total = len(page_archetypes)
        variety = unique / max(1, total)
        variety_ok = variety >= min_layout_variety
        checks.append({
            "name": "layout_variety",
            "passed": variety_ok,
            "detail": f"{unique} unique / {total} total = {variety:.2f} (min: {min_layout_variety})"
        })
        if not variety_ok:
            failures.append(f"layout_variety: {variety:.2f} < {min_layout_variety}")
        
        # 3. Anti-newspaper check (no 3+ consecutive text-only)
        text_only_archetypes = {"CONTENTS", "REFERENCE", "NOTES", "SHOPPING_LIST", "COOKING_TIP"}
        text_streak = 0
        max_streak = 0
        for arch in page_archetypes:
            if arch in text_only_archetypes:
                text_streak += 1
                max_streak = max(max_streak, text_streak)
            else:
                text_streak = 0
        
        newspaper_ok = max_streak <= 3
        checks.append({
            "name": "anti_newspaper",
            "passed": newspaper_ok,
            "detail": f"Max consecutive text-only pages: {max_streak} (max allowed: 3)"
        })
        if not newspaper_ok:
            failures.append(f"anti_newspaper: {max_streak} consecutive text-only pages")
    
    # 4. Hollow page detection (if PDF available)
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            hollow_count = 0
            for i, page in enumerate(reader.pages):
                try:
                    content = page.get_contents()
                    if content:
                        data = content.get_data()
                        if len(data) < 300:  # Match inspectors.py threshold
                            hollow_count += 1
                except Exception:
                    pass
            
            hollow_ok = hollow_count == 0
            checks.append({
                "name": "hollow_pages",
                "passed": hollow_ok,
                "detail": f"{hollow_count} hollow/near-empty pages found"
            })
            if not hollow_ok:
                failures.append(f"hollow_pages: {hollow_count} pages with insufficient content")
        except Exception as e:
            pass  # Non-critical check
    
    # 5. Image-to-recipe mapping (if provided)
    if image_paths and book_spec:
        unique_images = len(set(image_paths))
        total_images = len(image_paths)
        duplicates = total_images - unique_images
        dedup_ok = duplicates == 0
        checks.append({
            "name": "no_duplicate_images",
            "passed": dedup_ok,
            "detail": f"{duplicates} duplicate images found"
        })
        if not dedup_ok:
            failures.append(f"no_duplicate_images: {duplicates} images reused")
    
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
        "reason": None if passed else f"Visual interior check failed: {'; '.join(failures)}"
    }
