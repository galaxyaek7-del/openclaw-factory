#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One command: where does each stage of the automatic factory stand, and what blocks it?

Read-only. Every line is derived from a live file, process or ledger, never from a claim.
Reads only whether an .env key is SET, never its value.

    python scripts/autonomy_selfcheck.py          # table
    python scripts/autonomy_selfcheck.py --json

Stages are the ones in docs/factory/AUTONOMY_PLAN.md. Status words: OK, BLOCKED, WAITING.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def env_keys(root: Path = ROOT):
    """Names of keys set to a non-empty value in .env (values are never read out)."""
    out = {}
    p = root / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("\"'")
    return out


def _json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _age_minutes(path: Path):
    try:
        return (time.time() - path.stat().st_mtime) / 60.0
    except OSError:
        return None


def stage(n, name, status, detail, owner):
    return {"stage": n, "name": name, "status": status, "detail": detail, "owner": owner}


def collect(root: Path = ROOT, env=None, health_fn=None, gate_fn=None, autostart_fn=None):
    env = env_keys(root) if env is None else env
    rows = []

    # 0 demand gate
    try:
        if gate_fn is None:
            import demand_gate
            gate_fn = lambda: demand_gate.evaluate(root=root, environ=env)  # noqa: E731
        g = gate_fn()
    except Exception as e:  # pragma: no cover
        g = {"open": False, "why": "gate error: %s" % e, "signals": {}}
    gated = str(env.get("GF_DEMAND_GATED", "")).lower() == "true"
    freeze = str(env.get("GF_FREEZE_NEW_PRODUCTS", "")).lower() == "true"
    if g.get("open"):
        rows.append(stage(0, "demand gate", "OK", g.get("why", ""), "automatic"))
    else:
        rows.append(stage(0, "demand gate", "WAITING", g.get("why", "") + " signals=%s" % g.get("signals"), "real outside demand"))
    mode = "demand-gated" if (freeze and gated) else ("frozen absolutely" if freeze else "not frozen")
    rows.append(stage("0b", "freeze mode", "OK", mode, "founder"))

    # 1-5 loop, production switch, publish switches
    loop_log = root / "factory_loop.log"
    age = _age_minutes(loop_log)
    rows.append(stage(1, "factory loop alive", "OK" if age is not None and age < 25 else "BLOCKED",
                      "last tick %.0f min ago" % age if age is not None else "no factory_loop.log", "supervisor / autostart"))
    rows.append(stage(2, "automatic production switch",
                      "OK" if str(env.get("FACTORY_AUTO_PRODUCE", "")).lower() == "true" else "BLOCKED",
                      "FACTORY_AUTO_PRODUCE " + ("set" if str(env.get("FACTORY_AUTO_PRODUCE", "")).lower() == "true" else "not set")
                      + "; produces only while the demand gate is open", "founder"))
    live = str(env.get("FACTORY_LIVE_PUBLISH", "")).lower() == "true"
    auto = str(env.get("GF_AUTO_PUBLISH_APPROVED", "")).lower() == "true"
    rows.append(stage(5, "publish switches", "OK" if live and auto else "BLOCKED",
                      "FACTORY_LIVE_PUBLISH=%s GF_AUTO_PUBLISH_APPROVED=%s" % (live, auto), "founder"))

    # server
    try:
        ok = (health_fn or (lambda: urllib.request.urlopen("http://127.0.0.1:3000/health", timeout=10).status == 200))()
    except Exception:
        ok = False
    rows.append(stage("5b", "server /health", "OK" if ok else "BLOCKED", "200" if ok else "no answer", "supervisor"))

    # 6 distribution
    q = _json(root / "data" / "pinterest_queue.json", {}) or {}
    summ = q.get("summary") or {}
    if q.get("board"):
        rows.append(stage(6, "distribution (Pinterest)", "OK", "board found; queue %s" % summ, "automatic"))
    else:
        rows.append(stage(6, "distribution (Pinterest)", "BLOCKED",
                          "no board: %s pins blocked (%s)" % (summ.get("BLOCKED_NO_BOARD", "?"), str(q.get("board_lookup"))[:90]),
                          "founder: create the board"))

    # 7 measurement
    poll = _json(root / "data" / "sales_poll_last_check.json", {}) or {}
    last = (poll.get("arms", {}).get("gumroad") or {}).get("last_ok_at")
    rows.append(stage(7, "sales measurement", "OK" if last else "BLOCKED", "gumroad last ok %s" % last, "automatic"))

    # 8 money records
    reg = _json(root / "data" / "product_registry.json", {}) or {}
    prods = reg.get("products", [])
    sales = sum(int(p.get("sales_count") or 0) for p in prods if p.get("published"))
    rows.append(stage(8, "money so far", "WAITING" if sales == 0 else "OK",
                      "%s published, %s sales (registry %s)" % (sum(1 for p in prods if p.get("published")), sales, str(reg.get("generated_at"))[:16]),
                      "real buyers"))

    # 9 alerts
    bound = bool((_json(root / "data" / "telegram_binding.json", {}) or {}).get("chat_id"))
    chat_ok = bool(env.get("OPENCLAW_TELEGRAM_CHAT_ID")) or bound
    tg = bool(env.get("TELEGRAM_BOT_TOKEN")) and chat_ok
    rows.append(stage(9, "alerts to the founder", "OK" if tg else "BLOCKED",
                      "token %s, chat id %s" % ("set" if env.get("TELEGRAM_BOT_TOKEN") else "missing",
                                                "set" if chat_ok else "missing"),
                      "automatic" if tg else "founder: send the pairing code to the bot (docs/factory/TELEGRAM_SETUP.md)"))

    # 10 persistence
    try:
        state = (autostart_fn or _autostart_state)()
    except Exception as e:  # pragma: no cover
        state = "unknown (%s)" % e
    rows.append(stage(10, "autostart after reboot", "OK" if state == "Ready" else "BLOCKED", "task state %s; not proven by a real reboot" % state, "supervisor task"))

    # affiliate path
    tag = bool(env.get("AMAZON_ASSOCIATE_TAG"))
    rows.append(stage("A1", "Amazon affiliate", "OK" if tag else "BLOCKED", "AMAZON_ASSOCIATE_TAG %s" % ("set" if tag else "unset"), "founder: Associates account"))

    # connector intake: how fresh is what the Claude connectors last reported (the loop cannot call them; a session does)
    try:
        import connector_intake
        ci = connector_intake.summary(root / "data" / "connector_intake.jsonl")
        ages = [r["age_hours"] for r in ci["last_intake"]]
        newest = min(ages) if ages else None
        if newest is None:
            rows.append(stage("C1", "connector intake", "WAITING", "no connector round recorded yet", "agent: run a doctor round"))
        else:
            rows.append(stage("C1", "connector intake", "OK" if newest <= 48 else "WAITING",
                              "last round %.0f h ago; Pinterest outbound clicks %s over %s measured pin(s)" % (newest, ci["pin_outbound_clicks"], ci["pins_measured"]),
                              "automatic" if newest <= 48 else "agent: doctor round overdue (>48 h)"))
    except Exception as e:  # noqa: BLE001  a broken ledger must not stop the stage check
        rows.append(stage("C1", "connector intake", "WAITING", "unreadable (%s)" % type(e).__name__, "agent"))

    # regression gate: do the critical tests still pass (nightly)
    rg = _json(root / "data" / "regression_status.json", None)
    if not rg:
        rows.append(stage("R1", "regression gate", "WAITING", "no run recorded yet (loop step factory_regression runs nightly)", "automatic"))
    else:
        age = _age_minutes(root / "data" / "regression_status.json")
        stale = age is None or age > 36 * 60
        n = rg.get("failed", 0)
        rows.append(stage("R1", "regression gate", "OK" if (not n and not stale) else "WAITING",
                          "python %s passed in %s files, node %s/%s files; %s failing%s" % (rg.get("python", {}).get("passed"), rg.get("python", {}).get("files"),
                                                                                         rg.get("node", {}).get("passed_files"), rg.get("node", {}).get("files"), n,
                                                                                         "; last run older than 36 h" if stale else ""),
                          "agent: fix the failing tests in data/regression_status.json" if n else "automatic"))

    # storefront health guard: what a buyer can see wrong on a live listing
    lh = _json(root / "data" / "listing_health.json", None)
    if not lh:
        rows.append(stage("L1", "storefront health", "WAITING", "no report yet (loop step listing_health writes one daily)", "automatic"))
    else:
        sm = lh.get("summary", {})
        age = _age_minutes(root / "data" / "listing_health.json")
        stale = age is None or age > 48 * 60
        bad = sm.get("needs_action", 0)
        rows.append(stage("L1", "storefront health", "OK" if (not bad and not stale) else "WAITING",
                          "%s live listings, %s finding(s), %s critical/high%s" % (sm.get("live_listings"), sm.get("findings"), bad, "; report older than 48 h" if stale else ""),
                          "agent: fix the findings in data/listing_health.json" if bad else "automatic"))

    # children's YouTube arm (kids_studio): what each episode still waits for, from the loop step's own status file
    ks = _json(root / "data" / "kids_youtube_status.json", None)
    up = 0
    try:
        up = sum(1 for _ in open(root / "data" / "youtube_uploads.jsonl", encoding="utf-8"))
    except OSError:
        pass
    if not ks or not ks.get("episodes"):
        rows.append(stage("K1", "children's YouTube", "WAITING", "no status yet (loop step kids_youtube_publish has not written one)", "automatic"))
    else:
        eps = ks["episodes"]
        ready = [e for e in eps if e.get("passed")]
        failing = sorted({f for e in eps for f in e.get("failing", [])})
        who = {"approval": "founder: approve_kids_episode.py after the Arabic and child-safety review",
               "credentials": "founder: YouTube OAuth (kids_studio/publishing/README.md)"}
        status = "OK" if ready or up else "BLOCKED"
        rows.append(stage("K1", "children's YouTube", status,
                          "%s episode(s) built, %s ready to upload, %s uploaded; waiting on: %s" % (len(eps), len(ready), up, ", ".join(failing) or "nothing"),
                          "; ".join(who[f] for f in failing if f in who) or "automatic"))
    return rows


def _autostart_state():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-ScheduledTask -TaskName GalaxyForge-Factory-Autostart -ErrorAction Stop).State"],
                         capture_output=True, text=True, timeout=30)
    return out.stdout.strip() or "missing"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    rows = collect()
    if "--json" in argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for r in rows:
        print("%-3s %-30s %-8s %s  [%s]" % (r["stage"], r["name"], r["status"], r["detail"], r["owner"]))
    blocked = [r for r in rows if r["status"] == "BLOCKED"]
    print("\n%d BLOCKED, %d WAITING, %d OK" % (len(blocked), sum(r["status"] == "WAITING" for r in rows), sum(r["status"] == "OK" for r in rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
