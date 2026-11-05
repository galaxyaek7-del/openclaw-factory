#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protected affiliate ledger: verified-only writes, full audit trail.

Row: program/offer/link/channel/timestamp/click/conversion/commission/
commission_status/payout/payout_status/refund/evidence_source/verified_at.
States: PENDING -> CONFIRMED (commission), UNPAID -> PAID (payout).
Writes require verified=True + external source + ids; duplicates by
(transaction_id) are refused, never merged. Tests use Temp paths."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = _FACTORY_ROOT / "data" / "affiliate_commission_ledger.jsonl"


class LedgerError(PermissionError):
    pass


def _read(path: Path) -> list:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def record_commission(event: dict, path: Path | None = None) -> dict:
    ev = event or {}
    if ev.get("source") != "external" or ev.get("verified") is not True:
        raise LedgerError("affiliate ledger accepts verified-external only")
    tx = ev.get("transaction_id")
    if not tx:
        raise LedgerError("transaction_id required")
    p = Path(path) if path else DEFAULT_PATH
    for r in _read(p):
        if r.get("transaction_id") == tx:
            return {"recorded": False, "reason": "duplicate (idempotent)", "transaction_id": tx}
    row = {"program": ev.get("program"), "offer": ev.get("offer"),
           "link_id": ev.get("link_id"), "channel": ev.get("channel"),
           "timestamp": ev.get("timestamp") or datetime.now(timezone.utc).isoformat(),
           "commission": ev.get("commission"), "commission_status": "PENDING",
           "payout": None, "payout_status": "UNPAID", "refund": None,
           "evidence_source": ev.get("evidence_source"),
           "verified_at": datetime.now(timezone.utc).isoformat(),
           "transaction_id": tx}
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"recorded": True, "transaction_id": tx, "commission_status": "PENDING"}


def confirm_commission(transaction_id: str, path: Path | None = None) -> dict:
    """PENDING -> CONFIRMED. Rewrites file preserving history order.
    PENDING is never reported as revenue; only CONFIRMED counts."""
    p = Path(path) if path else DEFAULT_PATH
    rows = _read(p)
    for r in rows:
        if r.get("transaction_id") == transaction_id:
            if r.get("commission_status") == "CONFIRMED":
                return {"ok": True, "already": True}
            r["commission_status"] = "CONFIRMED"
            with open(p, "w", encoding="utf-8") as f:
                for w in rows:
                    f.write(json.dumps(w, ensure_ascii=False) + "\n")
            return {"ok": True, "already": False}
    return {"ok": False, "reason": "unknown transaction_id"}


def totals(path: Path | None = None) -> dict:
    p = Path(path) if path else DEFAULT_PATH
    rows = _read(p)
    confirmed = [r for r in rows if r.get("commission_status") == "CONFIRMED"]
    return {"rows": len(rows),
            "pending": sum(1 for r in rows if r.get("commission_status") == "PENDING"),
            "confirmed": len(confirmed),
            "revenue_rule": "only CONFIRMED counts; today that sum is $0 until a real row exists"}
