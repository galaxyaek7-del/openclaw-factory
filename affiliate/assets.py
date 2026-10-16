#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Asset reuse inventory: existing validated assets first (read-only).

Preferred sequence EXISTING → REPURPOSE → DERIVATIVE → VARIANT →
EXPERIMENT → NEW ONLY IF JUSTIFIED. Today the inventory is the answer:
nothing new is justified pre-first-signal."""

from __future__ import annotations

from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DO_NOT_CLONE_WITHOUT_EVIDENCE = True


def inventory() -> list:
    assets = []
    drafts = _FACTORY_ROOT / "drafts"
    if drafts.exists():
        for p in sorted(drafts.glob("*.md")):
            assets.append({"kind": "ARTICLE_DRAFT", "path": str(p),
                           "reuse": "publish-first, then repurpose to social/email"})
    books = _FACTORY_ROOT / "books"
    if books.exists():
        pdfs = sorted(books.glob("*.pdf"))
        assets.append({"kind": "PRODUCT_PORTFOLIO", "path": "books/",
                       "count": len(pdfs),
                       "reuse": "existing Gumroad portfolio — no new product justified"})
    video = _FACTORY_ROOT / "assets" / "affiliate" / "systeme_io" / "first_video"
    if (video / "final_video.mp4").exists():
        assets.append({"kind": "LONG_VIDEO", "path": str(video / "final_video.mp4"),
                       "qa": str(video / "qa_report.md"),
                       "reuse": "derivatives (shorts/FAQ/checklist) only post-publication with rationale"})
    return assets


def find_reuse_candidates(need: str) -> dict:
    inv = inventory()
    return {"need": need, "candidates": inv,
            "verdict": "reuse existing; NEW asset NOT justified pre-first-signal"}
