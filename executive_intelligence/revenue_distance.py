"""
Distance to next real revenue event (ADR-052) — deliberately NEVER a
numeric time estimate: this factory has zero real sales ever recorded
(confirmed directly, decision_engine/feedback.py, ADR-050), so there is
no historical rate to project a "days until next sale" figure from —
producing one would be exactly the fabricated KPI this layer exists to
refuse. Instead: the real, concrete blockers standing between today and
the next real sale, each traceable to a live signal, matching
BLOCKERS.md's own discipline.
"""

import channels.etsy_arm  # noqa: F401,E402 — self-registers on import
import channels.gumroad_arm  # noqa: F401,E402
import channels.payhip_arm  # noqa: F401,E402
from channels import registry as channel_registry
from channels.base_arm import ArmStatus
from decision_engine import ranking


def estimate_distance_to_next_revenue(decisions_path=None, outcomes_path=None):
    blockers = []

    ready_arms = [a.name for a in channel_registry.all_arms() if a.status() == ArmStatus.READY]
    if not ready_arms:
        blockers.append({
            "blocker": "no_live_platform_api_key",
            "evidence": "لا ذراع نشر واحدة بحالة READY في channels/registry.py — لا مفتاح API حي بعد (BLOCKERS.md #2)",
        })

    queue = ranking.rank_queue(decisions_path=decisions_path, outcomes_path=outcomes_path)
    if not queue:
        blockers.append({
            "blocker": "no_accepted_opportunity_in_queue",
            "evidence": "لا فرصة ACCEPTED واحدة في طابور القرار جاهزة للتنفيذ — decision_engine.ranking.rank_queue()",
        })

    if blockers:
        return {
            "maturity": "DISCOVERY",
            "blockers": blockers,
            "note": "لا تقدير زمني رقمي — صفر مبيعات حقيقية سابقة يمكن بناء معدّل تنبؤ عليه",
        }

    top = queue[0]
    return {
        "maturity": "ESTIMATED",
        "next_step": f"تنفيذ '{top.get('niche')}' (أعلى فرصة في الطابور) عبر orchestrator.run_cycle(..., execute_production=True)",
        "evidence": top.get("reasoning"),
        "note": "الخطوة التالية معروفة وحقيقية؛ التوقيت الزمني نفسه لا يزال غير معروف بلا سجل مبيعات حقيقي",
    }
