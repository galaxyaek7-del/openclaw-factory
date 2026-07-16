"""
Channel long-term value (ADR-054) — "Which production channels generate
the highest long-term value?"

Real sale COUNT per platform is always reported (unambiguous — a real
"sale" event in data/sales_ledger.jsonl, channels/ledger.py, grouped by
its own real "platform" field). A monetary total is reported alongside
it only when the real sale payload actually carries a numeric "price"
field (Gumroad's own documented API shape) — this factory has never
seen one real sale yet, so that field's presence/shape is unconfirmed in
practice; if it is ever missing or non-numeric, the monetary total is
"Unknown" rather than silently guessed at zero or skipped.
"""

import channels.etsy_arm  # noqa: F401,E402 — self-registers on import
import channels.gumroad_arm  # noqa: F401,E402
import channels.payhip_arm  # noqa: F401,E402
from channels import ledger as sales_ledger


def highest_long_term_value_channel(sales_ledger_path=None):
    sales = list(sales_ledger.read_events(event_type="sale", ledger_path=sales_ledger_path))

    if not sales:
        return {
            "answer": "Unknown",
            "reason": "صفر مبيعات حقيقية مسجَّلة بعد في data/sales_ledger.jsonl",
            "source": "channels.ledger.read_events(event_type='sale')",
        }

    counts = {}
    revenue = {}
    revenue_confirmed = {}
    for sale in sales:
        platform = sale.get("platform", "unknown")
        counts[platform] = counts.get(platform, 0) + 1
        raw = sale.get("raw") or {}
        price = raw.get("price")
        if isinstance(price, (int, float)):
            revenue[platform] = revenue.get(platform, 0) + price
            revenue_confirmed[platform] = True
        else:
            revenue_confirmed[platform] = revenue_confirmed.get(platform, False)

    ranked_by_count = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    ranked_by_revenue = sorted(revenue.items(), key=lambda kv: kv[1], reverse=True) if revenue else []

    return {
        "answer_by_count": ranked_by_count[0][0],
        "sale_counts": dict(ranked_by_count),
        "answer_by_revenue": ranked_by_revenue[0][0] if ranked_by_revenue else "Unknown",
        "revenue_totals": revenue if revenue else None,
        "revenue_note": (
            "إجمالي حقيقي من حقل 'price' الفعلي في بيانات المبيعات"
            if revenue else
            "لا حقل 'price' رقمي حقيقي متاح في المبيعات المسجَّلة — لا مجموع مالي يُحتسَب"
        ),
        "source": "channels.ledger.read_events(event_type='sale')",
    }
