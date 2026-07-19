"""
AI Capability Evaluator -- Autonomous Digital Company v1, Track B2 (2026-07-19).

recommend_for_task() is deliberately conservative: with real usage data for
exactly one provider (Groq) today, the only honest recommendation it can
ever make is "Groq, because it's the only provider this factory has real
data for" -- or nothing, if Groq itself has never been called. This becomes
genuinely comparative (multiple REAL-metric providers ranked against each
other) the moment a second credential is configured and actually called --
no code change required, since registry.list_providers() already computes
real stats generically for any provider with cost-log history.
"""

from . import registry


def recommend_for_task(task_type, cost_log_path=None):
    providers = registry.list_providers(cost_log_path)
    candidates = [p for p in providers if task_type in p["task_types"]]
    measured = [p for p in candidates if p["real_stats"] and p["real_stats"]["calls"] > 0]

    if not measured:
        return {
            "task_type": task_type,
            "recommendation": None,
            "reason": "لا يوجد أي مزوّد مرشَّح لهذه المهمة يملك بيانات استخدام حقيقية بعد.",
            "candidates_awaiting_configuration": [p["provider"] for p in candidates if not p["configured"]],
        }

    # Ranked by real avg cost per call ascending -- the one comparable REAL
    # number every measured provider has today. With exactly one measured
    # provider, "ranking" is trivial and honestly disclosed as such -- the
    # real, current limit, not a bug.
    ranked = sorted(measured, key=lambda p: p["real_stats"]["avg_cost_usd_per_call"] or float("inf"))
    top = ranked[0]
    reason = (
        f"{top['display_name']} هو المزوّد الوحيد الذي يملك بيانات استخدام حقيقية لهذه المهمة اليوم."
        if len(measured) == 1 else
        f"{top['display_name']} يملك أقل متوسط تكلفة حقيقية لكل استدعاء بين {len(measured)} مزوّدين يملكون بيانات حقيقية."
    )
    return {
        "task_type": task_type,
        "recommendation": top["provider"],
        "reason": reason,
        "measured_providers": [p["provider"] for p in measured],
        "candidates_awaiting_configuration": [p["provider"] for p in candidates if not p["configured"]],
    }
