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


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def record_click(product_id, referrer=None, ledger_path=None):
    """Records one real click event -- called at the moment a real user
    clicks a real affiliate link, before the real redirect fires."""
    record = {
        "product_id": product_id,
        "timestamp": _now_iso(),
        "referrer": referrer,
    }
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
