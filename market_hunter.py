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
no live market-research API integration anywhere in this factory.
"Scanning the market" here means combining a curated, real set of
professional business-problem categories (ADR-065's Strategic Production
Priority Ladder pivot, 2026-07-17 — retooled away from the original KDP/
Etsy consumer archetypes) with real Sensing Engine signals already flowing
into OPPORTUNITIES.md — never a fabricated live data pull. Every candidate
is then scored by profit_oracle's ladder_opportunity_score() (ADR-066), the
single, tested, ladder-aware scoring authority in this factory, not a
second, duplicate scorer.
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

# Retooled 2026-07-17 (ADR-065/ADR-068, MASTER_CHARTER.md §2, mission
# Step 4): every category now targets a real professional business problem
# (the "professional business problems" the mission asked for) instead of a
# KDP/Etsy consumer archetype, and is tagged with the Strategic Production
# Priority Ladder rank it belongs to (profit_oracle.LADDER_RANKS) so
# hunt_market() can score it with the new ladder_opportunity_score() gate
# (ADR-066) instead of the old flat score_opportunity() one. One KDP entry
# is kept, tagged "kdp_books" — books remain a real, supported (if
# deprioritized) track per MASTER_CHARTER.md §3 ("last/supporting, not shut
# down"), not deleted.
#
# The prior KDP/Etsy-flavored English list (planners/SVG templates/
# trackers) and its 1:1-translated Arabic predecessor are both preserved in
# git history (this same file, pre-2026-07-17) rather than deleted — same
# "no deletion of out-of-scope assets" policy ADR-020 already established.
SEED_CATEGORIES = [
    {"niche": "AI-powered compliance automation subscription system for accounting firms", "ladder": "ai_saas"},
    {"niche": "AI customer support automation platform for e-commerce businesses", "ladder": "ai_saas"},
    {"niche": "workflow automation system for logistics companies", "ladder": "b2b_systems"},
    {"niche": "inventory management system for wholesale distributors", "ladder": "b2b_systems"},
    {"niche": "automated invoice processing toolkit for small businesses", "ladder": "automation_tools"},
    {"niche": "automated social media scheduling tool for marketing agencies", "ladder": "automation_tools"},
    {"niche": "reusable API integration template bundle for SaaS developers", "ladder": "reusable_assets"},
    {"niche": "white-label client onboarding template system for B2B startups", "ladder": "reusable_assets"},
    {"niche": "compliance training course for financial advisors", "ladder": "educational"},
    {"niche": "printable monthly planner", "ladder": "kdp_books"},
]


def _generate_candidates(limit=10):
    """Returns up to `limit` (niche, ladder) tuples from SEED_CATEGORIES —
    a real, deterministic process, not a live market scan (see module
    docstring)."""
    return [(c["niche"], c["ladder"]) for c in SEED_CATEGORIES[:limit]]


# ADR-065 Step 3(b): closes the "Sensing Engine output -> market_hunter
# input" link. Before this fix, market_hunter.py only ever WROTE to
# OPPORTUNITIES.md (_append_to_opportunities() below) — the n8n Sensing
# Engine workflow (Openclaw_Sensing_Engine, server.js's /api/trends ->
# quality_gate()) already wrote real signals into that same shared file,
# but nothing ever read them back in as hunt candidates; profit_oracle.
# run_oracle() scored them later, separately, but market_hunter's own hunt
# never used them to generate/prioritize candidates. This reads them as a
# real, additional candidate source, distinguished from market_hunter's own
# prior output by the "market_hunter:" reason prefix _append_to_opportunities()
# always writes — anything else in the file came from somewhere else
# (Sensing Engine today; honestly labeled as "external", not assumed to be
# any one specific source).
def _read_sensing_engine_niches(limit=10, opps_file=None):
    opps_file = opps_file or OPPORTUNITIES_FILE
    if not os.path.exists(opps_file):
        return []
    line_re = re.compile(r'^-\s*\[(.+?)\]\s*(.+?)\s*—\s*(.+)$')
    niches = []
    seen = set()
    try:
        with open(opps_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception:
        return []
    for line in reversed(lines):  # most recent signals first
        m = line_re.match(line.strip())
        if not m:
            continue
        niche, reason = m.group(2).strip(), m.group(3).strip()
        if reason.startswith('market_hunter:'):
            continue  # our own prior output, not a new external signal
        niche_lower = niche.lower()
        if not niche or niche_lower in seen:
            continue
        seen.add(niche_lower)
        niches.append(niche)
        if len(niches) >= limit:
            break
    return niches


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
    """The main hunt: generate (niche, ladder) candidates → consult the
    Brain FIRST → score survivors via profit_oracle.ladder_opportunity_score()
    (ADR-066, the Strategic Production Priority Ladder gate) → keep accepted
    only → append to OPPORTUNITIES.md → re-run profit_oracle so
    GOLDEN_OPPORTUNITIES.md stays the single, consistent authority for the
    older, still-live score_opportunity() gate (this module never writes
    that file itself — see module docstring)."""
    seed_candidates = _generate_candidates(limit)  # [(niche, ladder), ...]
    seed_niches = [n for n, _ladder in seed_candidates]
    # Real link (ADR-065 Step 3(b)): Sensing Engine signals already sitting
    # in OPPORTUNITIES.md, not previously read back in as hunt input. These
    # carry no known ladder tag yet, so they default to "kdp_books" — the
    # same honest fallback profit_oracle.py/server.js's /finance use
    # elsewhere for untagged revenue, never a guessed different rank.
    sensing_niches = [n for n in _read_sensing_engine_niches(limit) if n not in seed_niches]
    sensing_candidates = [(n, "kdp_books") for n in sensing_niches]
    candidates = seed_candidates + sensing_candidates
    scanned = []
    skipped = []
    golden_catch = []

    for niche, ladder in candidates:
        should_skip, reason = _check_knowledge_brain(niche)
        brain_hits = _search_brain(niche.split()[0]) if niche.split() else []
        entry = {
            "niche": niche,
            "ladder": ladder,
            "brain_matches": len(brain_hits),
            "source": "sensing_engine" if niche in sensing_niches else "seed",
        }

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
            scored = PROFIT_ORACLE.ladder_opportunity_score(niche, ladder=ladder)
        except Exception as e:
            entry["error"] = str(e)
            skipped.append(entry)
            scanned.append(entry)
            continue

        entry.update({
            "ladder_score": scored["ladder_score"],
            "accepted": scored["accepted"],
            "price": scored["price"],
        })
        scanned.append(entry)

        if scored["accepted"]:
            entry["recommended_price"] = f"${scored['price']}"
            golden_catch.append(entry)
        else:
            entry["skip_reason"] = scored["reason"]
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
        "sensing_engine_linked_count": len(sensing_candidates),
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
        lines.append(
            f"- [{ts}] {entry['niche']} — market_hunter: ACCEPTED ladder={entry['ladder']} "
            f"({entry['ladder_score']}/100, ${entry['price']})\n"
        )
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
    # Concurrency note (STRUCTURAL_DIAGNOSIS.md disease #6, investigated
    # 2026-07-15): this block only runs when a human manually executes
    # `python market_hunter.py` (this __main__ demo, not hunt_market() — the
    # real automated path never touches REJECTED_NICHES.md). Its read-
    # modify-rewrite cleanup below could in theory clobber a real rejection
    # appended by factory_loop.js's separate process in the same instant.
    # Traced deliberately: hunt_market() itself never writes this file, so
    # the actual window is "a human runs this demo script by hand at the
    # exact moment factory_loop.js's own tick also calls
    # recordRejectedNiche()" — narrow, self-healing (a clobbered rejection
    # just gets re-evaluated and re-rejected next time), not a production
    # data-integrity risk. Not worth a cross-language file-locking library
    # for this specific, rare, non-catastrophic window; revisit only if this
    # demo path is ever wired into anything automated.
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
