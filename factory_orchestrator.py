"""Factory Master Orchestrator (OpenClaw Architecture Review, 2026-07-22)

The single, real control point that composes every stage this factory
already has, instead of requiring 3+ separate manual Mission Control
calls to reach the same real evaluation. Wraps, never rewrites:

    decision lookup (decision_engine.ranking)
        -> Executive Quality Gate (executive_quality_gate.py, ADR-087)
        -> AI Executive Board (executive_board.py, ADR-090 -- which
           itself calls Enterprise Readiness internally, ADR-089)
        -> Revenue Pipeline production (revenue_pipeline/pipeline.py)

"Automatically" here means "one real function call now runs what used
to take 3+ separate manual actions" -- this factory has no scheduler
(CLAUDE.md), so nothing in this module runs unattended; it runs when
invoked, exactly like every other on-demand engine built this session.

advisory_only=True by default (Full Architecture Review, 2026-07-22,
explicit design decision, not asked as a question): the Board's
decision is reported prominently alongside the real production result,
but does NOT block revenue_pipeline.process_opportunity()'s own
execute= safety switch. Hard-gating production on the Board today would
mean zero automatic production ever again, since zero real market
evidence exists for any niche yet (the same freeze risk flagged in the
prior Full Factory Integrity Audit). Pass advisory_only=False to make a
REJECTED/NOT_APPROVED board result actually block production -- an
explicit, deliberate choice for whoever calls this, never this
module's silent default.
"""

import json
import sys
from datetime import datetime, timezone


def _build_spec(decision):
    """The exact spec shape already proven live via mission_control_api.py's
    3 separate gate endpoints -- reused here verbatim so all 3 gates see
    identical real evidence, not 3 independently-built specs."""
    return {
        "niche": decision.get("niche"),
        "title": decision.get("niche"),
        "ladder": decision.get("ladder"),
        "evaluation_snapshot": decision.get("evaluation_snapshot"),
        "decided_at": decision.get("decided_at"),
    }


def find_decision(niche, decisions_path=None):
    """The real, already-recorded decision for this niche -- never
    re-scores, never fabricates one. None when no real decision exists."""
    from decision_engine import ranking
    decisions = ranking.rank_all(decisions_path) if decisions_path else ranking.rank_all()
    return next((d for d in decisions if d.get("niche") == niche), None)


def run_master_cycle(niche, execute=False, advisory_only=True, decisions_path=None,
                      timeline_path=None, analysis_db_file=None, outcomes_path=None,
                      state_path=None, board_path=None, competitor_db_file=None,
                      ledger_path=None, competitor_history_file=None):
    """Runs the full real governance + production chain for ONE niche
    that already has a real ACCEPTED decision recorded. Returns a single
    unified result -- never raises for a missing decision (reports it
    honestly instead), never fabricates a criterion any stage has no
    real data for (each stage's own UNKNOWN discipline is untouched)."""
    import executive_quality_gate as eqg
    import executive_board as eb
    from revenue_pipeline import pipeline as revenue_pipeline

    decision = find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return {
            "niche": niche,
            "success": False,
            "reason": f"لا قرار حقيقي مسجَّل لهذا النيتش بعد: {niche!r}",
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    spec = _build_spec(decision)

    quality_gate = eqg.run_executive_quality_gate(spec)
    board_meeting = eb.convene_board(spec, decision_type="production", board_path=board_path)

    board_blocks_production = (
        not advisory_only and board_meeting["tally"]["board_decision"] != "APPROVED"
    )

    production_result = None
    if execute and not board_blocks_production:
        production_result = revenue_pipeline.process_opportunity(
            decision, execute=True, timeline_path=timeline_path, decisions_path=decisions_path,
            analysis_db_file=analysis_db_file, outcomes_path=outcomes_path, state_path=state_path,
            competitor_db_file=competitor_db_file, ledger_path=ledger_path,
            competitor_history_file=competitor_history_file,
        )
    elif execute and board_blocks_production:
        production_result = {
            "executed": False,
            "reason": "advisory_only=False و AI Executive Board لم يوافق — إنتاج مرفوض عند هذه البوابة",
        }

    return {
        "niche": niche,
        "success": True,
        "advisory_only": advisory_only,
        "quality_gate": quality_gate,
        "board_meeting": board_meeting,
        "board_blocks_production": board_blocks_production,
        "production_result": production_result,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Factory Master Orchestrator")
    parser.add_argument("--niche", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--enforce-board", action="store_true", help="advisory_only=False")
    args = parser.parse_args()

    result = run_master_cycle(args.niche, execute=args.execute, advisory_only=not args.enforce_board)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
