"""
Golden Opportunity Hunter (ADR-060) — reuses the existing pipeline
end to end, adds no new engine and no new scoring. execute_production is
never a parameter of run_hunt(): production is hardcoded to never fire
from this module, structurally, not just by convention.

Standalone, deliberately-run tool, same convention as every module this
factory has introduced:

    python -m golden_hunter.hunt
"""

import json

from decision_engine import ranking as decision_ranking
from orchestrator import orchestrator as orch

from golden_hunter.evidence_package import build_evidence_package
from real_world_mode import signal_intake


def run_hunt(candidates_dir=None, timeline_path=None, decisions_path=None,
             analysis_db_file=None, outcomes_path=None, max_items=None, state_path=None):
    """Continuously monitors every currently available real evidence
    source (OPPORTUNITIES.md + tier1_intake/candidates/, re-read fresh
    every call), runs each through the existing pipeline in dry-run only,
    and returns a prioritized queue of evidence packages ranked by the
    existing real opportunity_score (demand+competition+profit+
    automation+long-term-value combined — not raw popularity)."""
    signals = signal_intake.collect_all_real_signals(candidates_dir=candidates_dir)

    for signal in signals:
        orch.run_cycle(
            signal["niche"], external_signal=signal["external_signal"],
            tier=signal.get("tier", "tier4"), execute_production=False,
            timeline_path=timeline_path, decisions_path=decisions_path,
            analysis_db_file=analysis_db_file, outcomes_path=outcomes_path,
            state_path=state_path,
        )

    ranked = decision_ranking.rank_all(path=decisions_path)
    if max_items is not None:
        ranked = ranked[:max_items]

    return [build_evidence_package(d) for d in ranked]


def main():
    queue = run_hunt()
    print(json.dumps(queue, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
