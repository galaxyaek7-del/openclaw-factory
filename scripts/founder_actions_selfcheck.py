#!/usr/bin/env python3
"""Daily dry run of every command docs/factory/FOUNDER_ACTIONS.md asks the founder to run.

A command in that page is only useful if it still works on the day the founder
runs it: a moved file, a changed product revision or a drifted live listing
would otherwise surface only then. Each check below is the command's own dry
run (or an equivalent read-only call); none performs a live change. Results go
to data/founder_actions_selfcheck.json (git-ignored); the dashboard's decision
queue shows any that fail.

    python scripts/founder_actions_selfcheck.py --once     # at most once per UTC day (loop step)
    python scripts/founder_actions_selfcheck.py --now      # run now
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "founder_actions_selfcheck.json"
PY = sys.executable


def _run(args, timeout=300):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY] + args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, p.stdout, p.stderr


def _last_json(text):
    for line in reversed((text or "").strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    try:
        return json.loads(text)
    except ValueError:
        return None


def check_publish(tmp):
    """Section 1: publish the approved products (dry run of the same command)."""
    reg = json.loads((ROOT / "data" / "product_registry.json").read_text(encoding="utf-8"))
    ready = [p for p in reg.get("products", []) if p.get("primary_state") == "READY_FOR_AUTHORIZATION"]
    if not ready:
        return "PASS", "no product waiting for publication"
    batches = sorted({p["internal_id"].split("-")[0].lower().replace("b", "batch") for p in ready})
    report = Path(tmp) / "publish.json"
    bad, awaiting = [], []
    for b in batches:
        ids = [p["internal_id"] for p in ready if p["internal_id"].lower().startswith(b.replace("batch", "b"))]
        rc, out, err = _run(["scripts/publish_batch14.py", "--batch", b, "--approvals", "data/publication_approvals.json",
                             "--only", *ids, "--report", str(report)])
        doc = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
        s = doc.get("summary") or {}
        # A product held only for the founder's own approval is not a broken
        # command: the decision queue already asks for that approval.
        for p in doc.get("products") or []:
            miss = p.get("missing_prerequisites") or []
            if p.get("status") == "HOLD" and miss and all(m.startswith("authorization:") for m in miss):
                awaiting.append(p.get("id"))
        if rc != 0 or (s.get("pass") or 0) + sum(1 for i in awaiting if i in ids) != len(ids):
            bad.append("%s: %s" % (b, s or (err or out)[-200:]))
    if bad:
        return "FAIL", "; ".join(bad)
    msg = "%d product(s) pass every publication gate" % (len(ready) - len(awaiting))
    return "PASS", msg + ("; awaiting your approval: %s" % ", ".join(awaiting) if awaiting else "")


def check_listing_repairs(tmp):
    """Section 2: the listing repairs (dry run against the live listings, GET only)."""
    rc, out, err = _run(["scripts/apply_listing_repairs_20261029.py"])
    doc = _last_json(out) or {}
    s = doc.get("summary") or {}
    if rc != 0 or doc.get("mode") != "DRY_RUN":
        return "FAIL", (err or out)[-200:]
    planned = {k: v for k, v in s.items() if k.endswith("PLANNED")}
    return "PASS", "still applies: %s" % (", ".join("%s %d" % (k.split(":")[0], v) for k, v in planned.items())
                                          or "nothing left to apply")


def check_kids(tmp):
    """Section 8: children's channel preflight; only founder-owned checks may fail."""
    rc, out, err = _run(["kids_studio/publishing/preflight.py"])
    rows = json.loads(out) if rc == 0 else None
    if rows is None:
        return "FAIL", (err or out)[-200:]
    other = ["%s: %s" % (r["episode"], ", ".join(f for f in r["failing"] if f not in ("approval", "credentials")))
             for r in rows if any(f not in ("approval", "credentials") for f in r["failing"])]
    return ("FAIL", "; ".join(other)) if other else ("PASS", "%d episode(s): only founder steps remain" % len(rows))


def check_accessibility_repair(tmp):
    """Section 6: the prepared accessibility repair of our own site (--check on a copy)."""
    rc, out, err = _run(["scripts/fix_site_accessibility_20261030.py", "--check"])
    if rc != 0 or "after:" not in out:
        return "FAIL", (err or out)[-200:]
    return "PASS", " / ".join(l.strip() for l in out.splitlines() if l.startswith(("before:", "after:")))


def check_analytics_install(tmp):
    """Section 6: the analytics install command (dry run with a dummy token)."""
    rc, out, err = _run(["scripts/set_cloudflare_analytics.py", "--token", "0" * 32])
    return ("PASS", out.strip().splitlines()[-1]) if rc == 0 and "would change" in out else ("FAIL", (err or out)[-200:])


def check_inquiry_queue(tmp):
    """Section 7: the inquiry queue command."""
    rc, out, err = _run(["inquiry_intake.py", "queue"])
    doc = _last_json(out) if rc == 0 else None
    try:
        doc = doc or json.loads(out)
    except ValueError:
        doc = None
    return ("PASS", "%s pending" % doc.get("pending")) if isinstance(doc, dict) and "pending" in doc else \
        ("FAIL", (err or out)[-200:])


CHECKS = [("publish_approved_products", check_publish), ("listing_repairs", check_listing_repairs),
          ("kids_channel_preflight", check_kids), ("accessibility_repair", check_accessibility_repair),
          ("analytics_install", check_analytics_install), ("inquiry_queue", check_inquiry_queue)]


# A dry run that could not reach the platform says nothing about the command:
# it is UNREACHABLE (not a failure, not shown as a broken command) and the
# whole check is repeated, at most hourly, until the network answers.
NETWORK_ERROR = re.compile(r"NameResolutionError|getaddrinfo failed|Failed to resolve|Temporary failure in name resolution|"
                           r"Max retries exceeded|ConnectionError|Connection refused|URLError|timed out|ConnectTimeout|ReadTimeout")
RETRY_AFTER_SECONDS = 3600


def run(now=None, out=OUT, checks=CHECKS):
    now = now or datetime.now(timezone.utc)
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for name, fn in checks:
            try:
                status, detail = fn(tmp)
            except Exception as exc:  # noqa: BLE001  (a broken check is itself a finding)
                status, detail = "FAIL", "%s: %s" % (type(exc).__name__, str(exc)[:160])
            if status == "FAIL" and NETWORK_ERROR.search(detail or ""):
                status = "UNREACHABLE"
            results[name] = {"status": status, "detail": detail}
    doc = {"checked_at": now.isoformat(timespec="seconds"), "results": results,
           "failing": [k for k, v in results.items() if v["status"] not in ("PASS", "UNREACHABLE")],
           "unreachable": [k for k, v in results.items() if v["status"] == "UNREACHABLE"]}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def once(now=None, out=OUT, checks=CHECKS):
    now = now or datetime.now(timezone.utc)
    try:
        prev = json.loads(Path(out).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prev = {}
    last = (prev.get("checked_at") or "")[:10]
    if last == now.date().isoformat():
        if not prev.get("unreachable"):
            return {"action": "none", "detail": "founder actions already checked today"}
        try:
            age = (now - datetime.fromisoformat(prev["checked_at"])).total_seconds()
        except (KeyError, ValueError):
            age = RETRY_AFTER_SECONDS
        if age < RETRY_AFTER_SECONDS:
            return {"action": "none", "detail": "network unreachable at the last check; retrying after an hour"}
    doc = run(now, out, checks)
    if doc["failing"]:
        return {"action": "failed", "detail": "failing: " + ", ".join(doc["failing"])}
    if doc["unreachable"]:
        return {"action": "unreachable", "detail": "platform not reachable, retried hourly: " + ", ".join(doc["unreachable"])}
    return {"action": "checked", "detail": "all %d founder commands still work" % len(doc["results"])}


if __name__ == "__main__":
    if "--now" in sys.argv:
        print(json.dumps(run(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(once(), ensure_ascii=False))
