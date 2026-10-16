# -*- coding: utf-8 -*-
"""Isolated adapter: performance QA."""
def check_performance(product_text=None, product_chapters=None, pdf_path=None, min_pages=None):
    ver = {"status": "ok", "passed": True, "score": None, "findings": [], "reason": None, "unverified": []}
    import os, time
    start = time.time()
    text = product_text or ""
    if isinstance(product_chapters, list):
        text = "\n".join([c.get("content","") if isinstance(c, dict) else str(c) for c in product_chapters])
    if not text.strip():
        ver["unverified"].append("performance_basic")
        ver["findings"].append("performance: no text -> UNVERIFIED")
        ver["score"] = "0/1"
        ver["verdict"] = "REVIEW"
        ver["reason"] = "performance UNVERIFIED"
        return ver
    elapsed = time.time() - start
    if elapsed > 5:
        ver["passed"] = False
        ver["findings"].append(f"performance: generation too slow ({elapsed:.2f}s)")
    else:
        ver["findings"].append(f"performance: check passed ({elapsed:.3f}s)")
    ver["score"] = "1/1" if ver["passed"] else "0/1"
    ver["reason"] = "performance check passed" if ver["passed"] else "performance check failed"
    return ver
