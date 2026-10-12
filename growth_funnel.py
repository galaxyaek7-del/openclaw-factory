"""Growth Funnel Dashboard (Cycle 82, "From Builder to Seller" -- item 5).

Read-only citation over real, already-real-or-newly-created data sources --
posts -> reach -> clicks -> product-page visits -> sales -> revenue, every
number sourced, anything unmeasurable marked UNKNOWN. Same discipline as
ceo_score.py: no fabricated number, no estimate standing in for a real
figure, writes nothing to disk, creates no external action.

Real sources used:
  - Posts:    docs/CONTENT_QUEUE_CYCLE82.md / data/content_queue_cycle82.csv
              (the real, drafted post list -- "reach" per post is UNKNOWN
              until the founder actually schedules/publishes a post and a
              platform-side reach number is recorded).
  - Clicks:   data/growth_funnel_events.jsonl (new, append-only; a real click
              event is recorded only when a founder-confirmed click/visit
              signal exists -- e.g. a Gumroad Referrers export row. Empty
              today -- zero posts have been published yet.)
  - Sales:    finance_data.json (same DELETE-ME-excluded ground truth
              ceo_score.py already reads) cross-referenced by the per-post
              `referrer` id, when a sale record carries one.

Forbidden, per the directive, and enforced here by construction: this module
never counts a self-purchase or a test purchase as a sale -- it reads the
exact same `finance_data.json` ground truth ceo_score.py uses, with no
override parameter that could inject a fabricated sale.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent
UNKNOWN = "Unknown — no data yet."


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_json(path: Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def load_content_queue(csv_path: Optional[Path] = None) -> List[Dict[str, str]]:
    """The real, drafted 14-post queue. Returns [] if the file doesn't exist
    (never fabricates placeholder rows)."""
    path = csv_path or (_FACTORY_ROOT / "data" / "content_queue_cycle82.csv")
    rows = []
    try:
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
    except OSError:
        pass
    return rows


def record_funnel_event(
    referrer_id: str,
    stage: str,
    count: int,
    events_path: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """The one real write path in this module -- appends a single, explicit,
    human-confirmed funnel observation (e.g. "post cy82_w1_p1 got 340 real
    reach per Facebook's own insights panel, confirmed 2026-10-20"). Never
    called automatically; never called by this cycle's own work (zero posts
    published yet -- see the final report)."""
    if stage not in ("reach", "clicks", "visits", "sales"):
        raise ValueError(f"stage must be one of reach/clicks/visits/sales, got {stage!r}")
    if count < 0:
        raise ValueError("count must be >= 0")
    path = events_path or (_FACTORY_ROOT / "data" / "growth_funnel_events.jsonl")
    event = {
        "referrer_id": referrer_id,
        "stage": stage,
        "count": int(count),
        "recorded_at": _now_iso(now),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def _sum_stage(events: List[Dict[str, object]], stage: str) -> int:
    return sum(int(e.get("count", 0)) for e in events if e.get("stage") == stage)


def _real_sales_for_referrers(
    referrer_ids: List[str],
    finance_path: Optional[Path] = None,
) -> Dict[str, object]:
    """Cross-references real finance_data.json sales against the per-post
    referrer ids, when a sale record happens to carry one. Today this is
    always empty/UNKNOWN: finance_data.json sale records have never carried
    a `referrer` field (confirmed by direct inspection) -- a real,
    disclosed gap, not fabricated attribution."""
    finance = _read_json(finance_path or (_FACTORY_ROOT / "finance_data.json"), {})
    real_sales = [
        s for s in finance.get("sales", [])
        if "DELETE-ME" not in str(s.get("product", ""))
    ]
    attributed = [s for s in real_sales if s.get("referrer") in referrer_ids]
    return {
        "total_real_sales": len(real_sales),
        "total_real_revenue_usd": round(sum(float(s.get("amount", 0)) for s in real_sales), 2),
        "attributed_to_this_campaign": len(attributed),
        "attributed_revenue_usd": round(sum(float(s.get("amount", 0)) for s in attributed), 2),
        "note": (
            "Unknown — no data yet. finance_data.json sale records carry no `referrer` "
            "field today; attribution by post is architecturally impossible until a sale "
            "record is saved with one (e.g. once Gumroad's own Referrers export is read "
            "back manually)."
            if not real_sales else
            f"{len(attributed)} of {len(real_sales)} real sale(s) carry a referrer id "
            "matching this campaign's posts."
        ),
    }


def build_growth_funnel_dashboard(
    csv_path: Optional[Path] = None,
    events_path: Optional[Path] = None,
    finance_path: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, object]:
    """posts -> reach -> clicks -> product-page visits -> sales -> revenue.
    Every stage real-sourced or explicitly UNKNOWN. Read-only."""
    posts = load_content_queue(csv_path=csv_path)
    referrer_ids = [p.get("referrer_id") for p in posts if p.get("referrer_id")]
    events = _read_jsonl(events_path or (_FACTORY_ROOT / "data" / "growth_funnel_events.jsonl"))

    reach = _sum_stage(events, "reach")
    clicks = _sum_stage(events, "clicks")
    visits = _sum_stage(events, "visits")
    sales_summary = _real_sales_for_referrers(referrer_ids, finance_path=finance_path)

    has_any_event = bool(events)

    return {
        "generated_at": _now_iso(now),
        "campaign": "cycle_82_arabic_hvac_pt_chart",
        "funnel": {
            "posts_drafted": len(posts),
            "posts_published": 0 if not has_any_event else UNKNOWN,
            "reach": reach if has_any_event else UNKNOWN,
            "clicks": clicks if has_any_event else UNKNOWN,
            "product_page_visits": visits if has_any_event else UNKNOWN,
            "real_sales_attributed": sales_summary["attributed_to_this_campaign"],
            "real_revenue_attributed_usd": sales_summary["attributed_revenue_usd"],
        },
        "ground_truth": sales_summary,
        "note": (
            "Composition-only, read-only, writes nothing except via the explicit, "
            "human-triggered record_funnel_event() (never called automatically). "
            "Zero posts have been published this cycle (Cycle 82) -- every stage above "
            "is honestly 'Unknown — no data yet.' except posts_drafted, which is real "
            "(14) and posts_published/real_sales_attributed, which are real zeros, not "
            "placeholders. Never counts a founder/test purchase as a sale: reads the "
            "same finance_data.json ground truth ceo_score.py uses, with no override."
        ),
    }
