"""
Golden Hunter — Evidence Identity Analyzer (Founder Priority, 2026-08-14).

Why this exists: real evidence in this factory is keyed by the OPPORTUNITY
NAME string (pain_evidence_cache.json, market_evidence.jsonl,
competitor_database.json), not by the stable decision/opportunity ID. When
an opportunity is renamed or repositioned, its real evidence stays under
the OLD name and becomes unreachable under the NEW decision's name — so
downstream gates report "PAIN NOT ESTABLISHED" and confidence silently
drops even though real evidence exists.

What this module does: it treats the DECISION ID as the primary identity
and resolves real evidence for that ID across EVERY name the same
opportunity has provably carried — the decision's own niche plus every
name linked to it through the Repositioning Engine's recorded lineage
(data/repositioning_attempts.jsonl, golden_hunter/repositioning.py). It
then recomputes evidence coverage/confidence using the SAME real
evidence_completeness machinery, from ONLY the evidence proven to belong
to that decision ID.

What it never does: never runs the acceptance gate (no new accept/reject,
no threshold change), never writes evidence, never fabricates/duplicates/
reinterprets a record, and never touches the decision record itself.

    python -m golden_hunter.evidence_identity --decision 5214fb83a464299d
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DECISIONS_PATH = _FACTORY_ROOT / "data" / "decisions.jsonl"
DEFAULT_PAIN_CACHE_PATH = _FACTORY_ROOT / "data" / "pain_evidence_cache.json"
DEFAULT_EVIDENCE_PATH = _FACTORY_ROOT / "data" / "market_evidence.jsonl"


def _normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _read_json(path):
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_decision(decision_id: str, decisions_path=None) -> Optional[dict]:
    """The decision record for a decision_id, or None. Read-only."""
    for d in _read_jsonl(decisions_path or DEFAULT_DECISIONS_PATH):
        if d.get("decision_id") == decision_id:
            return d
    return None


def resolve_identity_names(decision_id: str, decisions_path=None,
                           attempts_path=None) -> dict:
    """The set of niche names that PROVABLY belong to one decision identity.

    A decision's identity is not its current name — it is the decision ID,
    which is stable across renames. Every name in the returned set is
    justified by a real, recorded fact:

      - the decision's OWN niche (from its record),
      - any name recorded as the same identity via a RepositioningAttempt
        where this decision_id is the original (forward),
      - any earlier name linked in reverse: a recorded attempt whose
        proposed_positioning equals this decision's niche records that the
        original decision (and therefore its niche) is the same identity.

    Never guesses, never fuzzy-matches on text similarity."""
    decision = find_decision(decision_id, decisions_path=decisions_path)
    if not decision:
        return {"decision_id": decision_id, "primary_niche": None,
                "identity_names": [], "provenance": {}}

    primary = str(decision.get("niche") or "").strip()
    names = [primary]
    provenance = {primary: f"own decision record {decision_id}"}

    from golden_hunter.repositioning import read_attempts

    for a in read_attempts(attempts_path):
        proposed = (a.get("proposed_positioning") or "").strip()
        # Forward: this decision was the original, proposed is the new name.
        if a.get("original_decision_id") == decision_id and proposed and proposed not in names:
            names.append(proposed)
            provenance[proposed] = (
                f"recorded RepositioningAttempt {a.get('attempt_id')}: "
                f"original decision {decision_id} repositioned to this niche"
            )
        # Reverse: a recorded attempt targeted this decision's own niche, so
        # the attempt's original decision is the same opportunity's earlier name.
        if proposed and _normalize(proposed) == _normalize(primary):
            orig = find_decision(a.get("original_decision_id"), decisions_path=decisions_path)
            if orig:
                earlier = str(orig.get("niche") or "").strip()
                if earlier and earlier not in names:
                    names.append(earlier)
                    provenance[earlier] = (
                        f"recorded RepositioningAttempt {a.get('attempt_id')}: "
                        f"this niche is its proposed_positioning; original decision "
                        f"{a.get('original_decision_id')} (niche '{earlier}') is the same identity"
                    )

    return {
        "decision_id": decision_id,
        "primary_niche": primary,
        "identity_names": names,
        "provenance": provenance,
    }


def recover_pain_evidence(identity_names: List[str], pain_cache_path=None) -> Optional[dict]:
    """The best REAL pain evidence across all identity names, or None.

    Returns a single real cache entry (never merged, never invented). An
    entry counts as real only when it actually found signal
    (pain_language_hits or willingness_to_pay_hits > 0). The best entry is
    the one with the most real hits, so a stale-but-real scan is never
    silently displaced by a newer-but-empty scan."""
    cache = _read_json(pain_cache_path or DEFAULT_PAIN_CACHE_PATH)
    candidates = []
    for name in identity_names:
        entry = cache.get(_normalize(name)) or {}
        re_ = entry.get("real_evidence") or {}
        hits = (re_.get("pain_language_hits") or 0) + (re_.get("willingness_to_pay_hits") or 0)
        if hits > 0:
            candidates.append({
                "proven_under": name,
                "real_evidence": re_,
                "pain_score": entry.get("pain_score"),
                "confidence": entry.get("confidence"),
                "reason": entry.get("reason"),
                "cached_at": entry.get("cached_at"),
            })
    if not candidates:
        return None
    candidates.sort(key=lambda c: (
        (c["real_evidence"].get("pain_language_hits") or 0)
        + (c["real_evidence"].get("willingness_to_pay_hits") or 0)
    ), reverse=True)
    return candidates[0]


def recover_payment_evidence(identity_names: List[str], evidence_path=None) -> List[dict]:
    """Every real payment-evidence record under ANY identity name,
    deduplicated by (source_url, quote). Uses the real market_evidence
    ledger and its real PAYMENT_EVIDENCE_EVENT_TYPES gate."""
    import market_evidence as me

    seen = set()
    out = []
    for name in identity_names:
        for e in me.get_payment_evidence(name, evidence_path=evidence_path or DEFAULT_EVIDENCE_PATH):
            payload = e.get("payload") or {}
            key = (payload.get("source_url"), payload.get("quote"))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "event_type": e.get("event_type"),
                "source_url": payload.get("source_url"),
                "quote": payload.get("quote"),
                "recorded_at": e.get("recorded_at"),
                "proven_under": name,
            })
    return out


def _reconstruct_ladder_result(decision: dict, recovered_pain: Optional[dict]) -> dict:
    """A ladder_result-shaped dict built from the decision's OWN recorded
    snapshot fields plus the recovered real pain evidence — never a new
    gate computation. classify_criteria() reads only these real fields."""
    snapshot = decision.get("evaluation_snapshot") or {}
    ladder_result = {
        "components": snapshot.get("components") or {},
        "defensibility": snapshot.get("defensibility") or {},
        "ai_leverage": snapshot.get("ai_leverage") or {},
        "payment_evidence": snapshot.get("payment_evidence") or [],
        "price": snapshot.get("price"),
        "urgency": None,
    }
    if recovered_pain:
        import profit_oracle as po
        signal = {"customer_pain": {"real_evidence": recovered_pain["real_evidence"]}}
        score, level, note = po._score_urgency(decision.get("niche"), signal)
        ladder_result["urgency"] = {"score": score, "level": level, "note": note}
    return ladder_result


def recompute_confidence(decision_id: str, decisions_path=None, attempts_path=None,
                         pain_cache_path=None, evidence_path=None) -> dict:
    """OLD vs ACTUAL NEW evidence coverage/confidence for a decision ID.

    OLD: evidence resolved by the decision's CURRENT NAME only (the way the
    factory computes it today) — the renamed niche's own (often empty) pain
    cache is all that is visible.
    NEW: evidence resolved by DECISION ID — real pain recovered from every
    name the opportunity has provably carried.

    Both reuse evidence_completeness.classify_criteria() +
    evidence_coverage_report() + confidence_from_coverage() on the
    decision's own recorded snapshot. Neither re-runs the gate."""
    from evidence_completeness import (
        classify_criteria, confidence_from_coverage, evidence_coverage_report,
    )

    decision = find_decision(decision_id, decisions_path=decisions_path)
    if not decision:
        return {"decision_id": decision_id, "error": "decision not found"}

    identity = resolve_identity_names(decision_id, decisions_path=decisions_path,
                                      attempts_path=attempts_path)
    names = identity["identity_names"]

    # OLD: name-only resolution — only the decision's own niche.
    old_pain = recover_pain_evidence([identity["primary_niche"]] or [], pain_cache_path=pain_cache_path)
    old_lr = _reconstruct_ladder_result(decision, old_pain)
    old_class = classify_criteria(old_lr)
    old_report = evidence_coverage_report(old_class)

    # NEW: decision-ID resolution — evidence from every proven identity name.
    new_pain = recover_pain_evidence(names, pain_cache_path=pain_cache_path)
    new_lr = _reconstruct_ladder_result(decision, new_pain)
    new_class = classify_criteria(new_lr)
    new_report = evidence_coverage_report(new_class)

    payment_evidence = recover_payment_evidence(names, evidence_path=evidence_path)

    return {
        "decision_id": decision_id,
        "status": decision.get("status"),
        "primary_niche": identity["primary_niche"],
        "identity_names": names,
        "identity_provenance": identity["provenance"],
        "recovered_pain": new_pain,
        "recovered_payment_evidence": payment_evidence,
        "old_coverage_pct": old_report["coverage_pct"],
        "old_confidence": confidence_from_coverage(old_report["coverage_pct"]),
        "old_missing": old_report["missing_evidence"],
        "new_coverage_pct": new_report["coverage_pct"],
        "new_confidence": confidence_from_coverage(new_report["coverage_pct"]),
        "new_missing": new_report["missing_evidence"],
        "note": (
            "confidence is evidence coverage via evidence_completeness "
            "(ADR-127); recomputed ONLY from evidence proven to belong to "
            "this decision ID; the acceptance gate was never re-run"
        ),
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or "--decision" not in argv:
        print("usage: python -m golden_hunter.evidence_identity --decision <decision_id>")
        return 1
    decision_id = argv[argv.index("--decision") + 1]
    report = recompute_confidence(decision_id)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())