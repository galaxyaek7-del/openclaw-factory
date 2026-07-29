"""
Department Health (EOS Phase 2, 2026-07-19) — pure assembly of already-
computed real health signals per named department, zero new health
computation. Every department gets one of two honest shapes:

  - {"data_source": "real", ...real fields...} when a real, already-
    computed signal exists (an orchestrator engine's success rate, a
    real event log's recent activity count, real recovery/retry state).
  - {"data_source": "none", "reason": "..."} when nothing real backs
    the department yet -- Researchers (deliberately unbuilt,
    HIGH_VALUE_STRATEGY.md) and Customer Intelligence (zero real
    customer data) are honestly reported this way, never given a
    fabricated score.

No department here gets a single blended "health score" invented from
scratch -- each keeps its own real, named fields (success_rate,
recent_activity_count, pending_retries, etc.) exactly as its real
source already computes them.
"""

import json
import os
from datetime import datetime, timedelta, timezone

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
GOLDEN_HUNTER_EVENTS_FILE = os.path.join(FACTORY_DIR, 'data', 'golden_hunter_events.jsonl')


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def recent_activity_count(events, days=7, now=None):
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    count = 0
    for e in events:
        ts = e.get("timestamp")
        if not ts:
            continue
        try:
            when = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if when >= since:
            count += 1
    return count


def _engine_department(health, stage):
    stage_health = health.get(stage, {})
    if stage_health.get("maturity") != "REAL":
        return {"data_source": "none", "reason": stage_health.get("reason", f"لا سجل تنفيذ حقيقي كافٍ بعد لمحرّك {stage}")}
    return {
        "data_source": "real",
        "success_rate": stage_health.get("success_rate"),
        "total_executions": stage_health.get("total_executions"),
        "last_status": stage_health.get("last_status"),
        "last_run_at": stage_health.get("last_run_at"),
        "source": "executive_intelligence.engine_health",
    }


def build_department_health(timeline_path=None, events_path=None, ledger_path=None, now=None):
    from executive_intelligence import engine_health as engine_health_module
    from commercial_execution.approval_gates import check_approval_gates
    from ai_capability import registry as ai_registry
    from infrastructure_bridge import get_infrastructure_status
    from channels import ledger as channel_ledger
    import distributor  # noqa: F401 -- self-registers every real, live arm
    import factory_state

    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    events = _read_jsonl(events_path or GOLDEN_HUNTER_EVENTS_FILE)
    golden_hunter_activity = recent_activity_count(
        [e for e in events if e.get("action") in ("attempted", "skipped")], now=now,
    )

    gates = check_approval_gates()
    ai_providers = ai_registry.list_providers()
    infra = get_infrastructure_status()
    state = factory_state.load_state()
    sale_events = list(channel_ledger.read_events(event_type="sale", ledger_path=ledger_path))

    return {
        "executive": _engine_department(health, "decision"),
        "market_intelligence": _engine_department(health, "market_intelligence"),
        "golden_hunter": {
            "data_source": "real",
            "recent_activity_count_7d": golden_hunter_activity,
            "source": "data/golden_hunter_events.jsonl",
        },
        "pioneer": {
            "data_source": "none",
            "reason": "لا عدّاد نشاط منفصل لـPioneer اليوم -- اكتشافاته تُدمَج في نفس سجل Golden Hunter أعلاه",
        },
        "researchers": {
            "data_source": "none",
            "reason": "قرار مؤسِّس متعمَّد وقائم -- بحث حقيقي يحتاج طلباً صريحاً من الرئيس (HIGH_VALUE_STRATEGY.md)، غير مؤتمَت",
        },
        "production": _engine_department(health, "production"),
        "publishing": {
            "data_source": "real",
            "autonomous_channels": len(gates.get("autonomous", [])),
            "gated_channels": len(gates.get("gated", [])),
            "source": "commercial_execution.approval_gates",
        },
        "finance": {
            "data_source": "real",
            "recorded_sales": len(sale_events),
            "source": "channels.ledger.read_events(event_type='sale')",
        },
        "customer_intelligence": {
            "data_source": "none",
            "reason": "صفر بيانات عملاء حقيقية في هذا المصنع حتى الآن",
        },
        "infrastructure": {
            "data_source": "real" if infra else "none",
            "system": infra.get("system") if infra else None,
            "reason": None if infra else "تعذّر جلب حالة البنية التحتية هذه المرة",
            "source": "infrastructure_bridge.py",
        },
        "recovery": {
            "data_source": "real",
            "pending_retries": len(state.get("pending_retries") or []),
            "interrupted": bool((state.get("recovery_info") or {}).get("interrupted")),
            "last_checkpoint": state.get("last_successful_checkpoint"),
            "source": "factory_state.py",
        },
        "ai_capability_manager": {
            "data_source": "real",
            "configured_providers": sum(1 for p in ai_providers if p["configured"]),
            "total_providers": len(ai_providers),
            "source": "ai_capability.registry",
        },
    }


# Executive Intelligence Core, Round 4 (2026-07-29): same real threshold
# executive_intelligence.bottlenecks already uses for "a real engine is
# struggling" -- reused here, not reinvented, so the two real signals stay
# consistent with each other.
_FAILURE_RATE_ALERT_BELOW = 80


def rank_department_weakness(report=None, **kwargs):
    """Real, honest weakness classification over this module's own real
    per-department fields. Deliberately NOT a blended cross-department
    score -- this module's own docstring already establishes that rule
    (department fields have no common unit: success_rate is a percentage,
    recent_activity_count_7d is a raw count, autonomous_channels is a
    count of channels -- averaging them would be a fabrication, not a
    real signal). Three honest buckets instead:

      - no_data: data_source == "none" -- the department's own real,
        stated reason (e.g. Researchers/Customer Intelligence, both
        deliberately unbuilt).
      - below_threshold: a real success_rate exists and is below the
        same real alert threshold executive_intelligence.bottlenecks
        already uses for "engine failure rate" bottleneck detection.
      - healthy: every other department with real, unremarkable data.
    """
    if report is None:
        report = build_department_health(**kwargs)

    no_data = []
    below_threshold = []
    healthy = []
    for name, d in report.items():
        if d.get("data_source") == "none":
            no_data.append({"department": name, "reason": d.get("reason")})
        elif d.get("success_rate") is not None and d["success_rate"] < _FAILURE_RATE_ALERT_BELOW:
            below_threshold.append({"department": name, "success_rate": d["success_rate"]})
        else:
            healthy.append(name)

    return {
        "no_data": no_data,
        "below_threshold": below_threshold,
        "healthy": healthy,
        # Real departments that need real attention -- no fabricated
        # score attached, just the two honest reasons above, concatenated.
        "weakest": no_data + below_threshold,
    }


def render_markdown(report):
    lines = ["## صحة الأقسام\n"]
    for name, d in report.items():
        if d.get("data_source") == "none":
            lines.append(f"- **{name}**: لا بيانات حقيقية -- {d['reason']}")
        else:
            fields = ", ".join(f"{k}={v}" for k, v in d.items() if k not in ("data_source", "source", "reason"))
            lines.append(f"- **{name}**: {fields}")
    return "\n".join(lines) + "\n"
