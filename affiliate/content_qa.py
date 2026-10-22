#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanical pre-gate content QA (PASS/HOLD + reasons, never a score).

Checks only what is mechanically checkable; everything else is explicitly
out of scope (a human still owns meaning). Limits, disclosed:
- Cannot detect lies, only absolute phrases and missing pieces.
- Cannot verify pricing/commission figures (flags staleness by evidence date).
- Cannot judge thumbnails visually (checks claims text only).

Input asset dict fields (all optional except title+body):
  title, body, disclosure (bool), pricing_claims [{text, evidence_date}],
  commission_claims [{text, evidence_date}], thumbnail_claims [texts],
  cta_present (bool), evidence_date (ISO, newest supporting evidence),
  forbidden_terms [texts] (e.g. competitor names a program's terms ban).
Output: {"status": "PASS"|"HOLD", "failures": [...], "checked_at": ...}.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

_BANNED_PHRASES = (
    "guaranteed income", "guaranteed profit", "risk-free profit",
    "get rich", "no risk", "everyone qualifies",
)

_EVIDENCE_MAX_AGE_DAYS = 60

# 2026-10-22: the live systeme.io guide shipped "APPLICATIONImplementation"
# (two words fused, a leftover template token) inside its disclosure. An
# all-caps run glued to a capitalised word is never intended prose.
_FUSED_TOKEN = re.compile(r"\b[A-Z]{3,}[A-Z][a-z]{2,}")


def _age_days(iso_date, now):
    if not iso_date:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_date).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days


def qa_content(asset: dict, now=None) -> dict:
    """Pure function: asset in, verdict out. No I/O, no network."""
    now = now or datetime.now(timezone.utc)
    failures = []
    title = asset.get("title") or ""
    body = asset.get("body") or ""
    text = (title + "\n" + body).lower()

    if not title.strip() or not body.strip():
        failures.append("empty title or body")
    for phrase in _BANNED_PHRASES:
        if phrase in text:
            failures.append("banned phrase: %r" % phrase)
    if not asset.get("disclosure"):
        failures.append("affiliate disclosure missing")
    if not asset.get("cta_present"):
        failures.append("no CTA present")
    for claim in asset.get("pricing_claims", []) + asset.get("commission_claims", []):
        age = _age_days((claim or {}).get("evidence_date"), now)
        if age is None:
            failures.append("undated claim: %r" % str((claim or {}).get("text"))[:60])
        elif age > _EVIDENCE_MAX_AGE_DAYS:
            failures.append("stale claim (%dd): %r" % (age, str((claim or {}).get("text"))[:60]))
    for term in asset.get("forbidden_terms", []):
        if term and re.search(r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)", text):
            failures.append("forbidden term by program terms: %r" % term)
    for token in _FUSED_TOKEN.findall(title + " " + body):
        failures.append("fused/template token: %r" % token)
    for claim in asset.get("thumbnail_claims", []):
        if claim and claim.lower() not in text:
            failures.append("thumbnail claim not supported by body: %r" % str(claim)[:60])

    return {"status": "PASS" if not failures else "HOLD",
            "failures": failures,
            "checked_at": now.isoformat(),
            "limits": ("mechanical only: cannot detect lies, verify figures, "
                       "or judge visuals; human owns meaning")}
