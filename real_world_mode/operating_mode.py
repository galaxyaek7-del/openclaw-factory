"""
Real World Operating Mode (ADR-056) — the thin, deliberately-run entry
point that feeds every real external signal through the already-built
pipeline: orchestrator.orchestrator.run_cycle() (ADR-051), called
unchanged, once per real signal. Adds no new decision logic, no new
storage, no new orchestration.

Standalone, deliberately-run tool, same convention as every other
module this factory has introduced:

    python -m real_world_mode.operating_mode
"""

import json

from orchestrator import orchestrator as orch

from real_world_mode import signal_intake


def run_real_world_cycle(execute_production=False, candidates_dir=None, timeline_path=None,
                          decisions_path=None, analysis_db_file=None, outcomes_path=None,
                          state_path=None):
    signals = signal_intake.collect_all_real_signals(candidates_dir=candidates_dir)
    if not signals:
        return {
            "processed": 0,
            "results": [],
            "reason": "لا إشارات خارجية حقيقية موجودة اليوم في OPPORTUNITIES.md أو tier1_intake/candidates/",
        }

    results = []
    for signal in signals:
        stage_results = orch.run_cycle(
            signal["niche"],
            external_signal=signal["external_signal"],
            tier=signal.get("tier", "tier4"),
            execute_production=execute_production,
            timeline_path=timeline_path,
            decisions_path=decisions_path,
            analysis_db_file=analysis_db_file,
            outcomes_path=outcomes_path,
            state_path=state_path,
        )
        results.append({
            "niche": signal["niche"],
            "signal_source": signal["source"],
            "stages": [r.to_dict() for r in stage_results],
        })

    return {"processed": len(results), "results": results}


def main():
    result = run_real_world_cycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
