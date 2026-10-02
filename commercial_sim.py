"""Commercial simulation / shadow mode (S3-SIM-REALISM-01).

Deterministic (seeded RNG). All outputs labeled SIMULATED_INTERNAL.
Writes ONLY to data/sim_*.json — never touches commercial_evidence.jsonl,
finance_data.json, or any real ledger. A guard function blocks state names
that would contaminate real evidence.
"""
import datetime
import hashlib
import json
import random

SIM_DIR_PREFIX = "data/sim_"
REAL_STATES = {"SUBMITTED", "VERIFIED_SALE", "VERIFIED_REVENUE", "REAL_BUYER_REPLY",
               "OBSERVED_EXTERNAL", "PAID", "CONVERTED"}


def guard_no_real_states(obj):
    """Raise if any SIMULATED record claims a real-external state."""
    text = json.dumps(obj)
    bad = [s for s in REAL_STATES if '"%s"' % s in text or "'%s'" % s in text]
    if bad:
        raise ValueError("SIMULATION CONTAMINATION BLOCKED: %s" % bad)


SCENARIOS = [
    {"buyer": "clinic-admin", "problem": "50 intake forms to structured sheets",
     "volume": "50 docs", "deadline": "5d", "budget": [80, 150], "offer": "TRANSCRIPTION+FORMATTING",
     "price": 120, "objection": None, "contact": "C2"},
    {"buyer": "podcaster", "problem": "10 Arabic episodes need timestamps+speakers",
     "volume": "10x45min", "deadline": "7d", "budget": [100, 200], "offer": "MULTILINGUAL",
     "price": 160, "objection": "price", "contact": "C1"},
    {"buyer": "law-office", "problem": "interview tapes to PDF, confidential",
     "volume": "6h audio", "deadline": "3d", "budget": [200, 400], "offer": "PROFESSIONAL",
     "price": 300, "objection": "deadline", "contact": "C2"},
    {"buyer": "student", "problem": "lecture recordings to notes, cheap",
     "volume": "20h", "deadline": "14d", "budget": [15, 30], "offer": "BASIC",
     "price": 25, "objection": "price", "contact": "C1"},
    {"buyer": "agency", "problem": "weekly client-call summaries, recurring",
     "volume": "4x60min/mo", "deadline": "ongoing", "budget": [150, 250], "offer": "TRANSCRIPTION+SUMMARY",
     "price": 200, "objection": None, "contact": "C3"},
    {"buyer": "author", "problem": "oral history to structured chapters",
     "volume": "12h", "deadline": "10d", "budget": [120, 180], "offer": "STRUCTURED-DOC",
     "price": 150, "objection": "revision", "contact": "C1"},
]


def run_funnel(sc, rng):
    stages = ["DISCOVER", "SCREEN", "CAPABILITY_FIT", "BUDGET_FIT", "CONTACTABILITY",
              "OFFER", "PROPOSAL", "RESPONSE_SIM", "OBJECTION", "NEGOTIATION",
              "INTENT", "CHECKOUT_SIM", "CONVERSION_SIM"]
    log = []
    outcome = "SIMULATED_CONVERSION"
    # failure injection from scenario + randomness
    if sc["budget"][1] < 30:
        outcome, at = "LOW_BUDGET", "BUDGET_FIT"
    elif sc["contact"] == "C1" and rng.random() < 0.7:
        outcome, at = "NO_CONTACT", "CONTACTABILITY"
    elif sc["contact"] == "C1":
        outcome, at = "NO_RESPONSE", "RESPONSE_SIM"
    elif sc["objection"] == "price" and sc["price"] > sum(sc["budget"]) / 2 + 60:
        outcome, at = "PRICE_OBJECTION", "NEGOTIATION"
    elif sc["objection"] == "deadline" and "3d" in sc["deadline"]:
        outcome, at = "DEADLINE_TOO_SHORT", "NEGOTIATION"
    elif sc["objection"] == "revision":
        outcome, at = "REVISION_THEN_ACCEPT", "NEGOTIATION"
    else:
        at = "CONVERSION_SIM"
    for s in stages:
        log.append(s)
        if s == at and outcome != "SIMULATED_CONVERSION":
            break
    return {"stages_reached": log, "outcome": outcome,
            "failed_at": at if outcome != "SIMULATED_CONVERSION" else None}


def main():
    rng = random.Random(20261002)
    results = []
    for sc in SCENARIOS:
        r = {"scenario": sc["buyer"], "offer": sc["offer"], "price": sc["price"],
             "contact": sc["contact"]}
        r.update(run_funnel(sc, rng))
        # delivery dry-run: synthetic timing model (words/min pipelined)
        r["delivery_sim"] = {"automation_rate": 0.7, "qa_passes": 2,
                             "margin_pct": round((sc["price"] - sc["price"] * 0.3) / sc["price"] * 100)}
        results.append(r)
    conv = sum(1 for r in results if r["outcome"] == "SIMULATED_CONVERSION")
    report = {
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "label": "SIMULATED_INTERNAL — NOT_EXTERNAL_EVIDENCE",
        "scenarios": len(results),
        "simulated_conversions": conv,
        "simulated_conversion_rate": round(conv / len(results), 2),
        "outcomes": {r["scenario"]: r["outcome"] for r in results},
        "best_offer": max(results, key=lambda r: (r["outcome"] == "SIMULATED_CONVERSION",
                                                  r["delivery_sim"]["margin_pct"]))["offer"],
        "real_validation_required": True,
        "verified_sales": 0,
        "verified_revenue": 0,
    }
    guard_no_real_states(report)
    json.dump(report, open("data/sim_transcription_report.json", "w", encoding="utf-8"), indent=1)
    json.dump(results, open("data/sim_transcription_runs.jsonl", "w", encoding="utf-8"))
    print(json.dumps({"scenarios": len(results), "sim_conv": conv,
                      "rate": report["simulated_conversion_rate"],
                      "best": report["best_offer"]}))
    return 0


if __name__ == "__main__":
    main()
