#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Commercial truth firewall: no process writes revenue/commission/payout/
sale/customer/conversion without valid external evidence. Tests, mocks,
demos, QA, synthetic events and internal purchases can never pass."""

from __future__ import annotations

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
PROTECTED = ("finance_data.json", "config/reality.json")


class CommercialTruthFirewallError(PermissionError):
    pass


def assert_write_allowed(evidence: dict) -> dict:
    """Allow only: externally-sourced + verified + carrying a real
    transaction id. Everything else raises (never silently drops)."""
    ev = evidence or {}
    if ev.get("source") != "external":
        raise CommercialTruthFirewallError("source is not external: %r" % ev.get("source"))
    if ev.get("verified") is not True:
        raise CommercialTruthFirewallError("evidence not verified")
    if not ev.get("transaction_id"):
        raise CommercialTruthFirewallError("no real transaction id")
    return {"allowed": True, "transaction_id": ev["transaction_id"]}


def ledger_integrity() -> dict:
    """Read-only: protected files parse, totals are $0/empty, no secrets
    leaked into affiliate-owned files."""
    issues = []
    fin_p = _FACTORY_ROOT / "finance_data.json"
    try:
        fin = json.loads(fin_p.read_text(encoding="utf-8"))
        if fin.get("totalSales") != 0:
            issues.append("finance_data totalSales != 0")
    except (OSError, ValueError) as e:
        issues.append("finance_data unreadable: %s" % type(e).__name__)
    for name in ("affiliate_clicks.jsonl", "commission_attribution_log.jsonl",
                 "affiliate_page_views.jsonl"):
        p = _FACTORY_ROOT / "data" / name
        if p.exists():
            head = p.read_text(encoding="utf-8")[:20000].lower()
            for marker in ("sk-", "grok_", "api_key", "bearer "):
                if marker in head:
                    issues.append("possible secret in %s" % name)
    return {"ok": not issues, "issues": issues,
            "truth": "REAL_REVENUE = $0"}
