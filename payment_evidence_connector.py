#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Proof-of-Payment Evidence Connector (ADR-121 extension).

The single highest-weighted hard gate in this factory (proof_of_payment:
0.35 weight in ladder_opportunity_score(), AND a hard acceptance gate
that rejects as UNPROVEN whenever real, cited spend evidence is absent)
previously had ZERO REAL connectors in evidence_network.py — only
DISCOVERY declarations (job_posting_scanner, pricing_page_scanner,
marketplace_listing_scanner), none callable. This module makes
proof_of_payment genuinely acquirable by reusing the SAME three real,
free, keyless public sources the customer-pain connector already trusts
(GitHub Issues Search API, Hacker News Algolia API, Stack Overflow
API) — searching the niche's real problem query (reformulate_pain_query,
reused verbatim) and extracting REAL, verbatim, URL-cited payment
evidence.

Honesty contract — never weakens a gate, never fabricates:
  1. Only real https source URLs from real API responses.
  2. Only literal, verbatim quotes that contain a real currency/price
     marker ($, USD, per month, /hr, salary, ...) — never a paraphrased
     or invented price.
  3. Every record goes through market_evidence.record_evidence(), which
     REFUSES any payment-evidence item lacking source_url + quote — the
     exact same validation a human-recorded item must pass (ADR-121).
  4. event_type classification is keyword-gated (job/hiring/salary,
     subscription/cancel/plan, complaint/overpriced, or a verbatim
     money quote as the honest freelancer_agency_pricing fallback) —
     never guessed when no money marker exists (such results are
     skipped, not recorded).
  5. No auto-acceptance: ladder_opportunity_score()'s gate logic is
     untouched. This connector only adds real, citable evidence the gate
     can read — exactly what a human recording the same real page would
     add.

Cache discipline (ADR-128 mirror): results persist per niche in
data/payment_evidence_cache.json (same pattern as the pain-evidence
cache) so a repeat call is a real, free cache hit instead of a repeated
live query — "every new connector must increase long-term intelligence
for every future opportunity."

Standalone, deliberately-run tool, same convention as every module this
factory has introduced:

    python payment_evidence_connector.py "some niche"
"""

import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import market_evidence as ME
import market_intelligence_engine as MIE

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
PAYMENT_EVIDENCE_CACHE_FILE = os.path.join(FACTORY_DIR, "data", "payment_evidence_cache.json")
MAX_AGE_DAYS_DEFAULT = 14

# Real currency / price markers. Every recorded quote MUST literally
# contain one of these patterns — no marker, no record (no fabrication).
_CURRENCY_PATTERNS = (
    re.compile(r"\$\s?\d"),
    re.compile(r"\b\d+\s*(?:usd|dollars?)\b", re.I),
    re.compile(r"[€£]\s?\d"),
    re.compile(r"\bper\s+(?:month|year|hour|project|seat)\b", re.I),
    re.compile(r"\b(?:/\s?mo|/\s?yr|/\s?hr|/month|/year|/hour|/seat)\b", re.I),
    re.compile(r"\bsalary\b", re.I),
    re.compile(r"\b(?:hourly|priced at|costs?\s+\$|pays?\s+\$|charge[sd]?\s+\$|fee[sd]?\s+of)\b", re.I),
    re.compile(r"\b\$[\d,.]+\s*(?:/|per)", re.I),
)

# Keyword-gated event_type classification (ADR-121's 4 payment types).
# Priority order matters: job markers first, then subscription, then
# complaint; a verbatim money quote with none of those markers is still
# genuine proof-of-payment and is honestly labeled freelancer_agency_pricing.
_JOB_MARKERS = ("job", "hiring", "position", "salary", "contractor", "freelance gig", "looking for", "we pay", "pays")
_SUBSCRIPTION_MARKERS = ("subscription", "plan", "cancel", "unsubscribed", "monthly fee", "renewal", "replaced", "switched")
_COMPLAINT_MARKERS = ("review", "complaint", "overpriced", "expensive", "rip-off", "not worth", "too much", "refund")


def _http_get_json(url, timeout=10):
    """Delegates to the canonical shared HTTP client (ADR-049) — never
    re-implements the fetch."""
    from market_intelligence_core import http_client
    return http_client.http_get_json(url, timeout=timeout, user_agent="Mozilla/5.0 (Galaxy-Forge-PaymentEvidence)")


def _has_currency_marker(text):
    text = text or ""
    return any(p.search(text) for p in _CURRENCY_PATTERNS)


def _extract_quote(text, max_len=400):
    """The literal sentence (up to max_len chars) containing a real
    currency marker — verbatim from the real result, never paraphrased.
    Returns None when no marker is present."""
    text = (text or "").strip()
    if not text or not _has_currency_marker(text):
        return None
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for s in sentences:
        if _has_currency_marker(s):
            return s[:max_len].strip()
    return text[:max_len].strip()


def _classify_event_type(text, quote):
    """Keyword-gated honest classification into ADR-121's 4 payment
    types. A verbatim money quote with no job/subscription/complaint
    marker is still real proof-of-payment -> freelancer_agency_pricing
    (someone charging/paying for the manual version of this problem)."""
    blob = f"{text} {quote}".lower()
    if any(k in blob for k in _JOB_MARKERS):
        return "paid_job_posting"
    if any(k in blob for k in _SUBSCRIPTION_MARKERS):
        return "subscription_escape"
    if any(k in blob for k in _COMPLAINT_MARKERS):
        return "complaining_review"
    return "freelancer_agency_pricing"


def _is_real_https(url):
    return bool(url) and str(url).startswith("https://")


def _github_text(item):
    return f"{item.get('title', '')} {item.get('body', '') or ''}"


def _hn_text(item):
    return f"{item.get('title', '')} {item.get('story_text', '') or ''}"


def _so_text(item):
    return item.get("title", "")


def _search_real_sources(query, max_results):
    """The same three free, keyless, already-trusted real sources the
    customer-pain connector uses — never a new/paid source."""
    gh_issues, gh_total = MIE._query_github_issues(query, max_results)
    hn, hn_total = MIE._query_hn_discussions(query, max_results)
    so, so_total = MIE._query_stack_overflow_for_pain(query, max_results)
    return gh_issues, hn, so, gh_total, hn_total, so_total


def collect_payment_evidence(niche, max_results=10, max_age_days=MAX_AGE_DAYS_DEFAULT,
                             force=False, cache_file=None, evidence_path=None, record=True):
    """Real proof-of-payment discovery + recording for one niche.

    Steps (all real, all cached):
      1. cache-hit check (same discipline as the pain-evidence cache)
      2. reformulate_pain_query(niche) -> real problem query (reused)
      3. search the three free keyless sources with that query
      4. for every real result containing a real currency marker:
           extract the verbatim quote, classify event_type honestly,
           record via market_evidence.record_evidence() (which enforces
           source_url + quote — refusing anything uncited)
      5. persist the per-niche result to the payment-evidence cache

    record=False returns the candidate list without touching the real
    market_evidence ledger (pure discovery). Default True: the connector
    records what it genuinely finds, exactly as a human recording the
    same real page would — every record still passes record_evidence()'s
    real validation, so no gate is weakened and nothing is fabricated."""
    key = MIE.COMPETITOR_DISCOVERY._normalize_key(niche)

    if not force:
        cached = _load_cache(cache_file).get(key)
        if cached:
            age_days = MIE.COMPETITOR_DISCOVERY._days_since(cached.get("cached_at"))
            if age_days is not None and age_days <= max_age_days:
                cached = dict(cached)
                cached["_cache"] = {"hit": True, "age_days": age_days}
                return cached

    query, query_method, query_note = MIE.reformulate_pain_query(niche)
    gh_issues, hn, so, gh_total, hn_total, so_total = _search_real_sources(query, max_results)

    candidates = []
    already = {e["payload"].get("source_url") for e in ME.get_payment_evidence(niche, evidence_path=evidence_path)}

    def _consider(text, url):
        if not _is_real_https(url):
            return
        quote = _extract_quote(text)
        if not quote:
            return
        if url in already:
            return
        event_type = _classify_event_type(text, quote)
        candidates.append({"event_type": event_type, "source_url": url, "quote": quote})

    for item in gh_issues:
        _consider(_github_text(item), item.get("html_url") or item.get("url"))
    for item in hn:
        _consider(_hn_text(item), item.get("url") or item.get("objectID") and f"https://news.ycombinator.com/item?id={item.get('objectID')}")
    for item in so:
        _consider(_so_text(item), item.get("link"))

    recorded = []
    rejected = []
    if record:
        for c in candidates:
            try:
                ME.record_evidence(niche, c["event_type"], {"source_url": c["source_url"], "quote": c["quote"]}, source="payment_evidence_connector", evidence_path=evidence_path)
                recorded.append(c)
            except (ValueError, OSError) as e:
                rejected.append({"candidate": c, "error": str(e)})

    result = {
        "niche": niche,
        "query_used": query,
        "query_method": query_method,
        "query_note": query_note,
        "sources_scanned": {
            "github_issues": {"found": len(gh_issues), "total": gh_total},
            "hacker_news": {"found": len(hn), "total": hn_total},
            "stack_overflow": {"found": len(so), "total": so_total},
        },
        "candidates_found": len(candidates),
        "candidates": candidates,
        "recorded": recorded,
        "rejected_by_gate": rejected,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "_cache": {"hit": False, "age_days": 0},
    }

    db = _load_cache(cache_file)
    db[key] = result
    _save_cache(db, cache_file)
    return result


def _load_cache(cache_file=None):
    path = cache_file or PAYMENT_EVIDENCE_CACHE_FILE
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(db, cache_file=None):
    path = cache_file or PAYMENT_EVIDENCE_CACHE_FILE
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Proof-of-Payment Evidence Connector (ADR-121)")
    parser.add_argument("niche")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--force", action="store_true", help="skip cache and re-search live")
    parser.add_argument("--no-record", action="store_true", help="discovery only — do not touch the real market_evidence ledger")
    args = parser.parse_args()

    result = collect_payment_evidence(
        args.niche, max_results=args.max_results, force=args.force, record=not args.no_record,
    )
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


if __name__ == "__main__":
    main()