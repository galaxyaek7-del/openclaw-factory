"""Read-only n8n notification self-check.

Answers one question with zero side effects: *can this factory's notification
chain actually deliver a message right now, and if not, exactly why?*

Every check is read-only:
  * `GET /healthz` on the local n8n instance (no workflow is triggered)
  * a **copy** of n8n's own SQLite database, read with the stdlib — which
    webhook paths are registered, and what the last executions of the notify
    workflows actually did
  * presence checks on this repo's `.env` (keys are never printed)
  * Telegram's `getMe` / `getUpdates` (read-only API calls; `getUpdates`
    cannot work while a webhook is registered to the bot and returns an
    explanatory error instead)

It never sends a message, never writes a file, and never prints a secret
value. Designed to be run both by a human and by `factory_loop.js`.

Verdict vocabulary (Truth First): DELIVERING / BLOCKED / UNKNOWN.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent.parent

# Workflows whose delivery path matters to the commercial mission.
NOTIFY_WORKFLOWS = ("03_Production_Notify", "04_Telegram_Notify")
# n8n's own error text when N8N_BLOCK_ENV_ACCESS_IN_NODE is in force.
ENV_DENIED_MARKER = "access to env vars denied"


def _read_env_keys(env_path=None) -> set:
    """Key names present in .env. Values are never returned or printed."""
    path = Path(env_path) if env_path else FACTORY_DIR / ".env"
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    return keys


def _db_copy(db_path, dest_dir):
    """Copy n8n's live SQLite DB so every query is against a snapshot and can
    never lock or mutate the running instance."""
    src = Path(db_path).expanduser()
    if not src.exists():
        return None, f"n8n database not found at {src}"
    dest = Path(dest_dir) / "n8n_selfcheck.sqlite"
    try:
        shutil.copy2(src, dest)
        # n8n runs SQLite in WAL mode: rows written since the last checkpoint live only in the -wal file. Copying the
        # main file alone gave a stale snapshot that hid the newest executions (a fixed workflow still read as failing).
        for suffix in ("-wal", "-shm"):
            side = Path(str(src) + suffix)
            if side.exists():
                shutil.copy2(side, Path(str(dest) + suffix))
    except OSError as e:
        return None, f"could not read n8n database: {e!r}"
    return dest, None


def _query(db, sql, params=()):
    con = sqlite3.connect(str(db))
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def registered_webhooks(db):
    """Which webhook paths n8n currently has registered (active workflows)."""
    try:
        rows = _query(db, "select webhookPath, method, workflowId from webhook_entity")
    except sqlite3.Error as e:
        return {"status": "UNKNOWN", "detail": repr(e)[:200], "paths": []}
    return {"status": "OBSERVED",
            "paths": sorted({r[0] for r in rows if r[0]}),
            "entries": [{"path": r[0], "method": r[1], "workflow_id": r[2]} for r in rows]}


def workflow_states(db):
    try:
        rows = _query(db, "select id, name, active from workflow_entity")
    except sqlite3.Error as e:
        return {"status": "UNKNOWN", "detail": repr(e)[:200]}
    return {"status": "OBSERVED",
            "workflows": [{"id": r[0], "name": r[1], "active": bool(r[2])} for r in rows]}


def recent_executions(db, workflow_names=NOTIFY_WORKFLOWS, limit=25):
    """Last executions of the notify workflows, with the real error text
    classified. Reads execution_data only for the rows it reports."""
    try:
        wf = {r[0]: r[1] for r in _query(db, "select id, name from workflow_entity")}
        rows = _query(db, "select id, workflowId, status, startedAt from execution_entity "
                          "order by id desc limit ?", (limit,))
    except sqlite3.Error as e:
        return {"status": "UNKNOWN", "detail": repr(e)[:200], "executions": []}

    out = []
    for eid, wid, status, started in rows:
        name = wf.get(wid, "UNKNOWN")
        if name not in workflow_names:
            continue
        detail = ""
        try:
            d = _query(db, "select data from execution_data where executionId=?", (str(eid),))
            blob = d[0][0] if d and d[0] else ""
        except sqlite3.Error:
            blob = ""
        if ENV_DENIED_MARKER in blob:
            detail = "ENV_ACCESS_DENIED"
        elif status == "error":
            detail = "ERROR_OTHER"
        elif status == "success":
            detail = "DELIVERED"
        out.append({"execution_id": eid, "workflow": name, "status": status,
                    "started_at": started, "detail": detail or "UNCLASSIFIED"})
        if len(out) >= 6:
            break
    return {"status": "OBSERVED", "executions": out}


def n8n_health(base_url="http://localhost:5678", timeout=10):
    for path in ("/healthz", "/healthz/readiness"):
        try:
            r = urllib.request.urlopen(base_url + path, timeout=timeout)
            body = r.read(200).decode("utf-8", "replace")
            if r.status == 200:
                return {"status": "UP", "probe": path, "body": body[:80]}
        except Exception as e:  # noqa: BLE001
            last = repr(e)[:160]
    return {"status": "DOWN", "detail": locals().get("last", "no response")}


def telegram_reachability(token=None, timeout=15):
    """getMe + getUpdates. Read-only. Never returns the token."""
    if token is None:
        env = FACTORY_DIR / ".env"
        token = ""
        if env.exists():
            for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("TELEGRAM_BOT_TOKEN="):
                    token = line.split("=", 1)[1].strip()
    if not token:
        return {"status": "NOT_CONFIGURED", "detail": "TELEGRAM_BOT_TOKEN absent"}
    out = {"status": "UNKNOWN"}
    try:
        r = urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=timeout)
        d = json.loads(r.read())
        out["bot_username"] = (d.get("result") or {}).get("username")
        out["getme_ok"] = bool(d.get("ok"))
    except Exception as e:  # noqa: BLE001
        out["getme_error"] = repr(e)[:160]
    try:
        r = urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getUpdates?limit=100", timeout=timeout)
        d = json.loads(r.read())
        updates = d.get("result") or []
        chats = {}
        for upd in updates:
            c = (upd.get("message") or {}).get("chat") or {}
            if c.get("id"):
                chats[str(c["id"])] = {"type": c.get("type"),
                                       "name": c.get("username") or c.get("title") or c.get("first_name")}
        out["updates_seen"] = len(updates)
        out["discoverable_chat_ids"] = chats
        out["status"] = "OBSERVED"
    except Exception as e:  # noqa: BLE001
        out["getupdates_error"] = repr(e)[:160]
        out.setdefault("status", "UNKNOWN")
    return out


def assess(env_keys, health, webhooks, executions, telegram, db_error=None,
           db_path="~/.n8n/database.sqlite"):
    """Turn the raw observations into the one verdict the founder needs."""
    checks = {}
    checks["n8n_instance"] = health.get("status")
    checks["chat_id_configured"] = "OPENCLAW_TELEGRAM_CHAT_ID" in env_keys
    checks["bot_token_configured"] = "TELEGRAM_BOT_TOKEN" in env_keys
    paths = set(webhooks.get("paths") or [])
    checks["notify_webhooks_registered"] = sorted(
        p for p in paths if p in ("production-notify", "golden-hunter-notify"))

    # "last notify execution" means the MOST RECENT one (the list is newest first). Scanning the whole window kept a
    # fixed fault reported as current for six runs after the first success (seen 2026-11-06).
    runs = executions.get("executions", [])
    latest = runs[0] if runs else {}
    denial = latest.get("detail") == "ENV_ACCESS_DENIED"
    delivered = latest.get("detail") == "DELIVERED"
    checks["last_notify_execution_env_denied"] = denial
    checks["last_notify_execution_delivered"] = delivered

    reasons = []
    if db_error:
        reasons.append(f"n8n execution history unavailable ({db_error})")
    if not checks["chat_id_configured"]:
        reasons.append("OPENCLAW_TELEGRAM_CHAT_ID is not set in .env")
    if not checks["bot_token_configured"]:
        reasons.append("TELEGRAM_BOT_TOKEN is not set in .env")
    if denial:
        reasons.append("n8n denies $env access (N8N_BLOCK_ENV_ACCESS_IN_NODE); "
                       "every $env.* expression in the notify workflows fails")

    if delivered and not denial and checks["chat_id_configured"]:
        verdict = "DELIVERING"
    elif health.get("status") != "UP":
        verdict = "UNKNOWN"
        reasons.append("n8n instance is not reachable, so delivery cannot be assessed")
    elif reasons:
        verdict = "BLOCKED"
    else:
        verdict = "UNKNOWN"
        reasons.append("no notify execution found in the retained history to judge from")

    return {"verdict": verdict, "checks": checks, "reasons": reasons,
            "db_path": str(db_path) if db_error is None else db_error}


def run(db_path="~/.n8n/database.sqlite", env_path=None, base_url="http://localhost:5678",
        telegram_token=None, tmp_dir=None):
    env_keys = _read_env_keys(env_path)
    health = n8n_health(base_url)
    tmp = tempfile.mkdtemp(prefix="n8n_selfcheck_", dir=tmp_dir)
    db, db_error = _db_copy(db_path, tmp)
    if db:
        webhooks = registered_webhooks(db)
        executions = recent_executions(db)
    else:
        webhooks = {"status": "UNKNOWN", "paths": []}
        executions = {"status": "UNKNOWN", "executions": []}
    telegram = telegram_reachability(telegram_token)
    result = {
        "checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "env_keys_checked": sorted(k for k in env_keys
                                   if k in ("OPENCLAW_TELEGRAM_CHAT_ID", "TELEGRAM_BOT_TOKEN")),
        "n8n": health,
        "webhooks": webhooks,
        "executions": executions,
        "telegram": telegram,
    }
    result["assessment"] = assess(env_keys, health, webhooks, executions, telegram,
                                  db_error=db_error, db_path=db_path)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=os.path.expanduser("~/.n8n/database.sqlite"))
    ap.add_argument("--base-url", default="http://localhost:5678")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = run(db_path=args.db, base_url=args.base_url)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        a = out["assessment"]
        print(f"n8n notification delivery: {a['verdict']}")
        print(f"  instance: {a['checks'].get('n8n_instance')}")
        print(f"  notify webhooks registered: {a['checks'].get('notify_webhooks_registered')}")
        print(f"  chat id configured: {a['checks'].get('chat_id_configured')}")
        print(f"  env access denied in last notify run: {a['checks'].get('last_notify_execution_env_denied')}")
        print(f"  telegram bot: {out['telegram'].get('bot_username')} "
              f"(updates seen: {out['telegram'].get('updates_seen')})")
        for r in a["reasons"]:
            print(f"  reason: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
