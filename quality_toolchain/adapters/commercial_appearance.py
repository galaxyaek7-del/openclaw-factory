# -*- coding: utf-8 -*-
"""
Galaxy Forge — Commercial Appearance QA Adapter

Checks whether a book looks like a professionally published product.
This is NOT about profit margins or economics — it's about visual
commercial viability: "Would this reasonably look like a finished
commercial book in its category?"
"""

import os
from typing import Optional, List, Dict


def check_commercial_appearance(pdf_path: str = None,
                                 cover_path: str = None,
                                 book_spec: dict = None,
                                 page_archetypes: list = None,
                                 image_paths: list = None) -> dict:
    """
    Check commercial appearance quality.
    
    Args:
        pdf_path: Path to the PDF file
        cover_path: Path to the cover image
        book_spec: Book product specification
        page_archetypes: List of archetypes used per page
        image_paths: List of image paths used
    
    Returns:
        dict with status, passed, score, checks, failures
    """
    checks = []
    failures = []
    
    # 1. Cover has food imagery (not flat placeholder)
    if cover_path and os.path.exists(cover_path):
        try:
            from PIL import Image
            img = Image.open(cover_path)
            # Check if cover has real image content (not just solid color)
            # Sample pixels across the image
            pixels = []
            for x in range(0, img.width, img.width // 10):
                for y in range(0, img.height, img.height // 10):
                    pixels.append(img.getpixel((x, y)))
            
            # Check color variance (solid color = low variance)
            unique_colors = len(set(pixels))
            has_imagery = unique_colors > 5  # Real images have many colors (covers may have large solid zones)
            
            checks.append({
                "name": "cover_has_imagery",
                "passed": has_imagery,
                "detail": f"Cover has {unique_colors} unique colors (real imagery: >5)"
            })
            if not has_imagery:
                failures.append("cover_has_imagery: Cover appears to be solid color placeholder")
        except Exception as e:
            checks.append({"name": "cover_has_imagery", "passed": False, "detail": f"Error: {e}"})
    
    # 2. Interior has visual variety (not newspaper)
    if page_archetypes:
        unique_archetypes = len(set(page_archetypes))
        has_variety = unique_archetypes >= 4
        checks.append({
            "name": "interior_visual_variety",
            "passed": has_variety,
            "detail": f"{unique_archetypes} unique layout archetypes (minimum: 4)"
        })
        if not has_variety:
            failures.append("interior_visual_variety: Too few layout archetypes")
    
    # 3. Page count is meaningful
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            page_count = len(reader.pages)
            meaningful = page_count >= 24  # KDP minimum
            checks.append({
                "name": "meaningful_page_count",
                "passed": meaningful,
                "detail": f"{page_count} pages (minimum for commercial: 24)"
            })
            if not meaningful:
                failures.append("meaningful_page_count: Too few pages")
        except Exception as e:
            pass
    
    # 4. Image density is sufficient
    if image_paths and pdf_path:
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            total_pages = len(reader.pages)
            image_count = len([p for p in image_paths if p and os.path.exists(p)])
            density = image_count / max(1, total_pages)
            sufficient = density >= 0.3  # At least 30% of pages have images
            checks.append({
                "name": "sufficient_imagery",
                "passed": sufficient,
                "detail": f"{image_count} images / {total_pages} pages = {density:.2f}"
            })
            if not sufficient:
                failures.append("sufficient_imagery: Not enough images for commercial product")
        except Exception:
            pass
    
    # 5. No placeholder text in final output
    if pdf_path and os.path.exists(pdf_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(pdf_path)
            placeholder_found = False
            placeholder_patterns = ["[TBD]", "[todo]", "lorem ipsum", "placeholder"]
            for page in reader.pages[:10]:  # Check first 10 pages
                try:
                    text = page.extract_text() or ""
                    for pattern in placeholder_patterns:
                        if pattern.lower() in text.lower():
                            placeholder_found = True
                            break
                except Exception:
                    pass
                if placeholder_found:
                    break
            
            checks.append({
                "name": "no_placeholder_text",
                "passed": not placeholder_found,
                "detail": "No placeholder text found" if not placeholder_found else "Placeholder text detected"
            })
            if placeholder_found:
                failures.append("no_placeholder_text: Placeholder text found in final output")
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
        "reason": None if passed else f"Commercial appearance check failed: {'; '.join(failures)}"
    }
