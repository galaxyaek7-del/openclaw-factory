#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Error census: every kind of error the factory logged in the last N hours, grouped by signature (2026-11-07). Read-only.

    python scripts/error_census.py [hours=24] [--json]

Sources: factory_loop.log (step failures), data/agent_executions.jsonl (agent call errors), logs/*err*.log and server_crashes.log,
supervisor.log (crashes/restarts), health_monitor.log. A signature is the message with digits, ids and paths collapsed, so a repeated
error counts once with a number. Nothing is fixed here: this answers "what is going wrong, how often, since when".
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def signature(msg):
    s = str(msg)[:300]
    s = re.sub(r"[A-Za-z]:\\[^\s'\"]+|/[\w./-]{6,}", "<path>", s)
    s = re.sub(r"\b[0-9a-f]{8,}\b|\b[A-Za-z0-9_=-]{20,}\b", "<id>", s)
    s = re.sub(r"\d+", "N", s)
    return s.strip()[:140]


def since_iso(hours, now=None):
    return ((now or datetime.now(timezone.utc)) - timedelta(hours=hours)).isoformat()


def loop_failures(rows, since):
    out = defaultdict(list)
    for r in rows:
        ts = str(r.get("timestamp", ""))
        if ts < since:
            continue
        for a in r.get("actions", []) or []:
            if a.get("action") in ("failed", "error"):
                out[("loop:" + str(a.get("step")), signature(a.get("detail")))].append(ts)
    return out


def agent_errors(rows, since):
    out = defaultdict(list)
    for r in rows:
        ts = str(r.get("started_at", ""))
        if ts < since or r.get("outcome") in (None, "ok"):
            continue
        out[(f"agent:{r.get('agent')}:{r.get('outcome')}", signature(r.get("error")))].append(ts)
    return out


def jl(path):
    out = []
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("{"):
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    except OSError:
        pass
    return out


def text_errors(path, since, pattern=re.compile(r"\b(error|exception|traceback|unhandled|ECONN|EADDR|crash|FATAL)\b", re.I), max_lines=4000):
    """Last lines of a plain log whose own leading timestamp (ISO) is recent; lines without a timestamp are skipped."""
    out = defaultdict(list)
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()[-max_lines:]
    except OSError:
        return out
    for ln in lines:
        m = re.search(r"(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d)", ln)
        if m and m.group(1) >= since[:19] and pattern.search(ln):
            out[(f"log:{Path(path).name}", signature(re.sub(r"20\d\d-\d\d-\d\dT[\d:.]+Z?", "", ln)))].append(m.group(1))
    return out


def census(hours=24, root=ROOT, now=None):
    since = since_iso(hours, now)
    groups = defaultdict(list)
    for src in (loop_failures(jl(root / "factory_loop.log"), since), agent_errors(jl(root / "data" / "agent_executions.jsonl"), since)):
        for k, v in src.items():
            groups[k] += v
    for name in ("logs/factory_loop_supervised_err.log", "logs/server_supervised_err.log", "server_crashes.log", "supervisor.log", "health_monitor.log"):
        for k, v in text_errors(root / name, since).items():
            groups[k] += v
    rows = [{"source": k[0], "signature": k[1], "count": len(v), "first": min(v), "last": max(v)} for k, v in groups.items()]
    return sorted(rows, key=lambda r: -r["count"])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    nums = [a for a in argv if a.isdigit()]
    rows = census(int(nums[0]) if nums else 24)
    if "--json" in argv:
        sys.stdout.write(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
        return 0
    L = [f"ERROR CENSUS: {len(rows)} distinct error signatures, {sum(r['count'] for r in rows)} occurrences"]
    for r in rows[:40]:
        L.append(f"{r['count']:>5}x  {r['source']}  first {r['first'][:16]}  last {r['last'][:16]}\n        {r['signature']}")
    sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
