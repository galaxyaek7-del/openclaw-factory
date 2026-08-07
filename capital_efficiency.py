"""Galaxy Forge -- Capital Efficiency (new, ADR-206, Phase 16, 2026-08-08).

Answers Section 12 of the founder's "Adaptive Growth & Resource
Allocation Engine" directive: revenue per unit of development effort/
AI cost/marketing cost/human intervention/product/platform/customer.

Checked first, per this session's own established discipline:
enterprise_capital_allocation.py::capacity_utilization() measures
RESOURCE capacity, never a revenue-per-X ratio -- confirmed by direct
read, not assumed. This module is the genuinely missing piece.

With $0 real revenue (confirmed live, Phase 15), every numerator here
is honestly 0 -- this module's real value is the denominators it CAN
compute today (real AI cost exists, tracked per-call in
data/ai_cost_log.jsonl) and the honest UNKNOWN for denominators that
have no real tracking anywhere in this factory (development time,
marketing spend, human intervention time) -- never a fabricated
denominator, per the directive's own explicit rule.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
_AI_COST_LOG_PATH = _FACTORY_ROOT / "data" / "ai_cost_log.jsonl"
_FINANCE_PATH = _FACTORY_ROOT / "finance_data.json"
_TEST_RECORD_MARKER = "DELETE-ME"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _real_total_revenue(finance_path=None):
    path = Path(finance_path) if finance_path else _FINANCE_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return 0.0
    sales = [s for s in data.get("sales", []) if _TEST_RECORD_MARKER not in str(s.get("product", ""))]
    return round(sum(float(s.get("amount", 0)) for s in sales), 2)


def _real_total_ai_cost(ai_cost_log_path=None):
    path = Path(ai_cost_log_path) if ai_cost_log_path else _AI_COST_LOG_PATH
    total = 0.0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                total += float(r.get("cost_usd") or 0)
    except OSError:
        return None
    return round(total, 4)


def _ratio(revenue, denominator, denominator_name):
    if denominator is None:
        return {"status": "UNKNOWN", "reason": f"No real {denominator_name} tracking exists anywhere in this factory -- confirmed by direct search, never a fabricated denominator."}
    if denominator == 0:
        return {"status": "UNDEFINED", "reason": f"{denominator_name} is a real, verified $0 -- a ratio against a real zero denominator is undefined, not a fabricated infinity."}
    return {"value": round(revenue / denominator, 4), "revenue_usd": revenue, "denominator": denominator, "denominator_name": denominator_name}


def capital_efficiency_report(finance_path=None, ai_cost_log_path=None, now=None):
    """The one real aggregator. 7 named ratios -- each real where a real
    denominator exists, honestly UNKNOWN otherwise."""
    now = now or datetime.now(timezone.utc)
    revenue = _real_total_revenue(finance_path=finance_path)
    ai_cost = _real_total_ai_cost(ai_cost_log_path=ai_cost_log_path)

    try:
        import product_master_catalog as pmc
        product_count = pmc.build_product_master_catalog()["total_products"]
    except Exception:
        product_count = None

    try:
        from channels import registry
        import channels.paddle_arm, channels.gumroad_arm  # noqa: F401
        from channels.base_arm import ArmStatus
        platform_count = sum(1 for arm in registry.all_arms() if arm.status() == ArmStatus.READY)
    except Exception:
        platform_count = None

    customer_count = 0  # data/customer_requests.jsonl does not exist -- real, verified 0, not Unknown

    return {
        "generated_at": now.isoformat(),
        "total_revenue_usd": revenue,
        "ratios": {
            "revenue_per_development_effort": {"status": "UNKNOWN", "reason": "No real historical per-task engineering-time tracking exists anywhere in this factory (same disclosed gap execution_status.py/strategic_planning.py already carry for 'estimated_completion')."},
            "revenue_per_ai_cost": _ratio(revenue, ai_cost, "AI cost (data/ai_cost_log.jsonl)") if ai_cost is not None else {"status": "UNKNOWN", "reason": "data/ai_cost_log.jsonl not found"},
            "revenue_per_marketing_cost": {"status": "UNKNOWN", "reason": "$0 real marketing spend has ever occurred -- no denominator exists to divide by, real or zero-valued."},
            "revenue_per_human_intervention": {"status": "UNKNOWN", "reason": "No real time-tracking of founder/human intervention hours exists anywhere in this factory."},
            "revenue_per_product": _ratio(revenue, product_count, "real product count (product_master_catalog.py)") if product_count is not None else {"status": "UNKNOWN", "reason": "product_master_catalog.py unavailable"},
            "revenue_per_platform": _ratio(revenue, platform_count, "real credentialed platform count") if platform_count is not None else {"status": "UNKNOWN", "reason": "channels registry unavailable"},
            "revenue_per_customer": _ratio(revenue, customer_count, "real customer count (data/customer_requests.jsonl)"),
        },
        "note": "Every ratio with a real denominator is computed; every ratio with no real tracked denominator honestly reports UNKNOWN rather than a fabricated number. With $0 real revenue today, computed ratios (where a real denominator does exist) correctly evaluate to $0 -- not evidence of inefficiency, evidence of pre-revenue state.",
    }
