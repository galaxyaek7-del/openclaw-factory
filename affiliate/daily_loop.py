#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Productive autonomous intelligence heartbeat (read-only + own-files).

15 checks per cycle: product health, exposure, funnel, sales, channels,
regulatory freshness, affiliate freshness, errors, experiment, bottleneck,
prioritize, SAFE ACTION (authorized + reversible only), gate prep (no
execution), evidence record, sleep-unless-material.

Authorized actions (executed): public-access re-verify, reconciliation
re-check, tower rebuild, anomaly + maintenance scans, gate-packet dedupe
ensure. Everything else (publish, spend, outreach, accounts) stays gated.
Wake triggers: verification drift, new critical, gate change, window
transition, sales change, fingerprint change. Else: heartbeat, silence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = _FACTORY_ROOT / "data" / "daily_loop_state.json"


def _read_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def detect_drift(prev: dict, cur: dict) -> list:
    """Pure comparator: which material facts changed between cycles."""
    watched = ("public_access", "sales", "revenue", "gates", "critical",
               "window", "published", "price", "fp")
    return [k for k in watched if prev.get(k) != cur.get(k)]


def _tail_errors(path: Path, lines: int = 200) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            tail = f.readlines()[-lines:]
        return sum(1 for l in tail if "ERROR" in l or "CRITICAL" in l)
    except OSError:
        return -1


def run_daily() -> dict:
    from affiliate import control_tower as ct
    from affiliate import loop as lp
    from affiliate import anomalies as an, maintenance as mn
    from affiliate import ledger_firewall as fw
    from affiliate import gates as gt, market_state as ms
    from affiliate import reality as rv
    from prospecting import market_test as mt

    checks, acted = {}, []

    # 1. live product health (1 API GET: published? price? desc==V1?)
    try:
        from channels import gumroad_publisher as gp
        token = gp.load_token()
        prod = gp.get_product(token, mt.PRODUCT_ID)
        checks["product_health"] = {
            "published": prod.get("published"), "price": prod.get("price"),
            "v1_intact": (prod.get("description") or "").strip() == mt.V1_COPY["description"].strip()}
    except Exception as e:
        checks["product_health"] = {"error": type(e).__name__}

    # 2-4. exposure / funnel / sales
    try:
        probe = json.loads((_FACTORY_ROOT / "data" / "exposure_probe.json").read_text(encoding="utf-8"))
        checks["exposure"] = probe.get("interpretation")
    except (OSError, ValueError):
        checks["exposure"] = "UNKNOWN"
    checks["funnel"] = ms.self_awareness()["CURRENT_BOTTLENECK"]
    try:
        from channels import gumroad_publisher as gp2
        sales = len(gp2.get_sales(gp2.load_token(), mt.PRODUCT_ID))
    except Exception:
        sales = -1
    checks["sales"] = sales

    # 5-7. channels / regulatory freshness / affiliate freshness
    checks["channels"] = {"anomalies": len(an.detect_anomalies()["findings"])}
    checks["regulatory"] = {"gpsr_scope_docs": "2026-09-21 (age %dd)" % (
        (datetime.now(timezone.utc) - datetime(2026, 9, 21, tzinfo=timezone.utc)).days)}
    aff = _FACTORY_ROOT / "reports" / "AFFILIATE_CONTROL_CENTER.md"
    try:
        age_h = (datetime.now().timestamp() - aff.stat().st_mtime) / 3600
        checks["affiliate"] = "report age %.1fh" % age_h
    except OSError:
        checks["affiliate"] = "report missing"

    # 8-9. errors / experiment
    checks["errors"] = {"service_log_errors": _tail_errors(_FACTORY_ROOT / "logs" / "service_layer.log")}
    w = fw.window_status()
    checks["experiment"] = w.get("state")

    # 10-11. bottleneck / prioritize
    p2 = ct.phase2()
    checks["bottleneck"] = p2["BOTTLENECK"]
    checks["next"] = p2["NEXT_ACTION"]

    # 12. SAFE ACTIONS (each verified, each reversible-or-read-only)
    pub = rv.public_access_check()
    checks["public_access"] = pub["PUBLIC_ACCESS"]
    acted.append("public-access re-verify: %s" % pub["PUBLIC_ACCESS"])
    rec = __import__("affiliate.reality", fromlist=["reconcile"]).reconcile(
        sales if isinstance(sales, int) and sales >= 0 else None)
    checks["reconciliation"] = rec["FINANCIAL_RECONCILIATION"]
    acted.append("reconciliation re-check: %s" % rec["FINANCIAL_RECONCILIATION"])
    sweep = mn.sweep()
    acted.append("maintenance sweep: %d checks, %d failed" % (len(sweep["checks"]), len(sweep["failed"])))
    ct.build()
    acted.append("tower rebuilt")

    # 13. gate prep without execution (dedupe-ensured)
    from affiliate import gate_orchestrator as go
    g = go.get_or_create_gate("AST-MEDIUM-GPSR-01", "Medium")
    checks["gate"] = "%s deduped=%s" % (g["GATE_ID"], g["deduped"])
    gates = gt.pending_gates()

    # 14-15. evidence + sleep decision
    health = fw.assert_invariants()
    cur = {"public_access": checks["public_access"], "sales": sales,
           "revenue": health["REAL_REVENUE"], "gates": len(gates),
           "critical": len(an.detect_anomalies()["critical"]),
           "window": w.get("state"),
           "published": (checks.get("product_health") or {}).get("published"),
           "price": (checks.get("product_health") or {}).get("price"),
           "fp": lp._fingerprint(lp._counts())}
    prev = _read_state()
    drift = detect_drift(prev, cur)
    material = bool(drift)
    row = {"cycle": "productive-heartbeat",
           "ran_at": datetime.now(timezone.utc).isoformat(),
           "checks": checks, "acted": acted, "drift": drift, "material": material}
    lp._heartbeat(row)
    STATE_PATH.write_text(json.dumps({**cur, "last": row["ran_at"]}, ensure_ascii=False),
                          encoding="utf-8")
    row["reported"] = material
    return row
