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

Was deliberately NOT started by server.js or factory_loop.js's existing
tick through 2026-07-18 — run_cycle()/prioritize_queue() were only
called deliberately (CLI or a future, separately-approved wiring step).
**Strategic Phase (2026-07-19): the founder explicitly authorized wiring
this in**, via factory_loop.js's existing golden_hunter_bridge step and
its existing FACTORY_AUTO_PRODUCE safety gate (same gate
AUTO_PRODUCE_ACTIVATION_CHECKLIST.md already documents — no new env var,
no new review process). See this module's own `main()` / the real
`--run-ladder-opportunity` CLI mode below, and
`_cli_run_ladder_opportunity()` specifically: it reuses an ALREADY-
recorded decision (market_hunter.py's own daily record_ladder_decision()
call) via `existing_decision=`, rather than re-evaluating the niche a
second time — the real safeguard against recording two independent
decisions (and therefore two production_ids) for the same real
opportunity.

**Invocation note (found live while wiring the CLI in):** this module
MUST be invoked as `python -m orchestrator.orchestrator ...`, never
`python orchestrator/orchestrator.py ...` directly — the latter puts
`orchestrator/`'s own directory on sys.path, so `orchestrator/types.py`
shadows the Python standard library's own `types` module the moment
anything (even a stdlib import three levels down, e.g. `enum`) tries
`import types`, crashing with an unrelated-looking `ImportError` before
a single line of this file's real logic runs. Same class of bug as
Roadmap Step 3's `packaging/` -> `product_packaging/` rename (a
same-named module shadowing something outside this repo) — the fix here
is calling convention, not a rename, since `orchestrator.types` is
already imported correctly as a package submodule everywhere else.
"""

import hashlib
import json
import sys
from datetime import datetime, timezone

import competitor_discovery
import factory_state
from decision_engine import ranking as decision_ranking
from recovery import snapshot

from orchestrator import engines  # noqa: F401 — import triggers auto-registration
from orchestrator import retry, timeline
from orchestrator.registry import get_engines
from orchestrator.types import DUPLICATE_SENSITIVE_STAGES, EXECUTION_ORDER, ExecutionResult


def make_idempotency_key(stage_name, niche, tier):
    raw = f"{stage_name}|{str(niche).strip().lower()}|{tier}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _enrich_with_real_competition(niche, external_signal, max_results, competitor_db_file=None):
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
        competitors = competitor_discovery.get_or_refresh_competitors(
            niche, max_results=max_results, db_file=competitor_db_file)
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


def _run_stage(stage_name, fn, context, idempotency_key, timeline_path, max_attempts, state_path=None):
    # Operational Resilience Architecture §3/§4 (Phase A, 2026-07-18):
    # set_current_task() is the "in-flight, not yet resolved" evidence
    # startup recovery needs — orchestrator/timeline.py alone only records
    # *finished* attempts, never "this was started and the process died
    # before it finished." Cleared unconditionally below regardless of
    # success/failure — either way the stage is no longer in flight.
    # Best-effort only (factory_state's own functions never raise) — a
    # disk error here must never affect the real stage execution.
    factory_state.set_current_task(stage_name, idempotency_key=idempotency_key, path=state_path)

    # Unified Recovery System §7 (2026-07-18): snapshot the small set of
    # critical state files before a duplicate-sensitive stage (production/
    # publishing) runs — this is where a real external side effect
    # (Groq spend, a Paddle create) can happen, so it's the moment worth
    # protecting. Best-effort, never blocks the real stage.
    #
    # Gated on state_path is None (real production, no test override) —
    # found live during the Unified Recovery System's own validation pass:
    # an unconditional call here snapshotted the REAL data/decisions.jsonl
    # every time ANY test reached a duplicate-sensitive stage, regardless
    # of that test's own isolated timeline/decisions paths, littering the
    # repo with real .bak files from test runs. Same "omitting the
    # optional path param means real, tests always override it" contract
    # every other path parameter in this module already follows.
    if stage_name in DUPLICATE_SENSITIVE_STAGES and state_path is None:
        snapshot.snapshot_before(f"orchestrator stage {stage_name} ({idempotency_key})")

    started_at = datetime.now(timezone.utc).isoformat()
    output, error, attempts = retry.run_with_retry(fn, context, max_attempts=max_attempts)
    finished_at = datetime.now(timezone.utc).isoformat()
    result = ExecutionResult(
        engine=stage_name, status=("FAILED" if error else "SUCCESS"), started_at=started_at,
        finished_at=finished_at, attempts=attempts, idempotency_key=idempotency_key,
        output=output or {}, error=error,
    )
    timeline.append_execution(result, path=timeline_path)

    factory_state.clear_current_task(path=state_path)
    if not error:
        factory_state.record_checkpoint(stage_name, idempotency_key, path=state_path)

    return result


def run_cycle(niche, external_signal=None, tier="tier4", max_results=10,
              execute_production=False, max_attempts=3, timeline_path=None,
              decisions_path=None, analysis_db_file=None, outcomes_path=None,
              ladder=None, state_path=None, existing_decision=None,
              competitor_db_file=None, ledger_path=None):
    """Runs the full coordinated pipeline for ONE opportunity signal.

    existing_decision (Strategic Phase, 2026-07-19): a real Decision dict
    already recorded elsewhere (e.g. market_hunter.py's daily
    hunt_market() -> decision_engine.engine.record_ladder_decision(),
    decision_path="ladder_fast_gate") for this exact niche. When given,
    market_intelligence/decision are SKIPPED (marked "reusing an
    existing decision", not re-run) instead of live-re-evaluating the
    same niche a second time — calling the real "decision" stage again
    would run evaluate_and_decide() (decision_path="ai_ceo_full_evaluation")
    and record a SECOND, independent decision for the same real
    opportunity, with a different decision_id (make_decision_id() hashes
    in a fresh analyzed_at timestamp) and therefore a different
    production_id — two real productions/publishes for one real
    opportunity, exactly the duplicate-publishing risk every other layer
    of this factory (idempotency keys, DUPLICATE_SENSITIVE_STAGES,
    channels/paddle_arm.py's own dedup) already guards against. Every
    other stage and every existing safety mechanism below applies
    completely unchanged — this only changes where decision_result comes
    from. Omitting it (every caller before this parameter existed)
    reproduces the exact prior behavior.

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
    the exact prior behavior unchanged.

    state_path (Operational Resilience Architecture, Phase A, 2026-07-18):
    forwarded to factory_state's set_current_task()/clear_current_task()/
    record_checkpoint() calls in _run_stage() — omitting it (every caller
    before this parameter existed) writes to the real data/
    factory_state.json, the same default-path convention every other
    optional path parameter here already uses.

    competitor_db_file/ledger_path (post-reboot operational simulation,
    2026-07-23): forwarded to _enrich_with_real_competition() and the
    publishing engine respectively. Found missing by actually running
    run_cycle(execute_production=True) end to end rather than only
    reading the code — competitor_discovery.get_or_refresh_competitors()
    and channels.ledger.record_publish_attempt() already accepted
    db_file=/ledger_path= overrides, but nothing here threaded them
    through, so every execute=True run (test or real) wrote a real
    competitor-cache entry and a real sales-ledger publish-attempt
    record into data/competitor_database.json and data/sales_ledger.jsonl
    with no way to redirect either. Omitting them (every caller before
    this parameter existed) reproduces the exact prior behavior."""
    external_signal = _enrich_with_real_competition(niche, external_signal, max_results, competitor_db_file=competitor_db_file)
    context = {
        "niche": niche, "external_signal": external_signal, "tier": tier,
        "max_results": max_results, "dry_run": not execute_production,
        "decisions_path": decisions_path, "analysis_db_file": analysis_db_file,
        "outcomes_path": outcomes_path, "ladder": ladder, "ledger_path": ledger_path,
    }
    engines_map = get_engines()
    results = []

    for stage_name in EXECUTION_ORDER:
        idempotency_key = make_idempotency_key(stage_name, niche, tier)

        if existing_decision is not None and stage_name in ("market_intelligence", "decision"):
            if stage_name == "decision":
                context["decision_result"] = existing_decision
            results.append(_skip(stage_name, idempotency_key, "reusing an existing decision (existing_decision given) — not re-evaluated", timeline_path))
            continue

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

        result = _run_stage(stage_name, engine_fn, context, idempotency_key, timeline_path, max_attempts, state_path=state_path)
        results.append(result)
        context[f"{stage_name}_result"] = result.output

    return results


def prioritize_queue(max_items=None, decisions_path=None, outcomes_path=None):
    """Real prioritization + a real, simple resource-allocation cap.
    Reuses decision_engine.ranking.rank_queue() (ADR-050) — the existing,
    tested global ranking — rather than building a second one."""
    queue = decision_ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)
    return queue[:max_items] if max_items is not None else queue


def _cli_run_ladder_opportunity():
    """Strategic Phase (2026-07-19) CLI bridge: reads {"niche", "ladder",
    "tier"} from stdin (same JSON-in/JSON-out convention as
    book_generator.py --json, chosen over argv for real Arabic/unicode
    niche text) — meant to be spawned by factory_loop.js's
    golden_hunter_bridge step, the same way it already spawns
    market_hunter.py --run.

    Looks up the most recent ACCEPTED decision already recorded for this
    niche (market_hunter.py's own real daily record_ladder_decision()
    call — never re-evaluated here) and runs the real production/
    publishing/learning stages via existing_decision=. Fails honestly
    (never fabricates a decision) if none exists yet — the daily Golden
    Hunter scan must have already accepted this niche for real."""
    try:
        payload = json.loads(sys.stdin.read())
        niche = payload["niche"]
    except Exception as e:
        print(json.dumps({"success": False, "error": f"invalid input: {e}"}, ensure_ascii=False))
        sys.exit(1)
        return

    ladder = payload.get("ladder")
    tier = payload.get("tier", "tier4")

    from decision_engine import store as decision_store
    accepted = [d for d in decision_store.find_decisions_by_niche(niche) if d.get("status") == "ACCEPTED"]
    if not accepted:
        print(json.dumps({
            "success": False,
            "error": "no ACCEPTED decision recorded for this niche yet — market_hunter.py's daily scan must accept it first",
        }, ensure_ascii=False))
        sys.exit(1)
        return
    existing_decision = accepted[-1]  # most recent real decision for this niche

    results = run_cycle(niche, ladder=ladder, tier=tier, execute_production=True, existing_decision=existing_decision)
    by_stage = {r.engine: r for r in results}
    production_result = by_stage.get("production")
    publishing_result = by_stage.get("publishing")

    print(json.dumps({
        "success": True,
        "decision_id": existing_decision.get("decision_id"),
        "production_status": production_result.status if production_result else None,
        "production_id": (production_result.output or {}).get("production_id") if production_result else None,
        "production_success": (production_result.output or {}).get("success") if production_result else None,
        "publishing_status": publishing_result.status if publishing_result else None,
        "publish_record": (publishing_result.output or {}).get("publish_record") if publishing_result else None,
    }, ensure_ascii=False, default=str))


def main():
    if "--run-ladder-opportunity" in sys.argv:
        _cli_run_ladder_opportunity()
        return
    print(json.dumps({"success": False, "error": "unknown or missing CLI flag — expected --run-ladder-opportunity"}, ensure_ascii=False))
    sys.exit(1)


if __name__ == "__main__":
    main()
