#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Galaxy Forge — Safe Mode (Global Trust & Resilience Layer, Round 2,
2026-07-29).

Generalizes this factory's existing per-arm isolation pattern
(`channels/base_arm.py`'s `_consecutive_failures`/`COOLDOWN_THRESHOLD`
circuit breaker, `channels/publish_protection.py`'s per-arm cooldown +
global emergency stop) to real, named subsystems -- so an unstable
subsystem can be isolated on its own without halting the rest of the
company, per the founder's directive: "stop only the affected
subsystem, keep the rest running, never allow cascading failures."

Real, named subsystems only -- never a generic/arbitrary name, so this
stays a small, auditable set rather than an open-ended registry:

  ai_generation       -- Groq/AI-provider-backed content generation.
  marketplace_publishing -- real marketplace publishing. Deliberately NOT
                            given its own independent flag here: its real
                            signal already exists and is load-bearing --
                            channels/publish_protection.py's own global
                            emergency stop. is_subsystem_safe_mode() reads
                            that real state directly rather than
                            duplicating a second, potentially-diverging
                            flag for the same real concern.
  market_intelligence -- niche/opportunity discovery and scoring.

Same "ledger vs mutable state" split as every other module here:
data/safe_mode_state.json (mutable, atomic tmp-file-then-rename write,
same pattern as factory_state.py/publish_protection.py) holds the two
subsystems with their own independent flag (ai_generation,
market_intelligence). Never auto-clears -- only a real founder action or
a human-reviewed session calls clear_subsystem_unstable(), matching this
factory's standing "human-gated always" precedent for anything that
halts/resumes real automation.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "safe_mode_state.json"

# Subsystems with their own independent flag in data/safe_mode_state.json.
# marketplace_publishing is deliberately excluded -- see module docstring.
INDEPENDENTLY_TRACKED_SUBSYSTEMS = ("ai_generation", "market_intelligence")

# Every real subsystem this module knows about (for list_safe_mode_status()).
ALL_SUBSYSTEMS = ("ai_generation", "marketplace_publishing", "market_intelligence")


def _now():
    return datetime.now(timezone.utc)


def _default_state():
    return {name: {"unstable": False, "reason": None, "since": None, "triggered_by": None}
            for name in INDEPENDENTLY_TRACKED_SUBSYSTEMS}


def _load_state(state_path=None):
    """Never raises. A missing or corrupt file reads as the safe default,
    same discipline as factory_state.py::load_state()."""
    p = Path(state_path) if state_path else DEFAULT_STATE_PATH
    if not p.exists():
        return _default_state()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()

    state = _default_state()
    for name in INDEPENDENTLY_TRACKED_SUBSYSTEMS:
        if isinstance(data.get(name), dict):
            state[name].update(data[name])
    return state


def _save_state(state, state_path=None):
    """Atomic write -- exact pattern as factory_state.py::save_state()."""
    p = Path(state_path) if state_path else DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = p.parent / f"{p.name}.tmp-{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, p)
    return state


def mark_subsystem_unstable(name, reason, triggered_by="system", state_path=None):
    """Marks one real, named subsystem unstable -- never the whole
    company. Raises ValueError for marketplace_publishing (use
    channels.publish_protection.trigger_emergency_stop() instead -- that
    IS this subsystem's real signal) or any unrecognized name."""
    if name == "marketplace_publishing":
        raise ValueError(
            "marketplace_publishing has no independent Safe Mode flag -- "
            "use channels.publish_protection.trigger_emergency_stop() instead"
        )
    if name not in INDEPENDENTLY_TRACKED_SUBSYSTEMS:
        raise ValueError(f"unrecognized subsystem: {name!r}, expected one of {INDEPENDENTLY_TRACKED_SUBSYSTEMS}")

    state = _load_state(state_path)
    state[name] = {"unstable": True, "reason": reason, "since": _now().isoformat(), "triggered_by": triggered_by}
    _save_state(state, state_path)
    return state[name]


def clear_subsystem_unstable(name, state_path=None):
    if name == "marketplace_publishing":
        raise ValueError(
            "marketplace_publishing has no independent Safe Mode flag -- "
            "use channels.publish_protection.clear_emergency_stop() instead"
        )
    if name not in INDEPENDENTLY_TRACKED_SUBSYSTEMS:
        raise ValueError(f"unrecognized subsystem: {name!r}, expected one of {INDEPENDENTLY_TRACKED_SUBSYSTEMS}")

    state = _load_state(state_path)
    state[name] = {"unstable": False, "reason": None, "since": None, "triggered_by": None}
    _save_state(state, state_path)
    return state[name]


def is_subsystem_safe_mode(name, state_path=None):
    """Real per-subsystem check. marketplace_publishing reads
    channels/publish_protection.py's own real global emergency-stop state
    directly -- never a second, potentially-diverging flag for the same
    real concern."""
    if name == "marketplace_publishing":
        from channels import publish_protection
        status = publish_protection.list_publish_protection_status()
        return bool(status["global"]["emergency_stopped"])
    if name not in INDEPENDENTLY_TRACKED_SUBSYSTEMS:
        raise ValueError(f"unrecognized subsystem: {name!r}, expected one of {ALL_SUBSYSTEMS}")

    state = _load_state(state_path)
    return bool(state[name]["unstable"])


def list_safe_mode_status(state_path=None):
    """Mission Control read view -- real status for every named
    subsystem, marketplace_publishing included via the real passthrough
    above (not duplicated storage)."""
    from channels import publish_protection

    state = _load_state(state_path)
    protection_status = publish_protection.list_publish_protection_status()
    marketplace_unstable = bool(protection_status["global"]["emergency_stopped"])

    return {
        "ai_generation": state["ai_generation"],
        "market_intelligence": state["market_intelligence"],
        "marketplace_publishing": {
            "unstable": marketplace_unstable,
            "reason": protection_status["global"]["emergency_reason"],
            "since": protection_status["global"]["emergency_stopped_at"],
            "triggered_by": protection_status["global"]["emergency_triggered_by"],
        },
        "any_subsystem_unstable": marketplace_unstable or state["ai_generation"]["unstable"] or state["market_intelligence"]["unstable"],
    }
