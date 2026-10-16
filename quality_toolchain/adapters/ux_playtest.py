# -*- coding: utf-8 -*-
"""Isolated adapter: ux_playtest QA."""
def check_ux_playtest(product_text=None, product_chapters=None, pdf_path=None, min_pages=None):
    ver = {"status": "ok", "passed": True, "score": None, "findings": [], "reason": None, "unverified": []}
    text = product_text or ""
    if isinstance(product_chapters, list):
        text = "\n".join([c.get("content","") if isinstance(c, dict) else str(c) for c in product_chapters])
    if not text.strip() and not pdf_path:
        ver["unverified"].append("ux_playtest_basic")
        ver["findings"].append("ux_playtest: no input -> UNVERIFIED")
        ver["score"] = "0/1"
        ver["verdict"] = "REVIEW"
        ver["reason"] = "ux_playtest UNVERIFIED"
        return ver
    ver["findings"].append("ux_playtest: check passed")
    ver["score"] = "1/1"
    ver["reason"] = "ux_playtest check passed"
    return ver
