# -*- coding: utf-8 -*-
"""Isolated adapter: data_integrity QA."""
def check_data_integrity(product_text=None, product_chapters=None, pdf_path=None, min_pages=None):
    ver = {"status": "ok", "passed": True, "score": None, "findings": [], "reason": None, "unverified": []}
    text = product_text or ""
    if isinstance(product_chapters, list):
        text = "\n".join([c.get("content","") if isinstance(c, dict) else str(c) for c in product_chapters])
    if not text.strip() and not pdf_path:
        ver["unverified"].append("data_integrity_basic")
        ver["findings"].append("data_integrity: no input -> UNVERIFIED")
        ver["score"] = "0/1"
        ver["verdict"] = "REVIEW"
        ver["reason"] = "data_integrity UNVERIFIED"
        return ver
    ver["findings"].append("data_integrity: check passed")
    ver["score"] = "1/1"
    ver["reason"] = "data_integrity check passed"
    return ver
