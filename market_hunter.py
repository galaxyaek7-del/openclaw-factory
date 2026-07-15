#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Market Hunter (The Golden Hunter)

Per OPENCLAW_OS_CONSTITUTION.md's Golden Hunter Council: "The factory follows
opportunities, not platforms. Discover high-demand markets, profitable
niches." And per CONSTITUTION.md §19 (Golden Hunter): consult the Knowledge
Brain first, always — never re-propose a niche this factory already knows
is rejected or a duplicate.

Honesty note (same discipline as profit_oracle.py/inspectors.py): there is
no live Etsy/KDP/Google-Trends scraping or API integration anywhere in this
factory. "Scanning digital marketplaces" here means combining a curated,
real set of common profitable digital-product categories (planners,
templates, SVG cut files, trackers — genuine, publicly-known KDP/Etsy
niche archetypes) with the same seasonal calendar and keyword vocabulary
profit_oracle.py already uses — never a fabricated live data pull. Every
candidate is then scored by profit_oracle itself (the single, tested
scoring authority in this factory), not a second, duplicate scorer.
"""

import os
import re
import sys
import json
from datetime import datetime

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import profit_oracle as PROFIT_ORACLE
except Exception:
    PROFIT_ORACLE = None

try:
    import inspectors as INSPECTORS
except Exception:
    INSPECTORS = None

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
OPPORTUNITIES_FILE = os.path.join(FACTORY_DIR, 'OPPORTUNITIES.md')
REJECTED_NICHES_FILE = os.path.join(FACTORY_DIR, 'REJECTED_NICHES.md')  # factory_loop.js's circuit breaker
BRAIN_DIR = os.path.join(FACTORY_DIR, 'OpenClaw_Brain')
HUNT_LOG = os.path.join(FACTORY_DIR, 'market_hunter_runs.log')

MIN_BUTTER_VERDICT_SCORE = 60  # verdict != SKIP — same threshold used everywhere else in this factory

# Curated, real digital-product category archetypes (KDP/Etsy-style) — the
# closest honest substitute for "scanning marketplaces" without a live API.
# Reuses profit_oracle's own keyword vocabulary rather than redefining it,
# so a category's tier (premium/mid/recurring) is judged consistently
# everywhere in this factory, not just here.
#
# English (EU/US) per ADR-020 — corrected 2026-07-15 (STRUCTURAL_DIAGNOSIS.md
# disease #4): this list was still all-Arabic 3+ days after ADR-020 retargeted
# every new product at the English EU/US market, meaning every live Golden
# Hunter tick since 2026-07-12 was scanning the wrong market entirely. The
# 1:1-translated Arabic originals are preserved in git history (this same
# file, pre-2026-07-15) rather than deleted, per ADR-020's own "no deletion of
# out-of-scope Arabic assets" policy — a future Arabic-market decision should
# not have to start from zero.
SEED_CATEGORIES = [
    "printable monthly planner",
    "cuttable SVG design templates",
    "personal budget tracker",
    "daily habit tracker",
    "wedding planning journal",
    "professional resume templates",
    "monthly coaching subscription system",
    "professional presentation templates",
    "weekly meal planner",
    "personal project management system",
]

# Audience/qualifier phrases combined with a seed category to produce more
# specific candidates — reuses profit_oracle's SUBNICHE_QUALIFIERS list
# directly (see _generate_candidates()) rather than a second copy.


def _generate_candidates(limit=10):
    """Combines curated seed categories with profit_oracle's own seasonal
    calendar and subniche-qualifier vocabulary to produce candidate niche
    strings — a real, deterministic process, not a live market scan."""
    candidates = []
    now = datetime.now()

    seasonal_hits = []
    if PROFIT_ORACLE is not None:
        for kw, months in PROFIT_ORACLE.SEASONAL_KEYWORDS.items():
            if now.month in months:
                seasonal_hits.append(kw)
        # SEASONAL_KEYWORDS has both Arabic and English entries for the same
        # season (e.g. "العودة للمدارس" / "back to school") — every seed
        # category here is English (ADR-020), so prefer an English match to
        # avoid producing a mixed-language niche phrase.
        english_hits = [kw for kw in seasonal_hits if not re.search(r'[؀-ۿ]', kw)]
        if english_hits:
            seasonal_hits = english_hits

    # SUBNICHE_QUALIFIERS mixes English ("for beginners") and Arabic
    # ("للمبتدئين") entries — every seed category here is English (ADR-020),
    # so keep only the English qualifiers to avoid a mixed-language phrase.
    qualifiers = [q for q in PROFIT_ORACLE.SUBNICHE_QUALIFIERS if not re.search(r'[؀-ۿ]', q)] if PROFIT_ORACLE is not None else []

    for category in SEED_CATEGORIES:
        # Plain category on its own.
        candidates.append(category)
        # Seasonal variant, if anything is actually in-season right now.
        for kw in seasonal_hits[:1]:
            candidates.append(f"{category} {kw}")
        # One subniche-qualified variant per category for audience specificity.
        if qualifiers:
            candidates.append(f"{category} {qualifiers[hash(category) % len(qualifiers)]}")

    # De-duplicate while preserving order, then cap to `limit`.
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique[:limit]


def _read_rejected_niches():
    """Reads factory_loop.js's circuit-breaker memory (REJECTED_NICHES.md) —
    a plain markdown file, parsed directly rather than requiring a Node
    process to be running. Mirrors the exact format factory_loop.js writes."""
    if not os.path.exists(REJECTED_NICHES_FILE):
        return set()
    niches = set()
    line_re = re.compile(r'^\*\*النيتش:\*\*\s*(.+)$')
    with open(REJECTED_NICHES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            m = line_re.match(line.strip())
            if m:
                niches.add(m.group(1).strip().lower())
    return niches


def _search_brain(keyword, limit=5):
    """Real keyword search across OpenClaw_Brain/**/*.md — mirrors
    knowledge_brain.js's own logic in Python so this module never depends on
    a Node process being available. Used as an advisory signal (surfaced in
    reasoning), not a hard skip — a Brain mention isn't always "this exact
    niche failed," unlike REJECTED_NICHES.md/QUARANTINE.md which are."""
    if not keyword or not os.path.isdir(BRAIN_DIR):
        return []
    hits = []
    keyword_lower = keyword.lower()
    for root, _dirs, files in os.walk(BRAIN_DIR):
        for fname in files:
            if not fname.lower().endswith('.md'):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if keyword_lower in line.lower():
                            rel = os.path.relpath(fpath, BRAIN_DIR).replace(os.sep, '/')
                            hits.append({"file": rel, "line": i, "text": line.strip()})
                            if len(hits) >= limit:
                                return hits
            except Exception:
                continue
    return hits


def _check_knowledge_brain(niche):
    """CRITICAL per CONSTITUTION.md §19: consult the Knowledge Brain before
    ever proposing a candidate. Returns (should_skip: bool, reason: str|None).
    Three real, independent checks, cheapest first:
      1. factory_loop.js's circuit breaker (REJECTED_NICHES.md) — a hard skip
      2. inspectors.py's QUARANTINE.md history — a hard skip
      3. inspectors.py's generation-log duplicate check — a hard skip
    A Brain keyword match is logged into the result but does NOT by itself
    block a candidate — it's context, not a verdict."""
    niche_lower = niche.strip().lower()

    if niche_lower in _read_rejected_niches():
        return True, "مرفوض سابقاً في REJECTED_NICHES.md (قاطع الدائرة)"

    if INSPECTORS is not None:
        try:
            if niche_lower in INSPECTORS._read_quarantined_niches():
                return True, "مرفوض سابقاً في QUARANTINE.md (Dual Inspection)"
        except Exception:
            pass
        try:
            is_dup, dup_detail = INSPECTORS._is_duplicate(niche, None)
            if is_dup:
                return True, f"تكرار في سجل الإنتاج: {dup_detail}"
        except Exception:
            pass

    return False, None


def hunt_market(limit=10, write_opportunities=True):
    """The main hunt: generate candidates → consult the Brain FIRST → score
    survivors via profit_oracle → keep butter-tier only → append to
    OPPORTUNITIES.md → re-run profit_oracle so GOLDEN_OPPORTUNITIES.md stays
    the single, consistent authority (this module never writes that file
    itself — see module docstring)."""
    candidates = _generate_candidates(limit)
    scanned = []
    skipped = []
    golden_catch = []

    for niche in candidates:
        should_skip, reason = _check_knowledge_brain(niche)
        brain_hits = _search_brain(niche.split()[0]) if niche.split() else []
        entry = {"niche": niche, "brain_matches": len(brain_hits)}

        if should_skip:
            entry["skip_reason"] = reason
            skipped.append(entry)
            scanned.append(entry)
            continue

        if PROFIT_ORACLE is None:
            entry["error"] = "profit_oracle.py غير متوفر — لا يمكن التقييم"
            skipped.append(entry)
            scanned.append(entry)
            continue

        try:
            scored = PROFIT_ORACLE.score_opportunity(niche)
        except Exception as e:
            entry["error"] = str(e)
            skipped.append(entry)
            scanned.append(entry)
            continue

        entry.update({
            "profit_score": scored["profit_score"],
            "verdict": scored["verdict"],
            "butter_rating": scored["butter_rating"],
        })
        scanned.append(entry)

        if scored["profit_score"] >= MIN_BUTTER_VERDICT_SCORE:
            butter = PROFIT_ORACLE.butter_price(niche)
            entry["recommended_butter_price"] = f"${butter}"
            golden_catch.append(entry)
        else:
            entry["skip_reason"] = f"profit_score {scored['profit_score']} < {MIN_BUTTER_VERDICT_SCORE} (SKIP)"
            skipped.append(entry)

    if write_opportunities and golden_catch:
        _append_to_opportunities(golden_catch)
        if PROFIT_ORACLE is not None:
            try:
                PROFIT_ORACLE.run_oracle()  # profit_oracle remains the single writer of GOLDEN_OPPORTUNITIES.md
            except Exception:
                pass

    result = {
        "timestamp": datetime.now().isoformat(),
        "scanned_count": len(scanned),
        "skipped_count": len(skipped),
        "golden_count": len(golden_catch),
        "scanned": scanned,
        "golden_catch": golden_catch,
    }
    _log_hunt(result)
    return result


def _append_to_opportunities(golden_catch):
    """Feeds discovered golden niches into the same OPPORTUNITIES.md that
    n8n's /api/trends already writes to — one shared intake file, so
    profit_oracle.run_oracle() (the single GOLDEN_OPPORTUNITIES.md writer)
    doesn't need a second code path to understand market_hunter's output."""
    lines = []
    for entry in golden_catch:
        ts = datetime.now().isoformat()
        lines.append(f"- [{ts}] {entry['niche']} — market_hunter: {entry['verdict']} ({entry['profit_score']}/100)\n")
    try:
        with open(OPPORTUNITIES_FILE, 'a', encoding='utf-8') as f:
            f.writelines(lines)
    except Exception:
        pass


def _log_hunt(result):
    try:
        with open(HUNT_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    except Exception:
        pass


def main():
    if '--run' in sys.argv:
        result = hunt_market()
        print(json.dumps({
            "success": True,
            "scanned": result["scanned_count"],
            "skipped": result["skipped_count"],
            "golden": result["golden_count"],
        }, ensure_ascii=False))
        return

    # Demo mode: 3 sample scans chosen to show a real GOLDEN verdict, a real
    # SKIP verdict, and a real Brain-blocked skip — self-contained (scenario
    # 3 writes one temporary rejection entry and removes it immediately
    # after, leaving no lasting side effect on a fresh `python
    # market_hunter.py` run).
    print("=== 1. عيّنة تُتوقَّع GOLDEN (موسمية + اشتراك + تخصيص جمهور) ===")
    niche_golden = "اشتراك العودة للمدارس للمبتدئين"
    should_skip, reason = _check_knowledge_brain(niche_golden)
    if should_skip:
        print(json.dumps({"niche": niche_golden, "skipped": True, "reason": reason}, ensure_ascii=False))
    elif PROFIT_ORACLE is not None:
        print(json.dumps(PROFIT_ORACLE.score_opportunity(niche_golden), indent=2, ensure_ascii=False))
    print()

    print("=== 2. عيّنة تُتوقَّع SKIP (نيتش عام جداً بلا أي إشارة قوة) ===")
    niche_skip = "منتج"
    should_skip, reason = _check_knowledge_brain(niche_skip)
    if should_skip:
        print(json.dumps({"niche": niche_skip, "skipped": True, "reason": reason}, ensure_ascii=False))
    elif PROFIT_ORACLE is not None:
        print(json.dumps(PROFIT_ORACLE.score_opportunity(niche_skip), indent=2, ensure_ascii=False))
    print()

    print("=== 3. عيّنة تُحجَب بواسطة العقل المعرفي (رفض سابق حقيقي، مؤقت للعرض) ===")
    demo_rejected_niche = "نيتش تجريبي محجوب توضيحياً"
    _wrote_demo_entry = False
    try:
        if not os.path.exists(REJECTED_NICHES_FILE):
            with open(REJECTED_NICHES_FILE, 'w', encoding='utf-8') as f:
                f.write("# 🚫 Rejected Niches — ذاكرة قاطع الدائرة (Circuit Breaker)\n\n")
            _wrote_demo_entry = True
        with open(REJECTED_NICHES_FILE, 'a', encoding='utf-8') as f:
            f.write(f"## 🚫 {datetime.now().isoformat()}\n**النيتش:** {demo_rejected_niche}\n**السبب:** عرض توضيحي مؤقت\n\n")
        should_skip, reason = _check_knowledge_brain(demo_rejected_niche)
        print(json.dumps({"niche": demo_rejected_niche, "skipped": should_skip, "reason": reason}, ensure_ascii=False))
    finally:
        # Clean up: remove only the demo line(s) just added, or the whole
        # file if this demo was the one that created it — never touch any
        # real rejection recorded by factory_loop.js.
        try:
            with open(REJECTED_NICHES_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            content = re.sub(
                rf"## 🚫 [^\n]+\n\*\*النيتش:\*\* {re.escape(demo_rejected_niche)}\n\*\*السبب:\*\* عرض توضيحي مؤقت\n\n",
                "", content)
            if _wrote_demo_entry:
                os.remove(REJECTED_NICHES_FILE)
            else:
                with open(REJECTED_NICHES_FILE, 'w', encoding='utf-8') as f:
                    f.write(content)
        except Exception:
            pass


if __name__ == '__main__':
    main()
