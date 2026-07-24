#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Reality Mode (2026-07-24).

Formalizes, as one real named taxonomy, the discipline this entire
session already followed informally in every module built today
(`{"value": None, "reason": ...}`, `_unknown()`, `"maturity": "REAL"`
vs `"DISCOVERY"`): every fact this factory reports is one of exactly
four real evidence levels.

    VERIFIED_REALITY — a directly-observed external fact (a real
        logged Groq cost, a real Paddle/Gumroad sale, a real fetched
        HN/GitHub result, a real recorded board vote).
    ESTIMATED — a real, disclosed proxy or heuristic computed FROM real
        inputs, but not itself a direct observation (a discussion-
        volume demand proxy, a ladder-based automation-potential
        constant, a coarse b2b/b2c classification).
    SIMULATED — a real dry-run or hypothetical value, explicitly marked
        as such (e.g. a `dry_run: true` publish attempt) — never
        presented as if it were a live result.
    UNKNOWN — no real signal exists yet. Always carries a real, stated
        reason — never a bare null.

**Scope decision, made deliberately rather than left implicit:** this
module does NOT rewrite every existing module's output shape today.
Retrofitting ~15 modules built across this session (value_engine.py,
market_memory.py, growth_engine.py, commercial_intelligence.py,
investment_pipeline.py, portfolio_engine.py, production_blueprint.py,
execution_status.py, and more) to construct every field through this
module's own constructors would be a large, mechanical, regression-risk
rewrite spanning the whole codebase — exactly the kind of sweeping,
unreviewed change this factory's own engineering discipline (regression
first, no architectural shortcuts) argues against doing in one pass.

Instead: `classify_existing_field()` and `reality_audit()` are a real,
generic ADAPTER — they read any existing report's real, already-
established shapes (the `{"value": None, "reason": ...}` / `_unknown()`
/ `{"maturity": ...}` conventions already used everywhere) and classify
them onto the 4 levels without requiring the underlying module to
change at all. This is how "every report... must expose its evidence
level" is satisfied today: wrap any existing report through
`reality_audit()`. Going forward, "every future module must inherit
this rule automatically" means new modules should construct fields with
this module's own `verified()`/`estimated()`/`simulated()`/`unknown()`
directly, which `reality_audit()` also recognizes natively (an
`evidence_level` key already present is trusted, never re-classified).
"""

from datetime import datetime, timezone

VERIFIED_REALITY = "VERIFIED_REALITY"
ESTIMATED = "ESTIMATED"
SIMULATED = "SIMULATED"
UNKNOWN = "UNKNOWN"

_LEVELS = (VERIFIED_REALITY, ESTIMATED, SIMULATED, UNKNOWN)

_PROXY_WORDS = ("proxy", "تقدير", "تقريبي", "estimate", "heuristic", "best-effort", "best effort")


def verified(value, source):
    """A real, directly-observed external fact."""
    return {"evidence_level": VERIFIED_REALITY, "value": value, "source": source}


def estimated(value, basis):
    """A real, disclosed proxy/heuristic computed from real inputs."""
    return {"evidence_level": ESTIMATED, "value": value, "basis": basis}


def simulated(value, note):
    """A real dry-run/hypothetical value, explicitly marked."""
    return {"evidence_level": SIMULATED, "value": value, "note": note}


def unknown(reason):
    """No real signal exists yet — always carries a real, stated reason."""
    return {"evidence_level": UNKNOWN, "value": None, "reason": reason}


def classify_existing_field(field):
    """Real, best-effort classification of an already-existing field
    (from any module built before this one existed) onto the 4 levels
    — never rewrites the field, only reads its real, already-
    established shape. Conservative by design: an unwrapped raw value
    with no marker either way defaults to ESTIMATED, never VERIFIED_
    REALITY — this factory refuses to claim false certainty for a
    field this classifier cannot actually confirm is a direct
    observation."""
    if isinstance(field, dict):
        if field.get("evidence_level") in _LEVELS:
            return field["evidence_level"]
        if field.get("dry_run") is True:
            return SIMULATED
        if field.get("answer") == "Unknown":
            return UNKNOWN
        if "value" in field and field.get("value") is None and "reason" in field:
            return UNKNOWN
        if field.get("maturity") == "DISCOVERY":
            return UNKNOWN
        if field.get("maturity") == "REAL":
            return VERIFIED_REALITY
        note_text = " ".join(str(field.get(k, "")) for k in ("note", "reason", "basis")).lower()
        if any(w in note_text for w in _PROXY_WORDS):
            return ESTIMATED
        return ESTIMATED
    if field is None:
        return UNKNOWN
    return ESTIMATED


def reality_audit(report, _path=""):
    """Walks any existing report dict/list recursively, classifying
    every leaf value via classify_existing_field(). Returns a real,
    disclosed breakdown — counts and the exact field paths at each
    level, never a bare score with no way to audit it."""
    counts = {level: 0 for level in _LEVELS}
    paths = {level: [] for level in _LEVELS}

    def _walk(node, path):
        if isinstance(node, dict) and set(node.keys()) & {"evidence_level", "value", "answer", "maturity", "dry_run"}:
            level = classify_existing_field(node)
            counts[level] += 1
            paths[level].append(path)
            return
        if isinstance(node, dict):
            for k, v in node.items():
                _walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk(v, f"{path}[{i}]")
        else:
            counts[ESTIMATED] += 1
            paths[ESTIMATED].append(path)

    _walk(report, _path)
    total = sum(counts.values())
    return {
        "counts": counts,
        "total_fields": total,
        "verified_reality_pct": round(100 * counts[VERIFIED_REALITY] / total, 1) if total else None,
        "paths": paths,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def compute_company_reality_score(decisions_path=None, evidence_path=None, db_file=None, board_path=None):
    """The real, transparent Company Reality Score. Never a fabricated
    single number — built entirely from real counts, all disclosed
    alongside the score so it stays auditable, not a black box. Real
    external-evidence checks per real ACCEPTED decision: has a real
    market_memory closed-sale sample, has a real cached competitor
    snapshot, has real market_evidence events recorded, has a real
    convened board meeting. Score = share of real ACCEPTED
    opportunities backed by at least one real external evidence source
    — increases only when real evidence increases, per the directive."""
    from decision_engine import ranking
    import market_memory
    import market_evidence
    import competitor_discovery
    import executive_board

    accepted = [d for d in ranking.rank_all(path=decisions_path) if d.get("status") == "ACCEPTED" and d.get("niche")]
    if not accepted:
        return {
            "score_pct": None,
            "reason": "لا فرص مقبولة فعلاً بعد لحساب Reality Score حقيقي",
            "real_accepted_opportunities": 0,
        }

    backed = 0
    detail = []
    for d in accepted:
        niche = d["niche"]
        has_sale = bool((market_memory.niche_commercial_profile(niche, evidence_path=evidence_path) or {}).get("sample_size"))
        has_evidence_events = bool(list(market_evidence.read_evidence(niche=niche, evidence_path=evidence_path)))
        has_competitor_snapshot = bool(competitor_discovery.load_database(db_file=db_file).get(competitor_discovery._normalize_key(niche)))
        has_board_meeting = bool((executive_board.get_latest_board_brief(niche, board_path=board_path) or {}).get("has_meeting"))
        real_sources = sum([has_sale, has_evidence_events, has_competitor_snapshot, has_board_meeting])
        if real_sources > 0:
            backed += 1
        detail.append({
            "niche": niche, "real_evidence_sources": real_sources,
            "has_real_sale": has_sale, "has_market_evidence_events": has_evidence_events,
            "has_competitor_snapshot": has_competitor_snapshot, "has_board_meeting": has_board_meeting,
        })

    return {
        "score_pct": round(100 * backed / len(accepted), 1),
        "real_accepted_opportunities": len(accepted),
        "opportunities_with_real_external_evidence": backed,
        "detail": detail,
        "note": "النسبة = حصة الفرص المقبولة فعلاً المدعومة بمصدر دليل خارجي حقيقي واحد على الأقل — يزيد فقط عند زيادة الدليل الحقيقي، أبداً بتقدير مُختلَق",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
