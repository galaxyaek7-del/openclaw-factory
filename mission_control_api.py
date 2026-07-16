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


_ENDPOINTS = {
    "opportunities": _opportunities,
    "production": _production,
    "revenue": _revenue,
    "automation": _automation,
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
