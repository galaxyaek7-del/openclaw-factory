"""
Research Department (EOS Phase 2, 2026-07-19) — pure assembly of
already-real analysis under 7 named categories, zero new analysis
logic. "Researchers" (real, deep, per-product web research) remains a
deliberate, founder-gated non-build (`HIGH_VALUE_STRATEGY.md`,
`COMPANY_INTEGRATION_MAP.md`) -- unchanged by this phase. This module
answers a different, narrower question: what does this factory's
EXISTING real analysis already know, organized under named categories,
never re-triggering a live niche-specific call (analyze_customer_pain()/
classify_demand_pattern()/get_or_refresh_competitors() are all
per-niche, live-network functions -- calling them with no real niche
in mind would either be meaningless or would trigger an unwanted live
call; this module only ever reads what's already been saved).

  - Market: recent real entries from data/market_intelligence_analyses.jsonl
    (same real source market_intelligence_core/market_review.py already
    reads, presented as a recent-findings list rather than a trend
    average -- two different views of the same real data, not a second
    computation of the same statistic).
  - Competitor: competitor_discovery.py's own cached database
    (load_database() -- read-only, never triggers a fresh live discovery).
  - Pricing: profit_oracle.py's real, already-defined pricing bands/
    ceilings (MAX_BUTTER_PRICE*, LADDER_PRICE_BAND) -- the real, current
    pricing methodology, not a per-niche price guess.
  - Publishing: commercial_execution/approval_gates.py::check_approval_gates()
    (already real, no niche needed).
  - Automation: evolution_engine.py's bottleneck/ROI signals (reused,
    not recomputed).
  - Technology: Track C -- no module evaluates tech/tooling choices
    today (tool_intelligence/proposals.py is the closest real analog,
    referenced not duplicated).
  - Customer: Track C -- zero real customer data exists anywhere in
    this factory (confirmed repeatedly across every prior phase).
"""

import json
import os

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
MARKET_INTELLIGENCE_ANALYSES_FILE = os.path.join(FACTORY_DIR, 'data', 'market_intelligence_analyses.jsonl')


def _read_jsonl_tail(path, limit=5):
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
    return entries[-limit:]


def _market_research(analyses_path=None, limit=5):
    entries = _read_jsonl_tail(analyses_path or MARKET_INTELLIGENCE_ANALYSES_FILE, limit=limit)
    if not entries:
        return {"answer": "Unknown", "reason": "لا تحليلات ذكاء سوق حقيقية مسجَّلة بعد", "recent_findings": []}
    return {
        "recent_findings": [
            {
                "niche": e.get("niche"), "opportunity_gap": e.get("opportunity_gap"),
                "pain_score": (e.get("customer_pain") or {}).get("pain_score"),
                "analyzed_at": e.get("analyzed_at"),
            }
            for e in entries
        ],
        "source": "data/market_intelligence_analyses.jsonl",
    }


def _competitor_research(db_file=None):
    from competitor_discovery import load_database
    db = load_database(db_file)
    if not db:
        return {"answer": "Unknown", "reason": "لا قاعدة بيانات منافسين محفوظة بعد", "tracked_niches": 0}
    return {
        "tracked_niches": len(db),
        "sample_niches": list(db.keys())[:5],
        "source": "competitor_discovery.py load_database() (cached, no live call triggered)",
    }


def _pricing_research():
    import profit_oracle as po
    return {
        "kdp_book_ceiling_usd": po.MAX_BUTTER_PRICE,
        "printable_ceiling_usd": po.MAX_BUTTER_PRICE_PRINTABLE,
        "premium_ceiling_usd": po.MAX_BUTTER_PRICE_PREMIUM,
        "elite_ceiling_usd": po.MAX_BUTTER_PRICE_ELITE,
        "ladder_price_band": po.LADDER_PRICE_BAND,
        "source": "profit_oracle.py real pricing constants",
    }


def _publishing_research():
    import distributor  # noqa: F401 -- self-registers every real, live arm
    from commercial_execution.approval_gates import check_approval_gates
    return check_approval_gates()


def _automation_research(decisions_path=None, outcomes_path=None, timeline_path=None):
    import evolution_engine
    report = evolution_engine.build_evolution_report(
        decisions_path=decisions_path, outcomes_path=outcomes_path, timeline_path=timeline_path,
    )
    return {
        "bottlenecks": report["bottlenecks"],
        "high_roi_opportunities": report["high_roi_opportunities"],
        "source": "evolution_engine.py (reused, not recomputed)",
    }


def build_research_report(decisions_path=None, outcomes_path=None, timeline_path=None,
                            analyses_path=None, competitor_db_file=None):
    return {
        "market": _market_research(analyses_path),
        "competitor": _competitor_research(competitor_db_file),
        "pricing": _pricing_research(),
        "publishing": _publishing_research(),
        "automation": _automation_research(decisions_path, outcomes_path, timeline_path),
        "technology": {"answer": "Unknown", "reason": "لا وحدة تقيّم خيارات التقنية/الأدوات اليوم -- انظر tool_intelligence/proposals.py للاقتراحات المتاحة"},
        "customer": {"answer": "Unknown", "reason": "لا بيانات عملاء حقيقية في هذا المصنع بعد (صفر مبيعات حقيقية)"},
    }


def render_markdown(report):
    lines = ["## قسم الأبحاث\n"]

    lines.append("### أبحاث السوق")
    market = report["market"]
    if market.get("answer") == "Unknown":
        lines.append(f"- {market['reason']}")
    else:
        for f in market["recent_findings"]:
            lines.append(f"- {f['niche']}: فجوة الفرصة={f['opportunity_gap']}, درجة الألم={f['pain_score']}")

    lines.append("\n### أبحاث المنافسين")
    comp = report["competitor"]
    if comp.get("answer") == "Unknown":
        lines.append(f"- {comp['reason']}")
    else:
        lines.append(f"- {comp['tracked_niches']} نيتش متتبَّع في قاعدة البيانات المحفوظة")

    lines.append("\n### أبحاث التسعير")
    price = report["pricing"]
    lines.append(f"- سقف كتاب KDP: ${price['kdp_book_ceiling_usd']} | مطبوعات: ${price['printable_ceiling_usd']} | مميز: ${price['premium_ceiling_usd']} | نخبة: ${price['elite_ceiling_usd']}")

    lines.append("\n### أبحاث النشر")
    pub = report["publishing"]
    lines.append(f"- {len(pub.get('autonomous', []))} منصة تعمل تلقائياً، {len(pub.get('gated', []))} تحتاج إجراءً من المؤسِّس")

    lines.append("\n### أبحاث الأتمتة")
    auto = report["automation"]
    lines.append(f"- {'اختناقات حقيقية مكتشَفة' if auto['bottlenecks']['detected'] else 'لا اختناقات حقيقية اليوم'}")

    lines.append("\n### أبحاث التقنية")
    lines.append(f"- {report['technology']['reason']}")

    lines.append("\n### أبحاث العملاء")
    lines.append(f"- {report['customer']['reason']}")

    return "\n".join(lines) + "\n"
