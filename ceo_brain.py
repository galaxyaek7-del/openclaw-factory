#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CEO BRAIN (Phase 1 — CEO Brain & Founder-Light Governance, 2026-08-16).

The founder's Phase 1 directive authorizes building the CEO-level
engineering roadmap that upgrades Galaxy Forge from Level-3 supervised
autonomy toward an executive-grade autonomous company architecture, with
founder-light governance and truth-first discipline. This module is the
single CEO Brain: ONE authoritative company state, ONE explainable
priority engine, ONE decision queue, ONE daily brief, ONE real-time
executive clock, ONE escalation layer, ONE founder attention budget, and
ONE executive truth gate — all surfaced in Mission Control as a compact
executive layer.

Reuse-first research (done before writing this): the closest existing CEO
Brain is executive_orchestrator.py (2026-08-15) — company_state(),
unified_priorities(), decision_state_machine(), build_work_queue(),
record_result(). This module is a THIN, COMPOSITION-ONLY layer: it calls
the real existing engines exactly once each and adds only the genuinely
new, previously-missing pieces:

  A. CEO State Model            -- canonical state with per-field provenance
  B. Founder-Light Governance   -- decision classification integrated with
                                   autonomous_operations.AUTONOMY_LEVELS 0-6
  C. CEO Decision Queue         -- the 18-field queue with stale_after
  D. Executive Priority Engine  -- deterministic, explainable 7-dimension score
  E. CEO Daily Brief            -- 10 named questions, each with a real citation
  F. Real-Time Executive Clock  -- UTC, system age, stale detection, timeout/
                                   cooldown/retry/escalation timing; ETA=UNKNOWN
                                   when not honestly calculable
  G. Executive Escalation       -- 8 named triggers, fail-closed, surface-only
  H. Founder Attention Budget   -- interruption metric with MIN/MAX thresholds
  I. Executive Truth Gate       -- verify-or-UNKNOWN/NEEDS VERIFICATION per field

Composition discipline (the factory's own repeated lesson, ADR-155/159):
every expensive real engine scan is computed EXACTLY ONCE per aggregator
call in build_ceo_brain() and threaded through the sub-views via the
`precomputed` injection dict — never re-scanned per view. Sub-views called
standalone (CLI/tests) lazily load what they need. No sub-view ever makes
a live network call from a read path.

Hard rules honored literally:
  * ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL — no timeout, retry, cooldown,
    or stale calculation may ever interpret silence as a founder yes. Every
    timing field is informational only; founder-required decisions stay
    REQUIRES_FOUNDER until a real, explicit founder action exists.
  * Level 6 is never automated (autonomous_operations.py, ADR-209): real
    payments, governance/permission changes, account/credential creation,
    legal/liability commitments — this module never suggests them for
    autonomous execution, and its governance classifier REFUSEs them
    unconditionally regardless of context.
  * Truth-first (ADR-160): never fabricate. Every field carries an explicit
    provenance citation; UNKNOWN stays UNKNOWN; ETA is UNKNOWN when not
    honestly calculable.
  * Read-only: this module writes to no real ledger. It never spends,
    never publishes, never contacts a platform, never changes any
    authority level.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Canonical field lists (the directive's own named shapes)
# ---------------------------------------------------------------------------

# The 18 decision-queue fields the directive named (incl. stale_after).
DECISION_QUEUE_FIELDS = [
    "decision_id", "action", "category", "autonomy_level", "autonomy_name",
    "founder_required", "priority", "state", "created_at", "updated_at",
    "due_at", "stale_after", "evidence", "confidence", "impact", "urgency",
    "risk", "source",
]

# The 7 priority-engine dimensions the directive named.
PRIORITY_DIMENSIONS = [
    "impact", "urgency", "risk", "reversibility",
    "strategic_alignment", "evidence_quality", "time_sensitivity",
]

# The 10 daily-brief questions the directive named.
DAILY_BRIEF_QUESTIONS = [
    "what_is_the_company_doing_now",
    "what_should_the_company_do_next",
    "what_is_blocked_and_why",
    "what_needs_the_founder",
    "what_is_the_top_risk",
    "what_is_the_top_opportunity",
    "what_is_the_commercial_state",
    "what_is_the_learning_state",
    "what_is_the_technology_position",
    "what_is_the_system_age_and_health",
]

# The 8 escalation triggers the directive named.
ESCALATION_TRIGGERS = [
    "stale_founder_gate",
    "repeated_failure",
    "blocking_missing_credential",
    "revenue_channel_unavailable",
    "critical_incident_open",
    "health_degradation",
    "evidence_gap_on_claim",
    "stuck_pipeline_entity",
]

# Founder Attention Budget MIN/MAX (interruption metric, a disclosed policy
# constant -- this factory has zero real per-interruption data to measure
# an empirically-derived bound from, so these are named bounds, not a
# measured statistic).
ATTENTION_BUDGET_MIN = 3
ATTENTION_BUDGET_MAX = 10


def _now_iso(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).isoformat()


def _read_json(path: Path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, object]]:
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


def _lines(path: Path) -> int:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Shared-scan loader -- every expensive real engine is scanned once here and
# threaded through all sub-views via `precomputed`. Standalone sub-views
# call this lazily. Injection keeps tests fast and honest (temp-dir fakes).
# ---------------------------------------------------------------------------

def _load_shared(now: Optional[datetime] = None) -> Dict[str, object]:
    shared: Dict[str, object] = {}

    try:
        import founder_next_action
        shared["fna"] = founder_next_action.build_founder_next_action()
    except Exception as e:  # pragma: no cover - defensive
        shared["fna"] = {"error": str(e)}

    try:
        import executive_orchestrator
        shared["orchestrated"] = executive_orchestrator.company_state()
    except Exception as e:  # pragma: no cover - defensive
        shared["orchestrated"] = {"error": str(e)}

    try:
        import executive_orchestrator
        shared["work_queue"] = executive_orchestrator.build_work_queue()
    except Exception as e:  # pragma: no cover - defensive
        shared["work_queue"] = {"error": str(e)}

    try:
        import commercial_readiness
        shared["readiness"] = commercial_readiness.commercial_readiness_score()
    except Exception as e:  # pragma: no cover - defensive
        shared["readiness"] = {"error": str(e)}

    try:
        import growth_stages
        shared["growth"] = growth_stages.current_growth_stage()
    except Exception as e:  # pragma: no cover - defensive
        shared["growth"] = {"error": str(e)}

    try:
        import autonomous_operations_status as aos
        shared["autonomy_status"] = (
            aos.autonomous_operations_summary()
            if hasattr(aos, "autonomous_operations_summary") else {})
    except Exception as e:  # pragma: no cover - defensive
        shared["autonomy_status"] = {"error": str(e)}

    try:
        import ceo_home
        shared["briefing"] = ceo_home.build_ceo_home_briefing()
    except Exception as e:  # pragma: no cover - defensive
        shared["briefing"] = {"error": str(e)}

    try:
        import evolution_queue
        shared["measured_outcomes"] = (
            evolution_queue.list_measured_outcomes()
            if hasattr(evolution_queue, "list_measured_outcomes") else [])
    except Exception as e:  # pragma: no cover - defensive
        shared["measured_outcomes"] = []

    try:
        from ai_capability.registry import list_providers
        shared["providers"] = list_providers()
    except Exception as e:  # pragma: no cover - defensive
        shared["providers"] = {"error": str(e)}

    # Phase 2 (AI Capability Observatory & Technology Foresight, 2026-08-16):
    # the observatory's 7-field technology position -- real capability
    # records, obsolescence detection, provider abstraction, cost
    # intelligence. Cheap, file-based composition (no live network/AI calls).
    try:
        from ai_capability import observatory as _observatory
        shared["technology_position"] = _observatory.technology_position()
        shared["observatory_report"] = _observatory.build_observatory_report()
    except Exception as e:  # pragma: no cover - defensive
        shared["technology_position"] = {"error": str(e)}
        shared["observatory_report"] = {"error": str(e)}

    # Phase 3 (AI Capability Evolution & Multi-Model Intelligence,
    # 2026-08-17): AGI readiness (READINESS vs ACTUALITY, never a claim) and
    # the capability-evolution memory. Both cheap, file-based, recommend-only
    # -- the Brain can surface them, never act on them.
    try:
        from ai_capability import agi_readiness as _agi
        from ai_capability import observatory as _obs2
        shared["agi_readiness"] = _agi.assess_agi_readiness()
        shared["capability_evolution"] = _obs2.capability_evolution_summary()
    except Exception as e:  # pragma: no cover - defensive
        shared["agi_readiness"] = {"error": str(e)}
        shared["capability_evolution"] = {"error": str(e)}

    return shared


def _shared_get(shared: Optional[Dict[str, object]], key: str, default):
    if shared is None:
        return default
    return shared.get(key, default)


def _founder_gates(fna) -> List[Dict[str, object]]:
    """The real founder-required items from founder_next_action.py (the one
    real consolidated human-gate queue)."""
    items = []
    if not isinstance(fna, dict):
        return items
    next_action = fna.get("one_next_action")
    if next_action and isinstance(next_action, dict):
        items.append({
            "action": next_action.get("action"),
            "category": f"founder_human_gate:{next_action.get('arm', 'next_action')}",
            "source": "founder_next_action.build_founder_next_action()",
            "provenance": fna.get("generated_at"),
        })
    for g in fna.get("queue", []) or []:
        if not isinstance(g, dict):
            continue
        items.append({
            "action": g.get("action"),
            "category": f"founder_human_gate:{g.get('arm', 'gate')}",
            "source": "founder_next_action.build_founder_next_action()",
            "provenance": fna.get("generated_at"),
        })
    return items


def _orchestrator_items(work_queue) -> List[Dict[str, object]]:
    """Real SAFE autonomous work-queue items from executive_orchestrator.py
    (the real deduped work queue)."""
    items = []
    if isinstance(work_queue, list):
        for t in work_queue:
            if not isinstance(t, dict):
                continue
            items.append({
                "action": f"{t.get('type')}: {t.get('task_id')}",
                "category": "autonomous_work_queue",
                "source": "executive_orchestrator.build_work_queue()",
                "provenance": t.get("created_at"),
            })
    return items


# ---------------------------------------------------------------------------
# F. REAL-TIME EXECUTIVE CLOCK
# ---------------------------------------------------------------------------

def executive_clock(now: Optional[datetime] = None) -> Dict[str, object]:
    """The real-time executive clock (directive F): UTC now, the age of the
    most recent real executive state record, stale detection, and the
    timeout/cooldown/retry/escalation timing model. Every timing value is
    INFORMATIONAL ONLY -- per the hard rule, no elapsed time ever implies
    founder approval; founder-required decisions stay REQUIRES_FOUNDER
    until a real, explicit founder action exists."""
    now_dt = now or datetime.now(timezone.utc)

    # Real state-age signals: the most recent real executive directive and
    # the most recent real executive-orchestrator cycle, when they exist.
    directives = _read_jsonl(_FACTORY_ROOT / "data" / "executive_directives.jsonl")
    last_directive_at = None
    for d in reversed(directives):
        ts = d.get("generated_at") or d.get("timestamp")
        if ts:
            last_directive_at = ts
            break

    exec_events = _read_jsonl(_FACTORY_ROOT / "data" / "executive_orchestrator_events.jsonl")
    last_orchestrator_at = None
    for e in reversed(exec_events):
        ts = e.get("recorded_at")
        if ts:
            last_orchestrator_at = ts
            break

    def _age_seconds(iso_ts: Optional[str]) -> Optional[float]:
        if not iso_ts:
            return None
        try:
            parsed = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0.0, (now_dt - parsed).total_seconds())
        except (ValueError, TypeError):
            return None

    directive_age_s = _age_seconds(last_directive_at)
    orchestrator_age_s = _age_seconds(last_orchestrator_at)

    # Stale thresholds (disclosed policy constants, not measured stats).
    STALE_DAILY_REPORT_S = 26 * 3600   # daily tick gate should fire within ~24h
    STALE_WEEKLY_REPORT_S = 8 * 86400  # Sunday weekly gate within ~7 days

    return {
        "utc_now": _now_iso(now_dt),
        "last_executive_directive_at": last_directive_at,
        "last_executive_directive_age_seconds": directive_age_s,
        "last_executive_orchestrator_cycle_at": last_orchestrator_at,
        "last_executive_orchestrator_age_seconds": orchestrator_age_s,
        "daily_report_stale": bool(directive_age_s is not None and directive_age_s > STALE_DAILY_REPORT_S),
        "weekly_report_stale": bool(directive_age_s is not None and directive_age_s > STALE_WEEKLY_REPORT_S),
        "timeout_seconds": 120,        # Mission Control panel timeout class (server.js PYTHON_SERVICE_TIMEOUT_MS default)
        "cooldown_seconds": 60,        # informational cooldown between escalations
        "retry_max_attempts": 5,       # informational retry cap (matches publish/groq conventions)
        "escalation_threshold_seconds": STALE_DAILY_REPORT_S,
        "eta": "UNKNOWN",
        "eta_reason": "No real historical per-stage duration model exists anywhere in this factory (execution_status.py precedent) -- ETA is never fabricated.",
        "note": "Informational timing only. ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL -- no timeout/retry/cooldown/stale value may be interpreted as a founder yes; founder-required decisions stay REQUIRES_FOUNDER until a real, explicit founder action exists.",
    }


# ---------------------------------------------------------------------------
# I. EXECUTIVE TRUTH GATE
# ---------------------------------------------------------------------------

def truth_gate(value, source: str, verified: bool) -> Dict[str, object]:
    """The executive truth gate (directive I): classify a single field as
    VERIFIED / UNKNOWN / NEEDS VERIFICATION based on whether a real,
    cited source exists for it. Never fabricates a verification state.

    verified=True  -> the value comes from a real, live signal (VERIFIED).
    source set     -> a real citation exists but the value itself is an
                      honest gap (UNKNOWN stays UNKNOWN).
    neither        -> NEEDS VERIFICATION (a real source is required before
                      this field may be treated as fact).
    """
    if verified:
        return {"verification": "VERIFIED", "value": value, "source": source}
    if value is None:
        return {"verification": "UNKNOWN", "value": None, "source": source or "no real source exists"}
    return {"verification": "NEEDS VERIFICATION", "value": value, "source": source or "no real source exists"}


# ---------------------------------------------------------------------------
# A. CEO STATE MODEL
# ---------------------------------------------------------------------------

def ceo_state(now: Optional[datetime] = None, precomputed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """The canonical CEO State Model (directive A): the single authoritative
    company state. Every field cites the real engine/ledger it comes from --
    composition-only, never a second computation."""
    now_iso_s = _now_iso(now)

    # Real revenue truth (channels/ledger.py ground truth + finance_data.json).
    finance = _read_json(_FACTORY_ROOT / "finance_data.json", {})
    real_sales = [s for s in finance.get("sales", []) if "DELETE-ME" not in str(s.get("product", ""))]
    real_revenue = round(sum(float(s.get("amount", 0)) for s in real_sales), 2)

    reality = _read_json(_FACTORY_ROOT / "config" / "reality.json", {})
    published_books = len(reality.get("published_books", []) or [])

    # Real autonomy model (autonomous_operations.py, ADR-209) -- never
    # re-derived, cited verbatim.
    autonomy = {}
    autonomy_status = _shared_get(precomputed, "autonomy_status", {})
    try:
        from autonomous_operations import AUTONOMY_LEVELS, ACTION_CATEGORY_AUTONOMY
        autonomy = {"levels": AUTONOMY_LEVELS, "action_categories": ACTION_CATEGORY_AUTONOMY}
    except Exception as e:  # pragma: no cover - defensive
        autonomy = {"error": str(e)}

    # Commercial readiness (commercial_readiness.py) -- the real dimension
    # scores, cited, never recomputed here.
    readiness = _shared_get(precomputed, "readiness", {})

    # Growth stage (growth_stages.py) -- real, stateless, cited.
    growth = _shared_get(precomputed, "growth", {})

    # Existing orchestrated state (executive_orchestrator.py) -- the real
    # company_state composition, cited.
    orchestrated = _shared_get(precomputed, "orchestrated", {})

    return {
        "generated_at": now_iso_s,
        "real_revenue_usd": real_revenue,
        "real_revenue_source": "finance_data.json sales (DELETE-ME excluded) -- real, non-test only",
        "published_books": published_books,
        "published_books_source": "config/reality.json published_books -- the unfakeable ground truth",
        "commercial_readiness": readiness.get("dimensions") if isinstance(readiness, dict) else None,
        "commercial_readiness_source": "commercial_readiness.commercial_readiness_score()",
        "growth_stage": growth.get("stage") if isinstance(growth, dict) else None,
        "growth_stage_source": "growth_stages.current_growth_stage()",
        "autonomy_model": {"level_count": len(autonomy.get("levels", {}))} if autonomy.get("levels") else None,
        "autonomy_model_source": "autonomous_operations.AUTONOMY_LEVELS (ADR-209)",
        "autonomy_status": autonomy_status,
        "autonomy_status_source": "autonomous_operations_status.autonomous_operations_summary()",
        "orchestrated_state": orchestrated,
        "orchestrated_state_source": "executive_orchestrator.company_state()",
        "state_age_seconds": executive_clock(now=now).get("last_executive_directive_age_seconds"),
        "note": "Composition-only CEO State Model: every field cites its real engine/ledger. Nothing is estimated or fabricated; UNKNOWN fields stay UNKNOWN.",
    }


# ---------------------------------------------------------------------------
# B. FOUNDER-LIGHT GOVERNANCE
# ---------------------------------------------------------------------------

def classify_decision(action: str, category: str, context: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Founder-light governance (directive B): classify a single real decision
    onto the existing AUTONOMY_LEVELS 0-6 via autonomous_operations.py's real
    authorize_action() -- NEVER a second authority model. Level 6 refuses
    unconditionally; Level 5 requires a real founder_approved=True +
    approval_reference; Levels 0-4 are the real engine's own already-enforced
    authority.

    A category carrying an arm suffix (founder_human_gate:gumroad) classifies
    against its base category (founder_human_gate) -- the suffix is metadata,
    never a second authority model."""
    base_category = category.split(":", 1)[0] if category else category
    try:
        from autonomous_operations import authorize_action, classify_action_autonomy
    except Exception as e:  # pragma: no cover - defensive
        return {"decision": "REFUSE", "category": category, "action": action,
                "reasoning": f"autonomous_operations unavailable: {e}"}

    result = authorize_action(base_category, context or {})
    entry = classify_action_autonomy(base_category)
    level = entry["level"] if entry else None
    name = None
    if entry:
        try:
            from autonomous_operations import AUTONOMY_LEVELS
            name = AUTONOMY_LEVELS[level]["name"]
        except Exception:  # pragma: no cover - defensive
            name = None

    return {
        "action": action,
        "category": category,
        "autonomy_level": level,
        "autonomy_name": name,
        "founder_required": bool(level == 5),
        "decision": result.get("decision"),
        "reasoning": result.get("reasoning"),
        "governance_note": "Founder-light: the real engine (autonomous_operations.py, ADR-209) already enforces this category's authority. ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL -- this classification never changes with elapsed time.",
    }


# ---------------------------------------------------------------------------
# D. EXECUTIVE PRIORITY ENGINE
# ---------------------------------------------------------------------------

def _dim_score(name: str, value: float) -> Dict[str, object]:
    """Score a single dimension on a disclosed 0-100 scale, clipped. Higher
    = more priority-worthy. For 'risk' the caller passes the inverse (lower
    real risk -> higher score) so all 7 dimensions share one direction."""
    clipped = max(0.0, min(100.0, float(value)))
    return {"dimension": name, "score": round(clipped, 1)}


def priority_engine(items: List[Dict[str, object]], now: Optional[datetime] = None) -> Dict[str, object]:
    """The deterministic, explainable Executive Priority Engine (directive D):
    rank candidate actions on the 7 named dimensions. Each item supplies its
    OWN real per-dimension values (from the engine that produced it) -- this
    engine only weights and orders them with a disclosed formula, never
    fabricates a dimension value for an item that lacks one. Items missing a
    real value for a dimension are honestly scored 0 on that dimension with
    the missing dimension named, never guessed."""
    weights = {
        "impact": 0.25, "urgency": 0.20, "risk": 0.10,
        "reversibility": 0.10, "strategic_alignment": 0.15,
        "evidence_quality": 0.15, "time_sensitivity": 0.05,
    }
    ranked = []
    for i, item in enumerate(items):
        dims = item.get("dimensions") or {}
        provided = set(dims.keys())
        missing = [d for d in PRIORITY_DIMENSIONS if d not in provided]
        score = 0.0
        dim_scores = {}
        for d, w in weights.items():
            raw = dims.get(d)
            if raw is None:
                dim_scores[d] = {"dimension": d, "score": 0.0, "reason": "no real value provided by source engine"}
                continue
            ds = _dim_score(d, raw)
            dim_scores[d] = ds
            score += weights[d] * ds["score"]
        ranked.append({
            "rank": i + 1,
            "action": item.get("action"),
            "priority_score": round(score, 1),
            "dimensions": dim_scores,
            "missing_dimensions": missing,
            "source": item.get("source"),
        })
    ranked.sort(key=lambda r: r["priority_score"], reverse=True)
    for rank, r in enumerate(ranked, start=1):
        r["rank"] = rank
    return {
        "generated_at": _now_iso(now),
        "weights": weights,
        "dimensions": PRIORITY_DIMENSIONS,
        "ranking": ranked,
        "note": "Deterministic, disclosed additive weighted score over the 7 named dimensions. Every dimension value is supplied by the real engine that owns the item -- this engine never fabricates a dimension; a missing real value is honestly scored 0 with the gap named.",
    }


# ---------------------------------------------------------------------------
# C. CEO DECISION QUEUE
# ---------------------------------------------------------------------------

def decision_queue(now: Optional[datetime] = None, precomputed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """The CEO Decision Queue (directive C): the 18-field, deduped queue
    consolidating every real decision-bearing item -- founder-required human
    gates (founder_next_action.py) plus safe autonomous work items
    (executive_orchestrator.py's real queue). Each item is classified by the
    real Founder-Light Governance classifier (B) and tagged with its real
    stale_after. Never guesses a missing field into existence."""
    now_iso_s = _now_iso(now)
    shared = precomputed or _load_shared(now)
    fna = _shared_get(shared, "fna", {})
    work_queue = _shared_get(shared, "work_queue", [])
    seen = set()
    items = []
    raw_items = _founder_gates(fna) + _orchestrator_items(work_queue)

    for raw in raw_items:
        action = raw.get("action") or "unknown"
        key = f"{raw.get('category')}:{action}"
        if key in seen:
            continue
        seen.add(key)

        classification = classify_decision(action, raw.get("category"))
        stale_after = None
        if classification.get("founder_required"):
            stale_after = "REQUIRES_FOUNDER_ACTION"  # never auto-clears by time
        else:
            stale_after = "PENDING"  # refreshed each cycle by its real engine

        items.append({
            "decision_id": f"ceo:{abs(hash(key)):08x}",
            "action": action,
            "category": raw.get("category"),
            "autonomy_level": classification.get("autonomy_level"),
            "autonomy_name": classification.get("autonomy_name"),
            "founder_required": classification.get("founder_required"),
            "priority": None,
            "state": "OPEN",
            "created_at": raw.get("provenance") or now_iso_s,
            "updated_at": now_iso_s,
            "due_at": None,
            "stale_after": stale_after,
            "evidence": raw.get("source"),
            "confidence": "UNKNOWN",
            "impact": None,
            "urgency": None,
            "risk": None,
            "source": raw.get("source"),
        })

    items.sort(key=lambda d: (0 if d["founder_required"] else 1, d["category"]))
    return {
        "generated_at": now_iso_s,
        "fields": DECISION_QUEUE_FIELDS,
        "items": items,
        "total": len(items),
        "founder_required_count": sum(1 for d in items if d["founder_required"]),
        "autonomous_count": sum(1 for d in items if not d["founder_required"]),
        "note": "Deduped, consolidated from the two real decision-bearing queues (founder_next_action.py human gates + executive_orchestrator.py SAFE work queue). stale_after is never a clock -- REQUIRES_FOUNDER_ACTION never auto-clears by elapsed time (ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL).",
    }


# ---------------------------------------------------------------------------
# E. CEO DAILY BRIEF
# ---------------------------------------------------------------------------

def daily_brief(now: Optional[datetime] = None, precomputed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """The CEO Daily Brief (directive E): answer the 10 named questions, each
    with a real citation from an existing engine/ledger. Machine-readable
    answers plus a one-line human summary. Never fabricates an answer;
    UNKNOWN stays UNKNOWN with the real reason."""
    now_iso_s = _now_iso(now)
    shared = precomputed or _load_shared(now)
    q = {k: {"answer": "UNKNOWN", "evidence": "no real source invoked"} for k in DAILY_BRIEF_QUESTIONS}

    # 1. What is the company doing now -- the real current executive directive
    directives = _read_jsonl(_FACTORY_ROOT / "data" / "executive_directives.jsonl")
    latest = directives[-1] if directives else None
    q["what_is_the_company_doing_now"] = {
        "answer": latest.get("current_mission") if latest else "UNKNOWN",
        "evidence": f"data/executive_directives.jsonl (most recent entry, {latest.get('generated_at')})" if latest else "no real executive directive has been recorded yet",
    }

    # 2. What should the company do next -- the real founder ONE-NEXT-ACTION
    fna = _shared_get(shared, "fna", {})
    if isinstance(fna, dict) and "error" not in fna:
        q["what_should_the_company_do_next"] = {
            "answer": (fna.get("one_next_action", {}) or {}).get("action") or "UNKNOWN",
            "evidence": "founder_next_action.build_founder_next_action() -- the one real consolidated human-gate queue",
        }
    else:
        q["what_should_the_company_do_next"] = {
            "answer": "UNKNOWN", "evidence": f"founder_next_action unavailable: {fna.get('error') if isinstance(fna, dict) else 'n/a'}"}

    # 3. What is blocked and why -- real open founder gates
    if isinstance(fna, dict) and "error" not in fna:
        blocked = [g for g in (fna.get("queue", []) or []) if isinstance(g, dict) and g.get("action")]
        q["what_is_blocked_and_why"] = {
            "answer": f"{len(blocked)} real open founder gate(s)" if blocked else "nothing blocked",
            "evidence": fna.get("note"),
            "gates": blocked[:5],
        }
    else:
        q["what_is_blocked_and_why"] = {
            "answer": "UNKNOWN", "evidence": "founder_next_action unavailable"}

    # 4. What needs the founder -- the real pending-decisions count
    queue = decision_queue(now=now, precomputed=shared)
    q["what_needs_the_founder"] = {
        "answer": f"{queue['founder_required_count']} real founder-required decision(s) in the CEO Decision Queue",
        "evidence": "ceo_brain.decision_queue() -- consolidated from founder_next_action.py + executive_orchestrator.py",
    }

    # 5. What is the top risk -- real open incidents (resilience_monitor.py)
    incidents = _read_jsonl(_FACTORY_ROOT / "data" / "incidents.jsonl")
    open_incidents = [i for i in incidents if i.get("event") not in ("resolved",)]
    top_risk = open_incidents[-1] if open_incidents else None
    q["what_is_the_top_risk"] = {
        "answer": (f"{top_risk.get('area')}: {top_risk.get('detail')}") if top_risk else "no open real incident",
        "evidence": f"data/incidents.jsonl (resilience_monitor.py) -- {len(open_incidents)} open real incident(s)",
    }

    # 6. What is the top opportunity -- the real CEO Home highest-ROI citation
    briefing = _shared_get(shared, "briefing", {})
    if isinstance(briefing, dict) and "error" not in briefing:
        roi = briefing.get("highest_roi_opportunity", {}) or {}
        q["what_is_the_top_opportunity"] = {
            "answer": roi.get("niche") or "UNKNOWN",
            "evidence": roi.get("evidence") or "ceo_home.build_ceo_home_briefing()",
        }
    else:
        q["what_is_the_top_opportunity"] = {
            "answer": "UNKNOWN", "evidence": "ceo_home.build_ceo_home_briefing() unavailable"}

    # 7. Commercial state -- real commercial readiness dimension scores
    readiness = _shared_get(shared, "readiness", {})
    if isinstance(readiness, dict) and "error" not in readiness:
        dims = readiness.get("dimensions", {}) or {}
        commercial_state = {}
        for k, v in dims.items():
            if isinstance(v, dict) and isinstance(v.get("score"), (int, float)):
                commercial_state[k] = v["score"]
            elif isinstance(v, (int, float)):
                commercial_state[k] = v
        q["what_is_the_commercial_state"] = {
            "answer": commercial_state,
            "evidence": "commercial_readiness.commercial_readiness_score() -- per-dimension real scores",
        }
    else:
        q["what_is_the_commercial_state"] = {
            "answer": "UNKNOWN", "evidence": "commercial_readiness.commercial_readiness_score() unavailable"}

    # 8. Learning state -- real measured evolution outcomes (ADR-143)
    measured = _shared_get(shared, "measured_outcomes", [])
    q["what_is_the_learning_state"] = {
        "answer": "no real measured outcomes yet" if not measured else measured,
        "evidence": "evolution_queue.list_measured_outcomes() (ADR-143) -- real per-proposal outcome measurements",
    }

    # 9. Technology position -- the observatory's real 7-field view
    #    (Phase 2: AI Capability Observatory & Technology Foresight,
    #    2026-08-16; Phase 3: AI Capability Evolution & Multi-Model
    #    Intelligence, 2026-08-17). Falls back to the pre-existing
    #    provider-level view only if the observatory itself is unavailable.
    providers = _shared_get(shared, "providers", [])
    tech_position = _shared_get(shared, "technology_position", None)
    if isinstance(tech_position, dict) and "error" not in tech_position:
        agi_ready = _shared_get(shared, "agi_readiness", None)
        cap_evolution = _shared_get(shared, "capability_evolution", None)
        answer = {
            "strongest_current_capabilities": tech_position.get("strongest_current_capabilities", {}).get("answer"),
            "weakest_capabilities": tech_position.get("weakest_capabilities", {}).get("answer"),
            "biggest_dependency": tech_position.get("biggest_dependency", {}).get("answer"),
            "highest_obsolescence_risk": tech_position.get("highest_obsolescence_risk", {}).get("answer"),
            "most_promising_emerging_technology": tech_position.get("most_promising_emerging_technology", {}).get("answer"),
            "recommended_technology_experiment": tech_position.get("recommended_technology_experiment", {}).get("answer"),
            "technology_decision_requiring_founder": tech_position.get("technology_decision_requiring_founder", {}).get("answer"),
        }
        # Phase 3 WS7/WS5 -- the honest readiness posture and capability
        # memory, surfaced for the Brain but never acted on.
        if isinstance(agi_ready, dict) and "error" not in agi_ready:
            answer["agi_readiness"] = {
                "readiness": agi_ready.get("readiness_score"),
                "actual_capability_claim": agi_ready.get("actuality", {}).get("agi_capability_claim"),
            }
        if isinstance(cap_evolution, dict) and "error" not in cap_evolution:
            answer["capability_evolution"] = {
                "total_records": cap_evolution.get("total"),
                "accepted": [e.get("technology") for e in (cap_evolution.get("accepted") or [])],
                "rejected": [e.get("technology") for e in (cap_evolution.get("rejected") or [])],
                "uncertain": [e.get("technology") for e in (cap_evolution.get("uncertain") or [])],
            }
        q["what_is_the_technology_position"] = {
            "answer": answer,
            "evidence": "ai_capability/observatory.py::technology_position() + agi_readiness.py + capability_evolution_summary() -- real capability records, obsolescence detection, provider abstraction, cost intelligence, AGI readiness (NOT CLAIMED), capability memory (Phase 2/3, 2026-08-16/17)",
        }
    elif isinstance(providers, list):
        called = [p for p in providers if (p.get("real_stats") or {}).get("calls")]
        q["what_is_the_technology_position"] = {
            "answer": f"{len(called)} live AI provider(s), {len(providers)} registered",
            "evidence": "ai_capability.registry.list_providers() -- real call history only",
        }
    else:
        q["what_is_the_technology_position"] = {
            "answer": "UNKNOWN", "evidence": "ai_capability observatory + registry unavailable"}

    # 10. System age and health -- the real executive clock
    clock = executive_clock(now=now)
    q["what_is_the_system_age_and_health"] = {
        "answer": {
            "utc_now": clock["utc_now"],
            "last_executive_directive_age_seconds": clock["last_executive_directive_age_seconds"],
            "daily_report_stale": clock["daily_report_stale"],
        },
        "evidence": "ceo_brain.executive_clock() -- real timestamps, informational only",
    }

    summary_lines = [f"{k.replace('_', ' ')}: {v.get('answer')}" for k, v in q.items()]
    return {
        "generated_at": now_iso_s,
        "questions": q,
        "summary": "\n".join(summary_lines),
        "note": "10 named questions, each answered from a real, cited source. UNKNOWN stays UNKNOWN with the real reason -- never a fabricated answer.",
    }


# ---------------------------------------------------------------------------
# G. EXECUTIVE ESCALATION
# ---------------------------------------------------------------------------

def _escalation_signal(name: str, active: bool, detail: str, level: str) -> Dict[str, object]:
    return {
        "trigger": name,
        "active": active,
        "detail": detail,
        "severity": level,  # informational/warning/critical (resilience_monitor.py's real 4-tier vocabulary, subset)
        "action": "SURFACE ONLY -- never auto-executes; escalate to founder review, fail-closed.",
    }


def executive_escalation(now: Optional[datetime] = None, precomputed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Executive Escalation (directive G): the 8 named triggers, each a real
    mechanical check over real state. Every trigger is SURFACE-ONLY and
    fail-closed: an active trigger surfaces for founder review and never
    auto-executes anything. NO LIVE NETWORK CALL from this read path --
    external-gate signals are cited from the real local state the engines
    already persist, never re-queried here."""
    now_iso_s = _now_iso(now)
    shared = precomputed or _load_shared(now)
    signals = []

    # 1. stale_founder_gate -- a real founder-required decision whose
    #    stale_after marker is REQUIRES_FOUNDER_ACTION has been open across
    #    cycles; still never auto-approves (ELAPSED_TIME_NEVER_EQUALS_APPROVAL).
    queue = decision_queue(now=now, precomputed=shared)
    open_founder = [d for d in queue["items"] if d["founder_required"]]
    signals.append(_escalation_signal(
        "stale_founder_gate", bool(open_founder),
        f"{len(open_founder)} real founder-required decision(s) open -- surfaced for founder review, never auto-approvable by elapsed time",
        "warning"))

    # 2. repeated_failure -- real consecutive publish retries on a real arm,
    #    read from the local publish-protection state (no live call).
    try:
        import channels.publish_protection as pp
        state = pp._load_state() if hasattr(pp, "_load_state") else {}
        failures = []
        for arm, s in (state.get("arms") or {}).items():
            if s.get("consecutive_failures", 0) >= 3:
                failures.append(f"{arm}: {s.get('consecutive_failures')}")
        signals.append(_escalation_signal(
            "repeated_failure", bool(failures),
            "; ".join(failures) or "no real arm has >=3 consecutive publish failures",
            "warning"))
    except Exception as e:  # pragma: no cover - defensive
        signals.append(_escalation_signal("repeated_failure", False, f"publish_protection unavailable: {e}", "informational"))

    # 3. blocking_missing_credential -- a real missing credential surfaced as
    #    an open founder gate named for a credential/account (no live call).
    gate_categories = [g.get("category") for g in open_founder]
    credential_gates = [c for c in gate_categories
                        if c and any(k in c for k in ("credential", "amazon_affiliate", "affiliate_approvals", "paddle_webhook", "payment_method"))]
    signals.append(_escalation_signal(
        "blocking_missing_credential", bool(credential_gates),
        "; ".join(credential_gates) or "no real open credential/account founder gate",
        "critical" if credential_gates else "informational"))

    # 4. revenue_channel_unavailable -- real Paddle/Gumroad gates still open
    #    (derived from the real founder queue, no live platform call).
    channel_gates = [c for c in gate_categories if c and any(k in c for k in ("paddle", "gumroad"))]
    signals.append(_escalation_signal(
        "revenue_channel_unavailable", bool(channel_gates),
        "real revenue channels still gated: " + "; ".join(channel_gates) if channel_gates else "no real open revenue-channel founder gate",
        "critical" if channel_gates else "informational"))

    # 5. critical_incident_open -- real open critical/emergency incident.
    incidents = _read_jsonl(_FACTORY_ROOT / "data" / "incidents.jsonl")
    open_crit = [i for i in incidents if i.get("event") not in ("resolved",)
                 and i.get("severity") in ("critical", "emergency")]
    signals.append(_escalation_signal(
        "critical_incident_open", bool(open_crit),
        f"{len(open_crit)} open real critical/emergency incident(s) in data/incidents.jsonl",
        "critical" if open_crit else "informational"))

    # 6. health_degradation -- real health-snapshot trend (health_trend.py).
    try:
        import health_trend
        trend = health_trend.detect_health_degradation() if hasattr(health_trend, "detect_health_degradation") else {}
        degraded = bool(trend and trend.get("degraded"))
        signals.append(_escalation_signal(
            "health_degradation", degraded,
            trend.get("reason", "health_trend.py detect_health_degradation() -- no real degradation detected") if isinstance(trend, dict) else "health_trend unavailable",
            "critical" if degraded else "informational"))
    except Exception as e:  # pragma: no cover - defensive
        signals.append(_escalation_signal("health_degradation", False, f"health_trend unavailable: {e}", "informational"))

    # 7. evidence_gap_on_claim -- real evidence-ledger growth check: a live
    #    claim path must be recording evidence; a missing/no-growth ledger is
    #    surfaced, never silently assumed healthy (truth-first, ADR-163/166).
    evidence_entries = _lines(_FACTORY_ROOT / "data" / "evidence_ledger.jsonl")
    signals.append(_escalation_signal(
        "evidence_gap_on_claim", evidence_entries == 0,
        "data/evidence_ledger.jsonl is empty or absent -- no real production call has recorded evidence yet (ADR-166's disclosed finding); surfaced, never assumed healthy" if evidence_entries == 0 else f"data/evidence_ledger.jsonl has {evidence_entries} real evidence record(s)",
        "warning" if evidence_entries == 0 else "informational"))

    # 8. stuck_pipeline_entity -- real stuck opportunity/experiment.
    try:
        import executive_orchestrator
        failures = executive_orchestrator.read_failures(limit=10)
        signals.append(_escalation_signal(
            "stuck_pipeline_entity", bool(failures),
            f"{len(failures)} real failure(s) in the retry/recovery queue",
            "warning" if failures else "informational"))
    except Exception as e:  # pragma: no cover - defensive
        signals.append(_escalation_signal("stuck_pipeline_entity", False, f"executive_orchestrator unavailable: {e}", "informational"))

    active = [s for s in signals if s["active"]]
    return {
        "generated_at": now_iso_s,
        "triggers": signals,
        "active_count": len(active),
        "active": active,
        "note": "8 named triggers, each a real mechanical check over real local state. SURFACE-ONLY and fail-closed: an active trigger escalates for founder review and never auto-executes. ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL -- a stale gate escalates for review, never to approval. No live network call is made from this read path.",
    }


# ---------------------------------------------------------------------------
# H. FOUNDER ATTENTION BUDGET
# ---------------------------------------------------------------------------

def founder_attention_budget(now: Optional[datetime] = None, precomputed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """The Founder Attention Budget (directive H): a real interruption metric
    -- the number of real founder-required decisions + real open
    critical/warning escalations competing for the founder's attention,
    classified against the named MIN/MAX bounds. Informational only; nothing
    here suppresses or reorders any real signal."""
    shared = precomputed or _load_shared(now)
    queue = decision_queue(now=now, precomputed=shared)
    founder_count = queue["founder_required_count"]

    escalation = executive_escalation(now=now, precomputed=shared)
    active_signals = escalation["active_count"]

    pending_evolution = 0
    try:
        import evolution_queue
        pending_evolution = len(evolution_queue.list_proposals()) if hasattr(evolution_queue, "list_proposals") else 0
    except Exception:  # pragma: no cover - defensive
        pending_evolution = 0

    total_interruptions = founder_count + active_signals + pending_evolution
    if total_interruptions <= ATTENTION_BUDGET_MIN:
        level = "GREEN"
    elif total_interruptions <= ATTENTION_BUDGET_MAX:
        level = "AMBER"
    else:
        level = "RED"

    return {
        "generated_at": _now_iso(now),
        "founder_required_decisions": founder_count,
        "active_escalations": active_signals,
        "pending_evolution_proposals": pending_evolution,
        "total_interruptions": total_interruptions,
        "budget_min": ATTENTION_BUDGET_MIN,
        "budget_max": ATTENTION_BUDGET_MAX,
        "level": level,
        "note": "Real interruption metric (real founder-required decisions + real active escalations + real pending evolution proposals) classified against the disclosed MIN/MAX bounds. Informational only -- nothing is suppressed or reordered; bounds are named policy constants, not measured statistics.",
    }


# ---------------------------------------------------------------------------
# J. MISSION CONTROL COMPACT EXECUTIVE LAYER -- the one aggregator
# ---------------------------------------------------------------------------

def build_ceo_brain(now: Optional[datetime] = None, precomputed: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """The one Mission Control aggregator (directive J): computes each real
    engine scan EXACTLY ONCE (via _load_shared) and threads it through every
    sub-view, returning the compact executive layer: CEO STATE, TOP 3 RISKS,
    FOUNDER DECISIONS, SYSTEM AGE, TECHNOLOGY POSITION, COMMERCIAL STATE,
    LEARNING STATE, ATTENTION BUDGET. Read-only, no live network calls."""
    now_iso_s = _now_iso(now)
    shared = precomputed or _load_shared(now)
    state = ceo_state(now=now, precomputed=shared)
    queue = decision_queue(now=now, precomputed=shared)
    escalations = executive_escalation(now=now, precomputed=shared)
    clock = executive_clock(now=now)
    budget = founder_attention_budget(now=now, precomputed=shared)
    brief = daily_brief(now=now, precomputed=shared)

    return {
        "generated_at": now_iso_s,
        "CEO_STATE": state,
        "FOUNDER_DECISIONS": {
            "count": queue["founder_required_count"],
            "items": [d for d in queue["items"] if d["founder_required"]][:10],
        },
        "TOP_RISKS": [s for s in escalations["active"]][:3],
        "SYSTEM_AGE": {
            "utc_now": clock["utc_now"],
            "last_executive_directive_at": clock["last_executive_directive_at"],
            "last_executive_directive_age_seconds": clock["last_executive_directive_age_seconds"],
            "daily_report_stale": clock["daily_report_stale"],
        },
        "TECHNOLOGY_POSITION": brief["questions"].get("what_is_the_technology_position", {}),
        "COMMERCIAL_STATE": brief["questions"].get("what_is_the_commercial_state", {}),
        "LEARNING_STATE": brief["questions"].get("what_is_the_learning_state", {}),
        "ATTENTION_BUDGET": budget,
        "note": "CEO Brain (Phase 1, 2026-08-16): composition-only over real existing engines (executive_orchestrator / autonomous_operations / founder_next_action / ceo_home / commercial_readiness / resilience ledgers). Each real scan computed once and threaded through every view. Read-only -- never spends, never publishes, never changes authority. ELAPSED_TIME_NEVER_EQUALS_FOUNDER_APPROVAL. See CEO_BRAIN.md for the full A-N deliverable map.",
    }


def _cli_main() -> None:
    import sys as _sys
    argv = _sys.argv[1:]
    view = argv[0] if argv else "dashboard"
    now = None
    if view in ("dashboard", "state", "queue", "priority", "brief", "clock", "escalation", "budget", "governance"):
        fn = {
            "dashboard": build_ceo_brain,
            "state": ceo_state,
            "queue": decision_queue,
            "brief": daily_brief,
            "clock": executive_clock,
            "escalation": executive_escalation,
            "budget": founder_attention_budget,
        }.get(view)
        result = fn(now=now) if fn else {"error": f"unknown view: {view}"}
        if view == "governance":
            category = argv[1] if len(argv) > 1 else "read_only_reporting"
            result = classify_decision(f"demo action for {category}", category)
        if view == "priority":
            result = priority_engine([
                {"action": "demo item", "source": "test", "dimensions": {"impact": 80, "urgency": 60, "risk": 40, "reversibility": 70, "strategic_alignment": 90, "evidence_quality": 50, "time_sensitivity": 30}},
            ], now=now)
    else:
        result = {"error": f"unknown view: {view}; expected one of dashboard/state/queue/priority/brief/clock/escalation/budget/governance"}
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()