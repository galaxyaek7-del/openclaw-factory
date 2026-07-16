"""
Daily Executive Report (ADR-052) — assembles every real signal above into
one report, and renders a concise Markdown CEO summary designed to be
read in under 60 seconds: headline counts first, then evidence-backed
detail sections. Every number in the summary traces to a named source
file/function — never a bare figure with nothing behind it.

Standalone, deliberately-run tool (same convention as every other
analysis module this factory has introduced: market_hunter.py,
competitor_discovery.py, market_intelligence_engine.py, decision_engine,
orchestrator) — not wired into server.js/factory_loop.js's live tick.

    python -m executive_intelligence.report
"""

import json
from datetime import datetime, timezone

from decision_engine import learning as decision_learning

from executive_intelligence import bottlenecks as bottleneck_module
from executive_intelligence import engine_health as engine_health_module
from executive_intelligence import inactivity as inactivity_module
from executive_intelligence import opportunities as opportunities_module
from executive_intelligence import revenue_distance as revenue_distance_module


def generate_report(decisions_path=None, outcomes_path=None, timeline_path=None, sales_ledger_path=None):
    health = engine_health_module.compute_engine_health(timeline_path=timeline_path)
    opp = opportunities_module.track_opportunities(decisions_path=decisions_path)
    top_opportunity = opportunities_module.highest_value_pending_opportunity(
        decisions_path=decisions_path, outcomes_path=outcomes_path
    )
    accuracy = decision_learning.compute_prediction_accuracy(decisions_path=decisions_path, outcomes_path=outcomes_path)
    bottlenecks = bottleneck_module.detect_bottlenecks(health, decisions_path=decisions_path, outcomes_path=outcomes_path)
    revenue_distance = revenue_distance_module.estimate_distance_to_next_revenue(
        decisions_path=decisions_path, outcomes_path=outcomes_path
    )
    inactivity = inactivity_module.detect_inactive_components(
        decisions_path=decisions_path, timeline_path=timeline_path, sales_ledger_path=sales_ledger_path
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine_health": health,
        "opportunities": opp,
        "highest_value_pending_opportunity": top_opportunity,
        "prediction_accuracy": accuracy,
        "bottlenecks": bottlenecks,
        "revenue_distance": revenue_distance,
        "inactive_components": inactivity,
    }


def render_markdown(report):
    lines = []
    lines.append(f"# التقرير التنفيذي اليومي — OpenClaw Factory")
    lines.append(f"**التوليد:** {report['generated_at']}")
    lines.append("")

    counts = report["opportunities"]["counts"]
    lines.append(
        f"**الفرص:** {counts.get('ACCEPTED', 0)} مقبولة | "
        f"{counts.get('REJECTED', 0)} مرفوضة | {counts.get('DEFERRED', 0)} مؤجَّلة "
        f"(المصدر: {report['opportunities']['source']})"
    )

    top = report["highest_value_pending_opportunity"]
    if top["available"]:
        lines.append(f"**أعلى فرصة بانتظار التنفيذ:** {top['niche']} — Opportunity Score {top['opportunity_score']}/100")
    else:
        lines.append(f"**أعلى فرصة بانتظار التنفيذ:** {top['reason']}")

    acc = report["prediction_accuracy"]
    if acc.get("accuracy") is not None:
        lines.append(f"**دقة التنبؤ:** {acc['accuracy']}% (من {acc['real_outcomes']} نتيجة مبيعات حقيقية مطابَقة)")
    else:
        lines.append(f"**دقة التنبؤ:** غير متاحة — {acc.get('reason')}")

    rd = report["revenue_distance"]
    if rd["maturity"] == "ESTIMATED":
        lines.append(f"**الخطوة التالية نحو أول إيراد حقيقي:** {rd['next_step']}")
    else:
        lines.append(f"**الخطوة التالية نحو أول إيراد حقيقي:** معطَّلة — {len(rd['blockers'])} عائق حقيقي:")
        for b in rd["blockers"]:
            lines.append(f"  - {b['evidence']}")

    lines.append("")
    lines.append("## صحة المحرّكات (data/orchestrator_timeline.jsonl)")
    for engine, h in report["engine_health"].items():
        if h["maturity"] == "DISCOVERY":
            lines.append(f"- **{engine}**: {h['reason']}")
        else:
            lines.append(f"- **{engine}**: {h['total_executions']} تنفيذ، نجاح {h.get('success_rate')}٪، آخر حالة: {h['last_status']}")

    lines.append("")
    lines.append("## الاختناقات")
    if report["bottlenecks"]["detected"]:
        for b in report["bottlenecks"]["items"]:
            lines.append(f"- {b['evidence']}")
    else:
        lines.append(f"- {report['bottlenecks']['reason']}")

    lines.append("")
    lines.append("## مكوّنات غير نشطة")
    if report["inactive_components"]["detected"]:
        for c in report["inactive_components"]["items"]:
            lines.append(f"- {c['component']}: {c['evidence']}")
    else:
        lines.append("- لا شيء — كل مكوّن مسجَّل شهد نشاطاً حقيقياً واحداً على الأقل")

    return "\n".join(lines) + "\n"


def main():
    report = generate_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
