#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Affiliate economics: transparent model, OBSERVED vs ESTIMATED split.

Computes only what record fields support. Average order value is UNKNOWN
for every program (no order data anywhere) — so per-conversion commission
is a RANGE or UNKNOWN, never a point forecast. Estimates are labeled and
never summed into revenue."""

from __future__ import annotations

import re


def _num(text: str):
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text))
    return float(m.group(1)) if m else None


def model(program: dict) -> dict:
    fields = (program.get("record") or {}).get("fields", {})

    def val(k):
        return (fields.get(k) or {}).get("value")

    def ev(k):
        return (fields.get(k) or {}).get("evidence", "UNKNOWN")

    comm_text = val("commission_value")
    pct = _num(comm_text) if comm_text else None
    recurring = val("recurring_commission") is True
    cookie = val("cookie_duration")
    payout = {"method": "UNKNOWN (no payout-method field on record)",
              "threshold": "UNKNOWN (no threshold field on record)"}
    return {
        "opportunity_id": program.get("opportunity_id"),
        "commission_pct": {"value": pct, "source": "OBSERVED" if pct is not None else "UNKNOWN",
                           "raw": comm_text},
        "average_order_value": {"value": None, "source": "UNKNOWN",
                                "reason": "no order data in any ledger"},
        "commission_per_conversion": {"value": None, "source": "UNKNOWN",
                                      "reason": "needs AOV; not estimated without it"},
        "recurring": {"value": recurring, "source": ev("recurring_commission")},
        "cookie": {"value": cookie, "source": ev("cookie_duration")},
        "payout": payout,
        "refund_exposure": "UNKNOWN (no refund signal anywhere)",
        "effort": "ESTIMATED: content + distribution labor unmeasured",
        "verdict": ("QUALIFIED_FOR_TEST" if pct is not None else "ECONOMICS_UNKNOWN"),
    }


def select_rank(models: list) -> list:
    """Internal prioritization (never published): qualified economics first,
    recurring before one-time, UNKNOWN last. Ties keep input order."""
    def key(m):
        q = 0 if m["verdict"] == "QUALIFIED_FOR_TEST" else 1
        r = 0 if m["recurring"]["value"] else 1
        return (q, r)
    return sorted(models, key=key)
