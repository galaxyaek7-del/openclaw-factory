#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simulation Mode framework (ADR-153, 2026-07-30).

Generalizes this factory's own already-real dry_run discipline
(channels/base_arm.py's PublishResult.dry_run, distributor.py's
dry_run=True-by-default, reality.py's explicit "if event.get('dry_run')
is not False: continue" ground-truth filter at reality.py line 141) from
"don't really publish" to "don't really transact" -- purchases,
commissions, payouts, customer flows. No new safety pattern: the same
one, given a name and a config-only switch per the founder's own
Simulation-First directive ("architecture first, simulation second,
production activation only after the complete system is validated").

Every division's own simulation code calls is_simulation_mode() and
tags every simulated event with SIMULATION_TAG -- real ground-truth
ledgers (config/reality.json, finance_data.json, channels/ledger.py)
must never be written to by simulated code; simulated events live in
their own, separate ledger per division.
"""

import os

SIMULATION_TAG = {"simulation": True}

# Per-division env var names -- one flag per division, never a single
# global switch, so flipping one division to production never silently
# affects another (matches safe_mode.py's own "per-subsystem
# independence" principle, ADR-135).
_MODE_ENV_VARS = {
    "affiliate_commerce": "AFFILIATE_MODE",
}


def mode_env_var_for(division):
    return _MODE_ENV_VARS.get(division)


def is_simulation_mode(division):
    """True unless a real, explicit "production" value is set for this
    division's own env var. Defaults to simulation -- matches the
    directive's own ordering (simulation before production, never the
    reverse default)."""
    env_var = mode_env_var_for(division)
    if not env_var:
        return True  # unknown division: no real production path exists yet
    value = os.environ.get(env_var, "simulation").strip().lower()
    return value != "production"


def tag_simulated(record):
    """Returns a new dict with the real SIMULATION_TAG merged in --
    never mutates the caller's record, never omits the tag."""
    return {**record, **SIMULATION_TAG}
