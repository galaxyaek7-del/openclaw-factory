# -*- coding: utf-8 -*-
"""Auditable evidence recording for tool invocations that affect a quality
decision.

Every record carries (directive-required fields):
    tool, version, product, input_class, result, timestamp, status,
    evidence_classification, failure (if applicable)

This is a *quality-evidence* log for tooling invocations, deliberately kept
separate from financial truth (finance_data.json), the frozen Evidence OS
baseline, and config/reality.json. It is append-only JSONL and never
mutates those protected sources. Writing to this log does NOT by itself
approve or reject anything — decisions are made by gate logic, not by the
presence of a log line.
"""

import json
import os

DEFAULT_EVIDENCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
DEFAULT_EVIDENCE_FILE = os.path.join(DEFAULT_EVIDENCE_DIR, "tool_invocations.jsonl")


def _utcnow_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def record_tool_invocation(entry, path=None):
    """Append one tool-invocation evidence record (append-only, JSONL).
    Returns the path actually written, or None on failure (callers must
    treat None as 'evidence write failed', never as a result change).

    Identity fields (B remediation, additive, fail-closed):
      source_id, product_type, artifact_version, run_id, release,
      config_hash, model_id, layer — all Optional, None dropped.
    Schema extension is backward-compatible: old lines without these
    fields remain valid; a reader treats absent identity as UNKNOWN."""
    path = path or DEFAULT_EVIDENCE_FILE
    record = {
        "tool": entry.get("tool"),
        "version": entry.get("version"),
        "product": entry.get("product"),
        "input_class": entry.get("input_class"),
        "result": entry.get("result"),
        "timestamp": entry.get("timestamp") or _utcnow_iso(),
        "status": entry.get("status"),
        "evidence_classification": entry.get(
            "evidence_classification", "OBSERVED"
        ),
        "failure": entry.get("failure"),
        # Additive identity binding (B remediation, gating-adjacent):
        "source_id": entry.get("source_id"),
        "product_type": entry.get("product_type"),
        "artifact_version": entry.get("artifact_version"),
        "run_id": entry.get("run_id"),
        "release": entry.get("release"),
        "config_hash": entry.get("config_hash"),
        "model_id": entry.get("model_id"),
        "layer": entry.get("layer"),
        # Adaptation signal (next gate): reliability advisory at invocation time
        "adaptation_reliability": entry.get("adaptation_reliability"),
    }
    # Drop None-valued keys so records stay compact and honest (a missing
    # failure field = genuinely no failure, not a hidden one).
    record = {k: v for k, v in record.items() if v is not None}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return path
    except Exception:
        return None


def read_evidence(path=None, limit=None):
    """Read back evidence records (pure read; never used as a gate)."""
    path = path or DEFAULT_EVIDENCE_FILE
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
            if limit is not None and len(out) >= limit:
                break
    return out


def summarize_evidence(source_id=None, artifact_version=None, run_id=None,
                       product_type=None, path=None, limit=1000):
    """Gating-adjacent QA aggregation over tool_invocations.jsonl.

    Pure read, fail-closed: missing/malformed/unavailable evidence never
    becomes PASS. Returns a summary dict with:
      evidence_count, malformed_skipped, per_tool {tool: last_verdict},
      overall (PASS|REVIEW|MISSING|STALE|UNKNOWN), stale_excluded,
      generated_at, source_id, artifact_version, run_id.
    A filter that matches zero records is MISSING, not PASS. Any
    non-ok status or passed is not True yields REVIEW. Stale is reported
    when a record's artifact_version mismatches the requested one.
    UNKNOWN when the ledger is absent/unreadable.
    """
    path = path or DEFAULT_EVIDENCE_FILE
    if not os.path.exists(path):
        from datetime import datetime, timezone as _tz
        return {
            "overall": "MISSING",
            "evidence_count": 0,
            "malformed_skipped": 0,
            "per_tool": {},
            "stale_excluded": 0,
            "generated_at": datetime.now(_tz.utc).isoformat(),
            "source_id": source_id,
            "artifact_version": artifact_version,
            "run_id": run_id,
            "reason": "no evidence ledger exists (MISSING)",
        }
    total = 0
    malformed = 0
    per_tool = {}
    stale = 0
    matched = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    malformed += 1
                    continue
                total += 1
                # Identity filtering (fail-closed: absent field = UNKNOWN, not match):
                if source_id is not None and rec.get("source_id") is not None and rec.get("source_id") != source_id:
                    continue
                # If caller filters by source_id but record has none, treat as
                # legacy line — include it but mark as unmatched identity (do not
                # count as stale; it is UNKNOWN binding).
                if run_id is not None and rec.get("run_id") is not None and rec.get("run_id") != run_id:
                    continue
                if product_type is not None and rec.get("product_type") is not None and rec.get("product_type") != product_type:
                    continue
                if artifact_version is not None and rec.get("artifact_version") is not None and rec.get("artifact_version") != artifact_version:
                    stale += 1
                    continue
                matched += 1
                tool = rec.get("tool") or "unknown"
                # Keep last verdict per tool (most recent wins):
                per_tool[tool] = {
                    "status": rec.get("status"),
                    "passed": (rec.get("result") or {}).get("passed") if isinstance(rec.get("result"), dict) else None,
                    "timestamp": rec.get("timestamp"),
                    "version": rec.get("version"),
                    "layer": rec.get("layer"),
                }
                if limit is not None and matched >= limit:
                    break
    except Exception:
        from datetime import datetime, timezone as _tz
        return {
            "overall": "UNKNOWN",
            "evidence_count": 0,
            "malformed_skipped": malformed,
            "per_tool": {},
            "stale_excluded": stale,
            "generated_at": datetime.now(_tz.utc).isoformat(),
            "source_id": source_id,
            "artifact_version": artifact_version,
            "run_id": run_id,
            "reason": "evidence ledger unreadable (UNKNOWN)",
        }
    from datetime import datetime, timezone as _tz
    if matched == 0:
        overall = "MISSING"
        reason = "no evidence records matched identity filter (MISSING)"
    else:
        # Strict: any non-ok or non-pass yields REVIEW (mirrors runner.overall_verdict):
        any_review = any(v.get("status") != "ok" or v.get("passed") is not True for v in per_tool.values())
        overall = "REVIEW" if any_review else "PASS"
        reason = "all matched tool records are clean PASS" if overall == "PASS" else "one or more tool records is not a clean pass (REVIEW)"
    return {
        "overall": overall,
        "evidence_count": matched,
        "total_lines": total,
        "malformed_skipped": malformed,
        "per_tool": per_tool,
        "stale_excluded": stale,
        "generated_at": datetime.now(_tz.utc).isoformat(),
        "source_id": source_id,
        "artifact_version": artifact_version,
        "run_id": run_id,
        "product_type": product_type,
        "reason": reason,
    }