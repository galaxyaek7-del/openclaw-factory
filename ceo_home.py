"""CEO Home Briefing (new, ADR-184, 2026-08-07) -- the founder's
"Galaxy Forge Executive Operating System" directive's literal test:
"if the CEO opens Galaxy Forge for only 60 seconds, can they understand
the entire company and make the correct strategic decision?"

Deliberately built for speed, not freshness of every field: every real
source here is either a cheap local file read or an already-real,
already-computed daily ledger entry -- never a fresh multi-minute scan
(executive_brain.build_executive_directive() alone measures ~59s;
capital_allocation_engine's dashboard ~90s). A 60-second-glance page
that itself takes 90 seconds to load would defeat its own purpose.
Where "today's" freshness matters (the Executive Recommendation), this
cites the most recent real daily-tick entry and honestly timestamps it,
rather than pretending a cached number is live.

Pure citation over 8 already-real modules/ledgers -- zero new judgment
engine, matching every consolidation precedent this session. The
"Company Health Score" field is deliberately NOT computed here:
computeHealthStatus() (server.js/lib/health_checks.js) is JS-only with
no Python port, so server.js merges it in at the same layer
'resilience-status' already merges Python + JS signals -- see the
SERVICE_REGISTRY handler, not a second Python health check invented
here."""

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_REALITY_PATH = _FACTORY_ROOT / "config" / "reality.json"
_DECISIONS_PATH = _FACTORY_ROOT / "data" / "decisions.jsonl"
_FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
_AI_COST_LOG_PATH = _FACTORY_ROOT / "data" / "ai_cost_log.jsonl"
_INCIDENTS_PATH = _FACTORY_ROOT / "data" / "incidents.jsonl"
_EXECUTIVE_DIRECTIVES_PATH = _FACTORY_ROOT / "data" / "executive_directives.jsonl"
_EVIDENCE_LEDGER_PATH = _FACTORY_ROOT / "data" / "evidence_ledger.jsonl"


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


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


def _technical_readiness_from_ledger():
    """Cites the most recent real day's worth of reality_audit
    EXECUTION evidence already recorded by the daily evidence-recording
    audit (ADR-182) -- never re-runs the live, multi-minute scan just to
    render a home page. Honestly None if the ledger is empty."""
    entries = [e for e in _read_jsonl(_EVIDENCE_LEDGER_PATH) if e.get("module", "").startswith("reality_audit:")]
    if not entries:
        return {"score": None, "evidence": "No real evidence-recording audit has run yet.", "as_of": None}
    latest_day = max(e.get("timestamp", "")[:10] for e in entries if e.get("timestamp"))
    day_entries = [e for e in entries if (e.get("timestamp") or "").startswith(latest_day)]
    real_count = sum(1 for e in day_entries if e.get("output") == "REAL")
    total = len(day_entries)
    pct = round(100 * real_count / total, 1) if total else None
    return {
        "score": pct,
        "evidence": f"{real_count}/{total} endpoints REAL as of the last daily audit ({latest_day})",
        "as_of": latest_day,
    }


def _products_summary():
    reality = _read_json(_REALITY_PATH, {})
    published = len(reality.get("published_books", []) or [])

    decisions = _latest_decision_records()
    accepted = sum(1 for d in decisions.values() if d.get("status") == "ACCEPTED")
    deferred = sum(1 for d in decisions.values() if d.get("status") == "DEFERRED")

    finance = _read_json(_FINANCE_PATH, {})
    real_sales = [s for s in finance.get("sales", []) if "DELETE-ME" not in str(s.get("product", ""))]
    selling = len({s.get("product") for s in real_sales}) if real_sales else 0

    return {
        "products_ready": published,
        "products_ready_note": "config/reality.json published_books -- the unfakeable ground truth (a finished PDF on disk is not 'ready' by this factory's own definition until it has a real platform ASIN/listing)",
        "products_selling": selling,
        "products_selling_note": "distinct products with >=1 real non-test sale in finance_data.json",
        "products_waiting": deferred,
        "products_waiting_note": "real DEFERRED opportunities in data/decisions.jsonl",
        "active_opportunities": accepted + deferred,
    }


def _latest_decision_records(decisions_path=None):
    path = Path(decisions_path) if decisions_path else _DECISIONS_PATH
    latest = {}
    for d in _read_jsonl(path):
        niche = d.get("niche")
        if niche:
            latest[niche] = d
    return latest


def _highest_roi_opportunity(decisions_path=None):
    decisions = _latest_decision_records(decisions_path)
    candidates = [
        (niche, d.get("opportunity_score"))
        for niche, d in decisions.items()
        if d.get("status") in ("ACCEPTED", "DEFERRED") and isinstance(d.get("opportunity_score"), (int, float))
    ]
    if not candidates:
        return {"niche": None, "score": None, "evidence": "No real scored opportunity in the current pipeline."}
    niche, score = max(candidates, key=lambda c: c[1])
    return {"niche": niche, "score": score, "evidence": "Highest real opportunity_score among ACCEPTED/DEFERRED niches in data/decisions.jsonl."}


def _financial_summary():
    finance = _read_json(_FINANCE_PATH, {})
    real_sales = [s for s in finance.get("sales", []) if "DELETE-ME" not in str(s.get("product", ""))]
    revenue = round(sum(float(s.get("amount", 0)) for s in real_sales), 2)

    cost_entries = _read_jsonl(_AI_COST_LOG_PATH)
    ai_expenses = round(sum(float(e.get("cost_usd") or 0) for e in cost_entries), 4)

    return {
        "revenue": revenue,
        "revenue_note": "Sum of real, non-test sales in finance_data.json. $0 today.",
        "expenses": ai_expenses,
        "expenses_note": "AI (Groq) generation cost only, from data/ai_cost_log.jsonl -- does NOT include Claude Code/Anthropic usage, which has zero tracking anywhere in this repo. Understates real total cost; disclosed, not corrected with a guess.",
        "cash_flow": round(revenue - ai_expenses, 2),
        "cash_flow_note": "revenue - tracked AI expenses only -- directional, not a full P&L (no accounting-system integration exists).",
    }


def _critical_risks():
    incidents = _read_jsonl(_INCIDENTS_PATH)
    open_incidents = [
        i for i in incidents
        if i.get("event") not in ("resolved",) and not any(
            j.get("incident_id") == i.get("incident_id") and j.get("event") == "resolved"
            for j in incidents
        )
    ]
    return {
        "count": len(open_incidents),
        "items": [{"area": i.get("area"), "detail": i.get("detail")} for i in open_incidents[:5]],
        "evidence": f"{len(open_incidents)} open real incident(s) in data/incidents.jsonl (resilience_monitor.py)",
    }


def _ai_systems_status():
    try:
        from ai_capability.registry import list_providers
        providers = list_providers()
        called = [p for p in providers if (p.get("real_stats") or {}).get("calls")]
        return {
            "live_providers": [p.get("display_name") or p.get("provider") for p in called],
            "total_registered": len(providers),
            "total_real_calls": sum((p.get("real_stats") or {}).get("calls", 0) for p in called),
            "evidence": f"{len(called)}/{len(providers)} registered AI providers have real, live call history -- the rest are DISCOVERY status (never actually called).",
        }
    except Exception as e:
        return {"live_providers": [], "total_registered": None, "evidence": f"could not load ai_capability.registry: {e}"}


def _operational_readiness():
    try:
        import company_runtime
        state = company_runtime.company_state()
        return {"state": state.get("state") if isinstance(state, dict) else state, "evidence": "company_runtime.company_state() -- real, priority-ordered, read-only status label"}
    except Exception as e:
        return {"state": "UNKNOWN", "evidence": f"could not load company_runtime: {e}"}


def _todays_executive_recommendation():
    entries = _read_jsonl(_EXECUTIVE_DIRECTIVES_PATH)
    if not entries:
        return {"recommendation": None, "as_of": None, "evidence": "No real executive directive has been recorded yet."}
    latest = entries[-1]
    return {
        "recommendation": latest.get("current_mission") or latest.get("next_mission"),
        "next_mission": latest.get("next_mission"),
        "as_of": latest.get("generated_at") or latest.get("timestamp"),
        "evidence": "Most recent real entry in data/executive_directives.jsonl (executive_brain.py's daily tick) -- not re-computed live.",
    }


def build_ceo_home_briefing(decisions_path=None):
    from commercial_readiness import commercial_readiness_score

    readiness = commercial_readiness_score(decisions_path=decisions_path)
    technical = _technical_readiness_from_ledger()

    return {
        "commercial_readiness": readiness["dimensions"]["commercial"],
        "financial_readiness": readiness["dimensions"]["financial"],
        "technical_readiness": technical,
        "marketing_readiness": readiness["dimensions"]["marketing"],
        "legal_readiness": readiness["dimensions"]["legal"],
        "global_readiness": readiness["dimensions"]["global"],
        "operational_readiness": _operational_readiness(),
        "ai_systems_status": _ai_systems_status(),
        "critical_risks": _critical_risks(),
        "financials": _financial_summary(),
        "products": _products_summary(),
        "highest_roi_opportunity": _highest_roi_opportunity(decisions_path),
        "todays_executive_recommendation": _todays_executive_recommendation(),
        "note": "Company Health Score is merged in by server.js from the real GET /health check (JS-only, no Python port) -- not computed here.",
    }
