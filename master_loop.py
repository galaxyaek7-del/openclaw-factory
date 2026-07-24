#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenClaw Factory — Complete Autonomous Company Master Loop (2026-07-24).

**Explicit directive: "Do NOT create another isolated engine... Never
duplicate existing logic. Reuse every existing module."** This module
contains as close to zero new business logic as possible — it is a
real, disclosed map of the 20 named lifecycle stages onto the modules
this factory already has, plus thin orchestration/tracing over them.
Every one of the ~15 "engines" built earlier in this same session
(market_memory, growth_engine, commercial_intelligence, investment_
pipeline, portfolio_engine, production_blueprint, execution_status,
scheduler) is reused here, never re-implemented.

**The audit** (the directive's own step one): every stage below is
mapped to the exact real module/function that already performs it —
verified against this repo directly, not assumed:

  1. Global Opportunity Discovery -> market_hunter.py / golden_hunter/
     hunt.py (real, live-network; NOT invoked from this module — too
     expensive/side-effecting for an orchestration/read layer, same
     reasoning ADR-112 already gave for not re-deriving market
     intelligence signals live)
  2. Market Intelligence          -> market_intelligence_engine.py
  3. Executive Decision           -> decision_engine/engine.py +
                                      executive_board.py
  4. Portfolio Selection          -> portfolio_engine.py (ADR-113)
  5. Investment Priority          -> value_engine.py / investment_
                                      pipeline.py (ADR-102/112)
  6. Product Blueprint            -> production_blueprint.py (ADR-114)
  7. Production Pipeline          -> production_blueprint.
                                      classify_production_pipeline()
  8. Product Generation           -> book_generator.py / orchestrator/
                                      engines/production.py
  9. Quality Gate                 -> inspectors.py (Dual Inspection) +
                                      executive_quality_gate.py
  10. Commercial Packaging        -> dossier_bundle/build_bundle.py
  11. Store Selection             -> growth_engine.evaluate_channel_
                                      expansion() / revenue_pipeline.
                                      plan.build_production_plan()
  12. Automatic Publishing        -> distributor.py / channels/*
  13. Marketing Execution         -> lib/publisher_seo.js (real, thin —
                                      SEO metadata only, ADR-108)
  14. Sales Monitoring            -> scripts/poll_sales.py / channels/
                                      ledger.py
  15. Customer Feedback           -> production_evidence/record.py
                                      (real, honest gap — no channel)
  16. Knowledge Update            -> knowledge_graph/build.py (ADR-106)
  17. Market Memory Update        -> market_memory.py (ADR-106)
  18. Revenue Engine Update       -> revenue_pipeline/pipeline.py +
                                      channels/ledger.py::reconcile_
                                      ledger_to_finance()
  19. Executive Learning          -> decision_engine/learning.py (real,
                                      factory-wide, not niche-specific)
  20. Automatic Discovery of Next -> scheduler.py::decide_next_actions()
      Opportunity                    (real, evidence-based recommendation
                                      — on-demand, not a live trigger;
                                      unchanged standing decision, ADR-107,
                                      applied a third time)

Several of the 20 named stages collapse onto the SAME real underlying
signal in this factory today (e.g. stages 1-2 both resolve to "a real
decision exists," stages 8-9 both resolve to "a real production attempt
succeeded") — reported honestly as shared evidence, never split into
20 independently-fabricated booleans this factory cannot actually tell
apart yet.

**"Permanent heartbeat" / "never stop" / live process**: unchanged
standing decision (ADR-107, confirmed via AskUserQuestion; reaffirmed
ADR-110) — on-demand only. This module builds the real function a
human or external trigger calls; it does not start a live process,
does not schedule its own re-run, and does not auto-execute production/
publishing on its own (those stay behind the same real human
confirmation `run_master_cycle()` has always required).
"""

from datetime import datetime, timezone


def trace_lifecycle(niche, decisions_path=None, board_path=None, alerts_path=None,
                     reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """Real, evidence-based trace of one niche across the 20 named
    stages. Reuses production_blueprint.build_production_blueprint()
    and execution_status.build_execution_status() directly — zero new
    evidence computed here, only remapped onto these exact 20 names.
    Returns None (never fabricated) when this niche has no real
    decision on record at all."""
    import factory_orchestrator as fo
    import production_blueprint
    import execution_status
    import market_memory

    decision = fo.find_decision(niche, decisions_path=decisions_path)
    if decision is None:
        return None

    blueprint = production_blueprint.build_production_blueprint(
        niche, decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    status_result = production_blueprint.classify_production_status(
        niche, decisions_path=decisions_path, timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    lifecycle = status_result["lifecycle_stage"]
    stages = lifecycle["stages"]
    market_memory_profile = market_memory.niche_commercial_profile(niche, evidence_path=evidence_path)
    has_real_sales = bool(market_memory_profile and market_memory_profile.get("sample_size", 0) > 0)

    accepted = decision.get("status") == "ACCEPTED"

    def _stage(name, reached, evidence, owner):
        return {"stage": name, "reached": reached, "evidence": evidence, "owner": owner}

    return {
        "niche": niche,
        "stages": [
            _stage("1_global_opportunity_discovery", stages["global_opportunity_discovery"]["reached"],
                   stages["global_opportunity_discovery"]["evidence"], "market_hunter.py"),
            _stage("2_market_intelligence", decision is not None,
                   "قرار حقيقي مسجَّل (يفترض تحليل سوق سابق)" if decision else "لا قرار",
                   "market_intelligence_engine.py"),
            _stage("3_executive_decision", stages["evidence_based_validation"]["reached"],
                   stages["evidence_based_validation"]["evidence"], "decision_engine.py / executive_board.py"),
            _stage("4_portfolio_selection", accepted, blueprint.get("production_pipeline") if accepted else "يتطلب قراراً مقبولاً", "portfolio_engine.py"),
            _stage("5_investment_priority", accepted, "value_engine.compute_value_profile() حقيقي" if accepted else "يتطلب قراراً مقبولاً", "value_engine.py / investment_pipeline.py"),
            _stage("6_product_blueprint", blueprint is not None, "15 عنصر مخطط حقيقي مُجمَّع" if blueprint else "غير متاح", "production_blueprint.py"),
            _stage("7_production_pipeline", blueprint.get("production_pipeline") is not None if isinstance(blueprint.get("production_pipeline"), str) else False,
                   str(blueprint.get("production_pipeline")), "production_blueprint.classify_production_pipeline()"),
            _stage("8_product_generation", stages["prototype"]["reached"], stages["prototype"]["evidence"], "book_generator.py"),
            _stage("9_quality_gate", stages["premium_production"]["reached"], stages["premium_production"]["evidence"], "inspectors.py (Dual Inspection)"),
            _stage("10_commercial_packaging", stages["premium_production"]["reached"],
                   "نفس دليل نجاح الإنتاج الحقيقي (premium_production) — dossier_bundle.py يُبنى بعده مباشرة", "dossier_bundle/build_bundle.py"),
            _stage("11_store_selection", blueprint.get("distribution_channels", {}).get("recommended_platform") is not None,
                   str(blueprint.get("distribution_channels", {}).get("recommended_platform")), "growth_engine.py / revenue_pipeline/plan.py"),
            _stage("12_automatic_publishing", stages["commercial_launch"]["reached"], stages["commercial_launch"]["evidence"], "distributor.py / channels/*"),
            _stage("13_marketing_execution", stages["commercial_launch"]["reached"],
                   "SEO metadata فقط عند النشر الحقيقي (lib/publisher_seo.js) — قدرة حقيقية محدودة (ADR-108)", "lib/publisher_seo.js"),
            _stage("14_sales_monitoring", has_real_sales, f"{market_memory_profile.get('sample_size', 0)} بيع حقيقي" if market_memory_profile else "صفر", "scripts/poll_sales.py"),
            _stage("15_customer_feedback", stages["customer_testing"]["reached"], stages["customer_testing"]["evidence"], "production_evidence/record.py"),
            _stage("16_knowledge_update", has_real_sales, "نفس دليل المبيعات الحقيقي — knowledge_graph.py يُنشئ CommercialEvent من نفس الحدث", "knowledge_graph/build.py"),
            _stage("17_market_memory_update", has_real_sales, "نفس دليل المبيعات الحقيقي أعلاه", "market_memory.py"),
            _stage("18_revenue_engine_update", has_real_sales, "نفس دليل المبيعات الحقيقي — يُسوَّى تلقائياً إلى finance_data.json", "revenue_pipeline/pipeline.py / channels/ledger.py"),
            _stage("19_executive_learning", None, "إشارة على مستوى المصنع بالكامل، ليست خاصة بهذا النيتش — راجع decision_engine/learning.py::recalibration_report()", "decision_engine/learning.py"),
            _stage("20_next_opportunity_discovery", None, "توصية حقيقية عند الطلب عبر scheduler.py — ليست تلقائية حيّة", "scheduler.py"),
        ],
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def mission_control_heartbeat(decisions_path=None, board_path=None, alerts_path=None,
                               reopen_log_path=None, evidence_path=None, timeline_path=None, outcomes_path=None):
    """The real, thin 6-field heartbeat the directive named. Every
    field is a real value already computed elsewhere — reused, not
    re-derived. 'Current Opportunity' is scheduler.py's own real
    run_now pick (the single highest real-Priority-Score opportunity
    with no active risk); honestly None when nothing qualifies today."""
    import scheduler
    import production_blueprint
    import market_memory
    from decision_engine import learning as decision_learning
    import mission_control_api

    scheduling = scheduler.decide_next_actions(
        decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
        reopen_log_path=reopen_log_path, evidence_path=evidence_path,
        timeline_path=timeline_path, outcomes_path=outcomes_path,
    )
    run_now = scheduling["buckets"]["run_now"]
    current = run_now[0] if run_now else None

    current_product = None
    current_stage = None
    if current:
        blueprint = production_blueprint.build_production_blueprint(
            current["niche"], decisions_path=decisions_path, board_path=board_path, alerts_path=alerts_path,
            reopen_log_path=reopen_log_path, evidence_path=evidence_path,
            timeline_path=timeline_path, outcomes_path=outcomes_path,
        )
        current_product = blueprint.get("production_pipeline") if blueprint else None
        current_stage = blueprint.get("production_status", {}).get("status") if blueprint else None

    return {
        "current_opportunity": current["niche"] if current else None,
        "current_opportunity_reason": current["reason"] if current else "لا فرصة حقيقية تستحق run_now الآن",
        "current_product": current_product,
        "current_stage": current_stage,
        "current_revenue": mission_control_api._revenue(),
        "current_learning": {
            "monthly_market_evolution": market_memory.monthly_evolution_report(evidence_path=evidence_path),
            "recalibration": decision_learning.recalibration_report(decisions_path=decisions_path, outcomes_path=outcomes_path),
        },
        "current_next_action": scheduling,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }
