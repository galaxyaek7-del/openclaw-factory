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
RETRIEVAL_LEDGER_PATH = _FACTORY_ROOT / "data" / "discovery_retrievals.jsonl"

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
    "GATE_E": ("TRANSACTION", "DELIVER ��' FEEDBACK ��' REPEATABILITY"),
}

# ---------------------------------------------------------------------------
# Intake screening (Cycle 107 repair, 2026-10-20)
#
# Three consecutive discovery rounds were rejected *after* scoring, for the
# same reason: the candidate was already covered by an adequate free
# alternative. Scoring first meant a 19/25 or 16/25 number was computed for a
# product that could never be built, and that number then had to be explained
# away. Cycle 107 also proved that a URL can return 200 and still not contain
# what the record claimed, and that 403/404/DNS-failure links had been treated
# as if they were evidence.
#
# This block is the intake gate that runs BEFORE any score exists. It answers
# one question per source -- "what did the retrieval actually return?" -- and
# one question per candidate -- "does the evidence survive, and is the product
# already given away?" A single failed gate rejects the candidate; the score
# is never consulted, so no number can argue past a missing prerequisite.
# ---------------------------------------------------------------------------

# What a retrieval returned, not what the record hoped it returned.
SOURCE_STATUSES = ("FETCHED_OK", "REDIRECTED", "BLOCKED", "DEAD", "UNVERIFIED")

EVIDENCE_STATUSES = ("FETCHED_OK", "REDIRECTED")

INTAKE_GATES = {
    "G1": "every cited URL has a retrieval record that counts as evidence",
    "G2": "at least two independent source types survive retrieval",
    "G3": "an adequate free alternative is not materially duplicating the candidate",
    "G4": "a paid comparison exists and a specific differentiator is stated",
    "G5": "the buyer and the selling channel are named",
    "G6": "the build cost for this factory is $0",
}

_FREE_DUPLICATE_MARKERS = ("duplicate", "duplicated", "already free", "covers the same")


def classify_source(status_code=None, error=None, requested_url="",
                    final_url="", body_bytes=0):
    """Map an observed retrieval to one SOURCE_STATUSES value.

    Deliberately mechanical: a status code is not an opinion. 401/403/429 is
    BLOCKED (the host refused a plain client), 404/410/DNS failure is DEAD, a
    redirect is REDIRECTED only when the destination was actually observed,
    and a bodiless response -- EUR-Lex's 202 with 0 bytes is the real example
    -- is UNVERIFIED, never "served".
    """
    err = str(error or "").lower()
    if err:
        if "dns" in err or "getaddrinfo" in err or "name or service" in err:
            return {"status": "DEAD", "detail": "DNS resolution failed", "counts_as_evidence": False}
        return {"status": "UNVERIFIED",
                "detail": "transport error (%s) with no HTTP response observed" % (error or "unknown"),
                "counts_as_evidence": False}

    try:
        code = int(status_code)
    except (TypeError, ValueError):
        return {"status": "UNVERIFIED", "detail": "no status code recorded",
                "counts_as_evidence": False}

    if code in (401, 403, 429):
        return {"status": "BLOCKED",
                "detail": "HTTP %d: host refused a plain client (bot protection or auth)" % code,
                "counts_as_evidence": False}
    if code in (404, 410):
        return {"status": "DEAD", "detail": "HTTP %d: resource gone" % code,
                "counts_as_evidence": False}
    if 300 <= code < 400:
        if final_url and final_url != requested_url:
            return {"status": "REDIRECTED",
                    "detail": "HTTP %d to %s" % (code, final_url),
                    "counts_as_evidence": True}
        return {"status": "UNVERIFIED",
                "detail": "HTTP %d with no observed destination" % code,
                "counts_as_evidence": False}
    if 200 <= code < 300:
        if int(body_bytes or 0) > 0:
            return {"status": "FETCHED_OK",
                    "detail": "HTTP %d with %d bytes" % (code, int(body_bytes)),
                    "counts_as_evidence": True}
        return {"status": "UNVERIFIED",
                "detail": "HTTP %d with an empty body (async gate or bot wall)" % code,
                "counts_as_evidence": False}
    return {"status": "UNVERIFIED", "detail": "HTTP %d is not a usable retrieval" % code,
            "counts_as_evidence": False}


def record_retrieval(url, status_code=None, error=None, final_url="",
                     body_bytes=0, source_type=None, note="", path=None):
    """Append one real retrieval observation to the ledger.

    Append-only and never rewritten: a later successful fetch does not erase
    an earlier 403. Callers add the latest record for a URL when they need the
    current state. Nothing here fetches anything.
    """
    url = str(url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"recorded": False, "reason": "not an http(s) url"}
    verdict = classify_source(status_code=status_code, error=error,
                              requested_url=url, final_url=final_url,
                              body_bytes=body_bytes)
    record = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
        "status": verdict["status"],
        "detail": verdict["detail"],
        "counts_as_evidence": verdict["counts_as_evidence"],
        "status_code": status_code,
        "error": error,
        "final_url": final_url or None,
        "body_bytes": int(body_bytes or 0),
        "source_type": source_type,
        "note": note,
    }
    dest = Path(path) if path else RETRIEVAL_LEDGER_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"recorded": True, "status": record["status"], "url": url}


def latest_retrievals(path=None):
    """url -> most recent ledger record. Later records win; earlier ones stay."""
    latest = {}
    for rec in _read_jsonl(Path(path) if path else RETRIEVAL_LEDGER_PATH):
        url = rec.get("url")
        if url:
            latest[url] = rec
    return latest


def evidence_integrity(cited_urls, retrievals=None):
    """Check every cited URL against what retrieval actually returned.

    `cited_urls` is a list of {"url": ..., "source_type": ...} or plain URL
    strings. A URL with no ledger record is UNVERIFIED -- an assertion in a
    markdown file is not a retrieval.
    """
    retrievals = retrievals if retrievals is not None else latest_retrievals()
    rows = []
    evidence = []
    source_types = set()
    for item in cited_urls or []:
        if isinstance(item, str):
            url, source_type = item, None
        else:
            url = item.get("url")
            source_type = item.get("source_type")
        rec = retrievals.get(url)
        if rec is None:
            rows.append({"url": url, "source_type": source_type,
                         "status": "UNVERIFIED", "detail": "no retrieval record",
                         "counts_as_evidence": False})
            continue
        row = {"url": url, "source_type": source_type or rec.get("source_type"),
               "status": rec.get("status"), "detail": rec.get("detail"),
               "counts_as_evidence": bool(rec.get("counts_as_evidence"))}
        rows.append(row)
        if row["counts_as_evidence"]:
            evidence.append(row)
            if row["source_type"]:
                source_types.add(str(row["source_type"]).lower())

    problems = []
    if not cited_urls:
        problems.append("no cited URLs")
    blocked = [r["url"] for r in rows if r["status"] in ("BLOCKED", "DEAD")]
    unverified = [r["url"] for r in rows if r["status"] == "UNVERIFIED"]
    if blocked:
        problems.append("%d cited URL(s) are BLOCKED/DEAD" % len(blocked))
    if unverified:
        problems.append("%d cited URL(s) have no usable retrieval record" % len(unverified))
    if len(evidence) < 2:
        problems.append("only %d URL(s) count as evidence (2 required)" % len(evidence))
    return {"ok": not problems, "urls": rows, "evidence_urls": [r["url"] for r in evidence],
            "source_types": sorted(source_types), "problems": problems,
            "blocked": blocked, "unverified": unverified}


def _free_alternative_gate(free_alternative):
    """G3. The free substitute has to be named, assessed, and beaten.

    Saying nothing is a failure, not a pass: Cycle 107's three candidates were
    all rejected because the record never asked this question until scoring.
    """
    free = free_alternative or {}
    if not free:
        return False, "no free alternative was assessed"
    urls = free.get("urls") or ([free["url"]] if free.get("url") else [])
    if not urls:
        return False, "free alternative named no URL"
    if free.get("materially_duplicates") is True:
        return False, "materially duplicated by an adequate free alternative"
    advantage = str(free.get("demonstrated_advantage") or "").strip()
    if not advantage or advantage.upper() in ("UNKNOWN", "NONE", "N/A"):
        return False, "no demonstrated advantage over the free alternative"
    if any(m in advantage.lower() for m in _FREE_DUPLICATE_MARKERS):
        return False, "the stated advantage describes a duplication, not a difference"
    return True, "advantage stated: " + advantage


def evaluate_intake(candidate, retrievals=None):
    """The six hard gates, before any score exists.

    Any single FAIL rejects the candidate and sets scoring_skipped. There is
    deliberately no "close enough" path and no weighting: a missing
    prerequisite is not offset by strength elsewhere.
    """
    name = (candidate or {}).get("name") or "unnamed candidate"
    integrity = evidence_integrity((candidate or {}).get("cited_urls"), retrievals)

    gates = {}
    gates["G1"] = {"status": "PASS" if integrity["ok"] else "FAIL",
                   "reason": "all cited URLs count as evidence"
                   if integrity["ok"] else "; ".join(integrity["problems"])}
    types = integrity["source_types"]
    gates["G2"] = {"status": "PASS" if len(types) >= 2 else "FAIL",
                   "reason": "%d independent source type(s): %s"
                   % (len(types), ", ".join(types) if types else "none")}

    ok3, why3 = _free_alternative_gate(candidate.get("free_alternative"))
    gates["G3"] = {"status": "PASS" if ok3 else "FAIL", "reason": why3}

    paid = candidate.get("paid_comparison") or {}
    competitors = [c for c in (paid.get("competitors") or []) if c]
    differentiator = str(paid.get("differentiator") or "").strip()
    if not competitors:
        gates["G4"] = {"status": "FAIL", "reason": "no paid competitor recorded"}
    elif not differentiator or differentiator.upper() in ("UNKNOWN", "NONE", "N/A"):
        gates["G4"] = {"status": "FAIL",
                       "reason": "no specific differentiator against the paid competitor(s)"}
    else:
        gates["G4"] = {"status": "PASS", "reason": differentiator}

    buyer_channel = candidate.get("buyer_channel") or {}
    buyer = str(buyer_channel.get("buyer") or "").strip()
    channel = str(buyer_channel.get("channel") or "").strip()
    if buyer and channel:
        gates["G5"] = {"status": "PASS", "reason": "%s via %s" % (buyer, channel)}
    else:
        gates["G5"] = {"status": "FAIL", "reason": "buyer and channel must both be named"}

    cost = candidate.get("build_cost_usd")
    if cost is None:
        gates["G6"] = {"status": "FAIL", "reason": "build cost not stated"}
    elif float(cost) > 0:
        gates["G6"] = {"status": "FAIL", "reason": "build cost $%.2f exceeds $0" % float(cost)}
    else:
        gates["G6"] = {"status": "PASS", "reason": "build cost $0"}

    failed = [g for g, v in gates.items() if v["status"] == "FAIL"]
    return {
        "name": name,
        "verdict": "REJECTED" if failed else "QUALIFIED_FOR_SCORING",
        "failed_gates": failed,
        "gates": gates,
        "evidence_integrity": integrity,
        "claimed_score": candidate.get("claimed_score"),
        "score_consulted": False,
        "scoring_skipped": bool(failed),
    }


def screen_intake(candidates, retrievals=None):
    """Run evaluate_intake over a batch, with an honest rollup."""
    results = [evaluate_intake(c, retrievals) for c in (candidates or [])]
    return {
        "screened": len(results),
        "rejected_at_intake": sum(1 for r in results if r["verdict"] == "REJECTED"),
        "qualified": sum(1 for r in results if r["verdict"] == "QUALIFIED_FOR_SCORING"),
        "results": results,
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
