#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Demand gate: may the factory create and list NEW products right now?

Founder decision 2026-11-05 (second order): the freeze on new products is lifted ONLY when
real demand is recorded. 112 listings with zero sales say demand, not production, is the
bottleneck, so automatic production must follow demand, not precede it.

The gate is OPEN when at least one REAL demand signal exists in the factory's own ledgers:

  SALE            a published product with sales_count > 0 (data/product_registry.json)
  EXTERNAL_CLICK  an affiliate click that could come from an outside person
                  (affiliate_commerce.click_classification, possible_human > 0)
  BUYER_INTEREST  an inbound interest row that is not a test (customer_interest.jsonl)
  MARKET_DEMAND   a market_evidence row of a buyer-side type (demo/trial request, waitlist,
                  purchase attempt, closed sale, email reply, landing-page conversion)

Not demand: our own clicks (INTERNAL), TEST_EVENT rows, example addresses, competitor
observations, public-complaint research rows. Counting them would open the gate on nothing.

The gate is company-wide, not per niche: it says "somebody real has shown interest in
something we sell", it does not say which niche to build. Honest limit, stated here once.

Read-only. Run: python demand_gate.py [--json]
Env: GF_DEMAND_GATE_DAILY_CAP (default 3) = most new products per day while the gate is open.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

BUYER_EVENT_TYPES = (
    "demo_request", "trial_request", "waitlist_signup", "purchase_attempt", "closed_sale",
    "email_reply", "landing_page_conversion", "customer_interview", "discovery_call",
)
_FAKE_EMAIL_DOMAINS = ("t.com", "example.com", "example.org", "test.com", "localhost")
DEFAULT_DAILY_CAP = 3


def _read_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    with open(p, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _is_test_text(*values):
    blob = " ".join(str(v or "") for v in values).upper()
    return "TEST_EVENT" in blob or "SIMULATION" in blob


def sales_signal(root: Path):
    p = root / "data" / "product_registry.json"
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return sum(int(x.get("sales_count") or 0) for x in reg.get("products", []) if x.get("published"))


def external_click_signal(root: Path, ledger_path=None):
    try:
        sys.path.insert(0, str(root))
        from affiliate_commerce import click_classification as cc
        s = cc.summarize(ledger_path=ledger_path)
        return int(s.get("possible_human") or 0)
    except Exception:
        return 0


def buyer_interest_signal(root: Path, path=None):
    n = 0
    for r in _read_jsonl(path or root / "data" / "customer_interest.jsonl"):
        email = str(r.get("email") or "").lower()
        domain = email.rsplit("@", 1)[-1] if "@" in email else ""
        if _is_test_text(r.get("message"), r.get("name"), r.get("source")):
            continue
        if not email or domain in _FAKE_EMAIL_DOMAINS:
            continue
        n += 1
    return n


def market_demand_signal(root: Path, path=None):
    n = 0
    for r in _read_jsonl(path or root / "data" / "market_evidence.jsonl"):
        if r.get("event_type") not in BUYER_EVENT_TYPES:
            continue
        if _is_test_text(r.get("note"), json.dumps(r.get("payload") or {}, ensure_ascii=False), r.get("source")):
            continue
        n += 1
    return n


def evaluate(root=None, environ=None, now=None):
    root = Path(root) if root else ROOT
    env = os.environ if environ is None else environ
    signals = {
        "SALE": sales_signal(root),
        "EXTERNAL_CLICK": external_click_signal(root),
        "BUYER_INTEREST": buyer_interest_signal(root),
        "MARKET_DEMAND": market_demand_signal(root),
    }
    try:
        cap = max(0, int(env.get("GF_DEMAND_GATE_DAILY_CAP", DEFAULT_DAILY_CAP)))
    except (TypeError, ValueError):
        cap = DEFAULT_DAILY_CAP
    is_open = any(v > 0 for v in signals.values())
    return {
        "open": is_open,
        "daily_cap": cap if is_open else 0,
        "signals": signals,
        "why": ("real demand recorded: " + ", ".join(k for k, v in signals.items() if v > 0))
               if is_open else "WAITING FOR REAL DATA: no sale, outside click, buyer interest or buyer-side market evidence",
        "evaluated_at": (now or datetime.now(timezone.utc)).isoformat(),
    }


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, ensure_ascii=False, indent=None if "--json" in sys.argv else 1))
