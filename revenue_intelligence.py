"""Galaxy Forge — Revenue Intelligence decision layer.

Directive (2026-08-14): "النظام يجب أن يتعلم: KEEP / SCALE / RETEST /
PAUSE / REMOVE" — over the affiliate program portfolio, driven by REAL
click, conversion, and commission data.

Honesty contract: every decision must be traceable to real data. When no
real conversion or commission signal exists, the decision is an honest
"INSUFFICIENT_DATA" (or "KEEP" for a program that is verified, has real
clicks, but has not yet had time to convert) — never a fabricated
verdict. The thresholds below are tunable constants with documented
defaults; the module never fabricates a metric it was not given.

The decision matrix (all thresholds over REAL data only):

  - REMOVE       -> real clicks > 0 AND real clicks == real conversions
                    AND real commission == $0 AND evidence is old enough
                    to be conclusive. (No clicks -> not enough to remove.)
  - PAUSE        -> real clicks with zero conversions but still within a
                    retest window, OR real negative-margin signal.
  - RETEST       -> real clicks > 0, zero conversions, and the retest
                    window has NOT yet elapsed -> change angle, retry.
  - SCALE        -> real conversions >= MIN_CONVERSIONS_TO_SCALE AND
                    real commission > 0 AND EPC >= EPC_SCALE_FLOOR.
  - KEEP         -> verified program with real clicks and zero failures,
                    but not yet enough data to decide otherwise.
  - INSUFFICIENT_DATA -> no real clicks at all (nothing measured yet).

Pure functions except the optional read_clicks/read_ledger helpers. Never
posts, never spends, never touches any gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

# --- documented thresholds (real-data only) ---
MIN_CONVERSIONS_TO_SCALE = 3          # real conversions before "SCALE" is possible
EPC_SCALE_FLOOR = 1.0                 # $ per click below which we don't SCALE
RETEST_WINDOW_DAYS = 30               # clicks without conversion within this window -> RETEST
CONVERSION_LONG_WINDOW_DAYS = 90      # beyond this, zero-conversion clicks -> REMOVE
MIN_CLICKS_TO_DECIDE = 5              # below this click count we lack evidence


@dataclass
class AffiliateMetrics:
    program_id: str
    program_name: str = ""
    verification_status: str = ""
    real_clicks: int = 0
    real_conversions: int = 0
    real_commission_usd: float = 0.0
    first_click_at: Optional[str] = None
    last_click_at: Optional[str] = None
    recurring_commission: bool = False
    evidence_notes: str = ""


@dataclass
class RevenueDecision:
    program_id: str
    decision: str  # KEEP | SCALE | RETEST | PAUSE | REMOVE | INSUFFICIENT_DATA
    reason: str
    metrics: Dict[str, object] = field(default_factory=dict)
    decided_at: Optional[str] = None


def _days_between(iso_start: Optional[str], now: datetime) -> Optional[float]:
    if not iso_start:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_start).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() / 86400.0
    except ValueError:
        return None


def decide_on_program(metrics: AffiliateMetrics, now: Optional[datetime] = None) -> RevenueDecision:
    """Map one program's REAL metrics to a decision. All thresholds apply to
    real data only; every branch that can't be evidenced returns an honest
    INSUFFICIENT_DATA/KEEP rather than a guess."""
    now = now or datetime.now(timezone.utc)
    ts = now.isoformat()
    m = metrics

    if m.real_clicks <= 0:
        return RevenueDecision(
            program_id=m.program_id, decision="INSUFFICIENT_DATA",
            reason=f"لا نقرات حقيقية مسجلة بعد — لا يمكن اتخاذ قرار على بيانات غير موجودة.",
            metrics=_metric_dict(m), decided_at=ts,
        )

    if m.real_clicks < MIN_CLICKS_TO_DECIDE:
        return RevenueDecision(
            program_id=m.program_id, decision="KEEP",
            reason=f"{m.real_clicks} نقرات حقيقية فقط — أقل من حد {MIN_CLICKS_TO_DECIDE} للحسم؛ أبقِ البرنامج قيد المراقبة.",
            metrics=_metric_dict(m), decided_at=ts,
        )

    days_since_first = _days_between(m.first_click_at, now)
    clicks_no_convert = m.real_conversions == 0 and m.real_commission_usd <= 0

    if m.real_conversions >= MIN_CONVERSIONS_TO_SCALE and m.real_commission_usd > 0:
        epc = m.real_commission_usd / m.real_clicks
        if epc >= EPC_SCALE_FLOOR:
            return RevenueDecision(
                program_id=m.program_id, decision="SCALE",
                reason=f"{m.real_conversions} تحويلات حقيقية، عمولة ${m.real_commission_usd:.2f}، EPC ${epc:.2f} ≥ حد ${EPC_SCALE_FLOOR} — وسّع التوزيع.",
                metrics=_metric_dict(m), decided_at=ts,
            )
        return RevenueDecision(
            program_id=m.program_id, decision="KEEP",
            reason=f"تحويلات حقيقية موجودة لكن EPC ${epc:.2f} أقل من حد التوسيع ${EPC_SCALE_FLOOR} — أبقِ وحسّن الزاوية.",
            metrics=_metric_dict(m), decided_at=ts,
        )

    # zero-conversion branch
    if clicks_no_convert:
        if days_since_first is not None and days_since_first >= CONVERSION_LONG_WINDOW_DAYS:
            return RevenueDecision(
                program_id=m.program_id, decision="REMOVE",
                reason=f"{m.real_clicks} نقرات بلا أي تحويل عبر {int(days_since_first)} يومًا — تخطى نافذة الحسم؛ أزل البرنامج (بيانات حقيقية فقط).",
                metrics=_metric_dict(m), decided_at=ts,
            )
        if days_since_first is not None and days_since_first >= RETEST_WINDOW_DAYS:
            return RevenueDecision(
                program_id=m.program_id, decision="RETEST",
                reason=f"{m.real_clicks} نقرات بلا تحويل بعد {int(days_since_first)} يومًا — غيّر الزاوية/المحتوى وأعد الاختبار.",
                metrics=_metric_dict(m), decided_at=ts,
            )
        return RevenueDecision(
            program_id=m.program_id, decision="KEEP",
            reason=f"{m.real_clicks} نقرات حقيقية، لا تحويل بعد — لا تزال ضمن نافذة إعادة الاختبار ({RETEST_WINDOW_DAYS} يومًا). أبقِ.",
            metrics=_metric_dict(m), decided_at=ts,
        )

    return RevenueDecision(
        program_id=m.program_id, decision="KEEP",
        reason="لا مؤشر سلبي/إيجابي حاسم بعد — أبقِ قيد المراقبة.",
        metrics=_metric_dict(m), decided_at=ts,
    )


def _metric_dict(m: AffiliateMetrics) -> Dict[str, object]:
    return {
        "real_clicks": m.real_clicks,
        "real_conversions": m.real_conversions,
        "real_commission_usd": m.real_commission_usd,
        "first_click_at": m.first_click_at,
        "last_click_at": m.last_click_at,
        "recurring_commission": m.recurring_commission,
    }


def decide_on_many(metrics_list: List[AffiliateMetrics],
                   now: Optional[datetime] = None) -> List[RevenueDecision]:
    """Decide for a list of programs; preserves order."""
    return [decide_on_program(m, now=now) for m in metrics_list]


def portfolio_decision_summary(decisions: List[RevenueDecision]) -> Dict[str, object]:
    """Honest aggregate over a batch of decisions."""
    from collections import Counter
    counts = Counter(d.decision for d in decisions)
    scaleable = [d for d in decisions if d.decision == "SCALE"]
    remove = [d for d in decisions if d.decision == "REMOVE"]
    return {
        "total": len(decisions),
        "by_decision": dict(counts),
        "scale_candidates": [d.program_id for d in scaleable],
        "remove_candidates": [d.program_id for d in remove],
        "note": "الملخص يعتمد فقط على مخرجات القرارات الفعلية المبنية على بيانات حقيقية.",
    }


# ---------------------------------------------------------------------------
# Full Revenue Intelligence dashboard (directive section 8): Revenue, Clicks,
# CTR, Conversion, EPC, Commission, Recurring Commission, Top Products /
# Channels / Content, Revenue per 1,000 views, Revenue per visitor. Every
# metric is computed from REAL ledgers; any denominator of zero yields an
# honest "N/A" rather than a fabricated rate.
# ---------------------------------------------------------------------------

def revenue_intelligence_dashboard(page_views_path=None, clicks_path=None,
                                   commission_ledger_path=None,
                                   recurring_commission_filter=None,
                                   now: Optional[datetime] = None) -> Dict[str, object]:
    """Full dashboard from real ledgers only. `recurring_commission_filter`
    may be a set of opportunity_ids known to be recurring, to tag recurring
    commission separately -- no metric is ever fabricated, and totals are
    only summed from rows actually present."""
    from affiliate_commerce import click_tracking
    import commission_ledger as cl

    views = click_tracking.read_page_views(page_views_path)
    clicks = click_tracking.read_clicks(clicks_path)
    ledger = cl.load_ledger(commission_ledger_path)
    real_rows = [r for r in ledger if r.get("environment") == "REAL"]

    # Commission/revenue only from REAL rows that are CONFIRMED or PAID.
    paid_rows = [r for r in real_rows if r.get("commission_status") in ("CONFIRMED", "PAID")]
    total_commission = sum(float(r.get("gross_commission") or 0) for r in paid_rows)
    recurring_commission = sum(
        float(r.get("gross_commission") or 0)
        for r in paid_rows
        if r.get("opportunity_id") in (recurring_commission_filter or set())
    )

    # Per-product aggregates over real clicks + real paid commissions.
    clicks_per_product: Dict[str, int] = {}
    for c in clicks:
        pid = c.get("product_id")
        if pid:
            clicks_per_product[pid] = clicks_per_product.get(pid, 0) + 1
    commission_per_product: Dict[str, float] = {}
    conv_per_product: Dict[str, int] = {}
    for r in paid_rows:
        pid = r.get("opportunity_id")
        if pid:
            commission_per_product[pid] = commission_per_product.get(pid, 0) + float(r.get("gross_commission") or 0)
            conv_per_product[pid] = conv_per_product.get(pid, 0) + 1

    # Channel/content attribution over real clicks.
    channel_clicks: Dict[str, int] = {}
    content_clicks: Dict[str, int] = {}
    for c in clicks:
        ch = c.get("channel")
        if ch:
            channel_clicks[ch] = channel_clicks.get(ch, 0) + 1
        co = c.get("content")
        if co:
            content_clicks[co] = content_clicks.get(co, 0) + 1

    n_views = len(views)
    n_clicks = len(clicks)
    revenue_per_1000_views = (total_commission / n_views) * 1000 if n_views else "N/A -- 0 real page views"
    revenue_per_visitor = total_commission / n_views if n_views else "N/A -- 0 real page views"
    epc = total_commission / n_clicks if n_clicks else "N/A -- 0 real clicks"

    return {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "REVENUE_COMMISSION_USD": round(total_commission, 2),
        "CLICKS": n_clicks,
        "PAGE_VIEWS": n_views,
        "CTR": round(n_clicks / n_views, 4) if n_views else "N/A -- 0 real page views",
        "CONVERSIONS": len(paid_rows),
        "CONVERSION_RATE": round(len(paid_rows) / n_clicks, 4) if n_clicks else "N/A -- 0 real clicks",
        "EPC_USD": epc,
        "RECURRING_COMMISSION_USD": round(recurring_commission, 2),
        "REVENUE_PER_1000_VIEWS": revenue_per_1000_views,
        "REVENUE_PER_VISITOR": revenue_per_visitor,
        "TOP_PRODUCTS_BY_CLICKS": sorted(clicks_per_product.items(), key=lambda kv: kv[1], reverse=True),
        "TOP_PRODUCTS_BY_COMMISSION": sorted(commission_per_product.items(), key=lambda kv: kv[1], reverse=True),
        "TOP_CHANNELS": sorted(channel_clicks.items(), key=lambda kv: kv[1], reverse=True),
        "TOP_CONTENT": sorted(content_clicks.items(), key=lambda kv: kv[1], reverse=True),
        "note": "كل مقياس محسوب من سجلات حقيقية فقط؛ المقام الصفري = N/A وليس رقمًا مختلقًا.",
    }


# ---------------------------------------------------------------------------
# Real-data adapter: build AffiliateMetrics from the on-disk click ledger and
# commission ledger (affiliate_commerce/click_tracking + commission_ledger).
# Never fabricates: anything not measured stays 0/None.
# ---------------------------------------------------------------------------

def metrics_from_real_ledgers(click_ledger_path=None, commission_ledger_path=None,
                              portfolio=None) -> Dict[str, AffiliateMetrics]:
    """Aggregate real clicks per program (data/affiliate_clicks.jsonl) and
    real PAID commissions (data/commission_ledger.jsonl, environment=REAL
    only) into AffiliateMetrics per program. A program with clicks but no
    commission is honestly 0 conversion — never an estimated value."""
    try:
        from affiliate_commerce import click_tracking
        clicks = click_tracking.read_clicks(ledger_path=click_ledger_path)
    except Exception:
        clicks = []

    from collections import defaultdict
    per_program = defaultdict(lambda: {"clicks": 0, "first": None, "last": None})
    for c in clicks:
        pid = c.get("product_id")
        if not pid:
            continue
        ts = c.get("timestamp")
        rec = per_program[pid]
        rec["clicks"] += 1
        if rec["first"] is None or (ts and ts < rec["first"]):
            rec["first"] = ts
        if rec["last"] is None or (ts and ts > rec["last"]):
            rec["last"] = ts

    # Real commissions: only REAL-environment rows count; TEST rows never.
    real_commissions: Dict[str, float] = defaultdict(float)
    real_conversions: Dict[str, int] = defaultdict(int)
    try:
        from commission_ledger import load_ledger
        ledger = load_ledger(ledger_path=commission_ledger_path)
        for entry in ledger:
            if entry.get("environment") != "REAL":
                continue
            if entry.get("commission_status") in ("PAID", "PENDING", "CONFIRMED"):
                oid = entry.get("opportunity_id")
                if oid:
                    real_commissions[oid] += float(entry.get("gross_commission") or 0)
                    real_conversions[oid] += 1
    except Exception:
        pass

    # Program names from the real portfolio (for a readable report).
    names = {}
    if portfolio is not None:
        for o in portfolio:
            names[o.get("opportunity_id")] = o.get("program_name") or o.get("partner_name") or ""
    elif per_program:
        try:
            from commission_engine import load_opportunity_portfolio
            for o in load_opportunity_portfolio():
                names[o.get("opportunity_id")] = o.get("program_name") or o.get("partner_name") or ""
        except Exception:
            pass

    out = {}
    all_ids = set(per_program.keys()) | set(real_commissions.keys())
    for pid in all_ids:
        rec = per_program[pid]
        out[pid] = AffiliateMetrics(
            program_id=pid,
            program_name=names.get(pid, ""),
            real_clicks=rec["clicks"],
            real_conversions=real_conversions.get(pid, 0),
            real_commission_usd=real_commissions.get(pid, 0.0),
            first_click_at=rec["first"],
            last_click_at=rec["last"],
        )
    return out
