#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Galaxy Forge — Global Market Intelligence Engine (ADR-043)

ONE integrated decision system, not separate tools — per explicit
instruction. Every "engine" below is a section of this one module,
reusing real building blocks already built and tested rather than
duplicating them:
  - Demand/Margin/Risk/Confidence: profit_oracle.py (ADR-026/038/039/041)
  - Competitor discovery + Opportunity Gap: competitor_discovery.py (ADR-042)
  - Customer Pain: new in this file (real GitHub Issues + HN search)
  - Pricing Intelligence: NOT built — see honesty note below

Honesty triage, done before writing any code (per the explicit
instruction to research first and never fabricate):

  Customer Pain    -> REAL (GitHub Issues Search API + HN Algolia, both
                      free/keyless). Reddit and Product Hunt sources
                      remain Unknown (credentials / required official
                      contact — see BLOCKERS.md).
  Demand           -> Evergreen/Seasonal REUSES profit_oracle's real
                      date-based season check. Exploding/Declining
                      requires the SAME signal measured at multiple past
                      points in time — this factory has only ever taken
                      single snapshots so far, so that classification is
                      honestly "Unknown — insufficient history" today,
                      not a guess. It will become real automatically once
                      competitor_discovery.py's cached database
                      accumulates repeated real snapshots over time.
  Pricing          -> NOT BUILT. Real competitor pricing would require
                      fetching and parsing each competitor's actual
                      pricing page live — unreliable extraction (many
                      pages have no clear price, or hide it behind
                      signup), and building a scraper with unvalidated
                      accuracy would risk presenting confidently-wrong
                      prices as real data, which is worse than an honest
                      "Unknown". Registered as DISCOVERY with a concrete
                      unlock plan, not attempted here.
  Market Gap       -> REUSES competitor_discovery.compute_opportunity_gap()
                      (already real/estimated, ADR-042) — not rebuilt.
  Profit           -> REUSES profit_oracle's real fee+cost-aware margin
                      (ADR-041) — not rebuilt. CLV/upsell/cross-sell/
                      repurchase remain DISCOVERY (zero customers).
  Risk             -> REUSES profit_oracle._score_risk() (ADR-039) — not
                      rebuilt.
  AI CEO           -> NEW: a transparent, deterministic decision function
                      over the real components above. Not a black box —
                      every decision cites the specific real evidence
                      that produced it, and an overall confidence gate
                      pushes toward WAIT when the underlying data is too
                      thin to decide on, rather than a false-confident
                      BUILD/REJECT.

Standalone orchestrator — like market_hunter.py/competitor_discovery.py,
run deliberately, never invoked inside profit_oracle.py's synchronous
scoring path (same reasoning as ADR-041/042: live network calls stay out
of the fast production-gating code).
"""

import os
import re
import sys
import json
import argparse
import urllib.parse
from datetime import datetime, timezone

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import profit_oracle as PROFIT_ORACLE
import competitor_discovery as COMPETITOR_DISCOVERY
from market_intelligence_core import http_client as MIC_HTTP_CLIENT

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DB_FILE = os.path.join(FACTORY_DIR, 'data', 'market_intelligence_analyses.jsonl')

# Evidence Network (ADR-128, 2026-07-25): analyze_customer_pain() was a
# real but UNCACHED live search on every call -- competitor_discovery.py
# had already solved this exact problem for competitor data
# (load_database()/save_database()/MAX_AGE_DAYS_DEFAULT). Mirrors that
# same real pattern here so a real pain search becomes proprietary,
# accumulated intelligence instead of a repeated live query -- "every new
# connector must increase long-term intelligence for every future
# opportunity," not just the one call that triggered it. A longer default
# window than competitor_discovery's 7 days: customer pain signals (real
# GitHub Issues/HN/Stack Overflow activity) move slower than a
# competitor roster.
PAIN_EVIDENCE_DB_FILE = os.path.join(FACTORY_DIR, 'data', 'pain_evidence_cache.json')
PAIN_EVIDENCE_MAX_AGE_DAYS_DEFAULT = 14

GITHUB_ISSUES_SEARCH_URL = "https://api.github.com/search/issues"
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

# Real, human-written pain language — not invented, these are the actual
# phrases people use when a product doesn't solve their problem well.
PAIN_KEYWORDS = [
    "frustrating", "annoying", "wish there was", "no good solution", "hate that",
    "so hard to", "can't find a tool", "still no", "why is there no",
]
WILLINGNESS_TO_PAY_KEYWORDS = [
    "would pay for", "shut up and take my money", "take my money", "i'd pay",
    "worth paying for", "happily pay",
]


# ── CUSTOMER PAIN INTELLIGENCE (real GitHub Issues + HN search) ──

def _http_get_json(url, timeout=10):
    """ADR-049: delegates to market_intelligence_core.http_client — the
    urllib logic itself now lives in exactly one place (it was
    byte-for-byte duplicated with competitor_discovery.py's own copy
    before this). Kept as a real local function (not a bare re-export)
    so `@patch("market_intelligence_engine._http_get_json")` in
    tests/test_market_intelligence_engine.py keeps intercepting every
    caller below unchanged."""
    return MIC_HTTP_CLIENT.http_get_json(url, timeout=timeout)


def _query_github_issues(query, limit=10):
    """Real GitHub Issues search — genuine user complaints/requests, not
    fabricated. Returns [] on any network failure, never raises."""
    try:
        q = f"{query} in:title,body is:issue"
        url = f"{GITHUB_ISSUES_SEARCH_URL}?q={urllib.parse.quote(q)}&sort=reactions&order=desc&per_page={limit}"
        data = _http_get_json(url)
        return data.get('items', [])[:limit], data.get('total_count', 0)
    except Exception:
        return [], 0


def _query_hn_discussions(query, limit=10):
    try:
        url = f"{HN_SEARCH_URL}?query={urllib.parse.quote(query)}&tags=story&hitsPerPage={limit}"
        data = _http_get_json(url)
        return data.get('hits', [])[:limit], data.get('nbHits', 0)
    except Exception:
        return [], 0


def _count_keyword_hits(text, keywords):
    text_lower = (text or '').lower()
    return sum(1 for k in keywords if k in text_lower)


# ── SEMANTIC QUERY REFORMULATION (Opportunity Rejection Investigation,
# 2026-07-22) ──
#
# Root cause, confirmed directly against this factory's own real history:
# 6 of the 8 highest-scoring real opportunities ever scored (86-90.5/100,
# far above every acceptance bar) returned ZERO real customer-pain matches,
# because the search queried GitHub Issues/HN for the literal branded
# product name ("AI Agent Blueprint for Freelance Security Pentesting
# Automation") -- a phrase no real developer would ever type into a bug
# report. It searched for the pitch, not the pain. This was never a
# scoring-threshold problem; it was a query-design defect starving good
# candidates of the evidence that would let them clear the AI-CEO's
# confidence gate.
#
# Fix: reformulate the niche into a natural problem-description query
# before searching -- real semantic understanding via the one real LLM
# call this factory already has (book_generator.groq_chat(), same
# model/key/cost-logging as every other real Groq call here), not a
# second keyword list dressed up as "semantic". Degrades honestly in
# strict order, never fabricates a query, never silently hides which
# method actually ran:
#   1. groq_semantic       -- real LLM call succeeds
#   2. deterministic_fallback -- Groq unavailable/fails: real (not
#      invented) string manipulation, stripping common template/marketing
#      scaffolding words so the remainder reads closer to a problem domain
#   3. literal_fallback    -- both above produced nothing usable: the
#      original (pre-fix) behavior, used as an absolute last resort, never
#      silently passed off as an improvement

_TEMPLATE_WORDS_TO_STRIP = [
    "ai agent blueprint for", "ai agent blueprint", "blueprint for", "blueprint",
    "automation platform for", "automation system for", "automation tool for",
    "automation toolkit for", "automation for", "automation",
    "platform for", "system for", "toolkit for", "tool for",
]


def _deterministic_query_fallback(niche):
    """No Groq available -- a real, deterministic simplification (never a
    guess at meaning): strip common template/marketing scaffolding words
    so the remaining phrase reads closer to a real problem domain. Weaker
    signal than the Groq-based reformulation, but still strictly better
    than searching the literal branded pitch verbatim."""
    q = (niche or "").lower()
    for phrase in _TEMPLATE_WORDS_TO_STRIP:
        q = q.replace(phrase, " ")
    q = re.sub(r"\s+", " ", q).strip()
    return q or niche


def reformulate_pain_query(niche):
    """Returns (query, method, note). Never raises -- a reformulation
    failure must never break customer-pain analysis, it just falls back
    to a weaker (but still real, still logged) query."""
    niche = str(niche or "").strip()
    if not niche:
        return niche, "literal_fallback", "نيتش فارغ"

    try:
        # Galaxy Forge Strategic Principle (2026-07-23), multi-model
        # orchestration: routes through ai_capability.orchestrator.
        # generate() instead of calling book_generator.groq_chat()
        # directly -- the real provider is now chosen by
        # ai_capability.evaluator.recommend_for_task() (evidence-based,
        # never a hardcoded vendor), not a hardcoded import. Behavior is
        # unchanged today (Groq is the only real, measured provider), but
        # the moment a second provider gets real credentials and real
        # usage data, this call site adopts it automatically, with zero
        # further code change here.
        from ai_capability import orchestrator
        system = (
            "You extract the real-world problem a product idea solves. "
            "Respond with ONLY a short phrase (5-12 words) describing the "
            "underlying frustration or task, phrased the way someone would "
            "describe it in a support ticket, bug report, or forum post -- "
            "no product names, no marketing language, no punctuation beyond spaces."
        )
        # cost_context must be a dict, matching every other real groq_chat()
        # caller (book_generator.py) -- knowledge_graph/build.py reads
        # context.niche to build a real AIProvider edge; a bare string here
        # broke that assumption (found live, 2026-07-22).
        response = orchestrator.generate(
            "query_reformulation", system, niche, max_tokens=40, retries=1,
            cost_context={"niche": niche, "purpose": "customer_pain_query_reformulation"},
        )
        query = (response["content"] or "").strip().strip('"').strip("'").strip()
        if query and len(query) >= 5:
            return query, f"{response['provider']}_semantic", None
        return _deterministic_query_fallback(niche), "deterministic_fallback", f"رد {response['provider']} فارغ أو قصير جداً ليكون استعلاماً حقيقياً"
    except Exception as e:
        return _deterministic_query_fallback(niche), "deterministic_fallback", f"Groq غير متاح: {e}"


def _query_stack_overflow_for_pain(query, limit=10):
    """Reuses multi_source_intelligence's real, already-tested Stack
    Exchange connector verbatim (Opportunity Rejection Investigation,
    2026-07-22, mission point 2: expand evidence collection) -- a genuine
    third independent source, not a re-implementation. Its search API
    returns title/view_count/answer_count/score only (no body text), so
    keyword-hit counting here is honestly title-only -- a real but
    narrower signal than GitHub Issues/HN, never presented as equivalent."""
    try:
        from multi_source_intelligence.connectors.stack_overflow import _query_stack_overflow
        items = _query_stack_overflow(query, max_results=limit)
        return items, len(items)
    except Exception:
        return [], 0


def _load_pain_db(db_file=None):
    db_file = db_file or PAIN_EVIDENCE_DB_FILE
    if not os.path.exists(db_file):
        return {}
    try:
        with open(db_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_pain_db(db, db_file=None):
    db_file = db_file or PAIN_EVIDENCE_DB_FILE
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    with open(db_file, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def analyze_customer_pain(niche, max_results=10, db_file=None, max_age_days=PAIN_EVIDENCE_MAX_AGE_DAYS_DEFAULT, force=False):
    """Real signal only: severity from real reaction/comment/view counts,
    frequency from real result counts, willingness-to-pay from real
    keyword presence in real issue/discussion/question text. Reddit and
    Product Hunt are explicitly Unknown — no access today (BLOCKERS.md).

    Opportunity Rejection Investigation (2026-07-22): searches a real
    reformulated problem-description query (reformulate_pain_query()),
    never the literal niche/product name -- see that function's docstring
    for why. Also now checks Stack Overflow, a genuine third real source
    (mission point 2), alongside GitHub Issues and Hacker News.

    Evidence Network (ADR-128, 2026-07-25): now cached, same real
    "don't redo the full search unless needed" discipline
    competitor_discovery.get_or_refresh_competitors() already established
    -- db_file/max_age_days/force mirror that function's own real
    parameters exactly. Real callers never pass db_file (uses the real
    shared data/pain_evidence_cache.json); tests always override it."""
    key = COMPETITOR_DISCOVERY._normalize_key(niche)
    if not force:
        cached = _load_pain_db(db_file).get(key)
        if cached:
            age_days = COMPETITOR_DISCOVERY._days_since(cached.get('cached_at'))
            if age_days is not None and age_days <= max_age_days:
                result = dict(cached)
                result['_cache'] = {"hit": True, "age_days": age_days}
                return result

    query, query_method, query_note = reformulate_pain_query(niche)

    issues, issues_total = _query_github_issues(query, max_results)
    discussions, hn_total = _query_hn_discussions(f"{query} problem", max_results)
    so_questions, so_total = _query_stack_overflow_for_pain(query, max_results)

    severity_signals = []
    pain_hits = 0
    payment_hits = 0
    for issue in issues:
        text = f"{issue.get('title', '')} {issue.get('body', '') or ''}"
        reactions = (issue.get('reactions') or {}).get('total_count', 0)
        comments = issue.get('comments', 0)
        severity_signals.append(reactions + comments)
        pain_hits += _count_keyword_hits(text, PAIN_KEYWORDS)
        payment_hits += _count_keyword_hits(text, WILLINGNESS_TO_PAY_KEYWORDS)
    for d in discussions:
        text = f"{d.get('title', '')} {d.get('story_text', '') or ''}"
        severity_signals.append(d.get('points', 0) + d.get('num_comments', 0))
        pain_hits += _count_keyword_hits(text, PAIN_KEYWORDS)
        payment_hits += _count_keyword_hits(text, WILLINGNESS_TO_PAY_KEYWORDS)
    for q in so_questions:
        text = q.get('title', '') or ''
        severity_signals.append(q.get('view_count', 0) // 100 + q.get('answer_count', 0) * 5)
        pain_hits += _count_keyword_hits(text, PAIN_KEYWORDS)
        payment_hits += _count_keyword_hits(text, WILLINGNESS_TO_PAY_KEYWORDS)

    avg_severity = round(sum(severity_signals) / len(severity_signals), 1) if severity_signals else None
    frequency = issues_total + hn_total + so_total

    if not issues and not discussions and not so_questions:
        pain_score = None
        confidence = "low"
        reason = f"لا نتائج حقيقية من GitHub Issues أو Hacker News أو Stack Overflow لاستعلام \"{query}\" — لا يمكن تقييم الألم بلا دليل"
    else:
        # Real, bounded, explainable combination — not a fabricated single
        # number: frequency (log-scaled like ADR-038/041) + real severity
        # signal + real willingness-to-pay keyword presence.
        import math
        freq_score = max(0, min(100, round(20 * math.log10(frequency + 1))))
        severity_score = max(0, min(100, round((avg_severity or 0) * 2)))
        payment_score = min(100, payment_hits * 25)
        pain_score = round(freq_score * 0.4 + severity_score * 0.4 + payment_score * 0.2)
        confidence = "medium" if (len(issues) + len(discussions) + len(so_questions)) >= 5 else "low"
        reason = (
            f"{len(issues)} GitHub issue حقيقي (من أصل {issues_total} إجمالاً)، "
            f"{len(discussions)} نقاش HN حقيقي (من أصل {hn_total} إجمالاً)، "
            f"{len(so_questions)} سؤال Stack Overflow حقيقي (من أصل {so_total} إجمالاً)، "
            f"{pain_hits} إشارة ألم لغوية حقيقية، {payment_hits} إشارة استعداد دفع حقيقية "
            f"(استعلام: \"{query}\", طريقة: {query_method})"
        )

    result = {
        "pain_score": pain_score,
        "confidence": confidence,
        "reason": reason,
        # Full explainability (mission point 4): exactly what was searched
        # and how that query was produced, never hidden inside "reason".
        "query_used": query,
        "query_method": query_method,
        "query_note": query_note,
        "real_evidence": {
            "github_issues_found": len(issues),
            "github_issues_total": issues_total,
            "hn_discussions_found": len(discussions),
            "hn_discussions_total": hn_total,
            "stack_overflow_found": len(so_questions),
            "stack_overflow_total": so_total,
            "avg_severity_signal": avg_severity,
            "pain_language_hits": pain_hits,
            "willingness_to_pay_hits": payment_hits,
        },
        "unknown_sources": {
            "reddit": "لا بيانات اعتماد Reddit API متوفرة (BLOCKERS.md)",
            "product_hunt": "يحتاج تواصلاً رسمياً مسبقاً قبل استخدام تجاري",
            "reviews_marketplaces": "لا API مجاني لمراجعات Amazon/Etsy",
        },
    }

    # Evidence Network (ADR-128): persist this real search so the NEXT
    # call for this same niche (within max_age_days) is a real, free
    # cache hit instead of a repeated live query -- proprietary
    # accumulated intelligence, not a one-off lookup.
    result['cached_at'] = datetime.now(timezone.utc).isoformat()
    result['_cache'] = {"hit": False, "age_days": 0}
    db = _load_pain_db(db_file)
    db[key] = result
    _save_pain_db(db, db_file)
    return result


# ── DEMAND CLASSIFICATION (Evergreen/Seasonal real; Exploding/Declining honest) ──

def classify_demand_pattern(niche, now=None):
    """Evergreen vs Seasonal reuses profit_oracle's real, date-based
    seasonal keyword match — not re-derived. Exploding/Declining needs the
    same signal at multiple past points in time, which this factory has
    never collected before competitor_discovery.py's cache started
    accumulating snapshots today — honestly Unknown until real history
    exists, not guessed from a single snapshot."""
    now = now or datetime.now()
    niche_lower = niche.lower()
    for kw, months in PROFIT_ORACLE.SEASONAL_KEYWORDS.items():
        if kw in niche_lower:
            in_season = now.month in months
            return {
                "pattern": "Seasonal",
                "confidence": "high",
                "reason": f"يطابق كلمة موسمية حقيقية '{kw}' — {'في موسمه الآن' if in_season else 'خارج موسمه حالياً'}",
            }
    return {
        "pattern": "Evergreen (افتراضي) — Exploding/Declining: Unknown",
        "confidence": "low",
        "reason": (
            "لا كلمة موسمية مطابقة — يُفترَض دائم (evergreen) كافتراض محايد، لا دليل قوي. "
            "Exploding/Declining تحتاج نفس الإشارة (نقاط HN/نجوم GitHub) مقيسة عبر نقاط زمنية متعددة حقيقية — "
            "لا تاريخ متعدد النقاط متوفر بعد لهذا النيتش (يتراكم تلقائياً عبر data/competitor_database.json مستقبلاً)."
        ),
    }


# ── AI CEO — transparent decision synthesis over real components only ──

DECISIONS = ("BUILD", "IMPROVE", "WAIT", "REJECT", "PIVOT")


def ai_ceo_decision(analysis):
    """A deterministic decision TREE over already-real/estimated
    components — not a black box, not a new invented signal. Every branch
    cites the specific real evidence behind it. An overall low-confidence
    gate pushes toward WAIT rather than a false-confident BUILD/REJECT,
    per the explicit 'always show confidence' rule."""
    risk = analysis.get("risk", {})
    scores = analysis.get("scores", {})
    pain = analysis.get("customer_pain", {})
    opportunity_gap = analysis.get("opportunity_gap")
    confidence = analysis.get("confidence", {})

    evidence = []

    if risk.get("level") in ("blocked", "high"):
        evidence.append(f"مخاطرة {risk.get('level')}: {'; '.join(risk.get('notes', []))}")
        return {"decision": "REJECT", "evidence": evidence, "confidence_gate": "n/a — risk overrides confidence"}

    # Bug found in self-audit (2026-07-15): mapping pain's qualitative
    # "medium" confidence to 100 — the theoretical ceiling — inflated the
    # average enough to clear the WAIT gate on genuinely middling evidence,
    # undermining the whole point of the gate. Fixed to the SAME numeric
    # scale profit_oracle._score_confidence() already uses (80/55/30 for
    # high/medium/low) so both confidence sources are actually comparable,
    # not two different scales averaged together.
    PAIN_CONFIDENCE_SCALE = {"high": 80, "medium": 55, "low": 30}
    confidence_values = [v for v in [
        confidence.get("score"),
        PAIN_CONFIDENCE_SCALE.get(pain.get("confidence")),
    ] if v is not None]
    avg_confidence = round(sum(confidence_values) / len(confidence_values)) if confidence_values else 0

    if avg_confidence < 40:
        evidence.append(f"متوسط ثقة عام منخفض ({avg_confidence}/100) — بيانات حقيقية غير كافية بعد لاتخاذ قرار واثق")
        evidence.append(f"تفصيل: confidence.note={confidence.get('note')}; customer_pain.reason={pain.get('reason')}")
        return {"decision": "WAIT", "evidence": evidence, "confidence_gate": avg_confidence}

    if opportunity_gap is not None and opportunity_gap >= 65 and pain.get("pain_score") and pain["pain_score"] >= 50:
        evidence.append(f"فجوة فرصة حقيقية عالية ({opportunity_gap}/100) + ألم عملاء حقيقي ({pain['pain_score']}/100): {pain.get('reason')}")
        return {"decision": "BUILD", "evidence": evidence, "confidence_gate": avg_confidence}

    if scores.get("competition", 100) <= 30:
        evidence.append(f"منافسة حقيقية عالية جداً (competition_score={scores.get('competition')}/100) — يحتاج تمايزاً واضحاً قبل البناء")
        return {"decision": "PIVOT", "evidence": evidence, "confidence_gate": avg_confidence}

    if opportunity_gap is not None and 40 <= opportunity_gap < 65:
        evidence.append(f"فجوة فرصة متوسطة ({opportunity_gap}/100) — قابل للتحسين على أساس موجود، لا بناء من الصفر")
        return {"decision": "IMPROVE", "evidence": evidence, "confidence_gate": avg_confidence}

    evidence.append(f"لا دليل حقيقي كافٍ بعد لأي من BUILD/IMPROVE/PIVOT/REJECT بثقة (فجوة الفرصة={opportunity_gap}, ألم العملاء={pain.get('pain_score')})")
    return {"decision": "WAIT", "evidence": evidence, "confidence_gate": avg_confidence}


# ── ORCHESTRATION — one integrated analysis, not separate tool calls ──

def analyze_opportunity(niche, external_signal=None, tier="tier4", max_results=10, analysis_db_file=None):
    """The one integrated entry point — calls every real engine above and
    profit_oracle/competitor_discovery, combines into one analysis, and
    lets ai_ceo_decision() synthesize a single evidence-based decision.

    Bug found in self-audit (2026-07-15): an empty/blank niche raised an
    uncaught ValueError from profit_oracle.score_opportunity() — every
    other function in this file degrades honestly (None/Unknown) rather
    than crashing; this one didn't. Fixed to match."""
    niche = str(niche or '').strip()
    if not niche:
        return {
            "niche": niche,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "error": "لا نيتش صالح — لا يمكن تحليل نص فارغ",
            "ai_ceo": {"decision": "WAIT", "evidence": ["لا نيتش صالح لتحليله"], "confidence_gate": 0},
        }
    scored = PROFIT_ORACLE.opportunity_score(niche, tier=tier, external_signal=external_signal)
    competitors = COMPETITOR_DISCOVERY.get_or_refresh_competitors(niche, max_results=max_results)
    pain = analyze_customer_pain(niche, max_results=max_results)
    demand_pattern = classify_demand_pattern(niche)
    # Strategic Autonomy follow-up (Evidence Governance diagnostic, verified
    # against all 1,344 real historical decisions with zero mismatches
    # against the buggy version): compute_opportunity_gap(demand, competition)
    # expects raw competition INTENSITY (high=bad -- see its own docstring
    # "high demand + low competition = high gap" and its existing tests,
    # e.g. test_high_demand_low_competition_is_high_gap passes
    # competition_score=10 for a LOW-competition case). But
    # competition_favorability is already inverted the OTHER way (high=good,
    # i.e. low real competition) -- profit_oracle.py's own comment: "already
    # high=favorable". Passing it in directly double-inverted every real
    # evaluation, silently punishing genuinely low-competition niches
    # instead of rewarding them. This has suppressed opportunity_gap by
    # ~20-30 points on every one of 1,344 real evaluations -- confirmed
    # this is the reason opportunity_gap has never once reached the BUILD
    # threshold (65) in this factory's real history; the corrected formula
    # clears it for 1,263/1,344 (94%) of those same real records.
    # Un-inverting back to raw intensity here (100 - favorability) restores
    # compute_opportunity_gap()'s own documented contract without changing
    # that function itself or its existing, correct tests.
    opportunity_gap = COMPETITOR_DISCOVERY.compute_opportunity_gap(
        scored["components"]["market_demand"], 100 - scored["components"]["competition_favorability"]
    )

    analysis = {
        "niche": niche,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "scores": scored["components"],
        "risk": scored["risk"],
        "confidence": scored["confidence"],
        # Opportunity Intelligence Round 2 (2026-07-22): scored (profit_
        # oracle.opportunity_score()) already computes this -- was silently
        # discarded before this fix, same pattern as record_ladder_decision()
        # (decision_engine/engine.py) found and fixed the same day. .get()
        # so a caller/mock on the older pre-defensibility shape degrades to
        # None rather than raising KeyError.
        "defensibility": scored.get("defensibility"),
        # Strategic Opportunity Intelligence Engine (2026-07-22): same
        # proactive persistence -- scored already computes these too.
        "market_signal": scored.get("market_signal"),
        "ai_leverage": scored.get("ai_leverage"),
        "customer_pain": pain,
        "demand_pattern": demand_pattern,
        "competitors": {"total_found": competitors["total_found"], "by_category": competitors["by_category"]},
        "opportunity_gap": opportunity_gap,
        "pricing": {
            "recommended_price": scored["recommended_price"],
            "note": "تقدير من فئة كلمات مفتاحية فقط [ADR-041] — لا سعر منافس حقيقي مُجمَّع بعد؛ Price Position/Pricing Power/Revenue Potential: Unknown — يحتاج جلب أسعار منافسين حقيقية من صفحاتهم العامة، غير مبني بعد (خطر دقة استخلاص، ADR-043)",
        },
    }
    analysis["ai_ceo"] = ai_ceo_decision(analysis)

    try:
        target_file = analysis_db_file or ANALYSIS_DB_FILE
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        with open(target_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(analysis, ensure_ascii=False) + '\n')
    except Exception:
        pass  # storing history must never break returning a real analysis

    return analysis


def main():
    parser = argparse.ArgumentParser(description="Global Market Intelligence Engine (ADR-043)")
    parser.add_argument('--analyze', metavar='NICHE', help="Run a full integrated analysis for a niche")
    parser.add_argument('--tier', default='tier4')
    args = parser.parse_args()

    if args.analyze:
        result = analyze_opportunity(args.analyze, tier=args.tier)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    parser.print_help()


if __name__ == '__main__':
    main()
