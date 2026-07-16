"""
Production Evidence catalog (ADR-055) — an evidence record for every
niche ever decided, built by calling record.build_evidence_record() once
per real, distinct niche already present in decision_engine.store — no
separately-maintained roster of opportunities is kept here.
"""

from decision_engine import store as decision_store
from production_evidence import record as record_module


def list_all_evidence_records(tier="tier4", timeline_path=None, decisions_path=None, outcomes_path=None):
    latest = decision_store.latest_decision_per_niche(path=decisions_path)
    return [
        record_module.build_evidence_record(
            d["niche"], tier=d.get("tier", tier), timeline_path=timeline_path,
            decisions_path=decisions_path, outcomes_path=outcomes_path,
        )
        for d in latest.values()
    ]
