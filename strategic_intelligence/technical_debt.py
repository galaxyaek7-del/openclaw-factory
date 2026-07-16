"""
Architectural components that rarely contribute (ADR-054) — "Which
architectural components rarely contribute and may become technical
debt?"

Reused verbatim from executive_intelligence.inactivity.
detect_inactive_components() (ADR-052) — that function already answers
exactly this question (zero-activity orchestrator engines, zero-activity
channel arms) from the real timeline and sales ledger. No second
computation.
"""

from executive_intelligence import inactivity as inactivity_module


def components_at_risk_of_technical_debt(decisions_path=None, timeline_path=None, sales_ledger_path=None):
    result = inactivity_module.detect_inactive_components(
        decisions_path=decisions_path, timeline_path=timeline_path, sales_ledger_path=sales_ledger_path,
    )
    if not result["detected"]:
        return {
            "answer": "Unknown",
            "reason": "كل مكوّن مسجَّل شهد نشاطاً حقيقياً واحداً على الأقل حتى الآن",
            "source": "executive_intelligence.inactivity.detect_inactive_components()",
        }

    return {
        "answer": [item["component"] for item in result["items"]],
        "evidence": result["items"],
        "source": "executive_intelligence.inactivity.detect_inactive_components()",
    }
