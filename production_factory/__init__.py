"""
OpenClaw Factory — Production Factory (Phase 7).

Not new infrastructure: every section of a Production Dossier reuses an
already-built, already-real computation. Nothing here scores an
opportunity, decides ACCEPT/REJECT, or spends money — this package only
assembles what already exists into one standardized document per
opportunity, plus the two genuinely new (and trivial) pieces:
a deterministic Production ID and an honest per-product-type capability
matrix.

  Product specification    revenue_pipeline.plan.build_production_plan()
                            (Phase 6), reused verbatim.
  Market positioning         Decision.evaluation_snapshot's real
                            demand_pattern/competitors/opportunity_gap/
                            customer_pain (market_intelligence_core,
                            ADR-049), reused, not re-derived.
  Customer profile (ICP)      Honest: only a real audience qualifier
                            already in profit_oracle.SUBNICHE_QUALIFIERS
                            (the same real keyword list _score_
                            competition() already checks) counts as real
                            signal. No survey/analytics data exists
                            anywhere in this factory, so anything beyond
                            a literal keyword match is honestly Unknown
                            -- never an invented demographic.
  Pricing strategy            revenue_pipeline.plan + profit_oracle.
                            butter_price() (Constitution §16), reused.
  Asset checklist              The real, fixed set of artifacts book_
                            generator.py/cover_designer_v2.py actually
                            produce today -- not aspirational.
  Quality checklist             The real check names inspectors.py's
                            inspect_technical()/audit_commercial()
                            already run (ADR from this factory's Dual
                            Inspection system) -- listed as a template,
                            never re-implemented.
  Publishing checklist           channels.registry.all_arms()'s real,
                            live status() per platform -- never a
                            hardcoded list.
  Success metrics                revenue_pipeline.plan's real production
                            cost + ROI estimate (Phase 6), reused.
  Production ID                   A deterministic ID derived from the
                            Decision's own decision_id (already
                            deterministic, ADR-050) -- not a new ID
                            scheme.
  Pre-production verification      Evidence quality (confidence, ADR-
                            049), market readiness (real arm status),
                            production feasibility (execution dimension
                            score, ADR-049), expected ROI (Phase 6), risk
                            level (safety_filter.py, ADR-039) -- all
                            already-computed real values, assembled.

Product-type flexibility (requirement 6) is answered honestly, not
aspirationally: book/printable/premium/elite are REAL today via
book_engine (ADR-020/024/027); SaaS/AI Tools/APIs/Automation Systems are
explicitly reported as NOT YET BUILT (FACTORY_STATUS.md, OCTOPUS_
ARCHITECTURE.md's own track list) -- never claimed as capability this
factory doesn't have.

This package NEVER calls revenue_pipeline.process_opportunity(execute=
True) or spends any money -- "never produce a product without a
complete dossier" is enforced by this package only ever producing
dossiers; actually executing production for one remains a separate,
deliberate, explicitly-authorized action (Phase 6's revenue_pipeline).
"""
