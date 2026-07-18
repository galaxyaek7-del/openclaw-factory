"""
Executive Orchestrator — the coordinator itself (ADR-051).

run_cycle() drives one opportunity signal through EXECUTION_ORDER,
mediating every engine through the registry (dependency inversion — this
module never imports a concrete engine module directly, only the
registry's abstract callable(context) -> dict shape). Every stage's
outcome — success, failure, or skip — is appended to the immutable
timeline. Duplicate-execution prevention applies only to
DUPLICATE_SENSITIVE_STAGES (production/publishing) — see types.py for
why market_intelligence/decision/learning are deliberately exempt.

Deliberately NOT started by server.js or factory_loop.js's existing tick
— run_cycle()/prioritize_queue() are called deliberately (CLI or a
future, separately-approved wiring step), matching this factory's
standing convention for every new automation surface introduced this
session (market_intelligence_core, decision_engine) and explicit
instruction not to wire the Decision Engine directly into factory_loop.js.
"""

import hashlib
from datetime import datetime, timezone

import competitor_discovery
from decision_engine import ranking as decision_ranking

from orchestrator import engines  # noqa: F401 — import triggers auto-registration
from orchestrator import retry, timeline
from orchestrator.registry import get_engines
from orchestrator.types import DUPLICATE_SENSITIVE_STAGES, EXECUTION_ORDER, ExecutionResult


def make_idempotency_key(stage_name, niche, tier):
    raw = f"{stage_name}|{str(niche).strip().lower()}|{tier}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _enrich_with_real_competition(niche, external_signal, max_results):
    """ADR-057: closes a real, long-documented gap (BLOCKERS.md #4) —
    profit_oracle._score_competition() already accepts a real
    external_signal['competition']['related_results_count'] (ADR-041),
    and competitor_discovery.py already computes a real HN/GitHub
    competitor count, but nothing ever connected the two until now.
    Purely additive to whatever demand-shaped external_signal the caller
    already provided; never overwrites it, never fabricates a count —
    any competitor_discovery failure degrades to the original
    external_signal completely unchanged."""
    try:
        competitors = competitor_discovery.get_or_refresh_competitors(niche, max_results=max_results)
        total_found = competitors.get("total_found")
    except Exception:
        return external_signal

    if total_found is None:
        return external_signal

    enriched = dict(external_signal or {})
    enriched["competition"] = {"related_results_count": total_found}
    return enriched


def _skip(stage_name, idempotency_key, reason, timeline_path):
    now = datetime.now(timezone.utc).isoformat()
    status = "SKIPPED_DUPLICATE" if "duplicate" in reason.lower() else "SKIPPED_NOT_APPLICABLE"
    result = ExecutionResult(
        engine=stage_name, status=status, started_at=now, finished_at=now,
        attempts=0, idempotency_key=idempotency_key, output={"reason": reason}, error=None,
    )
    timeline.append_execution(result, path=timeline_path)
    return result


def _run_stage(stage_name, fn, context, idempotency_key, timeline_path, max_attempts):
    started_at = datetime.now(timezone.utc).isoformat()
    output, error, attempts = retry.run_with_retry(fn, context, max_attempts=max_attempts)
    finished_at = datetime.now(timezone.utc).isoformat()
    result = ExecutionResult(
        engine=stage_name, status=("FAILED" if error else "SUCCESS"), started_at=started_at,
        finished_at=finished_at, attempts=attempts, idempotency_key=idempotency_key,
        output=output or {}, error=error,
    )
    timeline.append_execution(result, path=timeline_path)
    return result


def run_cycle(niche, external_signal=None, tier="tier4", max_results=10,
              execute_production=False, max_attempts=3, timeline_path=None,
              decisions_path=None, analysis_db_file=None, outcomes_path=None,
              ladder=None):
    """Runs the full coordinated pipeline for ONE opportunity signal.

    execute_production=False (default): production/publishing are always
    skipped (SKIPPED_NOT_APPLICABLE), regardless of what the decision
    stage concludes — running this function with defaults never spends
    real money or publishes anything live, the same "dry_run=True by
    default at every layer" safety rule this factory already applies
    everywhere a real-world side effect is possible.

    decisions_path/analysis_db_file: forwarded to the decision/market_
    intelligence engine adapters (2026-07-16 fix) — without these, every
    call silently wrote into the real data/decisions.jsonl and
    data/market_intelligence_analyses.jsonl, discovered when this
    package's own test suite was found doing exactly that. Omitting them
    (every call before this parameter existed — there was no prior
    caller) uses the same real default paths those modules already use.

    external_signal is enriched with a real competition count (ADR-057)
    before being passed to context — see _enrich_with_real_competition().

    ladder (ADR-077, Product Generation Pipeline): threaded into context
    for the decision engine (ladder-aware gate, ADR-076) and the production
    engine (routes to the real technical-docs generator instead of the old
    AI-book path, same real routing factory_loop.js's
    briefFromGoldenOpportunity() already uses, ADR-071) — this deliberate/
    manual orchestration path and the automatic tick now make the exact
    same real decision about what to build, never a second, diverging one.
    Omitting it (every caller before this parameter existed) reproduces
    the exact prior behavior unchanged."""
    external_signal = _enrich_with_real_competition(niche, external_signal, max_results)
    context = {
        "niche": niche, "external_signal": external_signal, "tier": tier,
        "max_results": max_results, "dry_run": not execute_production,
        "decisions_path": decisions_path, "analysis_db_file": analysis_db_file,
        "outcomes_path": outcomes_path, "ladder": ladder,
    }
    engines_map = get_engines()
    results = []

    for stage_name in EXECUTION_ORDER:
        idempotency_key = make_idempotency_key(stage_name, niche, tier)

        if stage_name in ("production", "publishing"):
            if not execute_production:
                results.append(_skip(stage_name, idempotency_key, "execute_production=False", timeline_path))
                continue
            decision_status = (context.get("decision_result") or {}).get("status")
            if decision_status != "ACCEPTED":
                results.append(_skip(stage_name, idempotency_key, f"decision status is {decision_status!r}, not ACCEPTED", timeline_path))
                continue

        if stage_name in DUPLICATE_SENSITIVE_STAGES and timeline.has_succeeded(idempotency_key, path=timeline_path):
            results.append(_skip(stage_name, idempotency_key, "already succeeded — duplicate execution prevented", timeline_path))
            continue

        engine_fn = engines_map.get(stage_name)
        if engine_fn is None:
            results.append(_skip(stage_name, idempotency_key, "no engine registered for this stage", timeline_path))
            continue

        result = _run_stage(stage_name, engine_fn, context, idempotency_key, timeline_path, max_attempts)
        results.append(result)
        context[f"{stage_name}_result"] = result.output

    return results


def prioritize_queue(max_items=None, decisions_path=None, outcomes_path=None):
    """Real prioritization + a real, simple resource-allocation cap.
    Reuses decision_engine.ranking.rank_queue() (ADR-050) — the existing,
    tested global ranking — rather than building a second one."""
    queue = decision_ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)
    return queue[:max_items] if max_items is not None else queue
