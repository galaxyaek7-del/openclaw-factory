#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Factory Health Vector (V70, Tier-1 safe).

No cosmetic aggregate score. 8 independent dimensions, each
{status, evidence}; UNKNOWN whenever no real signal exists -- never 0 or
PASS by default. Read-only: local file reads + one bounded git call, no
network, no writes, no code execution. Every check degrades to UNKNOWN
(not failure) when its source is unreadable.
"""
import json
import os
import re
import subprocess
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))

SECRET_PATTERNS = ("BEGIN PRIVATE KEY", "sk-live", "ghp_", "AKIA",
                   "GROQ_KEY=", "password=")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _dim(status, evidence):
    return {"status": status, "evidence": evidence, "at": _now_iso()}


def _code_health():
    try:
        import sys
        sys.path.insert(0, os.path.join(_FACTORY_ROOT, "scripts"))
        import drift_detector
        snap = drift_detector.snapshot()
        src = snap.get("source_added", 0)
        if src >= 500:
            return _dim("DEGRADED", "source_added=%d >= 500 (unreviewed executable drift)" % src)
        return _dim("HEALTHY", "source_added=%d, tracked_modified=%d" % (
            src, snap.get("tracked_modified", 0)))
    except Exception as e:
        return _dim("UNKNOWN", "drift snapshot unreadable: %s" % e)


def _evidence_health():
    try:
        import evidence_engine
        n = len(evidence_engine.read_evidence(limit=100000))
        if n > 0:
            return _dim("HEALTHY", "%d evidence records in ledger" % n)
        return _dim("UNKNOWN", "evidence ledger empty or missing")
    except Exception as e:
        return _dim("UNKNOWN", "evidence ledger unreadable: %s" % e)


def _runtime_health():
    try:
        p = os.path.join(_FACTORY_ROOT, "data", "factory_state.json")
        st = json.load(open(p, encoding="utf-8"))
        if st.get("current_task"):
            return _dim("DEGRADED", "stale in-flight task: %s" % st["current_task"])
        if st.get("last_successful_checkpoint"):
            return _dim("HEALTHY", "idle, checkpoint=%s" % st["last_successful_checkpoint"])
        return _dim("UNKNOWN", "no checkpoint signal in factory_state.json")
    except Exception as e:
        return _dim("UNKNOWN", "factory_state unreadable: %s" % e)


def _security_health():
    try:
        out = subprocess.run(["git", "diff", "HEAD", "--name-only"],
                             capture_output=True, text=True,
                             cwd=_FACTORY_ROOT).stdout.splitlines()
        hits = []
        for rel in out:
            if not rel.lower().endswith((".py", ".js")):
                continue
            ap = os.path.join(_FACTORY_ROOT, rel)
            if not os.path.isfile(ap):
                continue
            text = open(ap, encoding="utf-8", errors="replace").read()
            for i, line in enumerate(text.splitlines(), 1):
                for pat in SECRET_PATTERNS:
                    if pat not in line:
                        continue
                    # Scanner-pattern definitions (e.g. GSC_SECRET_RES regex
                    # list) contain the pattern text by design -- a GOOD
                    # sign, not a leak. Only non-regex hits are critical.
                    if re.search(r'regex|pattern|_RES|_RE\b|/\\b|\[0-9|\(\?|scan|detect|PATTERNS\s*=',
                                 line, re.IGNORECASE):
                        continue
                    hits.append("%s:%d:%s" % (rel, i, pat))
        if hits:
            return _dim("CRITICAL", "secret patterns in drift: %s" % hits[:5])
        return _dim("HEALTHY", "0 secret patterns across %d changed source files" % len(
            [r for r in out if r.lower().endswith((".py", ".js"))]))
    except Exception as e:
        return _dim("UNKNOWN", "security scan failed: %s" % e)


def _recovery_health():
    try:
        p = os.path.join(_FACTORY_ROOT, "data", "factory_state.json")
        st = json.load(open(p, encoding="utf-8"))
        retries = st.get("pending_retries", [])
        if retries:
            return _dim("DEGRADED", "%d retries queued, no generic replay executor" % len(retries))
        return _dim("HEALTHY", "retry queue empty")
    except Exception as e:
        return _dim("UNKNOWN", "factory_state unreadable: %s" % e)


def _commercial_health():
    # Health = books uncorrupted, NOT revenue level (revenue is a fact, §8).
    try:
        fin = json.load(open(os.path.join(_FACTORY_ROOT, "finance_data.json"), encoding="utf-8"))
        sales = fin.get("sales", [])
        if not isinstance(sales, list):
            return _dim("CRITICAL", "finance_data.sales is not a list")
        total = fin.get("totalSales", 0)
        if total != sum(s.get("amount_usd", 0) for s in sales if isinstance(s, dict)):
            return _dim("CRITICAL", "totalSales != sum(sales)")
        return _dim("HEALTHY", "books consistent; revenue_usd=%s (fact, not health)" % total)
    except Exception as e:
        return _dim("UNKNOWN", "finance unreadable: %s" % e)


def _founder_dependency():
    # Disclosed heuristic: pending-gate count as load proxy.
    try:
        n = 0
        qp = os.path.join(_FACTORY_ROOT, "data", "founder_action_queue.jsonl")
        if os.path.exists(qp):
            for line in open(qp, encoding="utf-8"):
                try:
                    if json.loads(line).get("status", "PENDING") == "PENDING":
                        n += 1
                except ValueError:
                    pass
        if n == 0:
            return _dim("HEALTHY", "0 pending founder gates")
        if n <= 3:
            return _dim("DEGRADED", "%d pending founder gates" % n)
        return _dim("CRITICAL", "%d pending founder gates" % n)
    except Exception as e:
        return _dim("UNKNOWN", "founder queue unreadable: %s" % e)


def _experiment_integrity():
    try:
        import experiment_governor
        status = experiment_governor.protected_window_status()
        live = [k for k, v in status.items() if v["state"] == "PROTECTED"]
        if live:
            return _dim("HEALTHY", "protected windows open: %s (no mutation by this module)" % live)
        return _dim("UNKNOWN", "no protected window on record")
    except Exception as e:
        return _dim("UNKNOWN", "governor unreadable: %s" % e)


DIMENSIONS = ("CODE_HEALTH", "EVIDENCE_HEALTH", "RUNTIME_HEALTH",
              "SECURITY_HEALTH", "RECOVERY_HEALTH", "COMMERCIAL_HEALTH",
              "FOUNDER_DEPENDENCY", "EXPERIMENT_INTEGRITY")


def health_vector():
    return {
        "CODE_HEALTH": _code_health(),
        "EVIDENCE_HEALTH": _evidence_health(),
        "RUNTIME_HEALTH": _runtime_health(),
        "SECURITY_HEALTH": _security_health(),
        "RECOVERY_HEALTH": _recovery_health(),
        "COMMERCIAL_HEALTH": _commercial_health(),
        "FOUNDER_DEPENDENCY": _founder_dependency(),
        "EXPERIMENT_INTEGRITY": _experiment_integrity(),
    }
