#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate Commerce — real click tracking (ADR-149, 2026-07-30).

Real, append-only click ledger -- same "one JSON object per line,
append only, never overwrites" discipline as channels/ledger.py. Tracks
clicks only, never conversions: a real conversion requires the
affiliate network's real postback/reporting API, which does not exist
for this factory yet (no real approved Amazon Associates account) --
honestly out of scope, never fabricated.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEDGER_PATH = _FACTORY_ROOT / "data" / "affiliate_clicks.jsonl"
DEFAULT_PAGE_VIEW_LEDGER_PATH = _FACTORY_ROOT / "data" / "affiliate_page_views.jsonl"

_UTM_FIELDS = ("utm_source", "utm_medium", "utm_campaign", "utm_content")


def parse_utm_query(query):
    """Privacy-minimal UTM capture (Evidence Chain + Attribution phase,
    2026-08-17). Extracts ONLY the known UTM fields from a query dict (a
    parsed URL query string) and returns a dict of the fields present.
    No cookies, no fingerprinting, no session reconstruction -- a visitor's
    source is read strictly from the URL query they themselves arrived
    with, and only the fields that actually exist are returned (never a
    guessed/empty placeholder)."""
    if not query or not isinstance(query, dict):
        return {}
    out = {}
    for k, v in query.items():
        if k in _UTM_FIELDS and isinstance(v, str) and v.strip():
            out[k] = v.strip()
    return out


def _with_source(record, source):
    if source:
        record["source"] = source
    return record


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def record_click(product_id, referrer=None, ledger_path=None, source=None):
    """Records one real click event -- called at the moment a real user
    clicks a real affiliate link, before the real redirect fires."""
    record = {
        "product_id": product_id,
        "timestamp": _now_iso(),
        "referrer": referrer,
    }
    _with_source(record, source)
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def read_clicks(ledger_path=None):
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def record_attributed_click(product_id, channel=None, campaign=None, content=None,
                            referrer=None, utm_medium=None, utm_source=None,
                            ledger_path=None, source=None):
    """Records one real click with full attribution context (directive
    section 7: affiliate_program/product/channel/campaign/content + UTM).

    Same real, append-only discipline as record_click() -- the attribution
    fields are recorded at the moment of the real click; nothing is
    fabricated. Unset optional fields are simply omitted (not guessed).
    This is a superset of record_click(); the original call signature is
    unchanged and still works."""
    record = {
        "product_id": product_id,
        "timestamp": _now_iso(),
        "referrer": referrer,
    }
    if channel:
        record["channel"] = channel
    if campaign:
        record["campaign"] = campaign
    if content:
        record["content"] = content
    if utm_medium:
        record["utm_medium"] = utm_medium
    if utm_source:
        record["utm_source"] = utm_source
    _with_source(record, source)
    path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def attributed_click_summary(ledger_path=None):
    """Honest aggregate over real attributed clicks, grouped by the real
    fields present. Never invents a channel/campaign the record does not
    carry."""
    clicks = read_clicks(ledger_path)
    by_channel, by_campaign, by_content = {}, {}, {}
    for c in clicks:
        ch = c.get("channel") or "UNSET"
        by_channel[ch] = by_channel.get(ch, 0) + 1
        ca = c.get("campaign") or "UNSET"
        by_campaign[ca] = by_campaign.get(ca, 0) + 1
        co = c.get("content") or "UNSET"
        by_content[co] = by_content.get(co, 0) + 1
    return {
        "total_real_clicks": len(clicks),
        "clicks_by_channel": by_channel,
        "clicks_by_campaign": by_campaign,
        "clicks_by_content": by_content,
        "note": "تجميع حقيقي فقط على الحقول الموجودة في السجل؛ الحقل غير الموجود = UNSET، لا تخمين.",
    }


def click_summary(ledger_path=None):
    """Real, honest aggregate -- click counts only. Never a fabricated
    conversion rate or revenue figure; both require the real affiliate
    network postback this factory does not have yet."""
    clicks = read_clicks(ledger_path)
    by_product = {}
    for c in clicks:
        pid = c.get("product_id")
        if pid:
            by_product[pid] = by_product.get(pid, 0) + 1
    return {
        "total_real_clicks": len(clicks),
        "clicks_by_product": by_product,
        "note": "عدد نقرات حقيقية فقط -- لا معدل تحويل، لا إيراد عمولة مُختلَق؛ كلاهما يحتاج postback حقيقي من شبكة Amazon Associates غير متاح بعد.",
    }


def clicks_by_source(ledger_path=None):
    """Real aggregate of click records grouped by their real source
    (utm_source field, else source field, else UNSET). Never invents a
    source the record does not carry -- a record with no attribution
    fields is honestly grouped as UNSET (the current real state of the
    18 existing click records, which predate UTM capture)."""
    clicks = read_clicks(ledger_path)
    by_source = {}
    for c in clicks:
        src = c.get("utm_source") or c.get("source")
        by_source[src or "UNSET"] = by_source.get(src or "UNSET", 0) + 1
    return {
        "total_real_clicks": len(clicks),
        "clicks_by_source": by_source,
        "note": "Source is read strictly from the visitor's own URL query/referrer -- no cookies, no fingerprinting, no session reconstruction.",
    }


# ---------------------------------------------------------------------------
# Revenue Activation Directive (ADR-239), 2026-08-09, Section F -- the
# real "traffic -> page" step of the conversion funnel (traffic ->
# page -> outbound affiliate click -> attribution -> lead/customer ->
# commission -> payout). Same real, append-only, auditable discipline
# as record_click() above -- no fabricated visitor count, no session
# reconstruction, no fingerprinting/tracking beyond a real page-view
# timestamp + referrer, matching this factory's own established
# privacy-minimal precedent.
# ---------------------------------------------------------------------------

def record_page_view(page_id, referrer=None, ledger_path=None, source=None):
    """Records one real page-view event -- called when a real visitor
    loads a real content page (e.g. customer_site/affiliate-standing-
    desks.html), before any outbound affiliate click occurs."""
    record = {
        "page_id": page_id,
        "timestamp": _now_iso(),
        "referrer": referrer,
    }
    _with_source(record, source)
    path = Path(ledger_path) if ledger_path else DEFAULT_PAGE_VIEW_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def read_page_views(ledger_path=None):
    path = Path(ledger_path) if ledger_path else DEFAULT_PAGE_VIEW_LEDGER_PATH
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def conversion_funnel_summary(page_views_path=None, clicks_path=None, commission_ledger_path=None):
    """Real, auditable funnel counts only -- traffic (page views) ->
    outbound click -> commission. Every stage is a real, independent
    count from its own real ledger; no stage is ever inferred,
    interpolated, or presented as a rate without the two real counts
    behind it. Commission stage cites commission_ledger.py's own real
    ledger directly, never a second, duplicated commission source."""
    import commission_ledger as cl

    page_views = read_page_views(page_views_path)
    clicks = read_clicks(clicks_path)
    ledger = cl.load_ledger(commission_ledger_path)
    real_confirmed_commissions = [r for r in ledger if r.get("environment") == "REAL" and r.get("commission_status") in ("CONFIRMED", "PAID")]

    return {
        "generated_at": _now_iso(),
        "TRAFFIC_PAGE_VIEWS": len(page_views),
        "OUTBOUND_CLICKS": len(clicks),
        "REAL_COMMISSIONS": len(real_confirmed_commissions),
        "page_view_to_click_rate": round(len(clicks) / len(page_views), 4) if page_views else "N/A -- 0 real page views recorded",
        "click_to_commission_rate": round(len(real_confirmed_commissions) / len(clicks), 4) if clicks else "N/A -- 0 real clicks recorded",
        "note": "Every stage is a real, independent count from its own real, auditable ledger -- no rate is computed or displayed when its own denominator is 0.",
    }


def record_attributed_page_view(page_id, referrer=None, ledger_path=None,
                                utm_source=None, utm_medium=None,
                                utm_campaign=None, utm_content=None,
                                source=None):
    """Records one real page-view event carrying the full UTM/source
    attribution the visitor arrived with (Evidence Chain + Attribution
    phase, 2026-08-17). Privacy-minimal: fields are read strictly from the
    visitor's own URL query and omitted when absent -- never a cookie,
    never a fingerprint, never a guessed placeholder. A superset of
    record_page_view(); the original signature is unchanged and still
    works."""
    record = {
        "page_id": page_id,
        "timestamp": _now_iso(),
        "referrer": referrer,
    }
    if utm_source:
        record["utm_source"] = utm_source
    if utm_medium:
        record["utm_medium"] = utm_medium
    if utm_campaign:
        record["utm_campaign"] = utm_campaign
    if utm_content:
        record["utm_content"] = utm_content
    _with_source(record, source)
    path = Path(ledger_path) if ledger_path else DEFAULT_PAGE_VIEW_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


def page_views_by_source(ledger_path=None):
    """Real aggregate of page-view records grouped by their real source
    (utm_source field, else source field, else referrer host, else UNSET).
    Never invents a source the record does not carry -- a record with no
    attribution fields is honestly grouped as UNSET."""
    from urllib.parse import urlparse
    views = read_page_views(ledger_path)
    by_source = {}
    for v in views:
        src = v.get("utm_source") or v.get("source")
        if not src and v.get("referrer"):
            try:
                src = urlparse(v["referrer"]).netloc
            except Exception:
                src = v["referrer"]
        by_source[src or "UNSET"] = by_source.get(src or "UNSET", 0) + 1
    return {
        "total_real_page_views": len(views),
        "page_views_by_source": by_source,
        "note": "Source is read strictly from the visitor's own URL query/referrer -- no cookies, no fingerprinting, no session reconstruction.",
    }
