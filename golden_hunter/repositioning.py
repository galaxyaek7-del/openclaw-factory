"""
Golden Hunter — Repositioning Engine (Founder Green-Light, 2026-08-14).

A reusable Golden Hunter capability that turns REJECTED opportunities into
learnable, structured knowledge — WITHOUT lowering, bypassing, or re-tuning
any acceptance gate.

What this engine is:
  - A structured, append-only record of every repositioning attempt
    (data/repositioning_attempts.jsonl), preserving the original decision's
    history untouched (the original decision record in data/decisions.jsonl
    is never overwritten; this ledger only references it by decision_id).
  - A mechanical candidate generator (propose_repositionings()) that derives
    new positioning TEXT from the original niche using the existing premium
    keyword vocabulary (profit_oracle.PREMIUM_KEYWORDS) — never fabricates
    evidence, never invents market data.
  - A real scoring dispatcher (reposition_and_record()) that runs the
    PROPOSED positioning through the SAME real acceptance gate
    (profit_oracle.ladder_opportunity_score(), ADR-066) the original
    decision already went through. The resulting score and final outcome
    are the gate's real output — the engine never accepts anything itself,
    never lowers a threshold, never fabricates a score.
  - A real learning report (repositioning_learning_report()) over recorded
    attempts: which repositioning patterns (added premium keyword, changed
    target customer, changed price) preceded an ACCEPTED outcome — with the
    same minimum-real-sample guard decision_engine/learning.py already uses
    ("insufficient data" until >= 3 real attempts), never fake precision.

Integrates with the existing Knowledge Graph: every recorded attempt is a
real RepositionAttempt node in knowledge_graph/build.py, with a real edge
back to the original Decision node it came from (exact decision_id match
only — never a guessed link).

    python -m golden_hunter.repositioning --record '{...}'   # manual record
    python -m golden_hunter.repositioning --reposition '{"original_decision_id":"...","proposed_positioning":"..."}'
    python -m golden_hunter.repositioning --report
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ATTEMPTS_PATH = _FACTORY_ROOT / "data" / "repositioning_attempts.jsonl"

# Same minimum-real-sample discipline decision_engine/learning.py uses
# (MIN_SAMPLES_FOR_RECALIBRATION = 3) — no pattern learning from a handful
# of data points presented with fake confidence.
MIN_SAMPLES_FOR_LEARNING = 3

FINAL_OUTCOMES = ("ACCEPTED", "REJECTED", "RECORDED")


def _normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _read_all(path):
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


def _append(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


@dataclass
class RepositioningAttempt:
    """The structured, permanent record of ONE repositioning attempt.
    Every field named in the founder's green-light requirement #2 is
    present; `original_decision_id` links back to the untouched original
    decision in data/decisions.jsonl (never overwritten)."""

    attempt_id: str
    original_decision_id: str
    original_niche: str
    rejection_reason: str
    original_score: Optional[float]
    original_positioning: str
    proposed_positioning: str
    changed_target_customer: Optional[str]
    changed_value_proposition: Optional[str]
    changed_pricing: Optional[float]
    resulting_score: Optional[float]
    final_outcome: str  # one of FINAL_OUTCOMES
    recorded_at: str
    ladder: Optional[str] = None
    pattern: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self):
        return {
            "attempt_id": self.attempt_id,
            "original_decision_id": self.original_decision_id,
            "original_niche": self.original_niche,
            "rejection_reason": self.rejection_reason,
            "original_score": self.original_score,
            "original_positioning": self.original_positioning,
            "proposed_positioning": self.proposed_positioning,
            "changed_target_customer": self.changed_target_customer,
            "changed_value_proposition": self.changed_value_proposition,
            "changed_pricing": self.changed_pricing,
            "resulting_score": self.resulting_score,
            "final_outcome": self.final_outcome,
            "recorded_at": self.recorded_at,
            "ladder": self.ladder,
            "pattern": self.pattern,
            "note": self.note,
        }


def make_attempt_id(original_decision_id, proposed_positioning, recorded_at):
    """Deterministic — same (original_decision_id, proposed_positioning,
    recorded_at) always produces the same attempt_id, same reproducibility
    discipline as decision_engine/types.py's make_decision_id()."""
    raw = f"{original_decision_id}|{proposed_positioning}|{recorded_at}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _derive_pattern(original_positioning, proposed_positioning, changed_target_customer):
    """Mechanical pattern label derived from REAL text — never invented.
    Reports which premium keyword (from profit_oracle's real vocabulary)
    was added by the repositioning, and whether the target customer
    changed. Returns a stable, queryable string or None when nothing
    mechanically distinguishable changed."""
    from profit_oracle import PREMIUM_KEYWORDS, RECURRING_KEYWORDS, MID_KEYWORDS

    orig = _normalize(original_positioning)
    prop = _normalize(proposed_positioning)
    parts = []
    for kw in PREMIUM_KEYWORDS + MID_KEYWORDS + RECURRING_KEYWORDS:
        if kw and kw in orig:
            continue
        if kw and kw in prop:
            parts.append(f"added_keyword:{kw}")
    if changed_target_customer:
        parts.append("target_customer_changed:true")
    return "; ".join(parts) if parts else None


def propose_repositionings(original_decision, ladder=None, max_candidates=6):
    """Mechanical candidate generator — derives NEW positioning TEXT from
    the original niche using profit_oracle's real premium/mid/recurring
    keyword vocabulary. Never fabricates evidence, never invents market
    data, never scores anything itself. Each candidate carries the exact
    fields the record needs so a caller can choose one and pass it to
    reposition_and_record() for REAL gate scoring.

    The repositioning that proved successful this cycle
    ("AI Agent Blueprint for Legal Case Research Automation..." ->
    "Legal Case Research Automation System for Solo Attorneys") was exactly
    this maneuver: drop a weak lead-in token, insert a premium keyword
    before the "for <customer>" segment. This is the reusable pattern."""
    niche = str((original_decision or {}).get("niche") or "").strip()
    if not niche:
        return []

    from profit_oracle import PREMIUM_KEYWORDS, MID_KEYWORDS, RECURRING_KEYWORDS

    # Weak lead-in tokens that made the original read as a "Blueprint"/
    # "Agent" spec doc rather than a delivered system. Real, mechanical
    # text transforms only. Stripped FIRST so the "for <customer>"
    # partition below sees the clean core.
    weak_leads = ("ai agent blueprint for ", "agent blueprint for ",
                  "ai agent blueprint ", "blueprint for ", "agent ")

    base = niche.strip()
    for lead in weak_leads:
        if base.lower().startswith(lead):
            base = base[len(lead):].strip()
            break

    # Split the "for <target customer>" suffix off the niche text so a
    # premium keyword can be inserted before it, preserving the target.
    head, sep, tail = base.partition(" for ")
    if sep:
        core = head.strip()
        target = ("for " + tail.strip()) if tail.strip() else None
    else:
        core = base.strip()
        target = None

    keywords = PREMIUM_KEYWORDS + MID_KEYWORDS + RECURRING_KEYWORDS
    seen = set()
    candidates = []
    for kw in keywords:
        kw_l = kw.lower()
        if kw_l in _normalize(niche):
            continue  # keyword already present — not a change
        candidate_niche = f"{core} {kw}".strip()
        if target:
            candidate_niche = f"{candidate_niche} {target}"
        key = _normalize(candidate_niche)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "original_niche": niche,
            "original_positioning": niche,
            "proposed_positioning": candidate_niche,
            "changed_target_customer": None,  # this transform keeps the same target
            "changed_value_proposition": f"positioned as a deliverable '{kw}' product, not a blueprint",
            "changed_pricing": None,  # the real gate (butter_price) computes the real price
            "ladder": ladder,
            "pattern": _derive_pattern(niche, candidate_niche, None),
        })
        if len(candidates) >= max_candidates:
            break

    return candidates


def record_attempt(attempt, attempts_path=None):
    """Append one structured RepositioningAttempt (or dict shaped like its
    to_dict()) to the append-only ledger. Never overwrites, never rewrites
    — a corrupt write can't destroy prior attempts (same discipline as
    decision_engine/store.py). Returns the recorded dict."""
    record = attempt.to_dict() if hasattr(attempt, "to_dict") else attempt
    _append(record, attempts_path or DEFAULT_ATTEMPTS_PATH)
    return record


def read_attempts(attempts_path=None):
    """Every recorded repositioning attempt, oldest first. A missing file
    yields nothing (a factory with zero attempts yet is not an error)."""
    return list(_read_all(attempts_path or DEFAULT_ATTEMPTS_PATH))


def find_attempts_by_original(original_decision_id, attempts_path=None):
    """Every attempt ever recorded against one original decision —
    the guarantee that no repositioning history is ever lost or hidden."""
    return [
        a for a in read_attempts(attempts_path)
        if a.get("original_decision_id") == original_decision_id
    ]


def reposition_and_record(original_decision, proposed_positioning, ladder=None,
                          changed_target_customer=None, changed_value_proposition=None,
                          score_fn=None, attempts_path=None, rejection_reason=None,
                          original_score=None, external_signal=None, evidence_path=None):
    """Run a proposed repositioning through the REAL acceptance gate and
    record the attempt. The resulting score and final outcome are the gate's
    own output — this function accepts nothing, lowers no threshold, and
    never fabricates a score.

    original_decision: the untouched original decision record (dict-shaped,
      from decision_engine.store / data/decisions.jsonl) — read-only here,
      never modified or overwritten.
    proposed_positioning: the new positioning text to score.
    score_fn: the real gate, injectable for test isolation. Defaults to
      profit_oracle.ladder_opportunity_score() — the SAME gate the original
      decision passed through, unchanged. Its "accepted"/"ladder_score"/
      "price" fields are used verbatim.
    external_signal/evidence_path: the SAME real evidence context the
      original decision was scored under (the pipeline passes
      external_signal with real customer_pain, and evidence_path to the real
      market evidence ledger). Forwarded verbatim to the gate — running the
      gate without them would silently degrade it to "Unknown pain" and
      reject every repositioning even when real evidence exists (the exact
      "computed then dropped" fidelity bug this factory has fixed repeatedly).
      Never fabricated here: these are passed through, or left None (the
      gate's own real defaults) when a caller has none.
    rejection_reason/original_score: when not given, read from the original
      decision record's own real fields (reasoning / opportunity_score) —
      never invented.
    """
    original_id = (original_decision or {}).get("decision_id") or ""
    if not original_id:
        raise ValueError("original_decision must carry a real decision_id — never fabricate one")

    original_niche = (original_decision or {}).get("niche") or ""
    if rejection_reason is None:
        reasoning = (original_decision or {}).get("reasoning") or []
        rejection_reason = "; ".join(reasoning) if reasoning else (
            (original_decision or {}).get("ai_ceo_decision") or "no recorded reasoning"
        )
    if original_score is None:
        original_score = (original_decision or {}).get("opportunity_score")

    import profit_oracle
    gate = score_fn or profit_oracle.ladder_opportunity_score
    ladder = ladder or (original_decision or {}).get("ladder") or "kdp_books"
    result = gate(proposed_positioning, ladder=ladder,
                  external_signal=external_signal, evidence_path=evidence_path)

    resulting_score = result.get("ladder_score") if isinstance(result, dict) else None
    accepted = bool(result.get("accepted")) if isinstance(result, dict) else False
    resulting_price = result.get("price") if isinstance(result, dict) else None
    final_outcome = "ACCEPTED" if accepted else "REJECTED"

    now = datetime.now(timezone.utc).isoformat()
    attempt = RepositioningAttempt(
        attempt_id=make_attempt_id(original_id, proposed_positioning, now),
        original_decision_id=original_id,
        original_niche=original_niche,
        rejection_reason=rejection_reason,
        original_score=original_score,
        original_positioning=(original_decision or {}).get("niche") or "",
        proposed_positioning=proposed_positioning,
        changed_target_customer=changed_target_customer,
        changed_value_proposition=changed_value_proposition,
        changed_pricing=resulting_price,
        resulting_score=resulting_score,
        final_outcome=final_outcome,
        recorded_at=now,
        ladder=ladder,
        pattern=_derive_pattern((original_decision or {}).get("niche") or "",
                                proposed_positioning, changed_target_customer),
        note=None if accepted else (
            "رفض حقيقي من البوابة نفسها — راجِع الأدلة الحقيقية (دليل الدفع/الألم/الدفاعية) قبل أي إعادة محاولة"
            if isinstance(result, dict) and result.get("reason") else
            "رفض حقيقي من البوابة نفسها — لا أدلة جديدة مخترعة"
        ),
    )
    record_attempt(attempt, attempts_path=attempts_path)
    return attempt.to_dict()


def repositioning_learning_report(attempts_path=None):
    """Real learning from recorded attempts — which repositioning PATTERNS
    preceded an ACCEPTED outcome. Real, computed stats over real attempts
    only; reports "insufficient data" (never fake precision) until >=
    MIN_SAMPLES_FOR_LEARNING real attempts exist, same guard as
    decision_engine/learning.py. Reports a finding; it never auto-applies
    a reweighting to live scoring (that stays a separate, founder-approved
    change)."""
    attempts = read_attempts(attempts_path)
    total = len(attempts)
    if total == 0:
        return {
            "learned": False, "total_attempts": 0,
            "reason": "لا محاولات إعادة تموضع مسجَّلة بعد — لا شيء يُتعلَّم من لا شيء",
        }
    accepted = [a for a in attempts if a.get("final_outcome") == "ACCEPTED"]
    rejected = [a for a in attempts if a.get("final_outcome") == "REJECTED"]
    if total < MIN_SAMPLES_FOR_LEARNING:
        return {
            "learned": False, "total_attempts": total,
            "accepted_count": len(accepted), "rejected_count": len(rejected),
            "min_required": MIN_SAMPLES_FOR_LEARNING,
            "reason": f"{total} محاولة حقيقية فقط — أقل من الحد الأدنى {MIN_SAMPLES_FOR_LEARNING} لأي تعلُّم معنى",
        }

    success_rate = round(100 * len(accepted) / total, 1)
    patterns: Dict[str, List[Any]] = {}
    for a in attempts:
        pattern = a.get("pattern") or "no_mechanical_pattern"
        patterns.setdefault(pattern, []).append(a)

    by_pattern = {
        pattern: {
            "attempts": len(items),
            "accepted": sum(1 for i in items if i.get("final_outcome") == "ACCEPTED"),
            "accepted_rate_pct": round(100 * sum(1 for i in items if i.get("final_outcome") == "ACCEPTED") / len(items), 1),
        }
        for pattern, items in sorted(patterns.items(), key=lambda kv: -len(kv[1]))
    }

    return {
        "learned": True,
        "total_attempts": total,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "success_rate_pct": success_rate,
        "by_pattern": by_pattern,
        "note": "إحصاء حقيقي فقط — لا يُعدِّل تلقائياً أي بوابة/عتبة؛ يحتاج قراراً منفصلاً لتطبيقه",
    }


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Golden Hunter — Repositioning Engine")
    parser.add_argument("--record", metavar="JSON", help="append one attempt record verbatim")
    parser.add_argument("--reposition", metavar="JSON", help='{"original_decision_id":"...","proposed_positioning":"..."}')
    parser.add_argument("--report", action="store_true", help="print the real pattern-learning report")
    args = parser.parse_args()

    if args.record:
        record_attempt(json.loads(args.record))
    elif args.reposition:
        import decision_engine.store as store
        data = json.loads(args.reposition)
        original = None
        for d in store.read_decisions():
            if d.get("decision_id") == data.get("original_decision_id"):
                original = d
                break
        if original is None:
            print(json.dumps({"error": f"لا قرار حقيقي بهذا المعرّف: {data.get('original_decision_id')}"}, ensure_ascii=False))
            sys.exit(1)
        attempt = reposition_and_record(
            original,
            data.get("proposed_positioning"),
            ladder=data.get("ladder"),
            changed_target_customer=data.get("changed_target_customer"),
            changed_value_proposition=data.get("changed_value_proposition"),
        )
        print(json.dumps(attempt, ensure_ascii=False, indent=2))
    elif args.report:
        print(json.dumps(repositioning_learning_report(), ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()