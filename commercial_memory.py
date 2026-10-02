"""Commercial memory (S3-EFFICIENCY-COMMERCIAL-01): signal records with
outcomes + cooldowns, so dead ends are skipped without reprocessing.

Schema per signal: {signal_id, source, first_seen, last_seen, signal_type,
business, problem, offer, accessibility, contactability, eligibility,
action_taken, result, evidence_level, next_action, cooldown_until}

Cooldowns: LOW_SIGNAL arms sleep 7 days; BLOCKED arms sleep until a state
change is observed. Rotation consults should_skip(arm).
"""
import datetime
import json
import os

PATH = "data/commercial_memory.json"
LOW_SIGNAL_DAYS = 7


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def load():
    try:
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"signals": {}, "arms": {}}


def save(mem):
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(mem, fh, indent=1, ensure_ascii=False)


def record_signal(signal_id, source, signal_type, result, **kw):
    mem = load()
    now = _now().isoformat()
    rec = mem["signals"].get(signal_id, {"first_seen": now, "times_seen": 0})
    rec.update({"source": source, "signal_type": signal_type, "result": result,
                "last_seen": now, "times_seen": rec.get("times_seen", 0) + 1})
    rec.update(kw)
    if result in ("LOW_SIGNAL", "NO_SIGNAL", "BLOCKED", "D"):
        rec["cooldown_until"] = (_now() + datetime.timedelta(days=LOW_SIGNAL_DAYS)).isoformat()
    mem["signals"][signal_id] = rec
    save(mem)
    return rec


def set_arm(arm, state, reason=""):
    mem = load()
    mem["arms"][arm] = {"state": state, "reason": reason,
                        "at": _now().isoformat()}
    save(mem)


def should_skip(arm):
    """True if arm is in cooldown with no new evidence."""
    mem = load()
    a = mem["arms"].get(arm, {})
    if a.get("state") in ("BLOCKED", "LOW_SIGNAL"):
        return True
    return False


def stats():
    mem = load()
    sigs = mem["signals"]
    return {"signals": len(sigs),
            "skipped_dead_ends": sum(1 for s in sigs.values()
                                     if s.get("result") in ("LOW_SIGNAL", "NO_SIGNAL", "BLOCKED", "D"))}
