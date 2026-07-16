"""
Inactive/underused component detection (ADR-052) — real, zero-activity
checks only: an orchestrator engine with no timeline record, or a
distribution arm with no recorded publish attempt (channels/ledger.py,
same file scripts/poll_sales.py and distributor.py already write to).
"""

import channels.etsy_arm  # noqa: F401,E402
import channels.gumroad_arm  # noqa: F401,E402
import channels.payhip_arm  # noqa: F401,E402
from channels import ledger as sales_ledger
from channels import registry as channel_registry
from orchestrator import timeline as orch_timeline
from orchestrator.types import EXECUTION_ORDER


def detect_inactive_components(decisions_path=None, timeline_path=None, sales_ledger_path=None):
    items = []

    executed_engines = {r.get("engine") for r in orch_timeline.read_timeline(path=timeline_path)}
    for stage in EXECUTION_ORDER:
        if stage not in executed_engines:
            items.append({
                "component": f"orchestrator engine: {stage}",
                "evidence": "صفر تنفيذ واحد في data/orchestrator_timeline.jsonl",
            })

    attempted_platforms = {
        e.get("platform") for e in sales_ledger.read_events(event_type="publish_attempt", ledger_path=sales_ledger_path)
    }
    for arm in channel_registry.all_arms():
        if arm.name not in attempted_platforms:
            items.append({
                "component": f"channel arm: {arm.name}",
                "evidence": "صفر محاولة نشر واحدة في data/sales_ledger.jsonl",
            })

    if not items:
        return {"detected": False, "items": []}
    return {"detected": True, "items": items}
