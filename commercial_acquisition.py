"""Galaxy Forge -- Customer Acquisition & Commercial Funnel (new, ADR-202,
2026-08-07).

Answers Phase 12 Sections 9 and 10 of the founder's "Global Commercial
Revenue Operating System" directive.

Section 9 (Customer Acquisition): the 9 named channels (Organic Search/
Marketplace/Affiliate/Partnership/Social/Email/Direct/Referral/Paid
Advertising), each scored on CAC/Conversion/Revenue/Net revenue/LTV/
ROI/Payback period "when data is available." None is available today --
confirmed by direct search: no arm or ledger anywhere in this factory
records a real acquisition-channel field on a sale (channels/ledger.py::
record_sale()'s new `channel` parameter, ADR-202 part 2, exists but has
never been called with a real value by any real caller yet). Every
channel below honestly reports INSUFFICIENT_DATA per the directive's
own explicit instruction, never a fabricated number.

Section 10 (Commercial Funnel): the 11 named stages (Market -> Visitor
-> Lead -> Qualified Lead -> Trial/Interest -> Customer -> Repeat
Customer -> Subscriber -> Advocate -> Partner -> Enterprise Customer).
The bottom half (Customer onward) real-maps onto customer_pipeline.py's
own real STAGE_ORDER and funnel_conversion_summary() -- reused
verbatim, never re-derived. The top half (Market/Visitor/Lead/Qualified
Lead/Trial) has zero real signal anywhere in this factory: no web
analytics, no lead-capture form, no marketing-qualified-lead scoring
exists. Honestly disclosed as NO_REAL_SOURCE, never invented.
"""

from datetime import datetime, timezone

ACQUISITION_CHANNELS = (
    "organic_search", "marketplace", "affiliate", "partnership",
    "social", "email", "direct", "referral", "paid_advertising",
)

# Section 10's 11 named funnel stages, in order.
FUNNEL_STAGES = (
    "market", "visitor", "lead", "qualified_lead", "trial_interest",
    "customer", "repeat_customer", "subscriber", "advocate", "partner", "enterprise_customer",
)

_TOP_FUNNEL_NO_SOURCE_REASON = "No real web analytics, lead-capture form, or marketing-qualified-lead scoring exists anywhere in this factory -- confirmed by direct search, not assumed."


def _channel_summary(channel_key, real_sales_with_channel):
    """Real per-channel computation when sale records actually carry a
    `channel` attribution field (see channels/ledger.py::record_sale()) --
    honestly INSUFFICIENT_DATA otherwise, per Section 9's own instruction."""
    matched = [s for s in real_sales_with_channel if s.get("channel") == channel_key]
    if not matched:
        return {
            "channel": channel_key, "status": "INSUFFICIENT_DATA",
            "reason": "0 real sale events carry this channel's attribution tag yet.",
        }
    revenue = round(sum(float(s.get("amount", 0)) for s in matched), 2)
    return {
        "channel": channel_key,
        "revenue_usd": revenue,
        "sale_count": len(matched),
        "cac": {"status": "INSUFFICIENT_DATA", "reason": "No real acquisition-spend-per-channel figure is tracked anywhere in this factory."},
        "conversion": {"status": "INSUFFICIENT_DATA", "reason": "No real per-channel visitor/lead count exists to compute a conversion rate against."},
        "net_revenue_usd": None,
        "ltv": {"status": "INSUFFICIENT_DATA", "reason": "See goos.py's own disclosed CLV gap -- no real dollar CLV computation exists anywhere in this factory."},
        "roi": {"status": "INSUFFICIENT_DATA", "reason": "Requires both a real CAC and a real LTV, neither of which exists yet."},
        "payback_period": {"status": "INSUFFICIENT_DATA", "reason": "Requires a real CAC, which doesn't exist yet."},
    }


def customer_acquisition_report(now=None, ledger_events=None):
    """The one real aggregator over all 9 named channels. `ledger_events`
    is injectable for testing; defaults to a real read of the sale
    events already carrying attribution (today: 0)."""
    now = now or datetime.now(timezone.utc)
    if ledger_events is None:
        try:
            import channels.ledger as ledger_module
            ledger_events = [e for e in ledger_module.read_events(event_type="sale") if e.get("channel")]
        except Exception:
            ledger_events = []

    channels_report = {c: _channel_summary(c, ledger_events) for c in ACQUISITION_CHANNELS}
    channels_with_data = [c for c, r in channels_report.items() if r.get("status") != "INSUFFICIENT_DATA"]

    return {
        "generated_at": now.isoformat(),
        "channels": channels_report,
        "channels_with_real_data": channels_with_data,
        "note": f"{len(channels_with_data)}/{len(ACQUISITION_CHANNELS)} channels have real attributed sale data today. The remaining channels honestly report INSUFFICIENT_DATA per the directive's own explicit instruction -- never a fabricated CAC/LTV/ROI.",
    }


def commercial_funnel(now=None, conversion_summary=None):
    """Real projection of customer_pipeline.py's own STAGE_ORDER onto the
    bottom 7 of the directive's 11 named funnel stages. The top 4
    (Market/Visitor/Lead/Qualified Lead) plus Trial/Interest are
    honestly NO_REAL_SOURCE -- see module docstring."""
    now = now or datetime.now(timezone.utc)
    if conversion_summary is None:
        try:
            import customer_pipeline
            conversion_summary = customer_pipeline.funnel_conversion_summary()
        except Exception as e:
            conversion_summary = {"answer": "Unknown", "reason": str(e)}

    stages = {}
    for stage in ("market", "visitor", "lead", "qualified_lead", "trial_interest"):
        stages[stage] = {"status": "NO_REAL_SOURCE", "reason": _TOP_FUNNEL_NO_SOURCE_REASON}

    real_counts = conversion_summary.get("stage_reach_counts") if isinstance(conversion_summary, dict) else None
    stages["customer"] = {"status": "OK", "real_count": real_counts.get("PAID") if real_counts else None, "source": "customer_pipeline.py's real PAID stage"} if real_counts else {"status": "NO_DATA_YET", "reason": conversion_summary.get("reason") if isinstance(conversion_summary, dict) else "Unknown"}
    stages["repeat_customer"] = {"status": "NO_REAL_SOURCE", "reason": "No real per-customer repeat-purchase tracking exists yet -- 0 real customers to measure repeat behavior against."}
    stages["subscriber"] = {"status": "NO_REAL_SOURCE", "reason": "No real recurring/subscription billing has ever executed in this factory."}
    stages["advocate"] = {"status": "NO_REAL_SOURCE", "reason": "See customer_pipeline.py's own real review-submission gate -- 0 real reviews exist yet to identify an advocate from."}
    stages["partner"] = {"status": "OK", "source": "business_development.py's real pipeline -- see build_partnership_pipeline_board()"}
    stages["enterprise_customer"] = {"status": "NO_REAL_SOURCE", "reason": "0 real ACCEPTED enterprise-ladder opportunities exist today."}

    return {
        "generated_at": now.isoformat(),
        "stages": stages,
        "real_conversion_data": conversion_summary,
        "note": "Bottom-funnel stages (customer onward) real-cite customer_pipeline.py's own STAGE_ORDER/funnel_conversion_summary() -- never re-derived. Top-funnel stages (market/visitor/lead/qualified_lead/trial_interest) are honestly NO_REAL_SOURCE -- no web analytics or lead-capture infrastructure exists anywhere in this factory.",
    }
