"""Galaxy Forge — unified sales ledger writer (OCTOPUS_ARCHITECTURE.md §10.4).

Single append-only source of truth for distribution events, replacing the
"published: true" claim that OCTOPUS_ARCHITECTURE.md §7 identified as a
lie. One file, two event types — not a separate published_events.jsonl
plus a separate sales file:

  publish_attempt  — an arm's publish() call returned, success or failure.
                      Recorded from a PublishResult (channels/base_arm.py).
  sale             — a real sale as reported by a platform's get_sales().

Each line is one JSON object. Never overwrites, never rewrites history —
append only, so a corrupt write can't destroy prior events (unlike the
data/finance.json incident this project already hit once).

This module does not wire itself into reality.py or any arm automatically
— that integration is a deliberate follow-up, not done here, so existing
reads of config/reality.json / finance_data.json are untouched.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER_PATH = _FACTORY_ROOT / "data" / "sales_ledger.jsonl"

_VALID_EVENT_TYPES = {"publish_attempt", "sale"}


def append_event(event: dict, ledger_path=None) -> dict:
    """Append one validated event as a single JSON line. Returns the event
    actually written (with a timestamp filled in if missing)."""
    if event.get("event_type") not in _VALID_EVENT_TYPES:
        raise ValueError(
            f"event_type must be one of {_VALID_EVENT_TYPES}, got {event.get('event_type')!r}"
        )

    record = dict(event)
    record.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return record


def record_publish_attempt(product, result, ledger_path=None) -> dict:
    """Build a publish_attempt event from a Product + PublishResult and
    append it. Never raises on a failed publish — a failure is exactly what
    this ledger exists to record honestly."""
    event = {
        "event_type": "publish_attempt",
        "platform": result.platform,
        "ok": result.ok,
        "dry_run": result.dry_run,
        "product_id": result.product_id,
        "url": result.url,
        "error": result.error,
        "product_title": getattr(product, "title", None),
        "product_source_id": getattr(product, "source_id", None),
        "product_type": getattr(product, "product_type", None),
    }
    return append_event(event, ledger_path=ledger_path)


def record_sale(platform: str, sale: dict, ledger_path=None, niche=None) -> dict:
    """Append one real sale as reported by a platform's get_sales(). The raw
    sale dict is kept under "raw" verbatim — never reshaped/guessed, since a
    ledger meant to replace a lie must not introduce a new one.

    Market Learning Loop (2026-07-22): when the caller knows which real
    niche this sale belongs to, ALSO logs a real "closed_sale" event to
    market_evidence.py — this factory's real automatic evidence channel,
    consumed directly by the Executive Quality Gate. `niche` is optional
    and deliberately not auto-derived from the raw sale here: this
    factory has never seen an actual completed Paddle/Gumroad sale
    (zero real sales exist yet), so the real response shape needed to
    reliably map a sale back to its niche hasn't been verified against a
    live example — guessing that mapping blind risks recording a real
    evidence event against the wrong niche, which would be worse than
    not recording it at all. Wire this for real once the first real sale
    happens and its actual shape can be checked. A failure logging
    evidence must never lose the real sale record itself — wrapped in
    try/except, best-effort only."""
    event = {
        "event_type": "sale",
        "platform": platform,
        "raw": sale,
    }
    recorded = append_event(event, ledger_path=ledger_path)
    if niche:
        try:
            import market_evidence
            market_evidence.record_evidence(niche, "closed_sale", {"platform": platform, "raw": sale}, source="ledger.record_sale")
        except Exception:
            pass
    return recorded


def read_events(event_type=None, ledger_path=None):
    """Yield every event in the ledger, optionally filtered by event_type.
    Missing ledger file yields nothing (a ledger with zero events yet is not
    an error)."""
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type is not None and record.get("event_type") != event_type:
                continue
            yield record


# ── FINANCE RECONCILIATION (ADR-077, Product Generation Pipeline) ──
# Closes the real, confirmed gap COMPANY_INTEGRATION_AUDIT_20260718.md
# found: real sales already land here via record_sale() (scripts/
# poll_sales.py, every tick), but nothing ever carried them into
# finance_data.json — the file server.js's /finance actually reads for
# the founder's real revenue figure. A real sale could have landed and
# stayed invisible in Mission Control.

_FINANCE_FILE = _FACTORY_ROOT / "finance_data.json"
_LADDER_RANKS = ("ai_saas", "b2b_systems", "automation_tools", "reusable_assets", "educational", "kdp_books")
_PLATFORM_DISPLAY = {"gumroad": "Gumroad", "paddle": "Paddle", "payhip": "Payhip", "etsy": "Etsy"}


def _extract_sale_amount(raw, platform):
    """Real, per-platform amount extraction — never a guess or a flat
    default. Gumroad's real get_sales() shape (gumroad_publisher.py) uses
    a "price" field in whole dollars (confirmed against Gumroad's own API
    docs — the v2 Sales resource's `price` is already a decimal amount,
    not cents). Paddle's real get_transactions() shape (paddle_publisher.py)
    nests the charged total under details.totals.grand_total, a string in
    the smallest currency unit (cents for USD, per Paddle's own Billing API
    docs). Returns None (never 0) for anything unrecognized — an
    unrecognized real sale must never silently count as $0 revenue."""
    if platform == "gumroad":
        price = raw.get("price")
        try:
            return round(float(price), 2)
        except (TypeError, ValueError):
            return None
    if platform == "paddle":
        try:
            return round(int(raw["details"]["totals"]["grand_total"]) / 100, 2)
        except (KeyError, TypeError, ValueError):
            return None
    return None


def _default_finance_data():
    return {
        "sales": [], "totalKDP": 0, "totalEtsy": 0, "totalGumroad": 0, "totalPaddle": 0,
        "totalSales": 0, "byLadder": {r: 0 for r in _LADDER_RANKS}, "lastUpdated": None,
    }


def reconcile_ledger_to_finance(ledger_path=None, finance_path=None):
    """Reconciles real `sale` events already in the ledger into
    finance_data.json. Idempotent: each written sale record carries a
    `source_ledger_key` (f"{platform}:{raw_sale_id}") as its dedup key, so
    re-running this never double-counts a real sale already reconciled
    once — same discipline poll_sales.py's own ledger-side dedup already
    uses. A sale whose amount can't be honestly extracted (unrecognized
    platform shape) is skipped and counted in `skipped_unrecognized`, never
    guessed at $0 — reported so a human can look, not hidden.

    Uses the exact same finance_data.json shape server.js's loadFin()/
    saveFin() read and write (schemas/fields identical, including the
    ADR-065 byLadder/totalPaddle additions) and the same atomic
    temp-file-then-rename write server.js already uses, so either language
    writing this file stays safe."""
    finance_path = Path(finance_path) if finance_path else _FINANCE_FILE

    if finance_path.exists():
        try:
            with open(finance_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = _default_finance_data()
    else:
        data = _default_finance_data()

    # Defensive shape normalization — tolerates a partially-missing/legacy
    # file, same discipline as server.js's own loadFin().
    data["sales"] = data.get("sales") if isinstance(data.get("sales"), list) else []
    for key in ("totalKDP", "totalEtsy", "totalGumroad", "totalPaddle", "totalSales"):
        if not isinstance(data.get(key), (int, float)):
            data[key] = 0
    if not isinstance(data.get("byLadder"), dict):
        data["byLadder"] = {r: 0 for r in _LADDER_RANKS}

    already_reconciled = {s.get("source_ledger_key") for s in data["sales"] if s.get("source_ledger_key")}
    next_id = max([s.get("id", 0) for s in data["sales"] if isinstance(s.get("id"), int)], default=0) + 1

    reconciled = 0
    skipped_unrecognized = 0

    for event in read_events(event_type="sale", ledger_path=ledger_path):
        platform = event.get("platform")
        raw = event.get("raw") or {}
        source_key = f"{platform}:{raw.get('id')}"
        if source_key in already_reconciled:
            continue

        amount = _extract_sale_amount(raw, platform)
        if amount is None:
            skipped_unrecognized += 1
            continue

        data["sales"].append({
            "id": next_id,
            "platform": _PLATFORM_DISPLAY.get(platform, platform),
            "amount": amount,
            "product": raw.get("product_name") or raw.get("description") or "Unknown",
            "date": (event.get("timestamp") or "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "source_ledger_key": source_key,
        })
        already_reconciled.add(source_key)
        next_id += 1
        reconciled += 1

    if reconciled:
        data["totalKDP"] = sum(s["amount"] for s in data["sales"] if s["platform"] == "KDP")
        data["totalEtsy"] = sum(s["amount"] for s in data["sales"] if s["platform"] == "Etsy")
        data["totalGumroad"] = sum(s["amount"] for s in data["sales"] if s["platform"] == "Gumroad")
        data["totalPaddle"] = sum(s["amount"] for s in data["sales"] if s["platform"] == "Paddle")
        data["totalSales"] = data["totalKDP"] + data["totalEtsy"] + data["totalGumroad"] + data["totalPaddle"]

        # Mirrors server.js's recomputeByLadder() exactly: a sale with no
        # `ladder` field (every real sale reconciled here — a platform's
        # raw sale payload carries no notion of our internal Strategic
        # Production Priority Ladder) rolls up under 'kdp_books', the same
        # honest default server.js's own saveFin() path already uses.
        by_ladder = {r: 0 for r in _LADDER_RANKS}
        for s in data["sales"]:
            rank = s.get("ladder") if s.get("ladder") in _LADDER_RANKS else "kdp_books"
            by_ladder[rank] += s["amount"]
        data["byLadder"] = by_ladder

        data["lastUpdated"] = datetime.now(timezone.utc).isoformat()

        tmp_path = finance_path.parent / f"{finance_path.name}.tmp-{os.getpid()}"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, finance_path)

    return {"reconciled": reconciled, "skipped_unrecognized": skipped_unrecognized, "total_sales": data["totalSales"]}


# ── REVENUE TREND OVER TIME (EOS Phase 2, Round 2, 2026-07-19) ──
# The one real Revenue Intelligence gap: finance_data.json only ever holds
# current totals, no time series. Reads the ledger's own real, timestamped
# `sale` events, bucketed by day -- same "recent 7d vs. trailing daily
# average" pattern already proven by lib/infrastructure_intelligence.js's
# getCostTrend() and factory_loop.js's revenueSince(). Never a forecast:
# with zero real sales recorded today, this honestly reports that instead
# of fabricating a trend line from publish attempts or estimates.
def revenue_trend(now=None, ledger_path=None):
    now = now or datetime.now(timezone.utc)
    since_recent = now - timedelta(days=7)

    by_day = {}
    total_amount = 0.0
    total_count = 0
    recent_amount = 0.0
    recent_count = 0

    for event in read_events(event_type="sale", ledger_path=ledger_path):
        amount = _extract_sale_amount(event.get("raw") or {}, event.get("platform"))
        if amount is None:
            continue
        try:
            dt = datetime.fromisoformat((event.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            continue

        day_key = dt.strftime("%Y-%m-%d")
        by_day[day_key] = by_day.get(day_key, 0.0) + amount
        total_amount += amount
        total_count += 1
        if dt >= since_recent:
            recent_amount += amount
            recent_count += 1

    if not by_day:
        return {
            "total_sales_count": 0,
            "total_revenue_usd": 0,
            "recent_7d_revenue_usd": 0,
            "recent_7d_sales_count": 0,
            "trailing_daily_avg_usd": None,
            "by_day": {},
            "note": "لا توجد مبيعات حقيقية مسجَّلة بعد في data/sales_ledger.jsonl -- لا يوجد اتجاه إيراد حقيقي لعرضه (لا تنبّؤ، لا تقدير).",
        }

    trailing_days = [d for d in by_day if datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc) < since_recent]
    trailing_avg = (sum(by_day[d] for d in trailing_days) / len(trailing_days)) if trailing_days else None

    return {
        "total_sales_count": total_count,
        "total_revenue_usd": round(total_amount, 2),
        "recent_7d_revenue_usd": round(recent_amount, 2),
        "recent_7d_sales_count": recent_count,
        "trailing_daily_avg_usd": round(trailing_avg, 2) if trailing_avg is not None else None,
        "by_day": {d: round(v, 2) for d, v in sorted(by_day.items())},
        "note": None if trailing_avg is not None else "لا يوجد تاريخ كافٍ بعد (أقل من أسبوع من البيانات) لحساب متوسط اتجاه موثوق.",
    }
