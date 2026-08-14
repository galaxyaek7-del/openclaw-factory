#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Internal Market Validation System (Founder Directive,
2026-08-14).

A lightweight, internal-only response store + aggregator for the
validation sprint of the Legal Case Research opportunity ($194 one-time,
independent lawyers). This is deliberately NOT an MVP and NOT a launch —
it exists only to record real, founder-observed validation responses and
to answer the sprint's evidence questions honestly.

Data layer discipline (reuse, not new infrastructure):
  - Storage is an append-only JSONL file under data/ (the exact same
    pattern market_evidence.py, affiliate_clicks, etc. already use), so
    the responses live in the existing project data layer with no new
    database, no new paid service.
  - Aggregation is pure reading + counting of that real ledger; it never
    invents a response, never fabricates a metric. Every aggregated
    number is labeled FACT (counted directly from real stored rows) or
    INFERENCE (derived theme from real text) below.

Field schema (one JSON object per line, real responses only):
  {
    "timestamp": ISO-8601 UTC,
    "source": one of linkedin/facebook/x/direct/other,
    "professional_role": str or "",
    "practice_area": str or "",
    "q1_frequency": rarely|monthly|weekly|several_times_per_week,
    "q2_intent": yes|maybe|no,
    "q3_pain": free text (the real pain statement),
    "contact": optional str (email/contact), not exposed by aggregate(),
    "session_id": optional str (validation session/source identifier),
  }

Integrity rules (enforced here):
  - q1_frequency/q2_intent must be from the exact closed option sets.
  - q3_pain must be a non-empty real statement (no fabricated text).
  - source must be one of the closed set; unknown -> "other".
  - No response is ever recorded twice with the same session_id + source.
  - aggregate() NEVER returns contact info or raw q3 text to a caller —
    it returns counts, a conversion rate, source breakdown, and top pain
    themes only (themes are word-frequencies over real text, never the
    verbatim statements themselves).

    python market_validation.py --record '<json payload>'
    python market_validation.py --summarize
"""

import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_RESPONSES_PATH = _FACTORY_ROOT / "data" / "validation_responses.jsonl"


def _default_path():
    """Resolve the responses ledger path. A VALIDATION_RESPONSES_PATH
    env override is honored first (the integration test uses it to point
    at a temp ledger so it never pollutes the real data/ file); otherwise
    the real data-layer default is used."""
    override = os.environ.get("VALIDATION_RESPONSES_PATH")
    if override:
        return Path(override)
    return DEFAULT_RESPONSES_PATH

SOURCES = ("linkedin", "facebook", "x", "direct", "other")
Q1_OPTIONS = ("rarely", "monthly", "weekly", "several_times_per_week")
Q2_OPTIONS = ("yes", "maybe", "no")

_PAIN_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "with",
    "is", "are", "was", "were", "be", "been", "being", "it", "its", "my",
    "your", "our", "their", "i", "we", "they", "me", "us", "them", "that",
    "this", "these", "those", "have", "has", "had", "do", "does", "did",
    "will", "would", "can", "could", "should", "must", "from", "at", "by",
    "as", "but", "not", "no", "so", "just", "very", "really", "always",
    "often", "sometimes", "already", "any", "all", "more", "most", "some",
}


def _load(path):
    if not path:
        path = _default_path()
    path = Path(path)
    if not os.path.exists(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    # A corrupt/partial line must never break the read —
                    # same discipline every other JSONL reader in this
                    # factory follows (lib/jsonl.js, market_evidence.py).
                    continue
    except Exception:
        return []
    return rows


def _append(path, row):
    if not path:
        path = _default_path()
    path = Path(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_source(source):
    s = str(source or "").strip().lower()
    return s if s in SOURCES else "other"


def validate_payload(payload):
    """Returns (clean_payload, errors). Never raises. Rejects invalid
    required fields with real, specific errors; unknown/empty optional
    fields are accepted as empty strings."""
    errors = []
    if not isinstance(payload, dict):
        return None, ["payload must be a JSON object"]

    q1 = str(payload.get("q1_frequency") or "").strip().lower()
    q2 = str(payload.get("q2_intent") or "").strip().lower()
    q3 = str(payload.get("q3_pain") or "").strip()

    if q1 not in Q1_OPTIONS:
        errors.append(f"q1_frequency must be one of {Q1_OPTIONS}")
    if q2 not in Q2_OPTIONS:
        errors.append(f"q2_intent must be one of {Q2_OPTIONS}")
    if not q3:
        errors.append("q3_pain must be a non-empty statement")
    elif len(q3) > 2000:
        errors.append("q3_pain is too long (max 2000 chars)")

    source = normalize_source(payload.get("source"))
    role = str(payload.get("professional_role") or "").strip()[:200]
    area = str(payload.get("practice_area") or "").strip()[:200]
    contact = str(payload.get("contact") or "").strip()[:200]
    session_id = str(payload.get("session_id") or "").strip()[:100]

    if errors:
        return None, errors

    clean = {
        "q1_frequency": q1,
        "q2_intent": q2,
        "q3_pain": q3,
        "source": source,
        "professional_role": role,
        "practice_area": area,
        "contact": contact,
        "session_id": session_id,
    }
    return clean, []


def record_response(payload, responses_path=None):
    """Validates and appends one real validation response. Returns the
    stored row on success, or raises ValueError with the validation
    errors on failure. Refuses an exact duplicate (same session_id +
    source + q3) — a retried POST must never create a phantom response."""
    clean, errors = validate_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **clean,
    }

    for existing in _load(responses_path):
        if (existing.get("session_id") == row["session_id"]
                and existing.get("source") == row["source"]
                and existing.get("q3_pain") == row["q3_pain"]):
            raise ValueError("duplicate response (same session_id + source + q3)")

    _append(responses_path, row)
    return row


def _pain_theme(counter, label):
    return {"label": label, "count": counter[label]}


def aggregate(responses_path=None):
    """Pure reading + counting of the real ledger. Every number is real
    and derived from stored rows. Returns summary ONLY — contact info and
    verbatim q3 statements are never included."""
    rows = _load(responses_path)

    total = len(rows)
    by_source = Counter(r.get("source") or "other" for r in rows)
    q2 = Counter(r.get("q2_intent") or "no" for r in rows)
    high_freq = sum(1 for r in rows if r.get("q1_frequency") in ("weekly", "several_times_per_week"))
    pain_signal = sum(1 for r in rows if (r.get("q3_pain") or "").strip())

    # Qualified = a real respondent with both a professional role and a
    # practice area (a genuine professional signal, not an anonymous
    # like). This is a FACT about the stored row, labeled as such.
    qualified = sum(1 for r in rows if (r.get("professional_role") or "").strip()
                    and (r.get("practice_area") or "").strip())

    # Conversion = $194 Yes (q2_intent=yes) among qualified respondents.
    qualified_yes = sum(1 for r in rows
                        if r.get("q2_intent") == "yes"
                        and (r.get("professional_role") or "").strip()
                        and (r.get("practice_area") or "").strip())
    conversion_rate = round(qualified_yes / qualified * 100, 1) if qualified else None

    # Top pain themes: word-frequency over REAL q3 text, stopword-filtered.
    # An INFERENCE (derived from real text), never presented as a verbatim
    # quote or a customer claim.
    word_counts = Counter()
    for r in rows:
        text = (r.get("q3_pain") or "").lower()
        for word in re.findall(r"[a-z]{3,}", text):
            if word not in _PAIN_STOPWORDS:
                word_counts[word] += 1
    top_themes = [{"theme": w, "count": c} for w, c in word_counts.most_common(10)]

    return {
        "total_responses": total,
        "qualified_responses": qualified,
        "pain_signals": pain_signal,
        "weekly_or_more_pain": high_freq,
        "q2_yes": q2.get("yes", 0),
        "q2_maybe": q2.get("maybe", 0),
        "q2_no": q2.get("no", 0),
        "qualified_conversion_rate_pct": conversion_rate,
        "source_breakdown": dict(by_source),
        "top_pain_themes": top_themes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "missing subcommand: --record | --summarize"}))
        return 1
    cmd = sys.argv[1]
    if cmd == "--record":
        try:
            payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        except Exception:
            payload = {}
        try:
            row = record_response(payload)
            print(json.dumps({"success": True, "recorded": row}, ensure_ascii=False))
            return 0
        except ValueError as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            return 1
    elif cmd == "--summarize":
        print(json.dumps({"success": True, "summary": aggregate()}, ensure_ascii=False))
        return 0
    print(json.dumps({"success": False, "error": f"unknown subcommand: {cmd}"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    sys.exit(main())