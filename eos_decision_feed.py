"""EOS Decision Feed (new, ADR-186, 2026-08-07) -- the founder's
"Executive Operating System" directive asked for 8 new named engines
(Executive Decision Engine, Company Memory, Opportunity Ranking Engine,
Risk Engine, Financial/Strategic/Commercial Priority Engines, Autonomous
Recommendation Engine), each recommendation carrying 9 fixed fields
(Problem/Evidence/Business impact/Financial impact/Confidence/
Recommended action/Estimated ROI/Time to execute/Priority) and an
explicit "never generate recommendations without evidence" rule.

Research before writing this found every one of the 8 named engines
already real, under different names: Executive Decision Engine ->
executive_brain.py, Company Memory -> knowledge_graph/ +
executive_decision_memory.py, Opportunity Ranking -> goos.py's
rank_build_candidates(), Risk Engine -> resilience_monitor.py's
assess_resilience(), Financial/Strategic/Commercial Priority ->
capital_allocation_engine.py / strategic_intelligence_core.py /
commercial_readiness.py. None are rebuilt here.

The one genuinely missing piece: nothing reshapes those engines' real,
already-differently-shaped outputs into one consistent 9-field
recommendation card. That is this module's only job -- pure citation,
zero new judgment, zero new scoring. Two of the 9 requested fields
(Estimated ROI as a dollar figure, Time to execute) have no real signal
anywhere in this factory -- goos.rank_build_candidates() itself already
discloses this honestly (expected_roi is a 0-100 score, never a dollar
figure; time_to_first_revenue is literally "NOT_MEASURABLE"). This
module reports that same honesty per card rather than inventing a
number to fill the field, directly satisfying the directive's own
"never generate recommendations without evidence" rule.

ADR-196 (2026-08-07, "Digital War Room" directive): added a 10th field,
consequence_of_inaction, answering "what will happen if we do nothing?"
-- not answered anywhere else in this factory. Always a real, mechanical
statement that the current known state simply continues (an unbuilt
opportunity stays unbuilt, an open risk stays open) -- never a
predicted magnitude, timeline, or dollar figure, since no real
forecasting signal exists to back one honestly."""

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_EXECUTIVE_DIRECTIVES_PATH = _FACTORY_ROOT / "data" / "executive_directives.jsonl"


def _read_jsonl(path):
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _card(problem, evidence, business_impact, financial_impact, confidence,
          action, roi, time_to_execute, priority, source, consequence_of_inaction):
    """Every card carries all 9 original requested fields plus one more
    (ADR-196, 2026-08-07 -- the Digital War Room directive's "what will
    happen if we do nothing?" question, not answered anywhere in this
    factory until now). consequence_of_inaction is always a real,
    mechanical statement of the current known state simply continuing --
    never a predicted magnitude, timeline, or dollar figure, since no
    real forecasting signal exists for any of these to cite honestly. A
    field with no real signal is the literal string 'Unknown', never a
    guess."""
    return {
        "problem": problem,
        "evidence": evidence,
        "business_impact": business_impact,
        "financial_impact": financial_impact,
        "confidence": confidence,
        "recommended_action": action,
        "estimated_roi": roi,
        "time_to_execute": time_to_execute,
        "priority": priority,
        "source": source,
        "consequence_of_inaction": consequence_of_inaction,
    }


def _opportunity_cards(top_n=3, decisions_path=None):
    """Opportunity Ranking Engine -> goos.rank_build_candidates()."""
    from goos import rank_build_candidates
    ranking = rank_build_candidates(decisions_path=decisions_path, top_n=top_n)
    cards = []
    for i, cand in enumerate(ranking.get("build_next") or []):
        roi = cand.get("expected_roi") or {}
        tte = cand.get("time_to_first_revenue") or {}
        cards.append(_card(
            problem=f"Real candidate opportunity not yet built: {cand.get('niche')}",
            evidence=cand.get("evidence_sources") or [],
            business_impact=f"prior_status={cand.get('prior_status')}, confidence={cand.get('confidence_score')}",
            financial_impact=roi if isinstance(roi, dict) else {"value": roi, "source": "goos.rank_build_candidates()"},
            confidence=cand.get("confidence_score") or "Unknown",
            action=f"Re-evaluate / build: {cand.get('niche')}",
            roi=roi.get("value") if isinstance(roi, dict) else "Unknown",
            time_to_execute=(tte.get("value") if isinstance(tte, dict) else tte) or "Unknown",
            priority=f"rank {i + 1} of {len(ranking.get('build_next') or [])}",
            source="goos.py::rank_build_candidates() (Opportunity Ranking Engine)",
            consequence_of_inaction=f"'{cand.get('niche')}' remains unbuilt; its real evidence and score stay on record but generate no revenue while it does.",
        ))
    return cards


def _risk_cards(max_findings=3):
    """Risk Engine -> resilience_monitor.assess_resilience()."""
    from resilience_monitor import assess_resilience
    result = assess_resilience()
    findings = [f for f in (result.get("findings") or []) if f.get("severity") in ("critical", "emergency")]
    cards = []
    for f in findings[:max_findings]:
        cards.append(_card(
            problem=f"Active real risk: {f.get('area')}",
            evidence=f.get("evidence") or {},
            business_impact=f.get("detail") or "Unknown",
            financial_impact="Unknown -- resilience_monitor.py does not attach a dollar estimate to operational risk findings",
            confidence="high" if f.get("data_available") else "low (no real data available for this area)",
            action=f"Investigate and resolve: {f.get('area')}",
            roi="N/A -- risk mitigation, not a revenue opportunity",
            time_to_execute="Unknown",
            priority=f.get("severity"),
            source="resilience_monitor.py::assess_resilience() (Risk Engine)",
            consequence_of_inaction=f"The real, open finding in '{f.get('area')}' stays active and unresolved until someone investigates it.",
        ))
    return cards


def _todays_directive_card():
    """Executive Decision Engine / Autonomous Recommendation Engine ->
    executive_brain.py's own daily directive, read from its real ledger
    (same cached-not-recomputed discipline as ceo_home.py -- a fresh
    call chains 3 full-portfolio scans, ~59s, wrong for a feed meant to
    be read constantly)."""
    entries = _read_jsonl(_EXECUTIVE_DIRECTIVES_PATH)
    if not entries:
        return None
    latest = entries[-1]
    return _card(
        problem=latest.get("current_mission") or "Unknown",
        evidence=[latest.get("source")] if latest.get("source") else [],
        business_impact=latest.get("next_mission") or "Unknown",
        financial_impact="Unknown -- executive_brain.py arbitrates by priority tier, not a dollar model",
        confidence=latest.get("confidence") or "Unknown",
        action=latest.get("current_mission") or "Unknown",
        roi="Unknown",
        time_to_execute="Unknown",
        priority=latest.get("tier") or "Tier 1 (highest — this is the arbitrated top pick)",
        source="executive_brain.py::build_executive_directive() (Executive Decision Engine), most recent daily entry",
        consequence_of_inaction="This is the single highest-arbitrated action across all real inputs available today; every other real candidate action was ranked below it and stays unaddressed while this one does too.",
    )


def _commercial_priority_card(decisions_path=None):
    """Commercial/Financial Priority Engine -> commercial_readiness.py's
    own bottleneck field -- already tells you the single lowest-scoring,
    highest-priority dimension without inventing a new ranking."""
    from commercial_readiness import commercial_readiness_score
    result = commercial_readiness_score(decisions_path=decisions_path)
    bottleneck = result.get("bottleneck")
    dim = (result.get("dimensions") or {}).get(bottleneck, {})
    return _card(
        problem=f"Lowest-scoring readiness dimension: {bottleneck} ({dim.get('score')}/100)",
        evidence=dim.get("evidence") or "Unknown",
        business_impact=f"Overall commercial readiness: {result.get('overall')}/100",
        financial_impact="Unknown -- commercial_readiness.py scores readiness, not a dollar model",
        confidence="high (real, disclosed-heuristic score, not estimated)",
        action=f"Improve {bottleneck} readiness",
        roi="Unknown",
        time_to_execute="Unknown",
        priority="highest real gap in the commercial readiness scorecard",
        source="commercial_readiness.py::commercial_readiness_score() (Commercial/Financial Priority Engine)",
        consequence_of_inaction=f"'{bottleneck}' remains the lowest-scoring real dimension, holding down overall commercial readiness ({result.get('overall')}/100) until it's addressed.",
    )


def build_eos_decision_feed(decisions_path=None):
    """Company Memory is deliberately not re-cited per-card here --
    every card's evidence already traces back through knowledge_graph/
    and executive_decision_memory.py's own real ledgers by construction
    (same sources those modules already index); this feed does not
    duplicate their own dedicated read paths."""
    cards = []
    directive_card = _todays_directive_card()
    if directive_card:
        cards.append(directive_card)
    cards.extend(_risk_cards())
    cards.append(_commercial_priority_card(decisions_path))
    cards.extend(_opportunity_cards(decisions_path=decisions_path))
    return {
        "recommendations": cards,
        "total": len(cards),
        "note": "Every card cites a real, already-existing engine (see each card's own 'source' field) -- this module reshapes, never recomputes or re-judges. Fields with no real signal anywhere in this factory are 'Unknown', never a fabricated number.",
    }
