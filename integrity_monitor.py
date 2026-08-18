#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append-only ledger integrity detection (Security P1 C3, 2026-08-18).

The founder's approved P1 bundle item C3: "SHA-256 baseline for ledger
files; wire drift into existing resilience_monitor; don't change ledger
content; don't create financial data."

Why a hash chain over a prefix, not a whole-file SHA-256:
  This factory's ledgers are append-only JSONL -- a plain whole-file hash
  baseline would false-positive on every legitimate append (and a
  rewritten-in-place file like finance_data.json would false-positive on
  every legitimate write). So the baseline stores, per ledger: the number
  of lines baselined and a SHA-256 hash CHAIN over exactly that prefix
  (each line's digest is chained through the previous line's digest, the
  classic append-only-log integrity construction). Verification re-walks
  only the already-baselined prefix:
    - prefix matches  -> the baselined content is byte-for-byte intact;
      the baseline then ADVANCES to cover the now-current full content
      (so recently-appended lines get protected from the next check on).
    - prefix shorter  -> real truncation.
    - prefix differs  -> real modification of already-baselined content.
  A legitimate append is NEVER flagged; a tamper with existing content
  or a truncation ALWAYS is (from the moment that content was baselined).

Honestly scoped:
  - DEFAULT_LEDGERS lists only genuinely append-only JSONL ledgers
    (each writer verified to open with mode "a"/append semantics).
    Rewritten-in-place files (finance_data.json, config/reality.json,
    evolution_queue_state.json, paddle_products.json, seo_pages.json,
    knowledge_graph_snapshot.json) are deliberately EXCLUDED.
  - Generation-only: this module only PRODUCES the drift signal. The
    storage/display side (data/incidents.jsonl + Telegram) was already
    proven real by resilience_monitor.py; the signal is folded into its
    _classify_ledger_integrity() aggregator below.
  - Never writes to any ledger, never creates financial data. Its only
    write is its OWN baseline state file (data/ledger_integrity_baseline.
    json), which holds hashes + line counts only -- no ledger content.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

FACTORY_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BASELINE_PATH = os.path.join(FACTORY_DIR, "data", "ledger_integrity_baseline.json")

_D = lambda name: os.path.join(FACTORY_DIR, "data", name)

# Append-only JSONL ledgers -- every writer below was verified (2026-08-18)
# to append (mode "a" / appendFileSync), never rewrite in place:
DEFAULT_LEDGERS = (
    _D("decisions.jsonl"),               # decision_engine/store.py::_append
    _D("sales_ledger.jsonl"),            # channels/ledger.py::append_event
    _D("incidents.jsonl"),               # resilience_monitor.py::_append_incident
    _D("board_meetings.jsonl"),          # board meetings recorder
    _D("market_evidence.jsonl"),         # market_evidence.py::record_evidence
    _D("department_events.jsonl"),       # department_events.py
    _D("executive_orchestrator_events.jsonl"),  # executive_orchestrator.py::_append_event
    _D("recovery_actions.jsonl"),        # factory_loop.js appendFileSync
    _D("lead_discovery_events.jsonl"),   # lead_discovery.py::_append_jsonl
    _D("opportunity_rotation_events.jsonl"),   # opportunity_rotation_engine.py::_append_jsonl
    _D("verification_attempts.jsonl"),   # multi_source_intelligence/manual_verification.py
    _D("council_recommendations.jsonl"), # galaxy_council.py::record_council_recommendation
    _D("executive_directives.jsonl"),    # executive_brain.py::_append_ledger
    _D("evidence_ledger.jsonl"),         # evidence_engine.py::record_evidence
    _D("generated_business_blueprints.jsonl"),  # autonomous_business_builder.py
    _D("health_snapshots.jsonl"),        # lib/health_trend.js appendFileSync
)

STATUS_CLEAN = "CLEAN"
STATUS_DRIFT = "DRIFT"
STATUS_TRUNCATED = "TRUNCATED"
STATUS_MISSING = "MISSING"
STATUS_NOT_BASELINED = "NOT_BASELINED"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _read_baseline(path):
    if not os.path.exists(path):
        return {"version": 1, "ledgers": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("ledgers"), dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"version": 1, "ledgers": {}}


def _write_baseline(state, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _chain_hash(lines):
    """SHA-256 hash chain over an iterable of raw line bytes: each line's
    digest is computed over the previous digest + the line, so a single
    line change anywhere in the chain changes every subsequent digest."""
    h = b""
    for line in lines:
        h = hashlib.sha256(h + line).digest()
    return h.hex()


def _read_lines_until(path, max_lines):
    """Reads up to max_lines raw lines (including newline bytes) -- the
    exact byte-prefix semantics the chain is computed over. A ledger line
    is whatever the file holds (valid or not); integrity is byte-level."""
    lines = []
    with open(path, "rb") as f:
        for i, line in enumerate(f):
            if max_lines is not None and i >= max_lines:
                break
            lines.append(line)
    return lines


def build_baseline(ledgers=None, baseline_path=None):
    """(Re)builds the baseline for every currently-existing ledger --
    trust is established on the FIRST run by definition (the security
    audit itself is what establishes the trusted starting point). Only
    ledgers present on disk are baselined; a missing one is skipped, not
    an error. Returns the updated state dict."""
    ledgers = list(ledgers if ledgers is not None else DEFAULT_LEDGERS)
    path = baseline_path or DEFAULT_BASELINE_PATH
    state = _read_baseline(path)
    for ledger in ledgers:
        ledger = str(ledger)
        if not os.path.exists(ledger):
            continue
        lines = _read_lines_until(ledger, None)
        state["ledgers"][ledger] = {
            "lines": len(lines),
            "chain": _chain_hash(line for line in lines),
            "baselined_at": _now_iso(),
        }
    _write_baseline(state, path)
    return state


def check_ledger_integrity(ledgers=None, baseline_path=None):
    """Per-ledger integrity verdict against the stored baseline, and the
    one real write path for the baseline itself (advance-on-clean).

    Status vocabulary (Truth First, ADR-160 terms):
      NOT_BASELINED -- no baseline entry yet; one is established right
        now so the NEXT check is a real one. Never reported as clean.
      CLEAN         -- baselined prefix byte-for-byte intact; baseline
        advanced to the full current content.
      TRUNCATED     -- file is shorter than the baselined prefix.
      DRIFT         -- baselined prefix no longer matches (real tamper).
      MISSING       -- baselined file no longer exists on disk.

    On DRIFT/TRUNCATED/MISSING the baseline is deliberately left
    untouched, so every subsequent check keeps reporting the same real
    finding (deduped by resilience_monitor's incident recorder)."""
    ledgers = list(ledgers if ledgers is not None else DEFAULT_LEDGERS)
    path = baseline_path or DEFAULT_BASELINE_PATH
    state = _read_baseline(path)
    results = []
    for ledger in ledgers:
        ledger = str(ledger)
        entry = state["ledgers"].get(ledger)
        if entry is None:
            if os.path.exists(ledger):
                lines = _read_lines_until(ledger, None)
                state["ledgers"][ledger] = {
                    "lines": len(lines),
                    "chain": _chain_hash(line for line in lines),
                    "baselined_at": _now_iso(),
                }
                results.append({
                    "path": ledger, "status": STATUS_NOT_BASELINED,
                    "baselined_lines": 0, "current_lines": len(lines),
                    "detail": "baseline just established -- next check is the first real one",
                    "data_available": False,
                })
            else:
                results.append({
                    "path": ledger, "status": STATUS_NOT_BASELINED,
                    "baselined_lines": 0, "current_lines": 0,
                    "detail": "ledger does not exist yet -- nothing to baseline",
                    "data_available": False,
                })
            continue

        if not os.path.exists(ledger):
            results.append({
                "path": ledger, "status": STATUS_MISSING,
                "baselined_lines": entry["lines"], "current_lines": 0,
                "detail": f"baselined ledger file is missing from disk (was {entry['lines']} lines at {entry['baselined_at']})",
                "data_available": True,
            })
            continue

        current_lines = _read_lines_until(ledger, None)
        prefix = current_lines[: entry["lines"]]
        if len(prefix) < entry["lines"]:
            results.append({
                "path": ledger, "status": STATUS_TRUNCATED,
                "baselined_lines": entry["lines"], "current_lines": len(current_lines),
                "detail": f"ledger truncated: {entry['lines']} baselined lines, only {len(current_lines)} now on disk",
                "data_available": True,
            })
            continue

        if _chain_hash(prefix) != entry["chain"]:
            results.append({
                "path": ledger, "status": STATUS_DRIFT,
                "baselined_lines": entry["lines"], "current_lines": len(current_lines),
                "detail": f"ledger content drift: baselined prefix ({entry['lines']} lines, hashed {entry['baselined_at']}) no longer matches -- real tamper or corruption",
                "data_available": True,
            })
            continue

        # Clean: advance the baseline to protect newly appended lines.
        state["ledgers"][ledger] = {
            "lines": len(current_lines),
            "chain": _chain_hash(line for line in current_lines),
            "baselined_at": _now_iso(),
        }
        results.append({
            "path": ledger, "status": STATUS_CLEAN,
            "baselined_lines": entry["lines"], "current_lines": len(current_lines),
            "detail": "ledger append-only content intact",
            "data_available": True,
        })

    _write_baseline(state, path)
    return results


def assess_ledger_integrity(ledgers=None, baseline_path=None):
    """Aggregated read view -- per-ledger verdicts plus a real summary
    (counts per status). Never a fabricated composite score."""
    results = check_ledger_integrity(ledgers=ledgers, baseline_path=baseline_path)
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {
        "ledgers": results,
        "summary": counts,
        "generated_at": _now_iso(),
    }


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(assess_ledger_integrity(), ensure_ascii=False, indent=2))