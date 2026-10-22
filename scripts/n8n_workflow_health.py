#!/usr/bin/env python3
"""Read-only n8n workflow health: evidence of real execution, not "port answers".

The factory health check reported the Sensing Engine OK because n8n answered on
localhost:5678, while every run of every company workflow was failing
(2026-10-10 .. 2026-10-22, "access to env vars denied"). This tool reports five
separate facts per workflow and calls a workflow OK only when all hold:

  1. service      n8n /healthz answers
  2. active       the workflow is published/active
  3. last_status  the latest execution's status
  4. freshness    the latest execution is recent enough for its schedule
  5. business_op  the node that calls server.js returned {"success": true}

A workflow with no execution evidence is UNKNOWN, never OK. A workflow whose
latest success is older than its window is STALE.

Read-only by construction: it copies ~/.n8n/database.sqlite (+ -wal/-shm) to a
private temp dir, opens the COPY read-only, and deletes the copy afterwards. It
never writes to the live database and never calls n8n's API. Error text is
redacted (long token-like strings are masked) and truncated before output.

    python scripts/n8n_workflow_health.py            # human summary
    python scripts/n8n_workflow_health.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

N8N_DIR = Path.home() / ".n8n"
DB_FILES = ("database.sqlite", "database.sqlite-wal", "database.sqlite-shm")
HEALTHZ_URL = "http://localhost:5678/healthz"

# name -> (expected run interval or None for manual-only, node that calls server.js)
TARGETS = {
    "02_Sales_Poll": (timedelta(hours=4), "Poll Sales (server.js Brain)"),
    "Openclaw_Sensing_Engine": (timedelta(days=1), "HTTP Request1"),
    "01_Market_Scout": (None, "HTTP Request"),
}
# A run is fresh if it is younger than interval x FRESH_FACTOR (+ grace).
FRESH_FACTOR = 1.5
GRACE = timedelta(minutes=15)

_TOKENISH = re.compile(r"[A-Za-z0-9_\-:]{24,}")


def redact(text, limit=200):
    if text is None:
        return None
    text = _TOKENISH.sub("<redacted>", str(text))
    return text[:limit]


def _parse_ts(value):
    if not value:
        return None
    s = str(value).replace("T", " ").rstrip("Z")
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def revive_flatted(raw):
    """Decode n8n's flatted execution_data (strings referenced by index)."""
    arr = json.loads(raw)

    def r(v, depth=0):
        if depth > 60:
            return None
        if isinstance(v, str) and v.isdigit() and int(v) < len(arr):
            target = arr[int(v)]
            return target if isinstance(target, str) else r(target, depth + 1)
        if isinstance(v, dict):
            return {k: r(x, depth + 1) for k, x in v.items()}
        if isinstance(v, list):
            return [r(x, depth + 1) for x in v]
        return v

    return r(arr[0])


def _node_output_json(root, node_name):
    try:
        runs = root["resultData"]["runData"][node_name]
        items = runs[-1]["data"]["main"][0]
        return items[0]["json"] if items else None
    except (KeyError, IndexError, TypeError):
        return None


def service_up(url=HEALTHZ_URL, timeout=5):
    try:
        return urllib.request.urlopen(url, timeout=timeout).status == 200
    except Exception:
        return False


def snapshot_db(src_dir=N8N_DIR):
    tmp = Path(tempfile.mkdtemp(prefix="gf_n8n_health_"))
    for f in DB_FILES:
        if (src_dir / f).exists():
            shutil.copy2(src_dir / f, tmp / f)
    return tmp


def assess(db_path, now=None, healthz=None, targets=None):
    now = now or datetime.now(timezone.utc)
    targets = targets or TARGETS
    con = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    out = {"generated_at": now.isoformat(timespec="seconds"), "service_up": healthz, "workflows": {}}
    for name, (interval, node) in targets.items():
        rec = {"active": None, "last_status": None, "last_started_at": None,
               "last_success_at": None, "freshness": "UNKNOWN", "business_op": "UNKNOWN",
               "business_detail": None, "last_error": None, "runs_total": 0,
               "errors_total": 0, "verdict": "UNKNOWN", "reasons": []}
        wf = con.execute("select id, active from workflow_entity where name=?", (name,)).fetchone()
        if not wf:
            rec["reasons"].append("workflow not found")
            out["workflows"][name] = rec
            continue
        rec["active"] = bool(wf["active"])
        rows = con.execute(
            "select e.id, e.status, e.startedAt, d.data from execution_entity e "
            "left join execution_data d on d.executionId=e.id where e.workflowId=? "
            "order by e.startedAt desc", (wf["id"],)).fetchall()
        rec["runs_total"] = len(rows)
        rec["errors_total"] = sum(1 for r in rows if r["status"] in ("error", "crashed"))
        if rows:
            last = rows[0]
            rec["last_status"] = last["status"]
            rec["last_started_at"] = last["startedAt"]
            if last["status"] in ("error", "crashed") and last["data"]:
                try:
                    err = revive_flatted(last["data"]).get("resultData", {}).get("error") or {}
                    rec["last_error"] = redact(err.get("message"))
                except Exception:  # noqa: BLE001
                    rec["last_error"] = "undecodable execution data"
        success = next((r for r in rows if r["status"] == "success"), None)
        if success:
            rec["last_success_at"] = success["startedAt"]
            try:
                payload = _node_output_json(revive_flatted(success["data"]), node) if success["data"] else None
            except Exception:  # noqa: BLE001
                payload = None
            if isinstance(payload, dict) and payload.get("success") is True:
                rec["business_op"] = "OK"
            elif isinstance(payload, dict):
                rec["business_op"] = "FAILED"
                rec["business_detail"] = redact(payload.get("error") or "success flag not true")
            else:
                rec["business_detail"] = "no output captured for node " + repr(node)
        ts = _parse_ts(rec["last_success_at"])
        if interval is None:
            rec["freshness"] = "MANUAL_ONLY"
        elif ts is None:
            rec["freshness"] = "UNKNOWN"
        else:
            rec["freshness"] = "FRESH" if now - ts <= interval * FRESH_FACTOR + GRACE else "STALE"

        reasons = rec["reasons"]
        if healthz is False:
            reasons.append("n8n service not answering")
        if not rec["active"]:
            reasons.append("workflow not active")
        if not rows:
            reasons.append("no execution evidence")
        elif rec["last_status"] != "success":
            reasons.append(f"latest execution {rec['last_status']}")
        if rec["freshness"] == "STALE":
            reasons.append("latest success is stale")
        if rec["business_op"] != "OK" and rows:
            reasons.append(f"business operation {rec['business_op']}")

        if not rows:
            rec["verdict"] = "UNKNOWN"
        elif rec["last_status"] in ("error", "crashed"):
            rec["verdict"] = "FAILING"
        elif rec["freshness"] == "STALE":
            rec["verdict"] = "STALE"
        elif (healthz is not False and rec["active"] and rec["last_status"] == "success"
              and rec["business_op"] == "OK" and rec["freshness"] in ("FRESH", "MANUAL_ONLY")):
            rec["verdict"] = "OK"
        else:
            rec["verdict"] = "UNKNOWN"
        out["workflows"][name] = rec
    con.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    tmp = snapshot_db()
    try:
        report = assess(tmp / "database.sqlite", healthz=service_up())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    print(f"n8n service up: {report['service_up']}  ({report['generated_at']})")
    for name, r in report["workflows"].items():
        print(f"- {name}: {r['verdict']}  active={r['active']} last={r['last_status']}@{r['last_started_at']} "
              f"last_success={r['last_success_at']} freshness={r['freshness']} business_op={r['business_op']} "
              f"runs={r['runs_total']} errors={r['errors_total']}")
        if r["reasons"]:
            print("    reasons:", "; ".join(r["reasons"]))
        if r["last_error"]:
            print("    last error:", r["last_error"])


if __name__ == "__main__":
    main()
