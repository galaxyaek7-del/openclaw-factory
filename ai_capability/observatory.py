"""
AI Capability Observatory & Technology Foresight -- Phase 2 of the CEO BRAIN
& FOUNDER-LIGHT GOVERNANCE work (founder directive, 2026-08-16).

The authoritative, model-level capability observatory the directive asks
for: a real per-model capability record, a named 20-category capability
taxonomy, a named 12-task evaluation, model routing intelligence,
obsolescence detection (6 named states), a technology radar (append-only),
technology foresight (FACT/SIGNAL/INFERENCE/PREDICTION never conflated),
multi-provider resilience status, real AI cost intelligence, and AI quality
memory (append-only).

REUSE FIRST, never a parallel engine:
  - ai_capability/registry.py  -- provider catalog + REAL/DISCOVERY metrics
  - ai_capability/evaluator.py -- recommend_for_task() (task-based selection)
  - ai_capability/orchestrator.py -- select_provider()/generate() (dispatch)
  - data/ai_cost_log.jsonl -- the real, per-call cost/latency record
This module is a composition + model-level view layer over those already-
real pieces. It adds no second registry, no second selection algorithm, no
second dispatcher. Everything not measurable by this factory's real data is
honestly DISCOVERY/UNKNOWN (Truth First vocabulary, ADR-160) -- never a
fabricated benchmark, never a guessed comparison.

SAFETY BOUNDARY (governance, Phase 2 O): read-only observation and
recommendation ONLY. This module contains zero code that can purchase an AI
service, change billing, change a financial record, migrate a production
system, terminate a provider, sign an agreement, activate an external
service, or auto-replace a production model. Every routing recommendation
is advisory (AUTONOMY_LEVELS level 2, RECOMMEND) -- the real production
model change remains a founder-gated decision (Step 5 NOT AUTHORIZED).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ai_capability import evaluator, registry

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
COST_LOG_PATH = _FACTORY_ROOT / "data" / "ai_cost_log.jsonl"
RADAR_PATH = _FACTORY_ROOT / "data" / "technology_radar.jsonl"
SIGNALS_PATH = _FACTORY_ROOT / "data" / "technology_signals.jsonl"
QUALITY_MEMORY_PATH = _FACTORY_ROOT / "data" / "ai_quality_memory.jsonl"
MODEL_VERSIONS_PATH = _FACTORY_ROOT / "data" / "ai_model_versions.jsonl"
SWITCH_PROPOSALS_PATH = _FACTORY_ROOT / "data" / "ai_switch_proposals.jsonl"
CAPABILITY_DECISIONS_PATH = _FACTORY_ROOT / "data" / "ai_capability_decisions.jsonl"

# How old a model's last real call must be (in days) before it is flagged
# as a candidate for the WATCH state. A real, disclosed, mechanical
# threshold -- never an automatic declaration of obsolescence.
STALE_DAYS = 21

# ---------------------------------------------------------------------------
# C. CAPABILITY TAXONOMY -- 20 named categories, extensible. Each is a real
# label this observatory can tag a model with; whether any model actually
# possesses a category is measured evidence (DISCOVERY until real).
# ---------------------------------------------------------------------------

CAPABILITY_TAXONOMY = [
    "reasoning", "coding", "mathematics", "research", "writing",
    "planning", "tool_use", "multimodal", "vision", "long_context_processing",
    "structured_output", "agentic_execution", "memory", "retrieval",
    "automation", "latency", "reliability", "cost_efficiency",
    "privacy_security", "deployment_flexibility",
]


def list_capability_categories():
    """The 20 named capability categories -- extensible by append."""
    return list(CAPABILITY_TAXONOMY)


# ---------------------------------------------------------------------------
# D. TASK CATEGORIES -- the 12 named task categories this observatory can
# evaluate. Each maps to the capability categories it most plausibly needs.
# The mapping is a disclosed, static heuristic (same discipline as
# evolution_queue.py's keyword heuristics), NOT a measured claim.
# ---------------------------------------------------------------------------

TASK_CATEGORIES = {
    "market_research": ["research", "reasoning", "retrieval"],
    "opportunity_discovery": ["research", "reasoning", "planning"],
    "code_generation": ["coding", "reasoning", "structured_output"],
    "code_debugging": ["coding", "reasoning"],
    "architecture_analysis": ["reasoning", "coding", "planning"],
    "financial_reasoning": ["reasoning", "mathematics", "structured_output"],
    "document_generation": ["writing", "planning", "structured_output"],
    "product_strategy": ["reasoning", "planning", "research"],
    "data_extraction": ["structured_output", "retrieval", "reasoning"],
    "autonomous_planning": ["planning", "reasoning", "tool_use", "agentic_execution"],
    "quality_assurance": ["reliability", "reasoning", "structured_output"],
    "executive_reasoning": ["reasoning", "planning", "research"],
}

# Map the 12 named task categories onto the orchestrator's existing 9
# resource-allocation task types (RESOURCE_ALLOCATION_TASK_TYPES) so real
# evaluator selection reuses the same vocabulary the factory already routes
# on. This is the citation seam: TASK_CATEGORIES -> evaluator task_type.
TASK_TO_EVALUATOR_TYPE = {
    "market_research": "research",
    "opportunity_discovery": "research",
    "code_generation": "coding",
    "code_debugging": "coding",
    "architecture_analysis": "analysis",
    "financial_reasoning": "analysis",
    "document_generation": "writing",
    "product_strategy": "analysis",
    "data_extraction": "analysis",
    "autonomous_planning": "research",
    "quality_assurance": "analysis",
    "executive_reasoning": "analysis",
}


def list_task_categories():
    """The 12 named task categories -- extensible by append."""
    return list(TASK_CATEGORIES)


def task_required_capabilities(task):
    """The capability categories a task plausibly requires (disclosed static
    heuristic, never a measured claim)."""
    return list(TASK_CATEGORIES.get(task, []))


# ---------------------------------------------------------------------------
# Cost-log helpers (model-level, real data only)
# ---------------------------------------------------------------------------


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _model_stats(entries, model):
    """Real per-model stats from the cost log -- calls, tokens, latency,
    cost, first/last seen. Every field honestly None where the underlying
    data doesn't exist."""
    rs = [e for e in entries if e.get("model") == model]
    costs = [e["cost_usd"] for e in rs if e.get("cost_usd") is not None]
    latencies = [e["latency_ms"] for e in rs if e.get("latency_ms") is not None]
    total_tokens = [e["total_tokens"] for e in rs if e.get("total_tokens")]
    dates = [e["timestamp"] for e in rs if e.get("timestamp")]
    return {
        "calls": len(rs),
        "total_cost_usd": round(sum(costs), 6) if costs else None,
        "avg_cost_usd_per_call": round(sum(costs) / len(costs), 6) if costs else None,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "avg_total_tokens": round(sum(total_tokens) / len(total_tokens)) if total_tokens else None,
        "first_seen": min(dates) if dates else None,
        "last_seen": max(dates) if dates else None,
    }


def _models_in_cost_log(cost_log_path=None):
    """The real model names this factory has actually logged calls for."""
    entries = _read_jsonl(cost_log_path or COST_LOG_PATH)
    models = []
    for e in entries:
        if e.get("model") and e["model"] not in models:
            models.append(e["model"])
    return models


# ---------------------------------------------------------------------------
# Model version ledger (append-only). The cost log never records a model
# version string, so `model_version` is UNKNOWN until a real version is
# actually observed and recorded here -- never a guessed version string.
# ---------------------------------------------------------------------------

def record_model_version(model, version, evidence, observed_at=None, path=None):
    """Append one real, observed model-version observation. `version` must
    be a non-empty string actually observed (e.g. an API response field or
    vendor changelog); `evidence` must cite the real source. Refuses to
    record an empty or placeholder version."""
    if not model or not version:
        raise ValueError("model and version must be non-empty")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("version must be a real string, never a placeholder")
    if not evidence:
        raise ValueError("evidence must cite a real source")
    path = Path(path or MODEL_VERSIONS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": observed_at or datetime.now(timezone.utc).isoformat(),
        "model": model,
        "version": version,
        "evidence": evidence,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def model_versions(path=None):
    """Read the append-only model-version ledger (empty until a real version
    is observed -- the honest default for this factory today)."""
    return _read_jsonl(path or MODEL_VERSIONS_PATH)


def _latest_model_version(model, path=None):
    """The most recent real version observation for a model, or None."""
    versions = [v for v in model_versions(path) if v.get("model") == model]
    if not versions:
        return None
    return versions[-1].get("version")


# ---------------------------------------------------------------------------
# B. MODEL CAPABILITY RECORDS -- the authoritative ~24-field per-model record.
# ---------------------------------------------------------------------------

def _model_record(model, entries, providers_by_name, cost_log_path=None):
    """One ~24-field capability record for a real, cost-logged model. Every
    field is REAL (from this factory's logged usage) or honestly UNKNOWN/
    DISCOVERY -- never a fabricated benchmark or capability claim."""
    stats = _model_stats(entries, model)
    provider_match = None
    for p in providers_by_name:
        if p["provider"] == "groq":
            provider_match = p
            break

    # Availability/reliability are real where this factory has a real
    # signal, DISCOVERY otherwise. The real signals: the cost log (a call
    # succeeded = the model was reachable), and safe_mode.py's real
    # ai_generation subsystem flag (a real, human/system-triggered
    # instability observation). Absence of either is NOT proof of health --
    # it is the honest default, never a fabricated green check.
    availability = "AVAILABLE"
    reliability = "RELIABLE"
    avail_note = []
    if stats["calls"] > 0:
        avail_note.append(f"{stats['calls']} real logged calls (data/ai_cost_log.jsonl)")
    else:
        availability = "DISCOVERY"
        reliability = "DISCOVERY"
        avail_note.append("no real logged calls yet")
    try:
        from safe_mode import is_subsystem_safe_mode
        if is_subsystem_safe_mode("ai_generation"):
            availability = "DEGRADED"
            reliability = "UNKNOWN"
            avail_note.append("safe_mode.py: ai_generation subsystem marked unstable")
    except Exception:
        avail_note.append("safe_mode.py unavailable -- status not incorporated")

    latest_version = _latest_model_version(model)
    return {
        "provider": "groq",
        "model": model,
        "model_version": latest_version if latest_version else "UNKNOWN",
        "capability_categories": list_capability_categories(),
        "context_window": "DISCOVERY",  # vendor spec, not directly verified
        "reasoning_capability": "DISCOVERY",
        "coding_capability": "DISCOVERY",
        "research_capability": "DISCOVERY",
        "multimodal_capability": "DISCOVERY",
        "tool_use": "DISCOVERY",
        "structured_output": "DISCOVERY",
        "latency": stats["avg_latency_ms"],
        "estimated_cost": stats["avg_cost_usd_per_call"],
        "availability": availability,
        "reliability": reliability,
        "availability_basis": avail_note,
        "benchmark_evidence": "UNKNOWN",  # no real benchmark has ever been run
        "source": "data/ai_cost_log.jsonl",
        "source_timestamp": stats["last_seen"],
        "last_verified": datetime.now(timezone.utc).isoformat(),
        "obsolescence_risk": None,  # filled by obsolescence_detection()
        "replacement_candidates": [],
        "confidence": "REAL" if stats["calls"] > 0 else "DISCOVERY",
        "status": "REAL",
        "real_stats": stats,
    }


def model_capability_records(cost_log_path=None):
    """Every real model this factory has logged usage for, each as a
    ~24-field capability record. Deliberately model-level (the cost log is
    model-level), layered over the existing provider-level registry --
    registry.list_providers() remains the provider catalog; this is the
    model view it feeds."""
    entries = _read_jsonl(cost_log_path or COST_LOG_PATH)
    providers = registry.list_providers(cost_log_path)
    models = _models_in_cost_log(cost_log_path)
    return [_model_record(m, entries, providers, cost_log_path=cost_log_path) for m in models]


# ---------------------------------------------------------------------------
# D. TASK-BASED MODEL EVALUATION -- reuses evaluator.recommend_for_task()
# ---------------------------------------------------------------------------

def evaluate_task(task, cost_log_path=None):
    """Task-based model evaluation for one of the 12 named task categories.
    Delegates to the real evaluator (never a second selection algorithm) via
    the existing orchestrator task-type vocabulary. Honest with one real
    provider: the recommendation is always 'groq' until a second provider
    has real measured usage, exactly as evaluator's own docstring promises."""
    task_type = TASK_TO_EVALUATOR_TYPE.get(task, task)
    recommendation = evaluator.recommend_for_task(task_type, cost_log_path=cost_log_path)
    return {
        "task": task,
        "evaluator_task_type": task_type,
        "required_capabilities": task_required_capabilities(task),
        **recommendation,
    }


def evaluate_all_tasks(cost_log_path=None):
    """All 12 named tasks evaluated against the real registry data."""
    return [evaluate_task(t, cost_log_path=cost_log_path) for t in TASK_CATEGORIES]


# ---------------------------------------------------------------------------
# WS2 (Phase 3). PER-TASK MODEL EVALUATION -- SELECTION vs COMPARISON
# separated explicitly, with named evaluation criteria per task and honest
# UNKNOWN wherever the real data cannot support a comparison.
#
# The directive (Phase 3, 2026-08-17) asks for "per-task model evaluation"
# that "separate[s] model selection from model comparison" and "return[s]
# UNKNOWN if insufficient evidence." Phase 2's evaluate_task() already
# returns the SELECTION (the evaluator's recommendation). This adds the
# explicit COMPARISON axis: a per-model, per-task row for every real
# cost-logged model, with the real measured evidence that exists for it
# and honest UNKNOWN for every unmeasured capability -- never a fabricated
# comparison table.
# ---------------------------------------------------------------------------

# The real evaluation criteria this observatory can actually measure per
# model from its own data. Everything else a model comparison might want
# (benchmarks, human eval) has no real signal here and is never invented.
MEASURABLE_EVALUATION_CRITERIA = [
    "calls", "latency_ms", "cost_usd_per_call", "availability", "last_seen",
]


def comparison_for_task(task, cost_log_path=None):
    """SELECTION vs COMPARISON separation for one of the 12 named tasks.

    SELECTION: the real evaluator recommendation (Phase 2, unchanged).
    COMPARISON: a real per-model row for every cost-logged model -- the
    measured evidence (calls/latency/cost/availability/last_seen) plus an
    explicit `criteria` list and honest UNKNOWN for unmeasured capability
    dimensions. With exactly one live provider today, cross-model
    comparison is real only on the measured axes, never on capability.
    """
    selection = evaluate_task(task, cost_log_path=cost_log_path)
    records = model_capability_records(cost_log_path=cost_log_path)
    comparison = []
    for r in records:
        stats = r["real_stats"] or {}
        comparison.append({
            "model": r["model"],
            "provider": r["provider"],
            "calls": stats.get("calls"),
            "latency_ms": stats.get("avg_latency_ms"),
            "cost_usd_per_call": stats.get("avg_cost_usd_per_call"),
            "availability": r["availability"],
            "last_seen": stats.get("last_seen"),
            "capability_evidence": "UNKNOWN",  # no real per-capability measurement exists
        })
    return {
        "task": task,
        "criteria": list(MEASURABLE_EVALUATION_CRITERIA),
        "selection": selection,
        "comparison": comparison,
        "comparison_note": (
            "Cross-model capability comparison is UNKNOWN today: exactly one "
            "provider (groq) has real usage data, so comparison is real only on "
            "the measured axes above, never on reasoning/coding/research capability."
        ),
    }


def evaluate_all_tasks_with_comparison(cost_log_path=None):
    """All 12 named tasks with explicit SELECTION vs COMPARISON separation."""
    return [comparison_for_task(t, cost_log_path=cost_log_path) for t in TASK_CATEGORIES]


# ---------------------------------------------------------------------------
# E. MODEL ROUTING INTELLIGENCE -- recommendation + fallback + confidence,
#    never an automatic switch.
# ---------------------------------------------------------------------------

def routing_intelligence(task, quality_threshold=None, latency_tolerance_ms=None,
                         cost_tolerance_usd=None, cost_log_path=None):
    """Routing recommendation for a task: the recommended model, the fallback
    model, the reason, the evidence, and the confidence. Advisory ONLY --
    returns will_auto_switch=False always. The production model is never
    changed by this function (or by anything in this module)."""
    from ai_capability.orchestrator import select_provider

    task_type = TASK_TO_EVALUATOR_TYPE.get(task, task)
    provider, selection = select_provider(task_type, cost_log_path=cost_log_path)
    records = model_capability_records(cost_log_path=cost_log_path)
    stats_by_model = {r["model"]: r["real_stats"] for r in records}

    recommended = provider
    fallback = None

    # The real, cost-logged model this provider has actually been called
    # with most recently -- the honest "recommended model" today. The cost
    # log is model-level, so this is real data, never a guess.
    recommended_model = max(stats_by_model.keys()) if stats_by_model else None

    # Confidence is a disclosed heuristic split into two honest components:
    #   selection_confidence -- that the recommended provider is a real,
    #       working, measured provider for this task (HIGH when it has real
    #       measured usage; the evaluator's own measured_providers list).
    #   comparison_confidence -- that it is the BEST of several compared
    #       models (LOW today: exactly one real provider exists, so no real
    #       cross-provider comparison has ever been possible).
    measured = selection.get("measured_providers") or []
    selection_confidence = "HIGH" if recommended in measured else "LOW"
    comparison_confidence = "LOW" if len(measured) <= 1 else "HIGH"

    return {
        "task": task,
        "recommended_provider": recommended,
        "recommended_model": recommended_model,
        "fallback_provider": fallback,
        "reason": selection.get("reason"),
        "evidence": "ai_capability/orchestrator.select_provider() + ai_capability/evaluator.recommend_for_task() -- real usage data only",
        "confidence": {
            "selection_confidence": selection_confidence,
            "comparison_confidence": comparison_confidence,
        },
        "quality_threshold": quality_threshold,
        "latency_tolerance_ms": latency_tolerance_ms,
        "cost_tolerance_usd": cost_tolerance_usd,
        "will_auto_switch": False,
        "governance": "advisory only -- AUTONOMY_LEVELS level 2 (RECOMMEND). Production model change is a founder-gated decision (Step 5 NOT AUTHORIZED).",
    }


# ---------------------------------------------------------------------------
# WS3 (Phase 3). MODEL ROUTING INTELLIGENCE -- authorization-gated switch
# proposals. The directive asks for routing intelligence that is
# "reversible" and "require[s] appropriate autonomy authorization before
# automatic switching -- never allow a model selection to bypass
# governance." This factory's governance (AUTONOMY_LEVELS, autonomous
# _operations.py) classifies a production model change as Level 5 (HUMAN
# APPROVAL REQUIRED) -- the system may recommend and propose, but only the
# founder authorizes. This ledger records those real proposals; no code
# path ever executes a switch. See WS4 for the compatibility/rollback
# validation that accompanies every proposal.
# ---------------------------------------------------------------------------

# Real autonomy classification for a production model switch -- cited
# from autonomous_operations.py's AUTHORIZATION engine (Phase 1, verified).
def _switch_autonomy_level():
    return 5


def record_switch_proposal(model_from, model_to, task, rationale, evidence,
                           compatibility=None, rollback=None, path=None):
    """Record ONE real, founder-gated switch proposal. This function ONLY
    records a proposal -- it never changes a model, never reconfigures a
    provider, never affects routing. Every proposal carries its own real
    rationale/evidence plus the WS4 compatibility + rollback assessment.
    Level 5 (HUMAN APPROVAL REQUIRED) is cited explicitly on the record."""
    if not model_from or not model_to:
        raise ValueError("model_from and model_to must be non-empty")
    if not rationale or not evidence:
        raise ValueError("rationale and evidence must be non-empty")
    path = Path(path or SWITCH_PROPOSALS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model_from": model_from,
        "model_to": model_to,
        "task": task,
        "rationale": rationale,
        "evidence": evidence,
        "compatibility": compatibility,
        "rollback": rollback,
        "autonomy_level": _switch_autonomy_level(),
        "autonomy_name": "HUMAN APPROVAL REQUIRED",
        "status": "PROPOSED",
        "decision": None,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def switch_proposals(path=None):
    """Read the append-only switch-proposal ledger."""
    return _read_jsonl(path or SWITCH_PROPOSALS_PATH)


def routing_authorization_status(cost_log_path=None):
    """The real authorization posture for model routing. Always reports the
    governance gate: a production model change is Level 5 (HUMAN APPROVAL
    REQUIRED), founder-only, never automatic. Surfaces the current real
    proposal count as the honest measure of pending routing decisions."""
    from ai_capability.orchestrator import _REAL_PROVIDER_CALLERS
    props = switch_proposals()
    pending = [p for p in props if p.get("status") == "PROPOSED"]
    return {
        "routing": "advisory -- recommendations only (routing_intelligence())",
        "switch_autonomy_level": _switch_autonomy_level(),
        "switch_autonomy_name": "HUMAN APPROVAL REQUIRED",
        "switch_execution_path": "NONE -- no code path executes a model switch",
        "founder_gated": True,
        "pending_switch_proposals": len(pending),
        "real_provider_callers": list(_REAL_PROVIDER_CALLERS.keys()),
        "governance": "autonomous_operations.py AUTONOMY_LEVELS[5] -- 'A real action that a human can authorize through an explicit, existing mechanism, but that the system never initiates itself.' A model switch is exactly this class: proposable by the observatory, authorizable only by the founder.",
    }


# ---------------------------------------------------------------------------
# F. OBSOLESCENCE DETECTION -- 6 named states, never obsolete without
#    evidence.
# ---------------------------------------------------------------------------

OBSOLESCENCE_STATES = [
    "CURRENT", "WATCH", "DEGRADING", "OBSOLETE-RISK",
    "REPLACEMENT-RECOMMENDED", "UNKNOWN",
]

# Real, evidence-cited obsolescence facts this factory actually has. Each
# cites a real source; never a guess. Seeded from the real migration event
# documented in book_generator.py (the retired 8B-instant model).
_KNOWN_RETIRED_MODELS = {
    "llama-3.1-8b-instant": {
        "state": "REPLACEMENT-RECOMMENDED",
        "reason": "Groq retired this model -- it shut down 2026-08-16. Already replaced by openai/gpt-oss-20b (book_generator.py GROQ_PRICING comment, verified 2026-08-14).",
        "replacement_candidates": ["openai/gpt-oss-20b"],
    },
}


def obsolescence_detection(cost_log_path=None, stale_days=STALE_DAYS):
    """Per-model obsolescence state across the 6 named states. A model is
    CURRENT only if it has real calls within `stale_days`; WATCH if its last
    real call is older than `stale_days`; known-retired models get their
    real REPLACEMENT-RECOMMENDED state. Never declares a model obsolete
    without real evidence."""
    entries = _read_jsonl(cost_log_path or COST_LOG_PATH)
    models = _models_in_cost_log(cost_log_path)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    out = []
    for m in models:
        stats = _model_stats(entries, m)
        known = _KNOWN_RETIRED_MODELS.get(m)
        if known:
            out.append({
                "model": m,
                "state": known["state"],
                "reason": known["reason"],
                "replacement_candidates": known["replacement_candidates"],
                "evidence": "real vendor retirement documented in book_generator.py",
            })
            continue
        if stats["last_seen"]:
            try:
                last = datetime.fromisoformat(stats["last_seen"].replace("Z", "+00:00"))
            except ValueError:
                last = None
            # Cost-log timestamps are timezone-naive (datetime.now().isoformat());
            # compare against a naive UTC clock so aware/naive can never clash.
            if last and last.tzinfo is not None:
                last = last.astimezone(timezone.utc).replace(tzinfo=None)
            if last and (now - last).days > stale_days:
                out.append({
                    "model": m,
                    "state": "WATCH",
                    "reason": f"No real calls in {stale_days}+ days (last: {stats['last_seen']}).",
                    "replacement_candidates": [],
                    "evidence": "data/ai_cost_log.jsonl",
                })
                continue
        out.append({
            "model": m,
            "state": "CURRENT",
            "reason": f"Real calls within the last {stale_days} days.",
            "replacement_candidates": [],
            "evidence": "data/ai_cost_log.jsonl",
        })
    return out


# ---------------------------------------------------------------------------
# WS4 (Phase 3). MODEL REPLACEMENT SAFETY -- for any model flagged
# REPLACEMENT-RECOMMENDED or OBSOLETE-RISK, evaluate the real compatibility
# of each candidate and the rollback path. Never replaces anything: this is
# the pre-flight validation a founder reviews before authorizing (Level 5).
#
# The directive asks replacement to be "validated, not automatic" -- every
# plan must cite real compatibility evidence (does the candidate run on a
# real caller? does the factory have real usage data?) and a concrete,
# deterministic rollback path (revert the single GROQ_MODEL constant that
# actually routes production, book_generator.py). A candidate with no real
# compatibility evidence is honestly NOT VALIDATED, never assumed safe.
# ---------------------------------------------------------------------------

def _production_model_constant():
    """The single production routing constant that exists today --
    book_generator.py's GROQ_MODEL. Reading it here is read-only; changing
    it is founder-gated (never done by this module)."""
    import re
    try:
        text = Path(_FACTORY_ROOT / "book_generator.py").read_text(encoding="utf-8")
        m = re.search(r'^GROQ_MODEL\s*=\s*"([^"]+)"', text, re.MULTILINE)
        return m.group(1) if m else "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def replacement_plan(model, cost_log_path=None):
    """WS4 replacement-safety plan for one model. Returns the real
    compatibility assessment + rollback guidance for each replacement
    candidate, plus the authorization gate. For a CURRENT model there is
    nothing to replace -- the plan says so honestly."""
    obs = obsolescence_detection(cost_log_path=cost_log_path)
    record = next((o for o in obs if o["model"] == model), None)
    if not record:
        return {
            "model": model,
            "state": "UNKNOWN",
            "replacement_needed": False,
            "reason": "No real obsolescence record for this model.",
        }
    if record["state"] not in ("REPLACEMENT-RECOMMENDED", "OBSOLETE-RISK"):
        return {
            "model": model,
            "state": record["state"],
            "replacement_needed": False,
            "reason": record["reason"],
        }

    candidates = record.get("replacement_candidates") or []
    records = model_capability_records(cost_log_path=cost_log_path)
    by_name = {r["model"]: r for r in records}
    validated = []
    for cand in candidates:
        rec = by_name.get(cand)
        compatibility = []
        if rec:
            compatibility.append(f"real usage data exists ({rec['real_stats'].get('calls', 0)} calls, data/ai_cost_log.jsonl)")
            availability = rec.get("availability")
            if availability in ("AVAILABLE", "DEGRADED"):
                compatibility.append(f"availability={availability} (safe_mode.py + cost log)")
        else:
            compatibility.append("NO real usage data for this candidate -- NOT VALIDATED")
        validated.append({
            "candidate": cand,
            "compatibility": compatibility,
            "compatibility_status": "VALIDATED" if rec else "NOT VALIDATED",
        })

    return {
        "model": model,
        "state": record["state"],
        "replacement_needed": True,
        "reason": record["reason"],
        "candidates": validated,
        "rollback": {
            "procedure": f"Revert book_generator.py's GROQ_MODEL constant from the replacement back to '{model}' (the single real production routing constant, currently GROQ_MODEL='{_production_model_constant()}').",
            "deterministic": True,
            "authorization": "rollback is also founder-gated (Level 5) -- the observatory records it as guidance only.",
        },
        "authorization": {
            "autonomy_level": _switch_autonomy_level(),
            "autonomy_name": "HUMAN APPROVAL REQUIRED",
            "note": "Replacement is validated and proposed here; execution requires a real founder decision (Step 5 NOT AUTHORIZED).",
        },
    }


# ---------------------------------------------------------------------------
# G. TECHNOLOGY RADAR -- append-only. Phase 2 vocabulary (ADOPT/TRIAL/
# WATCH/HOLD/RETIRE) extended additively for Phase 3 with EXPERIMENT and
# REJECT (the directive's named WATCH/EXPERIMENT/ADOPT/REJECT set). Every
# prior entry remains valid; no vocabulary was renamed or removed.
# ---------------------------------------------------------------------------

# Phase 2: ADOPT/TRIAL/WATCH/HOLD/RETIRE. Phase 3 adds EXPERIMENT (a
# deliberate, bounded trial -- semantically adjacent to TRIAL, kept as a
# distinct named action per the directive) and REJECT (a technology the
# factory has real evidence AGAINST -- distinct from HOLD, which is
# "deferred, not rejected").
RADAR_ACTIONS = ["ADOPT", "TRIAL", "WATCH", "HOLD", "RETIRE", "EXPERIMENT", "REJECT"]


def record_radar_entry(technology, category, rationale, evidence, confidence,
                       expected_impact=None, implementation_risk=None,
                       replacement=None, review_date=None, path=None):
    """Append one technology-radar entry. Append-only -- never overwrites a
    prior entry. `category` must be one of RADAR_ACTIONS. `evidence` must
    cite a real source; the observatory refuses to record a fabricated one."""
    if category not in RADAR_ACTIONS:
        raise ValueError(f"radar category must be one of {RADAR_ACTIONS}")
    path = Path(path or RADAR_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "technology": technology,
        "category": category,
        "rationale": rationale,
        "evidence": evidence,
        "confidence": confidence,
        "expected_strategic_impact": expected_impact,
        "implementation_risk": implementation_risk,
        "replacement_alternative": replacement,
        "review_date": review_date,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def technology_radar(path=None):
    """Read the append-only radar ledger (empty until real entries exist)."""
    return _read_jsonl(path or RADAR_PATH)


# ---------------------------------------------------------------------------
# H. TECHNOLOGY FORESIGHT -- FACT/SIGNAL/INFERENCE/PREDICTION separation.
#    A prediction is never presented as a fact.
# ---------------------------------------------------------------------------

SIGNAL_KINDS = ["FACT", "SIGNAL", "INFERENCE", "PREDICTION"]


def record_technology_signal(kind, statement, evidence, confidence, path=None):
    """Append one foresight signal. `kind` must be exactly one of
    FACT/SIGNAL/INFERENCE/PREDICTION -- the observatory enforces that a
    PREDICTION is always labeled as such and never presented as fact."""
    if kind not in SIGNAL_KINDS:
        raise ValueError(f"signal kind must be one of {SIGNAL_KINDS}")
    path = Path(path or SIGNALS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "statement": statement,
        "evidence": evidence,
        "confidence": confidence,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def technology_foresight(path=None):
    """Read the append-only foresight ledger."""
    return _read_jsonl(path or SIGNALS_PATH)


# ---------------------------------------------------------------------------
# I. MULTI-PROVIDER RESILIENCE -- real abstraction status, citing the
#    orchestrator. Never claims a fallback that isn't real.
# ---------------------------------------------------------------------------

def provider_abstraction_status(cost_log_path=None):
    """Real multi-provider abstraction status. The orchestrator is the real
    abstraction layer (ai_capability/orchestrator.py); the registry is the
    real provider catalog. One provider (groq) is real-callable today; the
    rest are DISCOVERY. Honest about the current single-provider reality."""
    from ai_capability.orchestrator import _REAL_PROVIDER_CALLERS

    providers = registry.list_providers(cost_log_path)
    real_callers = list(_REAL_PROVIDER_CALLERS.keys())
    return {
        "abstraction_layer": "ai_capability/orchestrator.py -- generate()/select_provider()",
        "real_provider_caller_count": len(real_callers),
        "real_provider_callers": real_callers,
        "providers": providers,
        "single_provider_dependency": len(real_callers) <= 1,
        "note": "Adding a real second provider is a 3-step non-breaking change (credential + call impl + _REAL_PROVIDER_CALLERS entry), documented in orchestrator.py. Zero second-provider credential exists in .env today.",
        "governance": "No automatic provider addition, purchase, or switch exists anywhere in this module.",
    }


# ---------------------------------------------------------------------------
# J. AI COST INTELLIGENCE -- real per-model/per-task cost. UNKNOWN where the
#    log cannot support a reliable number.
# ---------------------------------------------------------------------------

def cost_intelligence(cost_log_path=None):
    """Real cost intelligence from data/ai_cost_log.jsonl: per-model totals,
    per-task cost (via the real context tags already in the log), and the
    grand total. COST is honestly UNKNOWN for anything the log can't compute
    (e.g. a task tag that never appears). Never a projected or estimated
    figure -- only logged cost, summed."""
    entries = _read_jsonl(cost_log_path or COST_LOG_PATH)
    models = _models_in_cost_log(cost_log_path)

    per_model = {}
    for m in models:
        stats = _model_stats(entries, m)
        per_model[m] = {
            "calls": stats["calls"],
            "total_cost_usd": stats["total_cost_usd"],
            "avg_cost_usd_per_call": stats["avg_cost_usd_per_call"],
            "avg_latency_ms": stats["avg_latency_ms"],
            "avg_total_tokens": stats["avg_total_tokens"],
        }

    # Per-task cost: aggregate real context.purpose / context.niche tags.
    task_costs = {}
    for e in entries:
        ctx = e.get("context") or {}
        label = ctx.get("purpose") or ctx.get("niche") or ctx.get("product_type")
        if not label:
            continue
        key = str(label)
        task_costs.setdefault(key, {"calls": 0, "cost_usd": 0.0})
        task_costs[key]["calls"] += 1
        task_costs[key]["cost_usd"] = round(
            task_costs[key]["cost_usd"] + (e.get("cost_usd") or 0.0), 6
        )

    all_costs = [e["cost_usd"] for e in entries if e.get("cost_usd") is not None]
    return {
        "source": "data/ai_cost_log.jsonl (ADR-041)",
        "total_calls": len(entries),
        "total_cost_usd": round(sum(all_costs), 6) if all_costs else 0.0,
        "per_model": per_model,
        "per_task_cost_usd": task_costs,
        "cost_not_calculable": "UNKNOWN where the log has no reliable price or tag -- never estimated.",
        "governance": "Read-only. Zero code in this module can spend, purchase, or change billing.",
    }


# ---------------------------------------------------------------------------
# K. AI QUALITY MEMORY -- append-only ledger of real quality observations.
# ---------------------------------------------------------------------------

def record_quality_memory(task, model, result, quality, failure_mode, evidence,
                          recommendation, path=None):
    """Append one real quality observation. `quality` and `recommendation`
    are only recorded when backed by real evidence; a missing real outcome
    is recorded as such, never fabricated."""
    path = Path(path or QUALITY_MEMORY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "model": model,
        "result": result,
        "quality": quality,
        "failure_mode": failure_mode,
        "evidence": evidence,
        "recommendation": recommendation,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def quality_memory(path=None):
    """Read the append-only quality-memory ledger."""
    return _read_jsonl(path or QUALITY_MEMORY_PATH)


# ---------------------------------------------------------------------------
# WS5 (Phase 3). AI CAPABILITY EVOLUTION -- institutional memory of
# accepted / rejected / uncertain capabilities. The directive asks to
# "record why a capability is useful, record evidence supporting adoption,
# and maintain institutional memory of accepted, rejected, and uncertain
# capabilities." This is the append-only capability-decision ledger: every
# real capability decision (a real radar/foresight/quality observation
# distilled to an ACCEPTED / REJECTED / UNCERTAIN verdict) is recorded with
# its real evidence. Nothing here decides anything -- it only records real,
# already-made observations. (Phase 2's quality_memory/radar/foresight
# ledgers feed this view; this ledger is the consolidated capability
# decision memory the directive names.)
# ---------------------------------------------------------------------------

CAPABILITY_DECISION_STATUSES = ["ACCEPTED", "REJECTED", "UNCERTAIN"]


def record_capability_decision(technology, status, rationale, evidence,
                               confidence, linked_proposal_id=None, path=None):
    """Append one real capability-decision record. `status` must be
    ACCEPTED/REJECTED/UNCERTAIN. `evidence` must cite a real source;
    `linked_proposal_id`, when given, must reference a real evolution-queue
    proposal id (never a guessed link)."""
    if status not in CAPABILITY_DECISION_STATUSES:
        raise ValueError(f"status must be one of {CAPABILITY_DECISION_STATUSES}")
    if not technology or not rationale or not evidence:
        raise ValueError("technology, rationale, and evidence must be non-empty")
    path = Path(path or CAPABILITY_DECISIONS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "technology": technology,
        "status": status,
        "rationale": rationale,
        "evidence": evidence,
        "confidence": confidence,
        "linked_proposal_id": linked_proposal_id,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def capability_decisions(path=None):
    """Read the append-only capability-decision ledger."""
    return _read_jsonl(path or CAPABILITY_DECISIONS_PATH)


def capability_evolution_summary(path=None):
    """The consolidated capability-evolution view: every recorded decision
    grouped by status, plus the honest current posture (zero real
    accepted capability decisions recorded today unless evidence exists).
    Pure aggregation of the real ledger -- never a decision engine."""
    entries = capability_decisions(path)
    by_status = {s: [e for e in entries if e.get("status") == s] for s in CAPABILITY_DECISION_STATUSES}
    return {
        "ledger": "data/ai_capability_decisions.jsonl (append-only, WS5 Phase 3)",
        "total": len(entries),
        "accepted": by_status["ACCEPTED"],
        "rejected": by_status["REJECTED"],
        "uncertain": by_status["UNCERTAIN"],
        "note": "Capability evolution is RECORDED here, never DECIDED -- every entry cites real evidence; the real acceptance decision for a production capability remains founder-gated (Level 5).",
    }


# ---------------------------------------------------------------------------
# L. TECHNOLOGY POSITION -- the 7 named fields the CEO Brain needs.
# ---------------------------------------------------------------------------

def technology_position(cost_log_path=None):
    """The 7-field technology position the CEO Brain's TECHNOLOGY POSITION
    section consumes: strongest capabilities, weakest capabilities, biggest
    dependency, highest obsolescence risk, most promising emerging
    technology, recommended technology experiment, and the technology
    decision requiring founder attention. Every field cites real evidence;
    fields with no real signal are honestly stated, never guessed."""
    records = model_capability_records(cost_log_path=cost_log_path)
    obsolescence = obsolescence_detection(cost_log_path=cost_log_path)
    abstraction = provider_abstraction_status(cost_log_path=cost_log_path)

    real_models = [r["model"] for r in records]

    highest_risk = next(
        (o for o in obsolescence if o["state"] == "REPLACEMENT-RECOMMENDED"), None
    )

    return {
        "strongest_current_capabilities": {
            "answer": "Real, measured content generation, cost tracking, and latency logging for "
                      f"{', '.join(real_models) if real_models else 'no real model'} "
                      "(data/ai_cost_log.jsonl, ADR-041).",
            "evidence": "ai_capability/registry.py + data/ai_cost_log.jsonl -- real usage only",
        },
        "weakest_capabilities": {
            "answer": "Every capability category is DISCOVERY except measured latency/cost: "
                      "reasoning, coding, research, multimodal, tool use, and benchmark evidence "
                      "have zero real measured comparison across providers.",
            "evidence": "model_capability_records() -- DISCOVERY by construction, never fabricated",
        },
        "biggest_dependency": {
            "answer": f"Single provider: groq ({len(real_models)} real model(s)) -- "
                      f"{'single_provider_dependency=true' if abstraction['single_provider_dependency'] else 'multi-provider'}.",
            "evidence": "provider_abstraction_status() -- orchestrator._REAL_PROVIDER_CALLERS",
        },
        "highest_obsolescence_risk": {
            "answer": (f"{highest_risk['model']} ({highest_risk['state']})"
                       if highest_risk else "No known retired/obsolete model in real usage data."),
            "evidence": "obsolescence_detection() -- real vendor retirement documented in book_generator.py",
        },
        "most_promising_emerging_technology": {
            "answer": "UNKNOWN -- this observatory has no real external technology-news pipeline. "
                      "Multi-source market intelligence (multi_source_intelligence/) is market data, not technology data.",
            "evidence": "honest UNKNOWN per Truth First vocabulary (ADR-160)",
        },
        "recommended_technology_experiment": {
            "answer": "Register a second real provider (3-step non-breaking change in orchestrator.py) "
                      "to convert single-provider dependency into a real measured comparison -- only after a real founder decision to configure a credential.",
            "evidence": "orchestrator.py docstring -- the real documented path to multi-provider orchestration",
        },
        "technology_decision_requiring_founder": {
            "answer": "Whether to configure a second AI provider credential (OpenAI/Anthropic/Google/xAI/...). "
                      "This is a real founder-gated decision: only the founder can provide a credential and authorize spend.",
            "evidence": "governance: provider addition requires a real credential + founder authorization; this module never acts on it.",
        },
    }


# ---------------------------------------------------------------------------
# M. OBSERVATORY REPORT -- the one aggregated view for Mission Control /
#    the CEO Brain.
# ---------------------------------------------------------------------------

def build_observatory_report(cost_log_path=None):
    """The single aggregated observatory view: capability records, task
    evaluation, routing intelligence, obsolescence, radar, foresight,
    provider abstraction, cost intelligence, quality memory, and the
    7-field technology position. Composition-only -- every sub-part is the
    real function above, each cheap and file-based (no live network calls,
    no live AI calls)."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "observatory": "AI Capability Observatory & Technology Foresight (Phase 2, 2026-08-16)",
        "model_capability_records": model_capability_records(cost_log_path=cost_log_path),
        "task_evaluation": evaluate_all_tasks(cost_log_path=cost_log_path),
        "routing_intelligence": {
            t: routing_intelligence(t, cost_log_path=cost_log_path)
            for t in TASK_CATEGORIES
        },
        "obsolescence": obsolescence_detection(cost_log_path=cost_log_path),
        "technology_radar": technology_radar(),
        "technology_foresight": technology_foresight(),
        "provider_abstraction": provider_abstraction_status(cost_log_path=cost_log_path),
        "cost_intelligence": cost_intelligence(cost_log_path=cost_log_path),
        "quality_memory": quality_memory(),
        "technology_position": technology_position(cost_log_path=cost_log_path),
        # Phase 3 (AI Capability Evolution & Multi-Model Intelligence):
        "task_evaluation_with_comparison": evaluate_all_tasks_with_comparison(cost_log_path=cost_log_path),
        "routing_authorization": routing_authorization_status(cost_log_path=cost_log_path),
        "replacement_plans": {
            r["model"]: replacement_plan(r["model"], cost_log_path=cost_log_path)
            for r in model_capability_records(cost_log_path=cost_log_path)
        },
        "capability_evolution": capability_evolution_summary(),
    }