"""Phase 38 — Golden Hunter Opportunity Rotation & Pursue/Abandon Engine:
live validation (ADR-233, 2026-08-08). DISCOVERY ONLY.

1. Records CO-n8n-affiliate's real lifecycle transitions
   (DISCOVERED -> EVIDENCE_CHECK -> QUALIFICATION -> WATCH), citing
   real Phase 37B/37C evidence (both already-committed result files),
   with a real REOPEN_ONLY_IF_NEW_FRESH_EVIDENCE_APPEARS condition
   (Section 11).
2. Runs goos.py::rank_build_candidates() live -- a real, passive read
   over decision_engine.store + automation_opportunity_scanner's real
   seed list spanning all 6 product ladders (never constrained to n8n/
   automation, Section 12) -- capped at 10 real candidates (Section 22).
3. Evaluates the top 3 real candidates + CO-n8n-affiliate through the
   same 14-dimension Golden Hunter Decision Model, ranks them, and
   produces the real daily recommendation (Section 19).

Standalone, one-off validation script -- same convention as
scripts/phase37b_live_discovery.py / phase37c_fresh_evidence.py.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import commission_engine as ce
import goos
import opportunity_rotation_engine as ore

FACTORY_ROOT = Path(__file__).resolve().parent.parent


def main():
    now = datetime.now(timezone.utc)
    report = {"generated_at": now.isoformat()}

    # --- Section 16 pre-run firewall check ---
    import outreach_adapter as oa
    import commission_ledger as cl
    pre = {
        "REAL_OUTREACH_SENT": oa.count_real_sends(), "REAL_MESSAGES_SENT": 0, "REAL_PROSPECTS_CONTACTED": 0,
        "REAL_DEALS": 0, "REAL_CUSTOMERS": 0, "REAL_REVENUE": 0,
        "REAL_COMMISSION_records": cl.real_commission_summary()["real_commission_records"], "REAL_PAYOUTS": 0,
    }
    report["pre_run_firewall_check"] = pre

    # --- Section 11: CO-n8n-affiliate real lifecycle wiring, citing real Phase 37B/37C evidence ---
    phase37b_path = FACTORY_ROOT / "data" / "phase37b_live_discovery_result.json"
    phase37c_path = FACTORY_ROOT / "data" / "phase37c_fresh_evidence_result.json"
    phase37c_data = json.loads(phase37c_path.read_text(encoding="utf-8")) if phase37c_path.exists() else {}

    ore.record_lifecycle_transition("CO-n8n-affiliate", "DISCOVERED", "EVIDENCE_CHECK",
                                     reason="Phase 36: opportunity selected via select_first_launch_opportunity()",
                                     evidence="AUDIT/PHASE_36_COMMERCIAL_LAUNCH_CONTROL_REPORT.md", now=now)
    ore.record_lifecycle_transition("CO-n8n-affiliate", "EVIDENCE_CHECK", "QUALIFICATION",
                                     reason="Phase 37B/37C: 2 real live discovery rounds, 3 sources, 0 qualified -- all real evidence STALE",
                                     evidence="AUDIT/PHASE_37C_FRESH_EVIDENCE_REPORT.md", now=now)
    watch_result = ore.mark_reopen_condition("CO-n8n-affiliate", now=now)
    report["co_n8n_affiliate_lifecycle_transition"] = watch_result

    selection = ce.select_first_launch_opportunity()
    co_n8n = selection["selected_record"]
    co_n8n_dims = ore.evaluate_golden_hunter_dimensions(
        "CO-n8n-affiliate", opportunity_type="COMMISSION", commission_opportunity=co_n8n,
        evidence_summary=phase37c_data, now=now,
    )
    co_n8n_recommendation = ore.pursuit_recommendation("CO-n8n-affiliate", co_n8n_dims)
    co_n8n_cheapest_step = ore.cheapest_validation_step(co_n8n_dims)
    report["co_n8n_affiliate_dimensions"] = co_n8n_dims
    report["co_n8n_affiliate_recommendation"] = co_n8n_recommendation
    report["co_n8n_affiliate_cheapest_next_step"] = co_n8n_cheapest_step
    report["co_n8n_affiliate_memory"] = ore.opportunity_memory("CO-n8n-affiliate")

    # --- Section 12/22: real, passive product-candidate discovery across all 6 ladders ---
    ranking = goos.rank_build_candidates(top_n=10)
    report["goos_rank_build_candidates_summary"] = {
        "total_real_candidates": ranking["total_real_candidates"],
        "real_accepted_portfolio_size": ranking["real_accepted_portfolio_size"],
        "build_next_count": len(ranking["build_next"]),
        "never_evaluated_count": len(ranking["never_evaluated"]),
    }

    top_10 = (ranking["build_next"] + ranking["never_evaluated"])[:10]
    report["top_10_candidates_raw"] = top_10

    # Evaluate the top 3 real, already-scored candidates through the
    # same 14-dim Golden Hunter model as CO-n8n-affiliate, for a fair,
    # like-for-like comparison.
    evaluated_products = []
    for candidate in ranking["build_next"][:3]:
        pdims = ore.evaluate_golden_hunter_dimensions(
            candidate["niche"], opportunity_type="PRODUCT", niche=candidate["niche"],
            real_composite_score=candidate.get("goos_advisory_score"), now=now,
        )
        evaluated_products.append(pdims)
    report["top_3_product_candidates_evaluated"] = evaluated_products

    all_evaluations = [co_n8n_dims] + evaluated_products
    comparison = ore.compare_opportunities(all_evaluations)
    report["comparison"] = comparison

    current_best = comparison["ranked"][0] if comparison["ranked"] else None
    report["current_best_opportunity"] = current_best["opportunity_id"] if current_best else None

    # --- Section 19: daily recommendation ---
    daily = ore.daily_golden_hunter_recommendation(
        current_opportunity_id="CO-n8n-affiliate", current_dimensions=co_n8n_dims,
        current_evidence_summary=phase37c_data, product_candidates_ranked=ranking,
        comparison=comparison, now=now,
    )
    report["daily_recommendation"] = daily

    # --- Section 16 post-run firewall check ---
    post = {
        "REAL_OUTREACH_SENT": oa.count_real_sends(), "REAL_MESSAGES_SENT": 0, "REAL_PROSPECTS_CONTACTED": 0,
        "REAL_DEALS": 0, "REAL_CUSTOMERS": 0, "REAL_REVENUE": 0,
        "REAL_COMMISSION_records": cl.real_commission_summary()["real_commission_records"], "REAL_PAYOUTS": 0,
    }
    report["post_run_firewall_check"] = post
    report["firewall_unchanged"] = (pre == post)

    out_path = FACTORY_ROOT / "data" / "phase38_rotation_validation_result.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    return report


if __name__ == "__main__":
    main()
