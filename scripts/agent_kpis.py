#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-agent performance, measured from the factory's own logs (2026-11-06). Read-only.

    python scripts/agent_kpis.py            # table
    python scripts/agent_kpis.py --json

Sources: data/agent_executions.jsonl (one row per LLM execution), data/agent_tasks.jsonl (the daily chain: done / failed /
stopped / blocked per step), data/ai_cost_log.jsonl (tokens and cost). Why this exists: before adding any agent the
question is "which measured bottleneck does it remove?". The first reading (2026-11-06) showed no capacity or cost problem
(224 executions, $0.0694 in total) and one quality problem: the QA agent stops about a third of the Scout briefs.

Flags (never guesses): IDLE (no activity for 7 days; expected while new products are frozen), DEGRADED (at least 8 tasks and
more than 25% failed or stopped), CONTRACT_FAILURES (the step contract was not met), TIMEOUTS.
"""
from __future__ import annotations

import collections
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _jsonl(path):
    out = []
    try:
        for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def _ts(v):
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None


def compute(executions, tasks, costs, now=None, idle_days=7, min_tasks=8, bad_rate=0.25):
    now = now or datetime.now(timezone.utc)
    ag = collections.defaultdict(lambda: {"executions": 0, "ms": [], "tokens": 0, "tasks": collections.Counter(), "last": None,
                                          "contract_failures": 0, "timeouts": 0, "stop_reasons": collections.Counter()})
    for r in executions:
        a = r.get("agent")
        if not a:
            continue
        x = ag[a]
        x["executions"] += 1
        if r.get("duration_ms"):
            x["ms"].append(r["duration_ms"])
        x["tokens"] += int(r.get("prompt_tokens") or 0) + int(r.get("completion_tokens") or 0)
        t = _ts(r.get("started_at"))
        if t and (x["last"] is None or t > x["last"]):
            x["last"] = t
    for r in tasks:
        a = r.get("agent")
        if not a:
            continue
        x = ag[a]
        st = r.get("status")
        x["tasks"][st] += 1
        err = str(r.get("error") or "")
        if st == "failed" and "contract" in err.lower():
            x["contract_failures"] += 1
        if st == "failed" and "timed out" in err.lower():
            x["timeouts"] += 1
        if st == "stopped":
            x["stop_reasons"][err[:70]] += 1
        t = _ts(r.get("at"))
        if t and (x["last"] is None or t > x["last"]):
            x["last"] = t
    rows = []
    for a, x in sorted(ag.items()):
        done = x["tasks"].get("done", 0)
        bad = x["tasks"].get("failed", 0) + x["tasks"].get("stopped", 0)
        n = done + bad
        flags = []
        if x["last"] is None or now - (x["last"] if x["last"].tzinfo else x["last"].replace(tzinfo=timezone.utc)) > timedelta(days=idle_days):
            flags.append("IDLE")
        if n >= min_tasks and bad / n > bad_rate:
            flags.append("DEGRADED")
        if x["contract_failures"]:
            flags.append("CONTRACT_FAILURES")
        if x["timeouts"]:
            flags.append("TIMEOUTS")
        ms = sorted(x["ms"])
        rows.append({"agent": a, "executions": x["executions"], "tasks_done": done, "tasks_failed": x["tasks"].get("failed", 0),
                     "tasks_stopped": x["tasks"].get("stopped", 0), "task_success_rate": round(done / n, 2) if n else None,
                     "median_ms": ms[len(ms) // 2] if ms else None, "tokens": x["tokens"],
                     "contract_failures": x["contract_failures"], "timeouts": x["timeouts"],
                     "last_activity": x["last"].isoformat(timespec="minutes") if x["last"] else None,
                     "top_stop_reason": (x["stop_reasons"].most_common(1)[0][0] if x["stop_reasons"] else None), "flags": flags})
    return {"agents": rows, "llm_calls": len(costs), "total_cost_usd": round(sum(float(c.get("cost_usd") or 0) for c in costs), 4),
            "total_tokens": sum(int(c.get("total_tokens") or 0) for c in costs)}


def gather(now=None):
    return compute(_jsonl(DATA / "agent_executions.jsonl"), _jsonl(DATA / "agent_tasks.jsonl"), _jsonl(DATA / "ai_cost_log.jsonl"), now)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    d = gather()
    if "--json" in argv:
        sys.stdout.write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")
        return 0
    L = [f"AGENTS: {d['llm_calls']} LLM calls, {d['total_tokens']} tokens, ${d['total_cost_usd']} in total", ""]
    for r in d["agents"]:
        L.append(f"{r['agent']:10} exec {r['executions']:4} | tasks done {r['tasks_done']:3} failed {r['tasks_failed']:2} stopped {r['tasks_stopped']:2} "
                 f"| success {r['task_success_rate']} | median {r['median_ms']} ms | last {r['last_activity']} | {','.join(r['flags']) or 'ok'}")
        if r["top_stop_reason"]:
            L.append(f"           most common stop: {r['top_stop_reason']}")
    sys.stdout.buffer.write(("\n".join(L) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
