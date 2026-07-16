"""
Decision Engine — learning from real outcomes (ADR-050).

Two real, tested functions over whatever real matched outcomes actually
exist:

  compute_prediction_accuracy() — of every ACCEPTED decision with a real,
    matched sales outcome, what fraction actually sold? A simple, honest
    hit-rate — not a fabricated statistical model dressed up as machine
    learning ("no placeholder AI").

  recalibration_report() — for each scoring dimension, the real average
    normalized_score among ACCEPTED-and-sold niches versus ACCEPTED-and-
    not-yet-sold niches. A real, computed difference a human (or a future,
    separately-approved change) can use to reweight confidence — this
    reports a finding, it does not silently rewrite market_intelligence_
    core's live scoring itself. Auto-applying a reweighting derived from
    a handful of data points would be exactly the "fake precision" this
    factory's discipline forbids (see ADR-034's trigger-gated pattern).

Both require a minimum real sample size before reporting anything beyond
"insufficient data" — with zero real sales in this factory as of
2026-07-16 (BLOCKERS.md #2), that is exactly what they report today, and
that is the correct, honest answer, not a bug to work around.
"""

from decision_engine import store

MIN_SAMPLES_FOR_RECALIBRATION = 3


def compute_prediction_accuracy(decisions_path=None, outcomes_path=None):
    decisions = store.latest_decision_per_niche(path=decisions_path)
    outcomes = list(store.read_outcomes(path=outcomes_path))
    matched_decision_ids = {o["decision_id"] for o in outcomes if o.get("matched") and o.get("decision_id")}

    accepted = [d for d in decisions.values() if d.get("status") == "ACCEPTED"]
    if not accepted:
        return {"accuracy": None, "accepted_decisions": 0, "real_outcomes": 0,
                "reason": "لا قرارات ACCEPTED بعد لقياس دقتها"}

    n_with_outcome = sum(1 for d in accepted if d["decision_id"] in matched_decision_ids)
    if n_with_outcome == 0:
        return {
            "accuracy": None, "accepted_decisions": len(accepted), "real_outcomes": 0,
            "reason": f"{len(accepted)} قراراً ACCEPTED لكن صفر نتيجة مبيعات حقيقية مرتبطة بعد — لا بيانات كافية لحساب الدقة",
        }

    # Every ACCEPTED decision with a matched real outcome did, by
    # definition of being matched to a real "sale" event, actually sell —
    # so today's hit-rate is trivially 100% of what's matched. This stops
    # being trivial the moment a decision can be matched to zero sales
    # over a real observation window (a real "did not sell" signal) rather
    # than only ever being matched on the sale event itself — a genuine
    # improvement documented as a follow-up in ADR-050, not attempted here
    # without that real window-based signal existing yet.
    accuracy = round(100 * n_with_outcome / len(accepted), 1)
    return {"accuracy": accuracy, "accepted_decisions": len(accepted), "real_outcomes": n_with_outcome}


def recalibration_report(decisions_path=None, outcomes_path=None):
    decisions = store.latest_decision_per_niche(path=decisions_path)
    outcomes = list(store.read_outcomes(path=outcomes_path))
    matched_decision_ids = {o["decision_id"] for o in outcomes if o.get("matched") and o.get("decision_id")}

    accepted = [d for d in decisions.values() if d.get("status") == "ACCEPTED"]
    sold = [d for d in accepted if d["decision_id"] in matched_decision_ids]
    not_sold = [d for d in accepted if d["decision_id"] not in matched_decision_ids]

    if len(sold) < MIN_SAMPLES_FOR_RECALIBRATION:
        return {
            "recalibrated": False,
            "real_sold_samples": len(sold),
            "min_required": MIN_SAMPLES_FOR_RECALIBRATION,
            "reason": f"{len(sold)} عينة مبيعات حقيقية مطابقة فقط — أقل من الحد الأدنى {MIN_SAMPLES_FOR_RECALIBRATION} لأي إعادة معايرة ذات معنى",
        }

    per_dimension = {}
    dims = set()
    for d in sold + not_sold:
        dims.update(d.get("evaluation_snapshot", {}).get("dimension_scores", {}).keys())

    for dim in dims:
        sold_scores = [
            d["evaluation_snapshot"]["dimension_scores"][dim]["normalized_score"]
            for d in sold
            if d["evaluation_snapshot"].get("dimension_scores", {}).get(dim, {}).get("normalized_score") is not None
        ]
        not_sold_scores = [
            d["evaluation_snapshot"]["dimension_scores"][dim]["normalized_score"]
            for d in not_sold
            if d["evaluation_snapshot"].get("dimension_scores", {}).get(dim, {}).get("normalized_score") is not None
        ]
        if not sold_scores or not not_sold_scores:
            continue
        avg_sold = sum(sold_scores) / len(sold_scores)
        avg_not_sold = sum(not_sold_scores) / len(not_sold_scores)
        per_dimension[dim] = {
            "avg_score_when_sold": round(avg_sold, 1),
            "avg_score_when_not_yet_sold": round(avg_not_sold, 1),
            "difference": round(avg_sold - avg_not_sold, 1),
        }

    return {
        "recalibrated": True,
        "real_sold_samples": len(sold),
        "real_not_yet_sold_samples": len(not_sold),
        "per_dimension": per_dimension,
        "note": "تقرير إحصائي حقيقي فقط — لا يُعدِّل تلقائياً منطق التسجيل الحي في market_intelligence_core؛ يحتاج قراراً منفصلاً لتطبيقه",
    }
