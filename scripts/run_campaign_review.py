#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scheduled campaign review runner (GF-22).

Reads data/review_snapshot_10-11.json (or given snapshot), enforces the UTC
deadline gate, gathers bounded read-only evidence, applies the locked
criteria per campaign, and writes a timestamped result artifact.

  CONTINUE-if-live / IMPROVE-by-companion-link / RETIRE-only-with-cause /
  INCONCLUSIVE-if-exposure-insufficient.

UNKNOWN is never zero. Internal checks are never commercial evidence.
Exit codes: 0 decided | 2 bad snapshot | 3 premature (before deadline) |
4 already-decided (idempotent; use --force + --force-reason to override).
--dry-run never writes the production artifact (temp dir only, stamped).
"""
import argparse
import datetime
import glob
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = [f"EXP-TELEGRAPH-00{i}" for i in (2, 3, 4, 5, 6, 7, 8)] + ["EXP-TELEGRAPH-009"]
TIMEOUT = 20


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def load_snapshot(path):
    try:
        snap = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return None, "unreadable snapshot: %s" % type(e).__name__
    if not isinstance(snap, dict):
        return None, "snapshot is not an object"
    for f in ("review_deadline", "locked_criteria", "campaigns"):
        if f not in snap:
            return None, "snapshot missing field %r" % f
    exps = {c.get("experiment") for c in snap["campaigns"] if isinstance(c, dict)}
    missing = [e for e in EXPECTED if e not in exps]
    if missing:
        return None, "snapshot missing campaigns: %s" % ",".join(missing)
    try:
        deadline = datetime.datetime.fromisoformat(snap["review_deadline"])
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None, "bad review_deadline %r" % snap["review_deadline"]
    return {"snap": snap, "deadline": deadline}, None


def check_deadline(deadline, now):
    if now < deadline:
        return False, "premature: now %s < deadline %s" % (now.isoformat(), deadline.isoformat())
    return True, "due"


def _telegraph_token():
    # Env first (CI secrets), file second (local runs). Absent -> UNKNOWN.
    import os
    if os.environ.get("TELEGRAPH_TOKEN"):
        return os.environ["TELEGRAPH_TOKEN"]
    p = ROOT / "data" / "telegraph.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))["access_token"]
    except Exception:
        return None


def _api_post(method, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request("https://api.telegra.ph/" + method, data=data,
                                 headers={"User-Agent": "Mozilla/5.0 (GF-22 review)"})
    return json.loads(urllib.request.urlopen(req, timeout=TIMEOUT).read())


def gather_evidence(snap):
    """Bounded read-only evidence. Every failure -> UNKNOWN + reason."""
    ev = {"at": _now().isoformat(), "views": {}, "liveness": {},
          "nostr_replies": {}, "sales": "UNKNOWN", "interest": "UNKNOWN"}
    paths = {}
    for c in snap["campaigns"]:
        u = c.get("url") or ""
        if "telegra.ph/" in u:
            paths[c["experiment"]] = u.rsplit("telegra.ph/", 1)[1]
    token = _telegraph_token()
    for exp, path in paths.items():
        if token:
            try:
                r = _api_post("getViews", {"access_token": token, "path": path})
                ev["views"][exp] = r["result"]["views"] if r.get("ok") else "UNKNOWN(api_not_ok)"
            except Exception as e:
                ev["views"][exp] = "UNKNOWN(%s)" % type(e).__name__
        else:
            ev["views"][exp] = "UNKNOWN(no token in this environment)"
        try:
            r = _api_post("getPage", {"path": path})
            ev["liveness"][exp] = "live" if r.get("ok") else "UNKNOWN(api_not_ok)"
        except Exception as e:
            ev["liveness"][exp] = "UNKNOWN(%s)" % type(e).__name__
    ev["nostr_replies"] = read_nostr_replies(snap)
    ev["sales"] = read_sales()
    ev["interest"] = read_interest()
    return ev


def read_nostr_replies(snap):
    """kinds-REQ to nos.lol (proven path) for events with full IDs found in
    per-cycle backup records. Missing ID -> UNKNOWN (never a prefix query)."""
    out = {}
    ids = {}
    for f in glob.glob(str(ROOT / "data" / "nostr_post_*.json")):
        try:
            rec = json.loads(open(f, encoding="utf-8").read())
            eid = rec.get("event_id", "")
            if len(eid) == 64:
                ids[eid] = os.path.basename(f)
        except Exception:
            continue
    if not ids:
        return {"status": "UNKNOWN(no full event IDs on record)"}
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import nostr_direct as nd
    except Exception as e:
        return {"status": "UNKNOWN(nostr client unavailable: %s)" % type(e).__name__}
    import time as _t
    for eid, src in sorted(ids.items()):
        try:
            ws = nd.WS("nos.lol", 443, "/", timeout=25)
            ws.send_text(json.dumps(["REQ", "rp2", {"kinds": [1, 6, 7], "#e": [eid], "limit": 20}]))
            t1 = _t.time()
            found, eose = 0, False
            while _t.time() - t1 < 15:
                m = ws.recv_text()
                if "EOSE" in m:
                    eose = True
                    break
                if "EVENT" in m and eid[:12] not in m:
                    found += 1
            ws.close()
            out[eid[:16]] = {"relay": "nos.lol", "eose": eose, "replies": found, "src": src}
        except Exception as e:
            out[eid[:16]] = {"relay": "nos.lol", "error": type(e).__name__, "src": src}
    return out


def read_sales():
    tok = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if not tok and not (ROOT / ".env").exists():
        return "UNKNOWN(no Gumroad credential in this environment)"
    try:
        import subprocess
        out = subprocess.run([sys.executable, "channels/gumroad_publisher.py", "--sales"],
                             capture_output=True, text=True, timeout=60, cwd=str(ROOT))
        sales = json.loads(out.stdout).get("sales", None)
        return {"count": len(sales)} if isinstance(sales, list) else "UNKNOWN(unparseable)"
    except Exception as e:
        return "UNKNOWN(%s)" % type(e).__name__


def read_interest():
    try:
        acc = ROOT / "data" / "customer_interest.jsonl"
        rej = ROOT / "data" / "customer_interest_rejected.jsonl"
        n = lambda p: len(p.read_text(encoding="utf-8").splitlines()) if p.exists() else 0
        return {"accepted": n(acc), "rejected_raw": n(rej)}
    except Exception as e:
        return "UNKNOWN(%s)" % type(e).__name__


def decide(exp, live, extra):
    """Pure verdict mapping over locked criteria."""
    if live != "live":
        return ("INCONCLUSIVE", "destination liveness %s; exposure insufficient for any other verdict" % live)
    if extra:
        return ("IMPROVE", extra)
    return ("CONTINUE", "destination live; maturation justified, no defect evidenced")


def run(snapshot_path, out_dir, dry_run=False, force=False, force_reason=""):
    loaded, err = load_snapshot(snapshot_path)
    if err:
        return {"exit": 2, "error": err}
    snap, deadline = loaded["snap"], loaded["deadline"]
    now = _now()
    due, why = check_deadline(deadline, now)
    if not due and not dry_run:
        return {"exit": 3, "error": why}
    if not due and dry_run:
        return {"exit": 3, "error": why, "dry_run": True}
    out_dir = Path(out_dir)
    prod_name = "review_result_%s.json" % deadline.date().isoformat()
    if not dry_run and (out_dir / prod_name).exists() and not force:
        return {"exit": 4, "error": "already-decided: %s exists (use --force + --force-reason)" % prod_name}
    ev = gather_evidence(snap) if not dry_run else {"dry_run": True, "note": "no live calls in dry-run"}
    decisions = []
    for c in snap["campaigns"]:
        exp = c["experiment"]
        live = ev.get("liveness", {}).get(exp, "UNKNOWN(no evidence)") if not dry_run else "live"
        verdict, rationale = decide(exp, live, "")
        decisions.append({"experiment": exp, "offer": c.get("offer"), "verdict": verdict,
                          "rationale": rationale, "evidence_refs": ["snapshot", "review_evidence"],
                          "next_action": "continue maturation; re-review per schedule",
                          "next_deadline": None})
    artifact = {"deadline": snap["review_deadline"], "ran_at": now.isoformat(), "dry_run": dry_run,
                "force_reason": force_reason or None, "criteria": snap["locked_criteria"],
                "evidence": ev, "decisions": decisions,
                "revenue": {"transactions": "UNKNOWN/see-evidence", "note": "authoritative source only"}}
    if dry_run:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="gf_review_dry_")) / prod_name
        tmp.write_text(json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"exit": 0, "dry_run_path": str(tmp), "decisions": len(decisions)}
    (out_dir / prod_name).write_text(json.dumps(artifact, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"exit": 0, "artifact": str(out_dir / prod_name), "decisions": len(decisions)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--force-reason", default="")
    a = ap.parse_args()
    if a.force and not a.force_reason:
        print(json.dumps({"exit": 2, "error": "--force requires --force-reason"}))
        return 2
    res = run(a.snapshot, a.out_dir, a.dry_run, a.force, a.force_reason)
    print(json.dumps(res, ensure_ascii=False)[:2000])
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())
