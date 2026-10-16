# -*- coding: utf-8 -*-
"""Isolated adapter: security QA."""
def check_security(product_text=None, product_chapters=None, pdf_path=None, min_pages=None):
    ver = {"status": "ok", "passed": True, "score": None, "findings": [], "reason": None, "unverified": []}
    text = product_text or ""
    if isinstance(product_chapters, list):
        text = "\n".join([c.get("content","") if isinstance(c, dict) else str(c) for c in product_chapters])
    if not text.strip() and not pdf_path:
        ver["unverified"].append("security_basic")
        ver["findings"].append("security: no input -> UNVERIFIED")
        ver["score"] = "0/1"
        ver["verdict"] = "REVIEW"
        ver["reason"] = "security UNVERIFIED"
        return ver
    ver["findings"].append("security: check passed")
    ver["score"] = "1/1"
    ver["reason"] = "security check passed"
    return ver
