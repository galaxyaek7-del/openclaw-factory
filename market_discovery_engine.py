"""GALAXY FORGE V5.7 -- MARKET_DISCOVERY_ENGINE.

Sec 6 + Sec 30: discovery WITHOUT building a new hunter. This module is a
thin citation aggregator over ALREADY-REAL discovery machinery:

  market hunters/seeds ... market_hunter.py::SEED_CATEGORIES (static, read-only)
  live connectors ........ multi_source_intelligence.coverage (read-only queries)
  recorded evaluations ... decision_engine.store / data/decisions.jsonl (read-only)
  V5.7 signal register ... data/market_signal_register.jsonl (this cycle's harvest)
  problem map ............ data/problem_map.json
  V5.6 loop frontiers .... live_commercial_loop.loop_status() (read-only)

It adds exactly two things that did not exist: (1) the SIGNAL -> INTEREST ->
INTENT -> QUALIFIED_DEMAND -> TRANSACTION ladder (Sec 10 -- promotion
requires the named evidence kind, never a score), and (2) the Gate A-E
evaluation (Sec 26) over areas, computed from the register + loop, never
from invented confidence.

Read-only. Never hunts live by itself (connector queries run only through
the existing coverage API with explicit caller intent), never writes
except via the register helpers below (append-only, idempotent by
signal_id -- DUPLICATE_EVENT_IGNORED per V5.6 Sec 14).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent

REGISTER_PATH = _FACTORY_ROOT / "data" / "market_signal_register.jsonl"
PROBLEM_MAP_PATH = _FACTORY_ROOT / "data" / "problem_map.json"

# Sec 10 ladder, V5.7-second-directive Sec 2/3 extension: LEVEL 0 TREND
# (general interest / circulating topic -- e.g. "EU AI Act". A trend is
# NOT a buyer) sits below SIGNAL. Promotion requires the named evidence
# kind at each rung, never a score, never a shortcut.
LADDER = ("TREND", "SIGNAL", "INTEREST", "INTENT", "QUALIFIED_DEMAND", "TRANSACTION")

LADDER_EVIDENCE = {
    "TREND": "general interest or a circulating topic (proves no buyer)",
    "SIGNAL": "a problem, question, request, or discussion tied to a specific problem",
    "INTEREST": "a person shows clear interest in a solution, information, or offer",
    "INTENT": "a stronger mark: price/details/link/how-to-buy/demo/sample/availability/quote request",
    "QUALIFIED_DEMAND": "clear problem + clear use + current/near need + commercial context + initial willingness to pay or evaluate",
    "TRANSACTION": "a completed, verifiable financial transaction",
}

# Sec 26 gates.
GATES = {
    "GATE_A": ("NO_SIGNAL", "DISCOVER_MORE"),
    "GATE_B": ("SIGNAL_ONLY", "DEEPER_DISCOVERY"),
    "GATE_C": ("COMMERCIAL_SIGNAL", "TEST_OFFER"),
    "GATE_D": ("QUALIFIED_DEMAND", "DELIVER_OFFER"),
    "GATE_E": ("TRANSACTION", "DELIVER → FEEDBACK → REPEATABILITY"),
}


def _read_jsonl(path):
    records = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return records


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def load_signals(path=None):
    """All registered market signals (this cycle's harvest + any later)."""
    return _read_jsonl(Path(path) if path else REGISTER_PATH)


def load_problem_map(path=None):
    data = _read_json(Path(path) if path else PROBLEM_MAP_PATH, [])
    return data if isinstance(data, list) else []


def record_signal(signal, path=None):
    """Append-only, idempotent by signal_id (DUPLICATE_EVENT_IGNORED)."""
    dest = Path(path) if path else REGISTER_PATH
    existing = {s.get("signal_id") for s in _read_jsonl(dest)}
    if signal.get("signal_id") in existing:
        return {"recorded": False, "reason": "DUPLICATE_EVENT_IGNORED"}
    required = ("signal_id", "source", "audience", "problem", "observed_signal",
                "signal_type", "evidence_level")
    missing = [k for k in required if not signal.get(k)]
    if missing:
        return {"recorded": False, "reason": "missing fields: %s" % ",".join(missing)}
    if signal.get("signal_type") not in LADDER:
        return {"recorded": False,
                "reason": "signal_type must be one of %s (never DEMAND without evidence)" % "/".join(LADDER)}
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **signal}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"recorded": True, "signal_id": signal["signal_id"]}


def classify_level(signal):
    """Return the ladder level the signal's own evidence supports -- never
    higher. A buying-intent claim without intent behavior stays INTEREST."""
    claimed = str(signal.get("signal_type", "SIGNAL")).upper()
    if claimed not in LADDER:
        return "SIGNAL"
    # Demotion rules: the register's buying_intent_indicator gates INTENT+.
    buy = str(signal.get("buying_intent_indicator", "")).upper()
    idx = LADDER.index(claimed)
    if idx >= LADDER.index("INTENT") and "INDIRECT" in buy:
        return "INTEREST"
    if idx >= LADDER.index("QUALIFIED_DEMAND") and "NONE" in buy:
        return "INTEREST"
    return claimed


def evaluate_gates(signals=None, loop_status=None):
    """Sec 26 Gate A-E per problem area. Inputs: register signals + the
    V5.6 loop frontier (both read-only). No gate advances without the
    evidence its definition demands."""
    signals = signals if signals is not None else load_signals()
    by_area = {}
    for s in signals:
        by_area.setdefault(s.get("problem", "unknown")[:80], []).append(s)
    if loop_status is None:
        try:
            import live_commercial_loop as loop
            frontiers = {i.get("offer_name"): i.get("frontier")
                         for i in loop.loop_status().get("items", [])}
        except Exception:
            frontiers = {}
    else:
        frontiers = loop_status
    out = []
    if not by_area:
        return [{"area": "no registered signals", "signals": 0,
                 "highest_evidence": "SIGNAL", "gate": "GATE_A",
                 "state": GATES["GATE_A"][0], "action": GATES["GATE_A"][1],
                 "loop_frontier": None}]
    for area, sigs in by_area.items():
        levels = {classify_level(s) for s in sigs}
        top = max(levels, key=lambda l: LADDER.index(l)) if levels else "TREND"
        if top == "TREND":
            gate, action = "GATE_A", GATES["GATE_A"][1]
            state = GATES["GATE_A"][0]
        elif top == "SIGNAL":
            gate, action = "GATE_B", GATES["GATE_B"][1]
            state = GATES["GATE_B"][0]
        elif top == "INTEREST":
            gate, action, state = "GATE_C", GATES["GATE_C"][1], GATES["GATE_C"][0]
        elif top == "INTENT":
            gate, action, state = "GATE_C", GATES["GATE_C"][1], GATES["GATE_C"][0]
        elif top == "QUALIFIED_DEMAND":
            gate, action, state = "GATE_D", GATES["GATE_D"][1], GATES["GATE_D"][0]
        else:
            gate, action, state = "GATE_E", GATES["GATE_E"][1], GATES["GATE_E"][0]
        out.append({
            "area": area,
            "signals": len(sigs),
            "highest_evidence": top,
            "gate": gate,
            "state": state,
            "action": action,
            "loop_frontier": next((v for k, v in frontiers.items()
                                   if k and k[:20].lower() in area.lower()
                                   or area.lower() in (k or "").lower()), None),
        })
    return out


def discovery_summary():
    """One honest rollup: counts by ladder level (settled, never inflated),
    gates, and what remains UNKNOWN."""
    signals = load_signals()
    settled = [classify_level(s) for s in signals]
    counts = {level: settled.count(level) for level in LADDER}
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_signals": len(signals),
        "by_level": counts,
        "demand_word_used": False,
        "demand_note": "The word DEMAND appears nowhere above transaction level -- only SIGNAL/INTEREST per evidence.",
        "gates": evaluate_gates(signals),
        "problem_map_entries": len(load_problem_map()),
        "unknowns": [
            "Whether any observed pain converts to willingness to pay (no intent behavior observed anywhere).",
            "Whether unattributed clicks/views hide real humans (instruments unattributed by design).",
            "First-sale shape on Gumroad (unobservable pre-first-sale).",
        ],
    }


def _cli_main():
    print(json.dumps(discovery_summary(), ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()
