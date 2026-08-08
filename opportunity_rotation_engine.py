"""Galaxy Forge — Golden Hunter Opportunity Rotation & Pursue/Abandon
Engine (Phase 38, ADR-233, 2026-08-08).

Audit before build (Section 1) found nearly every real signal this
directive names already exists, scattered across real modules built
across this session:

- `goos.py::rank_build_candidates()` (ADR-178) already ranks EVERY real
  candidate niche against every other, real duplicate-family detection,
  real engineering-without-revenue flag, a real never-evaluated seed
  list spanning all 6 product ladders (not just automation/n8n) --
  this IS Section 12's "new opportunity discovery... not constrained to
  n8n/automation" ask, already built. Reused directly, never
  re-implemented.
- `commission_engine.py::SCORING_DIMENSIONS`/`score_commission_opportunity()`
  already covers most commission-specific dimensions (commission value,
  recurring potential, competition, acquisition difficulty, partner
  reliability, geographic access, legal risk, data freshness).
- `lead_discovery.py`'s Phase 37C evidence hierarchy/freshness
  classifier (`classify_freshness()`, `SOURCE_TIER`) is the real
  evidence-quality/freshness signal for any opportunity with a real
  discovery run behind it.
- `commission_engine.py::record_pipeline_transition()`/`pipeline_history()`
  is the exact real append-only state-machine pattern this module's own
  lifecycle transitions reuse verbatim (same shape, new vocabulary).
- `autonomous_operations.py`'s Level 0-6 authorization engine remains
  the one real CEO-authority gate; this module recommends only and
  never calls it to authorize anything itself.

The one genuinely new piece: no existing module decides, across
heterogeneous opportunity types (a commission partner program vs. a
candidate product niche), whether Galaxy Forge should keep spending
discovery attention on a SPECIFIC opportunity_id at all -- that
upstream "is this still worth pursuing" lifecycle, distinct from
`COMMISSION_PIPELINE_STATES`'s downstream sales-funnel states (which
start only once an opportunity is already being actively worked), is
what this module adds.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent
DEFAULT_EVENTS_PATH = _FACTORY_ROOT / "data" / "opportunity_rotation_events.jsonl"

# Section 2 -- the real, immutable lifecycle vocabulary. A candidate
# must never jump DISCOVERED -> OUTREACH or DISCOVERED -> DEAL; this
# module's own record_lifecycle_transition() enforces that no state
# outside this tuple (or the terminal exits) is ever recorded.
OPPORTUNITY_LIFECYCLE_STATES = (
    "DISCOVERED", "EVIDENCE_CHECK", "QUALIFICATION", "PURSUE", "WATCH", "ABANDON", "ROTATE",
)

# Section 3 -- the 14 named Golden Hunter decision dimensions, verbatim.
GOLDEN_HUNTER_DECISION_DIMENSIONS = (
    "MARKET_SIGNAL", "PROBLEM_SEVERITY", "CUSTOMER_EXISTENCE", "COMMERCIAL_POTENTIAL",
    "PARTNER_FIT", "EVIDENCE_QUALITY", "EVIDENCE_FRESHNESS", "COMPETITION", "ACCESSIBILITY",
    "TIME_TO_REVENUE", "REPEATABILITY", "RECURRENCE_POTENTIAL", "CONFIDENCE", "RISK",
)

REPEATED_FAILURE_THRESHOLD = 2


def _now_iso(now=None):
    return (now or datetime.now(timezone.utc)).isoformat()


def _append_jsonl(record, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


# ---------------------------------------------------------------------------
# Section 2/10 -- lifecycle state machine + persistent opportunity memory.
# Same real append-only-event pattern as commission_engine.py's
# record_pipeline_transition()/pipeline_history(), a different
# vocabulary for a different, upstream question.
# ---------------------------------------------------------------------------

def record_lifecycle_transition(opportunity_id, from_state, to_state, reason=None, evidence=None,
                                 golden_hunter_reasoning=None, events_path=None, now=None):
    """Real, append-only audit event. Never allows a transition to a
    state outside the real, named vocabulary -- the concrete guard
    against DISCOVERED -> OUTREACH/DEAL Section 2 forbids."""
    valid_states = set(OPPORTUNITY_LIFECYCLE_STATES)
    if to_state not in valid_states:
        return {"ok": False, "reason": f"'{to_state}' is not a named opportunity-lifecycle state"}
    event = {
        "generated_at": _now_iso(now), "opportunity_id": opportunity_id,
        "from_state": from_state, "to_state": to_state, "reason": reason, "evidence": evidence,
        "golden_hunter_reasoning": golden_hunter_reasoning,
    }
    _append_jsonl(event, events_path or DEFAULT_EVENTS_PATH)
    return {"ok": True, "event": event}


def lifecycle_history(opportunity_id, events_path=None):
    events = _read_jsonl(events_path or DEFAULT_EVENTS_PATH)
    return [e for e in events if e.get("opportunity_id") == opportunity_id]


def current_lifecycle_state(opportunity_id, events_path=None):
    history = lifecycle_history(opportunity_id, events_path=events_path)
    if not history:
        return "DISCOVERED"
    return history[-1]["to_state"]


def all_known_opportunity_ids(events_path=None):
    events = _read_jsonl(events_path or DEFAULT_EVENTS_PATH)
    return sorted({e["opportunity_id"] for e in events if e.get("opportunity_id")})


def opportunity_memory(opportunity_id, events_path=None):
    """Section 10 -- the real, persistent per-opportunity memory record.
    Never a second data store: purely a real, computed reconstruction
    from this module's own append-only event ledger."""
    history = lifecycle_history(opportunity_id, events_path=events_path)
    if not history:
        return {
            "opportunity_id": opportunity_id, "first_seen": None, "last_seen": None,
            "status": "DISCOVERED", "previous_status": None,
            "qualification_history": [], "rejection_history": [], "resurrection_events": [],
            "note": "No real lifecycle event recorded yet for this opportunity_id.",
        }
    rejections = [e for e in history if e["to_state"] in ("ABANDON", "WATCH")]
    resurrections = [e for e in history if e["to_state"] == "EVIDENCE_CHECK" and e.get("reason") and "resurrection" in str(e["reason"]).lower()]
    return {
        "opportunity_id": opportunity_id,
        "first_seen": history[0]["generated_at"], "last_seen": history[-1]["generated_at"],
        "status": history[-1]["to_state"],
        "previous_status": history[-2]["to_state"] if len(history) >= 2 else None,
        "score_history": [{"generated_at": e["generated_at"], "to_state": e["to_state"], "reason": e.get("reason")} for e in history],
        "evidence_history": [e.get("evidence") for e in history if e.get("evidence")],
        "rejection_history": rejections,
        "qualification_history": [e for e in history if e["to_state"] == "QUALIFICATION"],
        "golden_hunter_reasoning": [e.get("golden_hunter_reasoning") for e in history if e.get("golden_hunter_reasoning")],
        "resurrection_events": resurrections,
        "transition_count": len(history),
    }


# ---------------------------------------------------------------------------
# Section 6 -- repeated-failure detection (never permanently destroys
# an opportunity; moves it to WATCH/ABANDON with a documented, real
# reason, always resurrectable).
# ---------------------------------------------------------------------------

def failure_count(opportunity_id, events_path=None):
    history = lifecycle_history(opportunity_id, events_path=events_path)
    return sum(1 for e in history if e["to_state"] in ("WATCH", "ABANDON"))


def repeated_failure_penalty(opportunity_id, events_path=None):
    count = failure_count(opportunity_id, events_path=events_path)
    if count >= REPEATED_FAILURE_THRESHOLD:
        return {
            "penalized": True, "failure_count": count,
            "recommended_ceiling": "ABANDON",
            "reason": f"{count} real prior WATCH/ABANDON transitions recorded -- repeated real failure to qualify, per Section 6's real, controlled penalty (never permanent -- resurrection remains possible with genuinely new evidence).",
        }
    return {"penalized": False, "failure_count": count, "recommended_ceiling": None,
            "reason": f"{count} real prior WATCH/ABANDON transition(s) -- below the {REPEATED_FAILURE_THRESHOLD}-failure threshold."}


# ---------------------------------------------------------------------------
# Section 3 -- Golden Hunter Decision Model: the 14 named dimensions,
# each a real citation of an existing function, never a fabricated
# signal. opportunity_type distinguishes COMMISSION (a commission_
# engine.py portfolio entry) from PRODUCT (a goos.py/decision_engine
# candidate niche) -- the two real shapes this factory's opportunities
# actually come in.
# ---------------------------------------------------------------------------

def evaluate_golden_hunter_dimensions(opportunity_id, opportunity_type="COMMISSION",
                                       commission_opportunity=None, niche=None,
                                       evidence_summary=None, now=None):
    """Real, per-dimension citation -- never a mysterious collapsed
    score. `evidence_summary` (optional) is a real lead_discovery.py
    result dict (e.g. Phase 37B/37C's own committed JSON) providing the
    real EVIDENCE_QUALITY/FRESHNESS signal when a live discovery run
    has actually happened for this opportunity."""
    now = now or datetime.now(timezone.utc)
    dims = {}

    if opportunity_type == "COMMISSION" and commission_opportunity:
        co = commission_opportunity
        dims["MARKET_SIGNAL"] = {"value": co.get("target_customer", "UNKNOWN"), "source": "commission_engine portfolio record"}
        dims["COMMERCIAL_POTENTIAL"] = {"value": co.get("commission_value", "COMMISSION_UNKNOWN"), "source": "commission_engine portfolio record"}
        dims["PARTNER_FIT"] = {"value": co.get("verification_status", "UNKNOWN"), "source": "commission_engine._derive_verification_status()"}
        dims["RECURRENCE_POTENTIAL"] = {"value": "recurring" if co.get("recurring_commission") else "one-time", "source": "commission_engine portfolio record"}
        dims["RISK"] = {"value": co.get("risk_score", "UNKNOWN"), "source": "commission_engine portfolio record"}
        dims["ACCESSIBILITY"] = {"value": co.get("eligibility", "UNKNOWN"), "source": "commission_engine portfolio record (eligibility field)"}
    else:
        dims["MARKET_SIGNAL"] = {"value": "NOT_MEASURABLE" if not niche else "requires goos.evaluate_dimensions(niche)", "source": "goos.py::evaluate_dimensions()"}
        dims["COMMERCIAL_POTENTIAL"] = {"value": "requires goos.evaluate_dimensions(niche)['profitability']", "source": "goos.py::evaluate_dimensions()"}
        dims["PARTNER_FIT"] = {"value": "NOT_APPLICABLE -- no partner program involved for a product-build candidate", "source": None}
        dims["RECURRENCE_POTENTIAL"] = {"value": "requires goos.evaluate_dimensions(niche)['recurring_revenue_potential']", "source": "goos.py::evaluate_dimensions()"}
        dims["RISK"] = {"value": "requires goos.evaluate_dimensions(niche)['risk_level']", "source": "goos.py::evaluate_dimensions()"}
        dims["ACCESSIBILITY"] = {"value": "requires goos.evaluate_dimensions(niche)['operational_complexity']", "source": "goos.py::evaluate_dimensions()"}

    # PROBLEM_SEVERITY / CUSTOMER_EXISTENCE / EVIDENCE_QUALITY / EVIDENCE_FRESHNESS:
    # real only when a real lead_discovery.py run exists for this opportunity.
    if evidence_summary:
        best = evidence_summary.get("best_candidate") or evidence_summary.get("best_current_prospect")
        qualified_count = evidence_summary.get("qualified_candidates", 0)
        dims["PROBLEM_SEVERITY"] = {
            "value": "real problem-signal keyword match found" if qualified_count or evidence_summary.get("candidates_found") else "UNKNOWN",
            "source": "lead_discovery.py real discovery run result",
        }
        dims["CUSTOMER_EXISTENCE"] = {
            "value": f"{evidence_summary.get('candidates_found', evidence_summary.get('new_candidates_found', 0))} real candidate(s) found" if evidence_summary else "UNKNOWN",
            "source": "lead_discovery.py real discovery run result",
        }
        freshness_breakdown = evidence_summary.get("evidence_freshness_breakdown") or {}
        fresh_count = freshness_breakdown.get("FRESH", 0)
        dims["EVIDENCE_FRESHNESS"] = {
            "value": "FRESH evidence exists" if fresh_count else "STALE -- no fresh (<=45 day) evidence found in the most recent real discovery run",
            "source": "lead_discovery.py::classify_freshness() (45-day gate, unchanged)",
        }
        dims["EVIDENCE_QUALITY"] = {
            "value": f"best real candidate confidence: {qualified_count and 'see qualified candidates' or 'no qualified candidate'}",
            "source": "lead_discovery.py::qualify_lead()",
        }
    else:
        dims["PROBLEM_SEVERITY"] = {"value": "UNKNOWN -- no real discovery run exists for this opportunity yet", "source": None}
        dims["CUSTOMER_EXISTENCE"] = {"value": "UNKNOWN -- no real discovery run exists for this opportunity yet", "source": None}
        dims["EVIDENCE_FRESHNESS"] = {"value": "UNKNOWN -- no real discovery run exists for this opportunity yet", "source": None}
        dims["EVIDENCE_QUALITY"] = {"value": "UNKNOWN -- no real discovery run exists for this opportunity yet", "source": None}

    if opportunity_type == "COMMISSION" and commission_opportunity:
        dims["COMPETITION"] = {"value": "NOT_MEASURED -- no real competition signal captured at this opportunity granularity", "source": None}
    else:
        dims["COMPETITION"] = {"value": "requires goos.evaluate_dimensions(niche)['competition_level']", "source": "goos.py::evaluate_dimensions()"}

    dims["TIME_TO_REVENUE"] = {"value": "NOT_MEASURABLE -- no real historical per-opportunity time-to-first-revenue signal exists anywhere in this factory", "source": None}

    # REPEATABILITY -- the one dimension genuinely computed by THIS
    # module's own real lifecycle ledger, not cited from elsewhere.
    fail = repeated_failure_penalty(opportunity_id)
    dims["REPEATABILITY"] = {
        "value": f"{fail['failure_count']} real prior WATCH/ABANDON cycle(s)",
        "source": "opportunity_rotation_engine.py::repeated_failure_penalty() (this module's own real lifecycle ledger)",
    }

    known = sum(1 for d in dims.values() if not str(d["value"]).startswith(("UNKNOWN", "NOT_MEASURABLE", "NOT_MEASURED", "NOT_APPLICABLE", "requires")))
    confidence = "LOW" if known <= 4 else ("MEDIUM" if known <= 9 else "HIGH")
    dims["CONFIDENCE"] = {"value": f"{known}/{len(GOLDEN_HUNTER_DECISION_DIMENSIONS) - 1} real factors known", "source": "computed from the other 13 dimensions above"}

    return {
        "generated_at": _now_iso(now), "opportunity_id": opportunity_id, "opportunity_type": opportunity_type,
        "dimensions": dims, "known_dimensions": known, "total_dimensions": len(GOLDEN_HUNTER_DECISION_DIMENSIONS) - 1,
        "overall_confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Section 4 -- PURSUE / WATCH / ABANDON / ROTATE classification.
# ---------------------------------------------------------------------------

def pursuit_recommendation(opportunity_id, dimensions_result, stronger_alternative_exists=False, events_path=None):
    """Real, explainable, disclosed heuristic -- never forces PURSUE.
    Order matters: repeated failure and freshness gates are checked
    before anything else, matching Section 6's own "repeated failure ->
    controlled penalty" priority."""
    reasons = []
    fail = repeated_failure_penalty(opportunity_id, events_path=events_path)
    dims = dimensions_result["dimensions"]
    freshness_val = str(dims.get("EVIDENCE_FRESHNESS", {}).get("value", ""))
    evidence_fresh = "FRESH evidence exists" in freshness_val
    confidence = dimensions_result["overall_confidence"]

    if fail["penalized"]:
        reasons.append(fail["reason"])
        recommendation = "ABANDON"
    elif stronger_alternative_exists:
        reasons.append("A real alternative opportunity has a materially stronger expected value (see compare_opportunities()).")
        recommendation = "ROTATE"
    elif not evidence_fresh:
        reasons.append(f"EVIDENCE_FRESHNESS={freshness_val} -- the 45-day freshness gate is not met; insufficient to justify continued focused pursuit today.")
        recommendation = "WATCH"
    elif confidence == "LOW":
        reasons.append(f"overall_confidence=LOW ({dimensions_result['known_dimensions']}/{dimensions_result['total_dimensions']} real dimensions known) -- too many real unknowns to justify PURSUE.")
        recommendation = "WATCH"
    else:
        reasons.append(f"Fresh evidence exists, {dimensions_result['known_dimensions']}/{dimensions_result['total_dimensions']} real dimensions known, no repeated-failure penalty, no stronger real alternative identified.")
        recommendation = "PURSUE"

    return {
        "opportunity_id": opportunity_id, "RECOMMENDATION": recommendation, "REASON": reasons,
        "note": "Golden Hunter recommends only -- this is never authorization for outreach, a deal, or any commercial commitment (Section 17).",
    }


# ---------------------------------------------------------------------------
# Section 5 -- cross-opportunity comparison / ranking.
# ---------------------------------------------------------------------------

def compare_opportunities(evaluations):
    """`evaluations` is a list of evaluate_golden_hunter_dimensions()
    results. Ranks by known_dimensions (a real, disclosed proxy for
    expected-value confidence -- never a fabricated blended score
    across heterogeneous COMMISSION/PRODUCT opportunity types) and
    produces a real, cited "A beats B because" explanation for the
    top pair."""
    ranked = sorted(evaluations, key=lambda e: e["known_dimensions"], reverse=True)
    explanation = None
    if len(ranked) >= 2:
        a, b = ranked[0], ranked[1]
        reasons = []
        if a["known_dimensions"] > b["known_dimensions"]:
            reasons.append(f"{a['opportunity_id']} has {a['known_dimensions']} real known dimensions vs. {b['opportunity_id']}'s {b['known_dimensions']}")
        a_fresh = "FRESH evidence exists" in str(a["dimensions"].get("EVIDENCE_FRESHNESS", {}).get("value", ""))
        b_fresh = "FRESH evidence exists" in str(b["dimensions"].get("EVIDENCE_FRESHNESS", {}).get("value", ""))
        if a_fresh and not b_fresh:
            reasons.append(f"{a['opportunity_id']} has real FRESH evidence; {b['opportunity_id']} does not")
        explanation = {
            "winner": a["opportunity_id"], "runner_up": b["opportunity_id"],
            "WHY_A_BEATS_B": reasons or ["Both opportunities are real but comparably evidenced -- no material real differentiator found this comparison."],
        }
    return {"ranked": ranked, "top_comparison": explanation, "generated_at": _now_iso()}


# ---------------------------------------------------------------------------
# Section 11 -- resurrection.
# ---------------------------------------------------------------------------

def mark_reopen_condition(opportunity_id, condition="REOPEN_ONLY_IF_NEW_FRESH_EVIDENCE_APPEARS", events_path=None, now=None):
    return record_lifecycle_transition(
        opportunity_id, from_state=current_lifecycle_state(opportunity_id, events_path=events_path), to_state="WATCH",
        reason=condition, events_path=events_path, now=now,
    )


def check_resurrection(opportunity_id, new_evidence_freshness_status, events_path=None, now=None):
    """Real, mechanical resurrection check -- only genuinely new FRESH
    evidence justifies reopening; STALE/UNKNOWN never does."""
    if new_evidence_freshness_status != "FRESH":
        return {"resurrect": False, "reason": f"new_evidence_freshness_status={new_evidence_freshness_status} -- only real FRESH evidence justifies resurrection"}
    result = record_lifecycle_transition(
        opportunity_id, from_state=current_lifecycle_state(opportunity_id, events_path=events_path), to_state="EVIDENCE_CHECK",
        reason="resurrection: genuinely new FRESH evidence found", events_path=events_path, now=now,
    )
    return {"resurrect": True, "reason": "real, fresh new evidence found -- resurrected to EVIDENCE_CHECK", "event": result.get("event")}


# ---------------------------------------------------------------------------
# Section 20 -- cheapest next validation step.
# ---------------------------------------------------------------------------

def cheapest_validation_step(dimensions_result):
    """Real, disclosed heuristic -- names the weakest actionable real
    dimension (unknown OR unfavorably known, e.g. STALE) and the
    cheapest real action that would inform it, preferring low-cost/
    high-information actions over more code or more search volume.
    EVIDENCE_FRESHNESS is checked first -- it's this factory's own
    single most common real blocker (Phase 37B/37C's own findings)."""
    dims = dimensions_result["dimensions"]
    suggestions = {
        "EVIDENCE_FRESHNESS": "re-run lead_discovery.py's real discovery pass after a real time gap (evidence naturally refreshes)",
        "CUSTOMER_EXISTENCE": "run one additional real, legitimate discovery source (e.g. Stack Overflow, GitHub) with a differently-phrased real query",
        "PROBLEM_SEVERITY": "manually review the strongest real candidate's actual post text for genuine pain language",
        "COMPETITION": "one real, targeted WebSearch/WebFetch for the partner's/niche's known competitors",
        "MARKET_SIGNAL": "run a real, targeted customer-discovery pass to fill the real target_customer gap",
        "TIME_TO_REVENUE": "NOT_MEASURABLE company-wide -- no cheap real validation step exists for this dimension yet",
    }
    priority_order = ["EVIDENCE_FRESHNESS", "CUSTOMER_EXISTENCE", "PROBLEM_SEVERITY", "COMPETITION", "MARKET_SIGNAL"]

    def _is_weak(value):
        v = str(value)
        return v.startswith(("UNKNOWN", "NOT_MEASURABLE", "NOT_MEASURED", "requires", "STALE"))

    for name in priority_order:
        if name in dims and _is_weak(dims[name]["value"]):
            return {"cheapest_next_step": suggestions.get(name), "targets_dimension": name}

    remaining_weak = [name for name, d in dims.items() if _is_weak(d["value"])]
    if not remaining_weak:
        return {"cheapest_next_step": "No unknown/unfavorable dimensions remain -- opportunity is already maximally evidenced given real, available sources.", "targets_dimension": None}
    target = remaining_weak[0]
    return {
        "cheapest_next_step": suggestions.get(target, f"gather real evidence for {target} via an existing, already-approved discovery source"),
        "targets_dimension": target,
    }
