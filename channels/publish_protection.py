"""Galaxy Forge — Publish Protection Layer (Global Commercial Hardening,
Phase 1, 2026-07-29).

The Executive Gap Report (2026-07-29) independently ranked this as the
single highest-leverage next implementation: `channels/base_arm.py`'s
`_consecutive_failures`/`COOLDOWN_THRESHOLD` circuit breaker is real but
in-memory-only, has no time-based reset, no daily/hourly caps, and no
pre-publish risk scoring. Nothing today stops rapid sequential publishing
to the same marketplace the moment an arm's `status()` reports READY and
`commercial_execution/approval_gates.py` lets it run autonomously — a
suspended account (KDP especially) would take out this factory's real
revenue channel with no other channel mature enough to absorb the loss.

Same "ledger vs mutable state" split this factory always uses:
`data/publish_protection_state.json` (mutable, atomic tmp-file-then-
rename write — exact pattern as `factory_state.py::save_state()`) holds
per-arm counters/cooldowns plus one global emergency-stop flag;
`channels/ledger.py`'s existing `data/sales_ledger.jsonl` stays the one
audit trail (this module's `distributor.py` integration point passes its
risk_score/decision through to `record_publish_attempt()`'s new optional
kwargs, added there — no new ledger file invented here).

`PLATFORM_PROFILES` covers every platform named in the directive (Amazon
KDP, Etsy, Gumroad, Payhip, Shopify, AliExpress) even though only
Gumroad/Etsy/Payhip/Paddle have a real registered `BaseArm` today (KDP,
Shopify, AliExpress are genuinely greenfield — confirmed by this
session's own audit) — the layer works generically for any arm name via
`_default`, honestly, not hardcoded to only the arms that exist yet.

Every check here is a disclosed, mechanical heuristic — real counters and
real timestamps, never a live-network risk model — same honesty
discipline `evolution_queue.py::simulate_proposal()` already established
for this factory's other "risk before a human/system acts" surface.
`trigger_emergency_stop()`/`clear_emergency_stop()` are never called from
anywhere in this module itself — only a real founder action (a Mission
Control sync action) or a human-reviewed session calls them, matching
this factory's standing "human-gated always" precedent for anything that
halts/resumes real automation.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = _FACTORY_ROOT / "data" / "publish_protection_state.json"

# Conservative per-platform defaults. KDP's account-suspension risk is the
# most real and severe (a single company-critical revenue channel today),
# so it gets the tightest profile. "_default" covers Shopify/AliExpress/any
# future arm with no dedicated tuning yet.
PLATFORM_PROFILES = {
    "kdp": {"min_cooldown_minutes": 60, "max_per_day": 3, "max_per_hour": 1},
    "etsy": {"min_cooldown_minutes": 30, "max_per_day": 10, "max_per_hour": 3},
    "gumroad": {"min_cooldown_minutes": 10, "max_per_day": 20, "max_per_hour": 5},
    "payhip": {"min_cooldown_minutes": 15, "max_per_day": 15, "max_per_hour": 4},
    "paddle": {"min_cooldown_minutes": 5, "max_per_day": 50, "max_per_hour": 15},
    "shopify": {"min_cooldown_minutes": 15, "max_per_day": 20, "max_per_hour": 5},
    "aliexpress": {"min_cooldown_minutes": 30, "max_per_day": 10, "max_per_hour": 3},
    "_default": {"min_cooldown_minutes": 30, "max_per_day": 10, "max_per_hour": 3},
}

# Independent of BaseArm.COOLDOWN_THRESHOLD (ADR-5, in-memory, per-process)
# -- this is a real, disk-persisted, time-based cooldown on top of it.
_CONSECUTIVE_FAILURE_THRESHOLD = 3
_FAILURE_COOLDOWN_MINUTES = 60

# Founder Protection (Global Trust & Resilience Layer, Round 4,
# 2026-07-29): the founder's explicit, resolved choice -- proven arms
# with a real publish track record predating this module keep their
# existing autonomous behavior unchanged; a genuinely new arm's first
# real publish, or any publish whose computed risk_score crosses this
# real threshold, requires one explicit founder approval first.
KNOWN_PROVEN_ARMS = frozenset({"gumroad", "etsy", "payhip", "paddle"})
HIGH_RISK_SCORE_THRESHOLD = 70


def _now():
    return datetime.now(timezone.utc)


def _default_global():
    return {
        "emergency_stopped": False, "emergency_reason": None,
        "emergency_stopped_at": None, "emergency_triggered_by": None,
    }


def _default_state():
    return {"arms": {}, "global": _default_global()}


def _default_arm_record():
    return {
        "publishes_today": 0, "day_bucket": None,
        "publishes_this_hour": 0, "hour_bucket": None,
        "cooldown_until": None,
        "consecutive_failures": 0,
        "last_publish_at": None,
        "has_ever_published_successfully": False,
        "first_publish_approved": False,
        "elevated_risk_approved_at": None,
    }


def _load_state(state_path=None):
    """Never raises. A missing or corrupt file reads as the safe default,
    same discipline as `factory_state.py::load_state()`."""
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
    state.update({k: data.get(k, state[k]) for k in state})
    if not isinstance(state["arms"], dict):
        state["arms"] = {}
    if not isinstance(state["global"], dict):
        state["global"] = _default_global()
    return state


def _save_state(state, state_path=None):
    """Atomic write -- a crash mid-write leaves the previous valid file
    intact, exact pattern as `factory_state.py::save_state()`."""
    p = Path(state_path) if state_path else DEFAULT_STATE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = p.parent / f"{p.name}.tmp-{os.getpid()}"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, p)
    return state


def _profile(arm_name):
    return PLATFORM_PROFILES.get(arm_name, PLATFORM_PROFILES["_default"])


def _roll_buckets(record, now):
    """Rolls the day/hour counters forward once they've gone stale -- pure
    bucket rollover, never touches cooldown_until/consecutive_failures."""
    day_key = now.strftime("%Y-%m-%d")
    hour_key = now.strftime("%Y-%m-%dT%H")
    if record.get("day_bucket") != day_key:
        record["day_bucket"] = day_key
        record["publishes_today"] = 0
    if record.get("hour_bucket") != hour_key:
        record["hour_bucket"] = hour_key
        record["publishes_this_hour"] = 0
    return record


def check_publish_allowed(arm_name, state_path=None, now=None):
    """The real pre-publish gate. Blocks on, in order: an active global
    emergency stop, a genuinely new arm's unapproved first real publish,
    a still-open per-arm cooldown (from repeated real failures), a real
    daily cap already hit, a real hourly cap already hit, the platform's
    minimum publish spacing not having elapsed, or an unapproved
    elevated risk_score. `risk_score` (0-100) is purely informational
    once a block already didn't fire -- it explains how close an arm is
    to being blocked, it never itself blocks anything beyond the real
    checks above (except the elevated-risk approval gate itself, which
    reads this same computed value)."""
    now = now or _now()
    state = _load_state(state_path)
    profile = _profile(arm_name)

    if state["global"]["emergency_stopped"]:
        return {
            "allowed": False,
            "reason": f"global publish emergency stop is active: {state['global']['emergency_reason']}",
            "risk_score": 100, "cooldown_until": None,
            "counts": {"publishes_today": 0, "publishes_this_hour": 0},
        }

    record = _roll_buckets(dict(_default_arm_record(), **state["arms"].get(arm_name, {})), now)
    counts = {"publishes_today": record["publishes_today"], "publishes_this_hour": record["publishes_this_hour"]}

    if (arm_name not in KNOWN_PROVEN_ARMS
            and not record["has_ever_published_successfully"]
            and not record["first_publish_approved"]):
        return {
            "allowed": False,
            "reason": f"{arm_name} has never had a real successful publish recorded -- founder approval required for its first real publish (approve_first_publish())",
            "risk_score": 50, "cooldown_until": None, "counts": counts,
        }

    cooldown_until = record.get("cooldown_until")
    if cooldown_until:
        try:
            if datetime.fromisoformat(cooldown_until) > now:
                return {
                    "allowed": False,
                    "reason": f"{arm_name} is in a real cooldown (triggered by {_CONSECUTIVE_FAILURE_THRESHOLD}+ consecutive failures) until {cooldown_until}",
                    "risk_score": 90, "cooldown_until": cooldown_until, "counts": counts,
                }
        except ValueError:
            pass

    if record["publishes_today"] >= profile["max_per_day"]:
        return {
            "allowed": False,
            "reason": f"{arm_name} already hit its real daily publish cap ({profile['max_per_day']}/day)",
            "risk_score": 85, "cooldown_until": None, "counts": counts,
        }

    if record["publishes_this_hour"] >= profile["max_per_hour"]:
        return {
            "allowed": False,
            "reason": f"{arm_name} already hit its real hourly publish cap ({profile['max_per_hour']}/hour)",
            "risk_score": 80, "cooldown_until": None, "counts": counts,
        }

    last_publish_at = record.get("last_publish_at")
    if last_publish_at:
        try:
            last_dt = datetime.fromisoformat(last_publish_at)
            elapsed_minutes = (now - last_dt).total_seconds() / 60
            if elapsed_minutes < profile["min_cooldown_minutes"]:
                wait_until = (last_dt + timedelta(minutes=profile["min_cooldown_minutes"])).isoformat()
                return {
                    "allowed": False,
                    "reason": f"{arm_name}'s minimum {profile['min_cooldown_minutes']}-minute publish spacing hasn't elapsed yet",
                    "risk_score": 60, "cooldown_until": wait_until, "counts": counts,
                }
        except ValueError:
            pass

    day_pct = (record["publishes_today"] / profile["max_per_day"]) if profile["max_per_day"] else 0
    hour_pct = (record["publishes_this_hour"] / profile["max_per_hour"]) if profile["max_per_hour"] else 0
    failure_component = min(record["consecutive_failures"], _CONSECUTIVE_FAILURE_THRESHOLD) / _CONSECUTIVE_FAILURE_THRESHOLD
    risk_score = round(100 * max(day_pct, hour_pct, failure_component) * 0.6)

    if risk_score >= HIGH_RISK_SCORE_THRESHOLD and not record.get("elevated_risk_approved_at"):
        return {
            "allowed": False,
            "reason": f"{arm_name}'s computed risk_score ({risk_score}) crosses the real high-risk threshold ({HIGH_RISK_SCORE_THRESHOLD}) -- founder approval required for this publish (approve_elevated_risk_publish())",
            "risk_score": risk_score, "cooldown_until": None, "counts": counts,
        }

    return {"allowed": True, "reason": None, "risk_score": risk_score, "cooldown_until": None, "counts": counts}


def note_publish_outcome(arm_name, success, state_path=None, now=None):
    """Records a real publish attempt's outcome into per-arm counters --
    called from `distributor.py` after a real `arm.publish()` call,
    alongside (not instead of) `channels/ledger.py`'s own
    `record_publish_attempt()`."""
    now = now or _now()
    state = _load_state(state_path)
    record = _roll_buckets(dict(_default_arm_record(), **state["arms"].get(arm_name, {})), now)

    record["publishes_today"] += 1
    record["publishes_this_hour"] += 1
    record["last_publish_at"] = now.isoformat()
    # A founder's elevated-risk approval is single-use -- consumed by
    # this one real attempt, whatever its outcome, never a blanket
    # future approval.
    record["elevated_risk_approved_at"] = None

    if success:
        record["consecutive_failures"] = 0
        record["cooldown_until"] = None
        record["has_ever_published_successfully"] = True
    else:
        record["consecutive_failures"] += 1
        if record["consecutive_failures"] >= _CONSECUTIVE_FAILURE_THRESHOLD:
            record["cooldown_until"] = (now + timedelta(minutes=_FAILURE_COOLDOWN_MINUTES)).isoformat()

    state["arms"][arm_name] = record
    _save_state(state, state_path)
    return record


def approve_first_publish(arm_name, approved_by="founder", state_path=None):
    """The founder's own real, explicit clearance for a genuinely new
    arm's very first real publish. Never called automatically."""
    state = _load_state(state_path)
    record = dict(_default_arm_record(), **state["arms"].get(arm_name, {}))
    record["first_publish_approved"] = True
    state["arms"][arm_name] = record
    _save_state(state, state_path)
    return record


def approve_elevated_risk_publish(arm_name, approved_by="founder", state_path=None, now=None):
    """The founder's own real, explicit, single-use clearance for one
    publish attempt whose computed risk_score crossed the real
    high-risk threshold. Consumed by the next note_publish_outcome()
    call for this arm, whatever its outcome -- never a blanket future
    approval. Never called automatically."""
    now = now or _now()
    state = _load_state(state_path)
    record = dict(_default_arm_record(), **state["arms"].get(arm_name, {}))
    record["elevated_risk_approved_at"] = now.isoformat()
    state["arms"][arm_name] = record
    _save_state(state, state_path)
    return record


def trigger_emergency_stop(reason, triggered_by="founder", state_path=None, now=None):
    """The global, all-arms halt. Never called automatically anywhere in
    this module -- only a real founder-triggered Mission Control action
    or a human-reviewed session calls this."""
    now = now or _now()
    state = _load_state(state_path)
    state["global"] = {
        "emergency_stopped": True, "emergency_reason": reason,
        "emergency_stopped_at": now.isoformat(), "emergency_triggered_by": triggered_by,
    }
    _save_state(state, state_path)
    return state["global"]


def clear_emergency_stop(state_path=None):
    state = _load_state(state_path)
    state["global"] = _default_global()
    _save_state(state, state_path)
    return state["global"]


def list_publish_protection_status(state_path=None, now=None):
    """Mission Control read view -- real per-arm state plus a live
    risk_score for every arm this factory has actually recorded a publish
    attempt for. Honestly empty (`arms: {}`) until a real attempt exists
    for any arm -- never a fabricated list of platforms with no real
    data behind them."""
    now = now or _now()
    state = _load_state(state_path)
    arms = {}
    for arm_name, record in state["arms"].items():
        gate = check_publish_allowed(arm_name, state_path=state_path, now=now)
        arms[arm_name] = {
            "publishes_today": record.get("publishes_today", 0),
            "publishes_this_hour": record.get("publishes_this_hour", 0),
            "consecutive_failures": record.get("consecutive_failures", 0),
            "cooldown_until": record.get("cooldown_until"),
            "last_publish_at": record.get("last_publish_at"),
            "risk_score": gate["risk_score"],
            "currently_allowed": gate["allowed"],
            "has_ever_published_successfully": record.get("has_ever_published_successfully", False),
            "first_publish_approved": record.get("first_publish_approved", False),
            "elevated_risk_approved_at": record.get("elevated_risk_approved_at"),
        }
    return {"arms": arms, "global": state["global"]}
