"""Galaxy Forge — session fact cache (P5).

Proven facts are stored with source/timestamp/state-hash/valid_until and
reused without recomputation until expiry or dependency change.
Backing file: data/fact_cache.json (derived, gitignored).
"""
import json
import os
import time

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "fact_cache.json")


def _load():
    try:
        with open(STATE, encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, STATE)


def remember(key, value, source, state_hash="", ttl_secs=86400):
    """Store a proven fact. Returns the record. Never raises."""
    try:
        data = _load()
        data[key] = {"value": value, "source": source,
                     "recorded_at": time.time(), "state_hash": state_hash,
                     "valid_until": time.time() + ttl_secs}
        _save(data)
        return data[key]
    except Exception:
        return {"value": value, "source": source}


def recall(key, state_hash=None):
    """Return (hit: bool, value). Miss on expiry or state change. Never raises."""
    try:
        rec = _load().get(key)
        if not rec:
            return False, None
        if time.time() > rec.get("valid_until", 0):
            return False, None
        if state_hash is not None and rec.get("state_hash") != state_hash:
            return False, None
        return True, rec.get("value")
    except Exception:
        return False, None
