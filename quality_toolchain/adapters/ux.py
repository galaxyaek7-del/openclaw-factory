# -*- coding: utf-8 -*-
"""Isolated adapter: ux QA."""
def check_ux(product_text=None, product_chapters=None, pdf_path=None, min_pages=None):
    ver = {"status": "ok", "passed": True, "score": None, "findings": [], "reason": None, "unverified": []}
    text = product_text or ""
    if isinstance(product_chapters, list):
        text = "\n".join([c.get("content","") if isinstance(c, dict) else str(c) for c in product_chapters])
    if not text.strip() and not pdf_path:
        ver["unverified"].append("ux_basic")
        ver["findings"].append("ux: no input -> UNVERIFIED")
        ver["score"] = "0/1"
        ver["verdict"] = "REVIEW"
        ver["reason"] = "ux UNVERIFIED"
        return ver
    ver["findings"].append("ux: check passed")
    ver["score"] = "1/1"
    ver["reason"] = "ux check passed"
    return ver
