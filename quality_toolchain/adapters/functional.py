# -*- coding: utf-8 -*-
"""Isolated adapter: functional QA for game/software/b2b.
Checks: file existence, content length, basic deterministic checks.
"""
def check_functional(product_text=None, product_chapters=None, pdf_path=None, min_pages=None):
    ver = {"status": "ok", "passed": True, "score": None, "findings": [], "reason": None, "unverified": []}
    passed = []
    attempted = ["functional_basic"]
    text = product_text or ""
    if isinstance(product_chapters, list):
        text = "\n".join([c.get("content","") if isinstance(c, dict) else str(c) for c in product_chapters])
    if not text.strip() and not pdf_path:
        ver["unverified"].append("functional_basic")
        ver["findings"].append("functional: no product text/pdf supplied -> UNVERIFIED")
        ver["score"] = "0/1"
        ver["verdict"] = "REVIEW"
        ver["reason"] = "functional check UNVERIFIED (no input)"
        return ver
    if text.strip():
        if len(text.strip()) < 100:
            ver["passed"] = False
            ver["findings"].append("functional: content too short (<100 chars)")
        else:
            passed.append("functional_basic")
            ver["findings"].append("functional: basic content length check passed")
    if pdf_path:
        import os
        if os.path.exists(pdf_path):
            passed.append("functional_file")
            ver["findings"].append("functional: pdf file exists")
        else:
            ver["passed"] = False
            ver["findings"].append("functional: pdf file missing")
        attempted.append("functional_file")
    ver["score"] = f"{len(passed)}/{len(attempted)}"
    if not ver["passed"]:
        ver["reason"] = "functional check failed"
    elif passed:
        ver["reason"] = "all functional checks passed"
    return ver
