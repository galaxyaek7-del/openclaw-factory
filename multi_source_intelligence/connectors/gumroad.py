"""
Gumroad connector (ADR-059) — checks the REAL arm status
(channels/registry.py, ADR-4) rather than a hardcoded "unavailable" —
this factory has a fully built Gumroad arm (channels/gumroad_arm.py),
and GUMROAD_ACCESS_TOKEN IS set in .env (updated 2026-08-15, CTO+COO
audit closure; a real product was created on the account 2026-08-14).
The connector asks the real arm, so its status reflects the current
account state automatically, with zero code change.

Note: even when READY, Gumroad's arm exposes account sales (get_sales())
and publishing, not third-party competitor/market search — Gumroad has
no public product-search API. "Available" here means "this factory
could poll ITS OWN account data," not "market research on competitors,"
and the parsed_data says so explicitly.
"""

import channels.gumroad_arm  # noqa: F401,E402 — self-registers
from channels import registry as channel_registry
from channels.base_arm import ArmStatus
from datetime import datetime, timezone

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import CONFIDENCE_SCALE, ConnectorResult, unavailable_result


def _arm_available():
    """True when the real Gumroad arm reports READY (token present)."""
    arm = channel_registry.get("gumroad")
    return arm is not None and arm.status() == ArmStatus.READY


@register_connector("gumroad")
def check(niche, max_results=10):
    arm = channel_registry.get("gumroad")
    if arm is None:
        return unavailable_result("gumroad", "ذراع Gumroad غير مُسجَّلة")

    status = arm.status()
    if status != ArmStatus.READY:
        return unavailable_result("gumroad", f"ذراع Gumroad الحقيقية: {status.value} — الرمز قد لا يكون حيًا في .env")

    return ConnectorResult(
        source="gumroad", timestamp=datetime.now(timezone.utc).isoformat(), availability="available",
        raw_data=None, parsed_data={"note": "الذراع جاهزة لبيانات الحساب الخاص فقط — لا بحث سوق/منافسين علني على Gumroad"},
        confidence=CONFIDENCE_SCALE["low"], evidence_quality="unknown", verification_status="UNKNOWN",
        reason="Gumroad لا يملك واجهة بحث منتجات منافسين علنية بأي حال",
    )
