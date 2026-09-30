#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Experiment Governor (V70, Tier-1 safe).

Central guard for live experiments. Read-only + raise-only: it never writes
to experiment records, never polls, never publishes. Two jobs:

1. PROTECTED registry: a live measurement window must not be mutated,
   re-polled out-of-protocol, re-run, parallel-probed, or finally
   concluded before its close. `assert_safe_to_mutate(target)` raises
   ExperimentProtectedError on any attempt; tick code can call it as a
   one-line guard (wiring into loops is Tier-2, proposed not applied).
2. Founder-dependency classification (§3): every factory action is typed
   A (must stay founder gate) / B (safe to automate) / C (needs external
   approval) / D (must be blocked outright).

EXP-SUB-001 is PROTECTED until 2026-10-02T03:00Z (per
data/nostr_sub_observation.json + data/v64_selection.json, re-read live;
a data file taking precedence over this module's fallback constant).
"""
import json
import os
from datetime import datetime, timezone

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))

FALLBACK_PROTECTED = {
    "EXP-SUB-001": {
        "window_close": "2026-10-02T03:00:00+00:00",
        "reason": "live nostr kind:1 exposure probe (GF-B10-01); response = replies/intent",
        "source": "data/nostr_sub_observation.json + data/v64_selection.json",
    },
}

# §3 classification. B = the ONLY class the factory may execute itself,
# and only via the Tier-1 whitelist (read-only / record / report).
CLASS_A_FOUNDER_GATE = {
    "spend", "payment", "publish", "external_post", "account_creation",
    "credential_use", "contract_sign", "price_change", "offer_change",
    "experiment_close_verdict", "strategy_choice",
}
CLASS_C_EXTERNAL_APPROVAL = {
    "paddle_onboarding", "channel_credential", "platform_limit_raise",
    "legal_review", "tax_registration",
}
CLASS_D_FORBIDDEN = {
    "secret_exfiltration", "evidence_rewrite", "history_rewrite",
    "parallel_probe_during_window", "midwindow_variable_change",
    "conclusion_before_close", "blind_retry_external",
}
CLASS_B_AUTOMATABLE = {
    "health_check", "drift_detect", "reconciliation_read", "test_execution",
    "evidence_normalization_read", "stale_state_detect", "recovery_triage_read",
    "report_generation", "consistency_check", "snapshot_record",
    "monitoring_read", "drift_snapshot",
}


class ExperimentProtectedError(RuntimeError):
    """Raised when code attempts a gated operation inside a live window."""


def _parse_close(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError, TypeError):
        return None


def protected_experiments():
    """Live registry: file-backed where possible, fallback constant otherwise."""
    reg = {}
    for exp_id, fb in FALLBACK_PROTECTED.items():
        close = fb["window_close"]
        source = fb["source"] + " (fallback constant)"
        obs_path = os.path.join(_FACTORY_ROOT, "data", "nostr_sub_observation.json")
        try:
            with open(obs_path, encoding="utf-8") as f:
                obs = json.load(f)
            for key in ("window_close", "window_closes", "window_end", "close_at", "stop"):
                if obs.get(key):
                    parsed = _parse_close(obs[key])
                    if parsed:
                        close = parsed.isoformat()
                        source = "data/nostr_sub_observation.json[%s] (live)" % key
                        break
        except (OSError, ValueError):
            pass
        reg[exp_id] = {"window_close": close, "reason": fb["reason"], "source": source}
    return reg


def protected_window_status(now=None):
    """Is any experiment window open right now? Read-only."""
    now = now or datetime.now(timezone.utc)
    out = {}
    for exp_id, rec in protected_experiments().items():
        close = _parse_close(rec["window_close"])
        out[exp_id] = {
            "state": "PROTECTED" if (close and now < close) else "CLOSED",
            "window_close": rec["window_close"],
            "reason": rec["reason"],
            "source": rec["source"],
        }
    return out


def assert_safe_to_mutate(target, operation="mutate", now=None):
    """Guard: raise ExperimentProtectedError if target is a protected
    experiment (or its records/variables) inside an open window.
    Pure check -- writes nothing, touches nothing."""
    status = protected_window_status(now=now)
    tid = str(target).upper()
    for exp_id, rec in status.items():
        if rec["state"] == "PROTECTED" and (exp_id in tid or tid in exp_id
                                            or "EXPERIMENT" in tid or "WINDOW" in tid):
            raise ExperimentProtectedError(
                "%s on %s blocked: %s window open until %s (%s)" % (
                    operation, target, exp_id, rec["window_close"], rec["reason"]))
    return {"ok": True, "checked_against": list(status)}


def classify_action(action):
    """§3 A/B/C/D typing for a factory action name. Static, disclosed."""
    a = str(action).lower()
    if a in CLASS_D_FORBIDDEN:
        return "D_FORBIDDEN"
    if a in CLASS_A_FOUNDER_GATE:
        return "A_FOUNDER_GATE"
    if a in CLASS_C_EXTERNAL_APPROVAL:
        return "C_EXTERNAL_APPROVAL"
    if a in CLASS_B_AUTOMATABLE:
        return "B_AUTOMATABLE"
    return "UNKNOWN"
