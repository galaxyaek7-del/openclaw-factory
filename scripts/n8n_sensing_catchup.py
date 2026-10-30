#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge -- catch up a daily Sensing run lost to a network outage (2026-10-23).

Openclaw_Sensing_Engine runs once a day (07:00 UTC). The host loses its
network most mornings (reports/NETWORK_OUTAGES_2026-10-22.md); on
2026-10-23 the 07:00 run failed with `getaddrinfo ENOTFOUND
trends.google.com` inside a 06:08-07:28 outage, losing the day's trends.

`--once` (called every factory_loop tick) triggers ONE re-run through the
workflow's existing, authenticated webhook (`scout-trigger`, which feeds
the same Google Trends -> /api/trends pipeline) only when all hold:
  * today's latest Sensing execution failed with a network-class error;
  * no successful Sensing run has happened today;
  * DNS for trends.google.com resolves now (the network is back);
  * fewer than MAX_ATTEMPTS_PER_DAY catch-ups were made today;
  * N8N_WEBHOOK_SECRET is configured (the webhook rejects unauthenticated calls).
It changes no n8n configuration, reads n8n state from a read-only DB copy
(scripts/n8n_workflow_health.py), and never prints the secret.
"""
import argparse
import json
import re
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORKFLOW = "Openclaw_Sensing_Engine"
WEBHOOK_URL = "http://127.0.0.1:5678/webhook/scout-trigger"
STATE_PATH = ROOT / "data" / "n8n_sensing_catchup.json"
MAX_ATTEMPTS_PER_DAY = 2
NETWORK_ERROR = re.compile(r"ENOTFOUND|EAI_AGAIN|ECONNREFUSED|ECONNRESET|ETIMEDOUT|connection cannot be established"
                           r"|timed? ?out|getaddrinfo", re.I)


# 2026-10-29: n8n was down at 08:00 local (07:00 UTC) and the day's run never
# started, so there was no failed run to catch up and the day's trends were lost.
# A run that never started counts too, once the schedule has passed with an hour
# of grace. All other limits below are unchanged.
MISSED_AFTER_UTC_HOUR = 8


def decide(workflow, today, attempts_today, dns_ok, secret_set, now_hour=None):
    """Pure decision. Returns (should_trigger, reason).

    now_hour (UTC) enables the missed-run case; without it the original rule
    (only a network-class failure today) applies."""
    if not workflow:
        return False, "workflow state UNKNOWN"
    if str(workflow.get("last_success_at") or "")[:10] == today:
        return False, "already succeeded today"
    started_today = str(workflow.get("last_started_at") or "")[:10] == today
    if not started_today and now_hour is not None:
        if now_hour < MISSED_AFTER_UTC_HOUR:
            return False, "today's scheduled run is not overdue yet"
        reason_ok = "today's scheduled run never started (n8n was down) and the network is back"
    else:
        if workflow.get("last_status") != "error" or not started_today:
            return False, "no failed run today"
        if not NETWORK_ERROR.search(str(workflow.get("last_error") or "")):
            return False, "today's failure is not a network error: needs diagnosis, not a retry"
        reason_ok = "network-class failure today and the network is back"
    if attempts_today >= MAX_ATTEMPTS_PER_DAY:
        return False, f"catch-up limit reached ({MAX_ATTEMPTS_PER_DAY}/day)"
    if not dns_ok:
        return False, "network still down (trends.google.com does not resolve)"
    if not secret_set:
        return False, "N8N_WEBHOOK_SECRET not configured"
    return True, reason_ok


def _dns_ok(host="trends.google.com"):
    try:
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


def _read_state(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_state(state, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(path)


def run_once(now=None, state_path=STATE_PATH, health=None, dns_ok=None, secret=None, trigger=None):
    now = now or datetime.now(timezone.utc)
    today = now.date().isoformat()
    state = _read_state(state_path)
    # 2026-10-30: once today's run has succeeded nothing can be due until
    # tomorrow; skip the n8n database copy that every 10-minute tick paid
    # (2.6 s idle, 14 s under load).
    if state.get("succeeded_on") == today:
        return {"action": "none", "detail": "already succeeded today (recorded)"}
    if health is None:
        from scripts import n8n_workflow_health as h
        health = h.build_report() if hasattr(h, "build_report") else json.loads(
            __import__("subprocess").run([sys.executable, str(ROOT / "scripts" / "n8n_workflow_health.py"), "--json"],
                                         capture_output=True, text=True, timeout=60).stdout)
    workflow = (health.get("workflows") or {}).get(WORKFLOW)
    attempts = int(state.get(today, 0))
    if secret is None:
        from channels.env_config import read_env_value
        secret = read_env_value("N8N_WEBHOOK_SECRET", ROOT / ".env") or ""
    ok, reason = decide(workflow, today, attempts, _dns_ok() if dns_ok is None else dns_ok, bool(secret),
                        now_hour=now.hour)
    if not ok:
        if reason == "already succeeded today":
            _write_state({today: attempts, "succeeded_on": today}, state_path)
        return {"action": "none", "detail": reason}
    state = {today: attempts + 1}  # keep only today's counter
    _write_state(state, state_path)
    try:
        if trigger:
            code = trigger(WEBHOOK_URL, secret)
        else:
            req = urllib.request.Request(WEBHOOK_URL, headers={"X-GF-Webhook-Secret": secret,
                                                               "User-Agent": "GalaxyForge-sensing-catchup/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                code = r.status
    except Exception as e:  # noqa: BLE001  (never echoes the secret)
        return {"action": "failed", "detail": f"catch-up trigger failed: {type(e).__name__}", "attempt": attempts + 1}
    return {"action": "triggered", "detail": f"Sensing re-run requested (HTTP {code}), attempt {attempts + 1}/"
                                             f"{MAX_ATTEMPTS_PER_DAY} today: {reason}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.parse_args()
    print(json.dumps(run_once(), ensure_ascii=False))


if __name__ == "__main__":
    main()
