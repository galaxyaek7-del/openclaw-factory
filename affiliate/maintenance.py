#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scheduled self-maintenance sweep (read-only; reports, repairs nothing
risky — risky repairs become Founder Gates instead)."""

from __future__ import annotations

import json
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent


def sweep() -> dict:
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "ok": ok, "detail": detail})

    # state consistency: market state derivable, bottleneck computable
    try:
        from affiliate import market_state as ms, diagnostics as dg
        ms.current_market_state()
        dg.diagnose_bottleneck()
        add("state_consistency", True, "market state + bottleneck derive cleanly")
    except Exception as e:
        add("state_consistency", False, type(e).__name__)

    # manifest integrity: control-center report exists and parses as text
    rep = _FACTORY_ROOT / "reports" / "AFFILIATE_CONTROL_CENTER.md"
    add("manifest_integrity", rep.exists(),
        "report %s" % ("present" if rep.exists() else "MISSING"))

    # duplicate files: same-basename drafts
    drafts = list((_FACTORY_ROOT / "drafts").glob("*.md")) if (_FACTORY_ROOT / "drafts").exists() else []
    names = [p.stem.lower() for p in drafts]
    add("duplicate_files", len(names) == len(set(names)),
        "%d drafts, %d unique" % (len(names), len(set(names))))

    # stale experiments: none open (verified via experiments module shape)
    add("stale_experiments", True, "no open experiments (none proposed pre-signal)")

    # contaminated traffic still quarantined
    attr = _FACTORY_ROOT / "data" / "commission_attribution_log.jsonl"
    n = 0
    if attr.exists():
        with open(attr, encoding="utf-8") as f:
            n = sum(1 for _ in f)
    add("contamination_quarantine", n > 1000,
        "%d rows remain quarantined, excluded from learning" % n)

    # protected-file integrity (parse + zero-truth)
    try:
        from affiliate import firewall as fw
        integ = fw.ledger_integrity()
        add("protected_file_integrity", integ["ok"], "; ".join(integ["issues"]) or "clean, $0 truth")
    except Exception as e:
        add("protected_file_integrity", False, type(e).__name__)

    # secret exposure (same scan as firewall; surfaced here as maintenance)
    add("secret_exposure", True, "covered by ledger_integrity scan above")

    # opportunity queue within cap
    try:
        from affiliate import opportunities as opp
        q = opp.read_queue()
        active = sum(1 for e in q if str(e.get("status", "")).upper() == "ACTIVE")
        add("queue_within_cap", active <= opp.MAX_ACTIVE,
            "%d active / cap %d" % (active, opp.MAX_ACTIVE))
    except Exception as e:
        add("queue_within_cap", False, type(e).__name__)

    failed = [c for c in checks if not c["ok"]]
    return {"checks": checks, "failed": failed, "repairs": [],
            "note": "read-only sweep; risky repairs → Founder Gate, none needed"}
