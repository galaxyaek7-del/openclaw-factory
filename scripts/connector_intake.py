#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intake ledger for what Claude connectors report about the factory (2026-11-06).

The connectors (Metricool, Gmail, ...) exist only inside a Claude session; the headless factory loop cannot call them.
This module is the door between the two: the factory doctor (a Claude session) reads a connector, then records the
result here. A record is accepted only if it is real, well-formed and from a registered connector; otherwise it is
refused with the reason. Nothing here calls a connector or a network.

    echo '<json>' | python scripts/connector_intake.py --add      # validate and append one record
    python scripts/connector_intake.py --summary                   # last intake per source, staleness, pin clicks

Record: {"kind", "source", "fetched_at" (ISO UTC), "period": {"from","to"}, "payload": {...}, "dedupe_key"?}
Kinds: pin_metrics (payload.pins: [{pin_id,title,impressions,saves,pin_clicks,outbound_clicks}], payload.measured),
       sale_email_check / inquiry_email_check (payload.matching_threads, payload.window_days; the latter counts replies/requests to the site's mailto forms), connector_status (payload.state, payload.detail).
Truth First: a metric that was not measured is recorded with measured=false, never as 0 clicks.
Privacy: no email addresses, tokens or message bodies are stored; strings are short and screened.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "data" / "connector_intake.jsonl"
REGISTRY = ROOT / "config" / "connectors.json"
STATES = ("AUTHENTICATED", "NEEDS_AUTH", "UNPROBED", "ERROR")
_SECRETISH = re.compile(r"(bot\d{6,}:[A-Za-z0-9_-]{20,}|[A-Za-z0-9_-]{32,}|Bearer\s+\S+|access_token=)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PIN_FIELDS = ("impressions", "saves", "pin_clicks", "outbound_clicks")


def registry(path=REGISTRY):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")).get("connectors", {})
    except (OSError, ValueError):
        return {}


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def _is_iso(ts):
    try:
        datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate(rec, reg=None):
    reg = reg if reg is not None else registry()
    errs = []
    if not isinstance(rec, dict):
        return ["record is not an object"]
    src, kind = rec.get("source"), rec.get("kind")
    if src not in reg:
        errs.append(f"source {src!r} is not a registered connector")
    elif kind not in reg[src].get("intake_kinds", []):
        errs.append(f"kind {kind!r} is not an intake kind of {src}")
    if not _is_iso(rec.get("fetched_at")):
        errs.append("fetched_at must be an ISO timestamp")
    pl = rec.get("payload")
    if not isinstance(pl, dict):
        return errs + ["payload must be an object"]
    for s in _strings(rec):
        if len(s) > 300:
            errs.append("a string longer than 300 characters (message bodies are never stored)")
            break
        if _SECRETISH.search(s):
            errs.append("a secret-looking string")
            break
        if _EMAIL.search(s):
            errs.append("an email address (personal data is not stored)")
            break
    if kind == "pin_metrics":
        if not isinstance(pl.get("measured"), bool):
            errs.append("pin_metrics needs payload.measured (true/false)")
        pins = pl.get("pins", [])
        if not isinstance(pins, list):
            errs.append("payload.pins must be a list")
        else:
            if pl.get("measured") is False and pins:
                errs.append("measured=false cannot carry pin numbers")
            for p in pins:
                if not isinstance(p, dict) or not p.get("pin_id"):
                    errs.append("each pin needs a pin_id")
                    continue
                for f in PIN_FIELDS:
                    if not isinstance(p.get(f), int) or isinstance(p.get(f), bool) or p[f] < 0:
                        errs.append(f"pin {p.get('pin_id')}: {f} must be a non-negative integer")
    elif kind in ("sale_email_check", "inquiry_email_check"):
        for f in ("matching_threads", "window_days"):
            if not isinstance(pl.get(f), int) or pl[f] < 0:
                errs.append(f"{kind} needs a non-negative integer {f}")
    elif kind == "connector_status":
        if pl.get("state") not in STATES:
            errs.append(f"connector_status.state must be one of {STATES}")
    return errs


def dedupe_key(rec):
    if rec.get("dedupe_key"):
        return str(rec["dedupe_key"])
    base = json.dumps({k: rec.get(k) for k in ("kind", "source", "period", "payload")}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def read(path=LEDGER):
    out = []
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def add(rec, path=LEDGER, reg=None):
    errs = validate(rec, reg)
    if errs:
        return {"accepted": False, "errors": errs}
    key = dedupe_key(rec)
    if any(r.get("dedupe_key") == key for r in read(path)):
        return {"accepted": False, "errors": [], "duplicate": True}
    row = {**rec, "dedupe_key": key, "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"accepted": True, "dedupe_key": key}


def pin_outbound_clicks(path=LEDGER):
    """(total, pins_counted): the highest outbound-click figure seen per pin across measured records."""
    best = {}
    for r in read(path):
        pl = r.get("payload") or {}
        if r.get("kind") != "pin_metrics" or r.get("source") != "metricool" or pl.get("measured") is not True:
            continue
        for p in pl.get("pins", []):
            best[p["pin_id"]] = max(best.get(p["pin_id"], 0), int(p.get("outbound_clicks") or 0))
    return sum(best.values()), len(best)


def summary(path=LEDGER, now=None):
    now = now or datetime.now(timezone.utc)
    last = {}
    for r in read(path):
        last[(r.get("source"), r.get("kind"))] = r
    rows = []
    for (src, kind), r in sorted(last.items()):
        age = (now - datetime.fromisoformat(r["fetched_at"].replace("Z", "+00:00"))).total_seconds() / 3600
        rows.append({"source": src, "kind": kind, "fetched_at": r["fetched_at"], "age_hours": round(age, 1)})
    total, n = pin_outbound_clicks(path)
    return {"last_intake": rows, "pin_outbound_clicks": total, "pins_measured": n}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--add" in argv:
        try:
            rec = json.loads(sys.stdin.read())
        except ValueError as e:
            print(json.dumps({"accepted": False, "errors": [f"not JSON: {e}"]}))
            return 1
        r = add(rec)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get("accepted") or r.get("duplicate") else 1
    print(json.dumps(summary(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
