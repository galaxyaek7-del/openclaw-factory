"""
Production Factory orchestration (Phase 7).

Standalone, deliberately-run tool, same convention as every module this
factory has introduced:

    python -m production_factory.factory
"""

import json

from decision_engine import ranking as decision_ranking

from production_factory.dossier import build_production_dossier


def run_production_factory(decisions_path=None, outcomes_path=None):
    """Requirement: never produce a product without a complete dossier.
    This function ONLY ever produces dossiers — it never calls
    revenue_pipeline.process_opportunity(execute=True) itself. Actually
    executing production for a specific dossier remains a separate,
    deliberate, explicitly-authorized action (Phase 6's revenue_pipeline),
    never triggered automatically here."""
    accepted = decision_ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)

    if not accepted:
        return {"processed": 0, "dossiers": [], "reason": "لا فرصة ACCEPTED واحدة اليوم — لا حاجة لملف إنتاج"}

    dossiers = [build_production_dossier(d) for d in accepted]
    return {"processed": len(dossiers), "dossiers": dossiers}


def main():
    result = run_production_factory()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
