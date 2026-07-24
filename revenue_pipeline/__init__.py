"""
Galaxy Forge — Revenue Pipeline (Phase 6).

Not a new engine, not a new architecture: every step reuses an already-
built, already-tested component. This package's only job is to wire them
together in business-execution order for ACCEPTED opportunities.

  1. Select ACCEPTED   decision_engine.ranking.rank_queue() (ADR-050) —
                        reused, not re-derived.
  2. Production plan    revenue_pipeline.plan.build_production_plan() —
                        labels data the pipeline already computed
                        (recommended price/platform, reasoning,
                        evidence snapshot), zero new scoring.
  3. Prepare assets     orchestrator.orchestrator.run_cycle() (ADR-051) —
                        the existing production stage (book_generator.py
                        subprocess). Gated by an explicit `execute` flag,
                        default False — never spends real money unless
                        a caller deliberately opts in, same convention
                        every execution surface this factory has ever
                        introduced already uses.
  4. Validate quality    inspectors.final_inspection() — the existing
                        Dual Inspection gate (technical + commercial),
                        reused directly. Only meaningful once a real PDF
                        actually exists; otherwise honestly reports it
                        hasn't run yet.
  5. Publication package  the same run_cycle() call's "publishing" stage
                        (distributor.distribute(), dry_run preserved).
  6. Business lifecycle   production_evidence.record.build_evidence_record()
                        (ADR-055) — reused verbatim, zero new storage.
  7. Time-to-market       real elapsed time between Decision.decided_at
                        and the production stage's real finished_at —
                        the only genuinely new (and trivial) computation
                        here; Unknown until real production has actually
                        happened.
  8. Production cost      profit_oracle._real_average_ai_cost_per_call()
                        (ADR-041) — reused directly, real logged Groq
                        cost, never fabricated when zero calls are logged.
  9. Expected ROI          economics.net_profit() (ADR-041) — the exact
                        real fee-math function _score_margin() already
                        uses — applied to the recommended price, minus
                        real production cost. No new profit formula.
  10. CEO Revenue Report   pipeline.render_ceo_revenue_report() — a plain
                        Markdown assembly of everything above.
"""
