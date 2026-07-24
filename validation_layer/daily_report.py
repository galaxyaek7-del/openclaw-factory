"""
Daily Validation Report (ADR-053) — the specific breakdown requested:
opportunities discovered/accepted/rejected, production completed,
publication completed, revenue generated, failures (exact reason +
source module), bottlenecks, recommendations. Every figure reuses an
already-built real function; nothing here is a second implementation of
a number computed elsewhere (executive_intelligence's opportunity
counts/bottleneck detection, decision_engine's outcome store).

Standalone, deliberately-run tool, same convention as every other
analysis module this factory has introduced:

    python -m validation_layer.daily_report
"""

import json
from datetime import datetime, timezone

from decision_engine import store as decision_store
from executive_intelligence import bottlenecks as bottleneck_module
from executive_intelligence import engine_health as engine_health_module
from executive_intelligence import opportunities as opportunities_module
from executive_intelligence import revenue_distance as revenue_distance_module
from orchestrator import timeline as orch_timeline

from validation_layer import reliability as reliability_module
from validation_layer import stalled as stalled_module


def _real_failures(timeline_path=None):
    """Every real FAILED execution, with its exact reason and source
    module (the engine name) — requirement 4, read verbatim from the
    immutable timeline, never summarized into a bare count."""
    return [
        {"engine": r.get("engine"), "reason": r.get("error"), "at": r.get("finished_at")}
        for r in orch_timeline.read_timeline(path=timeline_path)
        if r.get("status") == "FAILED"
    ]


def _recommendations(opp, stalled, bottleneck_snapshot, revenue_distance):
    """Every recommendation cites the real evidence already computed
    above — never a generic tip disconnected from this run's own data."""
    recs = []

    if stalled["detected"]:
        recs.append({
            "recommendation": "تحقَّق من الفرص المقبولة العالقة قبل الإنتاج",
            "evidence": f"{len(stalled['items'])} فرصة ACCEPTED بلا تنفيذ إنتاج حقيقي — انظر قسم stalled_opportunities",
        })

    if bottleneck_snapshot["detected"]:
        recs.append({
            "recommendation": "عالج الاختناقات المكتشَفة قبل زيادة حجم الفرص المُقيَّمة",
            "evidence": f"{len(bottleneck_snapshot['items'])} اختناق حقيقي مكتشَف — انظر قسم bottlenecks",
        })

    if revenue_distance.get("maturity") == "DISCOVERY":
        for b in revenue_distance.get("blockers", []):
            recs.append({"recommendation": f"عالج العائق: {b['blocker']}", "evidence": b["evidence"]})

    if not recs:
        recs.append({
            "recommendation": "لا توصية عاجلة — لا اختناقات أو فرص عالقة مكتشَفة اليوم",
            "evidence": "مبني على opportunities/bottlenecks/stalled الحقيقية أعلاه",
        })

    return recs


def generate_daily_report(decisions_path=None, outcomes_path=None, timeline_path=None, sales_ledger_path=None):
    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    opp = opportunities_module.track_opportunities(decisions_path=decisions_path)
    stalled = stalled_module.detect_stalled_opportunities(decisions_path=decisions_path, timeline_path=timeline_path)
    bottleneck_snapshot = bottleneck_module.detect_bottlenecks(
        health, decisions_path=decisions_path, outcomes_path=outcomes_path
    )
    revenue_distance = revenue_distance_module.estimate_distance_to_next_revenue(
        decisions_path=decisions_path, outcomes_path=outcomes_path
    )
    reliability = reliability_module.compute_reliability_statistics(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path
    )
    failures = _real_failures(timeline_path=timeline_path)

    real_revenue_events = [
        o for o in decision_store.read_outcomes(path=outcomes_path) if o.get("matched")
    ]

    def _completed(stage):
        h = health.get(stage, {})
        return h.get("successes", 0) if h.get("maturity") == "REAL" else 0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "opportunities_discovered": sum(opp["counts"].values()),
        "opportunities_accepted": opp["counts"].get("ACCEPTED", 0),
        "opportunities_rejected": opp["counts"].get("REJECTED", 0),
        "opportunities_deferred": opp["counts"].get("DEFERRED", 0),
        "production_completed": _completed("production"),
        "publication_completed": _completed("publishing"),
        "revenue_generated": len(real_revenue_events),
        "failures": failures,
        "bottlenecks": bottleneck_snapshot,
        "stalled_opportunities": stalled,
        "reliability": reliability,
        "revenue_distance": revenue_distance,
        "recommendations": _recommendations(opp, stalled, bottleneck_snapshot, revenue_distance),
    }


def render_markdown(report):
    lines = []
    lines.append("# تقرير التحقُّق اليومي — Galaxy Forge")
    lines.append(f"**التوليد:** {report['generated_at']}")
    lines.append("")
    lines.append(f"- **فرص مُكتشَفة:** {report['opportunities_discovered']}")
    lines.append(f"- **فرص مقبولة:** {report['opportunities_accepted']}")
    lines.append(f"- **فرص مرفوضة:** {report['opportunities_rejected']}")
    lines.append(f"- **فرص مؤجَّلة:** {report['opportunities_deferred']}")
    lines.append(f"- **إنتاج مكتمل (حقيقي):** {report['production_completed']}")
    lines.append(f"- **نشر مكتمل (حقيقي):** {report['publication_completed']}")
    lines.append(f"- **إيراد حقيقي مُسجَّل:** {report['revenue_generated']}")
    lines.append("")

    lines.append("## الإخفاقات (سبب دقيق + محرّك المصدر)")
    if report["failures"]:
        for f in report["failures"]:
            lines.append(f"- **{f['engine']}** ({f['at']}): {f['reason']}")
    else:
        lines.append("- صفر إخفاق حقيقي مسجَّل")

    lines.append("")
    lines.append("## الاختناقات")
    if report["bottlenecks"]["detected"]:
        for b in report["bottlenecks"]["items"]:
            lines.append(f"- {b['evidence']}")
    else:
        lines.append(f"- {report['bottlenecks']['reason']}")

    lines.append("")
    lines.append("## فرص مقبولة عالقة قبل الإنتاج")
    if report["stalled_opportunities"]["detected"]:
        for s in report["stalled_opportunities"]["items"]:
            lines.append(f"- {s['niche']}: {s['evidence']}")
    else:
        lines.append("- لا شيء")

    lines.append("")
    lines.append("## التوصيات")
    for r in report["recommendations"]:
        lines.append(f"- **{r['recommendation']}** — {r['evidence']}")

    return "\n".join(lines) + "\n"


def main():
    report = generate_daily_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
