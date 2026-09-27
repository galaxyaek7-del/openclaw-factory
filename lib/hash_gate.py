"""Galaxy Forge — hash-gated validation (P2).

A check recorded PASS with unchanged source + dependency hashes skips
full revalidation. Emits SKIPPED_BY_HASH_GATE (never a fake PASS).
Any hash change forces revalidation. State: data/hash_gate_state.json
(derived, gitignored).
"""
import hashlib
import json
import os

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "hash_gate_state.json")


def sha_of(paths):
    """sha256 over concatenated file bytes. Missing file -> 'MISSING:<path>'."""
    h = hashlib.sha256()
    for p in paths:
        if not os.path.isfile(p):
            return "MISSING:" + p
        with open(p, "rb") as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                h.update(chunk)
    return h.hexdigest()


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


def should_skip(key, paths, dependencies=()):
    """Return (skip: bool, reason: str). Never raises."""
    try:
        current = sha_of(paths) + "|" + "|".join(sorted(dependencies))
        rec = _load().get(key)
        if rec and rec.get("sha") == current and rec.get("verdict") == "PASS":
            return True, "SKIPPED_BY_HASH_GATE:" + key
        return False, "no prior PASS or state changed"
    except Exception as e:
        return False, "gate error, revalidate: %s" % str(e)[:100]


def record(key, paths, dependencies, verdict):
    """Persist verdict ('PASS' only gates future skips). Never raises."""
    try:
        data = _load()
        data[key] = {"sha": sha_of(paths) + "|" + "|".join(sorted(dependencies)),
                     "verdict": verdict}
        _save(data)
    except Exception:
        pass
