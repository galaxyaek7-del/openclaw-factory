"""
Strategic Intelligence Report (ADR-054) — assembles the six required
questions into one report. Completely read-only: every module this
imports only reads already-persisted data; nothing here executes,
publishes, changes production state, modifies a score, or edits any
other module.

Standalone, deliberately-run tool, same convention as every other
analysis module this factory has introduced:

    python -m strategic_intelligence.report
"""

import json
from datetime import datetime, timezone

from strategic_intelligence import bottleneck_effort, channel_value, decision_patterns, rejection_patterns, technical_debt


def generate_strategic_report(decisions_path=None, outcomes_path=None, timeline_path=None, sales_ledger_path=None):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "which_decision_patterns_lead_to_success": decision_patterns.find_success_patterns(
            decisions_path=decisions_path, outcomes_path=outcomes_path
        ),
        "most_frequent_rejection_reasons": rejection_patterns.most_frequent_rejection_reasons(
            decisions_path=decisions_path
        ),
        "bottleneck_consuming_most_effort": bottleneck_effort.most_effort_consuming_bottleneck(
            decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path
        ),
        "least_predictive_scoring_dimensions": decision_patterns.find_least_predictive_dimensions(
            decisions_path=decisions_path, outcomes_path=outcomes_path
        ),
        "highest_long_term_value_channel": channel_value.highest_long_term_value_channel(
            sales_ledger_path=sales_ledger_path
        ),
        "components_at_risk_of_technical_debt": technical_debt.components_at_risk_of_technical_debt(
            decisions_path=decisions_path, timeline_path=timeline_path, sales_ledger_path=sales_ledger_path
        ),
    }


def render_markdown(report):
    lines = []
    lines.append("# التقرير الاستراتيجي — Galaxy Forge")
    lines.append(f"**التوليد:** {report['generated_at']}")
    lines.append("")

    questions = [
        ("أي أنماط قرار تؤدي تكراراً لنتائج ناجحة؟", "which_decision_patterns_lead_to_success"),
        ("ما أكثر أسباب الرفض تكراراً؟", "most_frequent_rejection_reasons"),
        ("أي اختناق يستهلك أكبر جهد؟", "bottleneck_consuming_most_effort"),
        ("أي أبعاد تسجيل الأقل قدرة على التنبؤ؟", "least_predictive_scoring_dimensions"),
        ("أي قناة إنتاج تُولِّد أعلى قيمة طويلة الأمد؟", "highest_long_term_value_channel"),
        ("أي مكوّنات معمارية نادرة المساهمة (دَين تقني محتمل)؟", "components_at_risk_of_technical_debt"),
    ]

    for question, key in questions:
        section = report[key]
        lines.append(f"## {question}")
        answer = section.get("answer")
        if answer == "Unknown" or answer is None:
            lines.append(f"**الإجابة: Unknown** — {section.get('reason', 'دليل غير كافٍ')}")
        else:
            lines.append(f"**الإجابة:** {answer}")
            if "evidence" in section:
                evidence = section["evidence"]
                if isinstance(evidence, list):
                    for e in evidence:
                        if isinstance(e, dict):
                            lines.append(f"  - {e.get('component', e)}: {e.get('evidence', '')}")
                        else:
                            lines.append(f"  - {e}")
                else:
                    lines.append(f"  - {evidence}")
        lines.append(f"  - *المصدر: {section.get('source', 'غير محدَّد')}*")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    report = generate_strategic_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
