"""
Revenue Pipeline orchestration (Phase 6) — see package docstring for the
full mapping of every step to the existing component it reuses.

Standalone, deliberately-run tool, same convention as every module this
factory has introduced:

    python -m revenue_pipeline.pipeline
"""

import json
from datetime import datetime, timezone

from decision_engine import ranking as decision_ranking
from production_evidence import record as evidence_record

from revenue_pipeline import plan as plan_module


def _time_to_market(decision, evidence):
    """Real elapsed time between the real decision timestamp and the
    real production stage's finished_at — Unknown until real production
    has actually happened. The only genuinely new computation in this
    package; everything else is reuse."""
    decided_at = decision.get("decided_at")
    production_events = evidence.get("execution_status") or []
    completed = [e for e in production_events if e.get("status") == "SUCCESS"]

    if not completed or not decided_at:
        return {"maturity": "DISCOVERY", "reason": "لم يُنفَّذ إنتاج حقيقي بعد لقياس الوقت الفعلي للسوق"}

    try:
        start = datetime.fromisoformat(decided_at)
        end = datetime.fromisoformat(completed[-1]["finished_at"])
        return {"maturity": "REAL", "seconds": round((end - start).total_seconds(), 1)}
    except (KeyError, ValueError, TypeError):
        return {"maturity": "DISCOVERY", "reason": "تعذَّر حساب الوقت من الطوابع الزمنية المسجَّلة"}


def _validate_quality(niche, production_output, production_plan):
    """Reuses inspectors.final_inspection() directly — the existing Dual
    Inspection gate (technical + commercial). Only meaningful once a real
    PDF actually exists (execute=True and production succeeded);
    otherwise honestly not yet applicable."""
    if not production_output or not production_output.get("success"):
        return {"maturity": "DISCOVERY", "reason": "لم يُنتَج ملف PDF حقيقي بعد لتطبيق فحص الجودة عليه"}

    import inspectors

    product = {
        "pdf_path": production_output.get("path"),
        "cover_path": (production_output.get("cover") or {}).get("path"),
        "title": production_output.get("topic") or niche,
        "subtitle": "",
        "author": "OpenClaw Factory",
        "niche": niche,
        "price": production_plan.get("recommended_price"),
        # ADR-077: the ECONOMICS platform (which real fee/royalty band to
        # validate against), not the distribution-channel recommendation —
        # "paddle" has no config/economics.json entry, would raise
        # "unknown platform" from inspectors.py's own economics lookup.
        "platform": production_plan.get("economics_platform", production_plan.get("recommended_platform")),
    }
    return inspectors.final_inspection(product)


def process_opportunity(decision, execute=False, timeline_path=None, decisions_path=None,
                         analysis_db_file=None, outcomes_path=None, state_path=None,
                         competitor_db_file=None, ledger_path=None, competitor_history_file=None):
    """One ACCEPTED opportunity through the revenue pipeline. execute=False
    (default) never spends real money or publishes anything live — this
    only reuses orchestrator.run_cycle()'s own existing safety switch,
    never bypasses it.

    competitor_db_file/ledger_path: forwarded to orchestrator.run_cycle()
    (2026-07-23) — without these, every execute=True call here wrote real
    competitor-cache and sales-ledger records with no test-isolation
    switch, unlike every other stateful side effect this function already
    exposes an override for. competitor_history_file (Live Competitive
    Intelligence Layer, 2026-07-23): same reasoning, for the new real
    snapshot-history write get_or_refresh_competitors() now also makes."""
    from orchestrator import orchestrator as orch

    production_plan = plan_module.build_production_plan(decision)

    production_output = None
    if execute:
        stage_results = orch.run_cycle(
            decision["niche"], external_signal=decision.get("external_signal"),
            tier=decision.get("tier", "tier4"), execute_production=True,
            timeline_path=timeline_path, decisions_path=decisions_path,
            analysis_db_file=analysis_db_file, outcomes_path=outcomes_path,
            state_path=state_path, existing_decision=decision,
            competitor_db_file=competitor_db_file, ledger_path=ledger_path,
            competitor_history_file=competitor_history_file,
        )
        production_stage = next((r for r in stage_results if r.engine == "production"), None)
        production_output = production_stage.output if production_stage else None

    evidence = evidence_record.build_evidence_record(
        decision["niche"], tier=decision.get("tier", "tier4"), timeline_path=timeline_path,
        decisions_path=decisions_path, outcomes_path=outcomes_path,
    )

    quality = _validate_quality(decision["niche"], production_output, production_plan)
    cost = plan_module.estimate_production_cost()
    roi = plan_module.estimate_roi(
        production_plan["recommended_price"],
        cost.get("estimated_cost_usd") if cost.get("maturity") == "REAL" else None,
        platform=production_plan.get("economics_platform", production_plan["recommended_platform"]),
    )

    return {
        "niche": decision["niche"],
        "production_plan": production_plan,
        "quality_validation": quality,
        "business_lifecycle": evidence,
        "time_to_market": _time_to_market(decision, evidence),
        "production_cost": cost,
        "expected_roi": roi,
        "executed": execute,
    }


def run_revenue_pipeline(execute=False, timeline_path=None, decisions_path=None,
                          analysis_db_file=None, outcomes_path=None,
                          competitor_db_file=None, ledger_path=None, competitor_history_file=None):
    """Requirement 1: select ONLY accepted opportunities — reuses
    decision_engine.ranking.rank_queue() (ADR-050) directly, the exact
    same real, ranked, ACCEPTED-and-not-yet-executed queue every other
    layer this factory built today already reads from."""
    accepted = decision_ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)

    if not accepted:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processed": 0,
            "results": [],
            "reason": "لا فرصة ACCEPTED واحدة في طابور القرار اليوم — لا نشاط إيراد حقيقي لتسجيله",
        }

    results = [
        process_opportunity(
            d, execute=execute, timeline_path=timeline_path, decisions_path=decisions_path,
            analysis_db_file=analysis_db_file, outcomes_path=outcomes_path,
            competitor_db_file=competitor_db_file, ledger_path=ledger_path,
            competitor_history_file=competitor_history_file,
        )
        for d in accepted
    ]

    return {"generated_at": datetime.now(timezone.utc).isoformat(), "processed": len(results), "results": results}


def render_ceo_revenue_report(pipeline_result):
    lines = []
    lines.append("# تقرير الإيراد التنفيذي — OpenClaw Factory")
    lines.append(f"**التوليد:** {pipeline_result['generated_at']}")
    lines.append("")

    if pipeline_result["processed"] == 0:
        lines.append(f"**لا نشاط إيراد اليوم:** {pipeline_result['reason']}")
        return "\n".join(lines) + "\n"

    lines.append(f"**فرص قيد التنفيذ:** {pipeline_result['processed']}")
    lines.append("")

    for r in pipeline_result["results"]:
        lines.append(f"## {r['niche']}")
        plan = r["production_plan"]
        lines.append(f"- **السعر المُوصى به:** {plan['recommended_price']} | **المنصة:** {plan['recommended_platform']}")

        cost = r["production_cost"]
        if cost["maturity"] == "REAL":
            lines.append(f"- **تكلفة الإنتاج الحقيقية:** ${cost['estimated_cost_usd']} (من {cost['sample_size']} استدعاء حقيقي)")
        else:
            lines.append(f"- **تكلفة الإنتاج:** غير معروفة — {cost['reason']}")

        roi = r["expected_roi"]
        if roi["maturity"] == "REAL":
            lines.append(f"- **العائد المتوقَّع:** {roi['roi_pct']}% (صافٍ ${roi['expected_net_after_cost']} بعد التكلفة)")
        else:
            lines.append(f"- **العائد المتوقَّع:** غير معروف — {roi['reason']}")

        ttm = r["time_to_market"]
        if ttm["maturity"] == "REAL":
            lines.append(f"- **الوقت الفعلي للسوق:** {ttm['seconds']} ثانية")
        else:
            lines.append(f"- **الوقت للسوق:** غير معروف — {ttm['reason']}")

        quality = r["quality_validation"]
        if quality.get("maturity") == "DISCOVERY":
            lines.append(f"- **فحص الجودة:** لم يُطبَّق بعد — {quality['reason']}")
        else:
            lines.append(f"- **فحص الجودة:** {'نجح' if quality.get('passed') else 'فشل'}")

        lines.append(f"- **نُفِّذ فعلياً:** {'نعم' if r['executed'] else 'لا — تخطيط فقط'}")
        lines.append("")

    return "\n".join(lines) + "\n"


def main():
    result = run_revenue_pipeline()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
