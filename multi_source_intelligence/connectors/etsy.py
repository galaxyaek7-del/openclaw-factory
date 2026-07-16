"""
Etsy connector (ADR-059) — honestly unavailable for market evidence
today, for two independent real reasons, both stated explicitly:
  1. channels/etsy_arm.py exists for PUBLISHING only, gated on real
     Etsy API credentials (ETSY_API_KEY etc.) which are not present in
     .env today (confirmed: .env has only GROQ_KEY).
  2. Even if those credentials existed, this factory has never built a
     market-research/competitor-search connector against Etsy's public
     Open API v3 — only the publish-side integration exists. Adding
     read-only market search would be new, real, buildable work once
     credentials exist — not attempted here without them to avoid
     guessing at an untested integration.
"""

import channels.etsy_arm  # noqa: F401,E402 — self-registers
from channels import registry as channel_registry
from channels.base_arm import ArmStatus

from multi_source_intelligence.registry import register_connector
from multi_source_intelligence.types import unavailable_result


@register_connector("etsy")
def check(niche, max_results=10):
    arm = channel_registry.get("etsy")
    status = arm.status() if arm else None

    if arm is None or status != ArmStatus.READY:
        detail = status.value if status else "غير مُسجَّلة"
        return unavailable_result("etsy", f"ذراع Etsy الحقيقية: {detail} — لا مفتاح API حي بعد")

    return unavailable_result(
        "etsy",
        "بيانات اعتماد Etsy حقيقية موجودة، لكن لا مُوصِّل بحث سوق/منافسين مبني بعد — فقط تكامل نشر أحادي الاتجاه",
    )
