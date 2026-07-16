#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Factory — Mission Control API bridge (Phase 8).

A thin CLI dispatcher, zero new business logic: every branch below calls
an already-built, already-tested function from this session's packages
and prints its real result as JSON — the exact same stdin/stdout-JSON
convention every other script in this factory already uses (book_
generator.py, market_analyzer.py, distributor.py, etc.), so server.js
can spawn this the same way it already spawns those.

None of these endpoints re-run an expensive real evaluation live (that
would make a dashboard route hang for minutes on real network calls) —
each one only reads/ranks/assembles data that's already been computed
and persisted by a deliberate, separate run of the underlying package.

    python mission_control_api.py opportunities
    python mission_control_api.py production
    python mission_control_api.py revenue
    python mission_control_api.py automation
    python mission_control_api.py decision_history
    python mission_control_api.py system_configuration
"""

import json
import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

for _stream in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _opportunities():
    from decision_engine import ranking
    return {"all": ranking.rank_all(), "queue": ranking.rank_queue()}


def _production():
    from production_factory import factory
    return factory.run_production_factory()


def _revenue():
    from revenue_pipeline import pipeline
    result = pipeline.run_revenue_pipeline()
    return {**result, "ceo_report_markdown": pipeline.render_ceo_revenue_report(result)}


def _automation():
    """Real, but honestly bounded: n8n's REST API needs a login this
    factory does not have credentials for (BLOCKERS.md #1) — this reads
    the last real, exported workflow definitions instead (n8n_workflows/
    *.fixed.json, ADR-045) and labels them explicitly as a static export,
    never live state."""
    workflows_dir = _FACTORY_ROOT / "n8n_workflows"
    workflows = []
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.glob("*.fixed.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                workflows.append({
                    "name": data.get("name", path.stem),
                    "active_in_export": data.get("active", False),
                    "source_file": path.name,
                })
            except (OSError, json.JSONDecodeError):
                continue
    return {
        "workflows": workflows,
        "live_status_available": False,
        "reason": "n8n REST API يحتاج تسجيل دخول يدوي (BLOCKERS.md #1) — هذه حالة آخر تصدير حقيقي محفوظ، لا حالة حية",
    }


_DECISION_SUMMARY_FIELDS = (
    "decision_id", "niche", "tier", "decided_at", "status",
    "ai_ceo_decision", "opportunity_score", "opportunity_score_accepted", "reasoning",
)


def _decision_history():
    """Every ACCEPTED/REJECTED/DEFERRED decision ever recorded, unfiltered
    and newest first — decision_engine/store.py's own guarantee is that
    none of this history is ever dropped. Projected to summary fields only
    (the full evaluation_snapshot per record is already reachable through
    the opportunity-queue/market-intelligence services and would make this
    listing multiple MB); no new logic, just a field selection over the
    real record."""
    from decision_engine import store
    records = sorted(store.read_decisions(), key=lambda d: d.get("decided_at", ""), reverse=True)
    summaries = [{k: r.get(k) for k in _DECISION_SUMMARY_FIELDS} for r in records]
    return {"history": summaries, "count": len(summaries)}


def _system_configuration():
    """Real, non-secret configuration values only — unit economics, tier
    weights/floors, and the capability maturity registry, all read from
    their existing single sources of truth (config/economics.json,
    profit_oracle.py's constants, config/capability_registry.json). No
    values are computed or estimated here."""
    from profit_oracle import TIER_WEIGHTS, MIN_OPPORTUNITY_SCORE, AUTOMATION_POTENTIAL_BY_TIER, LONG_TERM_VALUE_BY_TIER

    def _read_json(rel_path):
        p = _FACTORY_ROOT / rel_path
        if not p.exists():
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "tier_weights": TIER_WEIGHTS,
        "min_opportunity_score": MIN_OPPORTUNITY_SCORE,
        "automation_potential_by_tier": AUTOMATION_POTENTIAL_BY_TIER,
        "long_term_value_by_tier": LONG_TERM_VALUE_BY_TIER,
        "economics": _read_json("config/economics.json"),
        "capability_registry": _read_json("config/capability_registry.json"),
    }


_ENDPOINTS = {
    "opportunities": _opportunities,
    "production": _production,
    "revenue": _revenue,
    "automation": _automation,
    "decision_history": _decision_history,
    "system_configuration": _system_configuration,
}


def main():
    endpoint = sys.argv[1] if len(sys.argv) > 1 else None
    fn = _ENDPOINTS.get(endpoint)
    if fn is None:
        print(json.dumps({"success": False, "error": f"unknown endpoint: {endpoint!r}, expected one of {list(_ENDPOINTS)}"}, ensure_ascii=False))
        sys.exit(1)

    try:
        result = fn()
        print(json.dumps({"success": True, **result}, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
