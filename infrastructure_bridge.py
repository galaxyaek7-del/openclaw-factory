"""
Infrastructure Bridge (EOS Phase 1, extracted as a shared module in
Phase 2, 2026-07-19) — reuses lib/infrastructure_intelligence.js's real
getInfrastructureStatus() via its CLI entry point, rather than
reimplementing CPU/memory/disk/cost-trend logic in Python a second
time (the first Python-spawns-JS call in this codebase; every other
cross-language call goes the other way). Extracted out of
mission_control_api.py so ai_doctor.py can reuse it too, without
depending on mission_control_api.py (a thin CLI dispatcher, not meant
to be imported as a library by other modules).

Fails honestly (returns None) on any error — a missing Node binary or a
subprocess hiccup must never break the report calling this.
"""

import json
import os
import subprocess

_FACTORY_ROOT = os.path.dirname(os.path.abspath(__file__))


def get_infrastructure_status(timeout=15):
    try:
        result = subprocess.run(
            ["node", os.path.join(_FACTORY_ROOT, "lib", "infrastructure_intelligence.js")],
            capture_output=True, encoding="utf-8", timeout=timeout, cwd=_FACTORY_ROOT,
        )
        if result.returncode != 0:
            return None
        return json.loads(result.stdout.strip())
    except Exception:
        return None


def render_infrastructure_markdown(status):
    if status is None:
        return "تعذّر جلب حالة البنية التحتية الحقيقية هذه المرة (Node غير متاح أو فشل الاستدعاء) — لم يُدرَج قسم البنية التحتية.\n"
    sys_info = status.get("system", {})
    cost = status.get("ai_cost_trend", {})
    cpu = sys_info.get("cpu", {})
    mem = sys_info.get("memory", {})
    disk = sys_info.get("disk", {})
    lines = [
        f"- **CPU**: {cpu.get('count', '؟')} أنوية — {cpu.get('model', '؟')}",
        f"- **الذاكرة**: {mem.get('used_pct', '؟')}% مستخدَم",
        f"- **القرص**: {disk.get('used_pct', disk.get('error', '؟'))}%" if not disk.get("error") else f"- **القرص**: {disk['error']}",
        f"- **تكلفة الذكاء الاصطناعي (7 أيام)**: ${cost.get('recent_7d_cost_usd', 0)} عبر {cost.get('recent_7d_calls', 0)} استدعاء"
        + (" ⚠️ ارتفاع غير معتاد" if cost.get("outlier") else ""),
    ]
    return "\n".join(lines) + "\n"
