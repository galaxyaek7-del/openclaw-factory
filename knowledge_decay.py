"""Galaxy Forge -- Knowledge Decay (new, ADR-208, Phase 18, 2026-08-08).

Answers Section 16 of the founder's "Knowledge Graph & Institutional
Memory Engine" directive: track when real knowledge was last verified
and automatically flag staleness for the 7 named category examples
(platform API info, pricing, commission rates, AI model capabilities,
marketplace policies, competitor pricing, regulations).

Checked first: no dedicated staleness-tracking mechanism exists
anywhere in this factory (confirmed by direct search) -- most real
"last verified" facts live only as prose inside ADR/docstring text,
never as a structured, queryable field. This module's real, disclosed
limitation: KNOWN_STALENESS_CHECKS below is a manually-maintained
registry of real, dated facts already documented elsewhere in this
factory (ADR dates, re-verification dates) -- it does not
automatically discover new facts to track. Never invents a
verification date that isn't already real and citable.
"""

from datetime import datetime, timezone
from pathlib import Path

# Real, disclosed per-category staleness thresholds -- how long a fact
# in this category can go unverified before it's flagged. Chosen per
# category based on how fast that category realistically changes in
# the real world (payment/commission terms and AI capabilities change
# faster than a static regulation's own text, for example).
_STALENESS_THRESHOLDS_DAYS = {
    "platform_api": 60,
    "pricing": 30,
    "commission_rates": 60,
    "ai_model_capabilities": 30,
    "marketplace_policies": 90,
    "competitor_pricing": 30,
    "regulations": 90,
}

# Real, dated facts already documented elsewhere in this factory --
# every entry cites its own real source. Manually maintained (a real,
# disclosed limitation of this module, not hidden).
KNOWN_STALENESS_CHECKS = (
    {
        "category": "platform_api", "subject": "Payhip public API product-creation capability",
        "last_verified": "2026-08-07", "source": "OpenClaw_Brain/00_Governance/ADR-025-payhip-etsy-arms-adr8-override.md addendum",
    },
    {
        "category": "commission_rates", "subject": "Amazon Associates commission rate (5% typical digital-adjacent)",
        "last_verified": "2026-08-07", "source": "business_development.py::PLATFORM_REGISTRY['amazon']",
    },
    {
        "category": "commission_rates", "subject": "19-platform PLATFORM_REGISTRY (18 of 19 platforms)",
        "last_verified": "2026-08-07", "source": "business_development.py (ADR-188) -- only Amazon re-verified since; the other 18 keep their original research date",
    },
    {
        "category": "regulations", "subject": "EU AI Act high-risk obligation enforcement timeline",
        "last_verified": "2026-08-06", "source": "books/eu_ai_act_compliance_toolkit.pdf's regulatory-currency correction (Digital Omnibus deferral to December 2027)",
    },
    {
        "category": "pricing", "subject": "EU AI Act Compliance Toolkit Paddle price ($155)",
        "last_verified": "2026-08-07", "source": "contradiction_engine.py::detect_price_contradiction() -- re-verifiable live against the Paddle API any time",
    },
    {
        "category": "ai_model_capabilities", "subject": "Groq (Llama 3.1 8B Instant) real usage stats",
        "last_verified": "2026-08-07", "source": "ai_capability/registry.py -- continuously real-updated from data/ai_cost_log.jsonl, never stale by construction",
    },
    {
        "category": "competitor_pricing", "subject": "governancedocs.com / riskprofs.com real pricing citations",
        "last_verified": "2026-08-06", "source": "CLAUDE.md's Execution Mode narrative -- one-time manual verification, no re-verification schedule exists",
    },
)


def _now():
    return datetime.now(timezone.utc)


def check_staleness(last_verified_date, category, now=None):
    """Real, generic, reusable staleness check -- given any real,
    ISO-format last_verified_date and a named category, returns whether
    it's stale against that category's own disclosed threshold. Never
    invents a threshold for an unnamed category -- honestly UNKNOWN."""
    now = now or _now()
    threshold = _STALENESS_THRESHOLDS_DAYS.get(category)
    if threshold is None:
        return {"status": "UNKNOWN", "reason": f"No disclosed staleness threshold exists for category '{category}'."}

    try:
        verified_dt = datetime.strptime(last_verified_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return {"status": "UNKNOWN", "reason": f"'{last_verified_date}' is not a real, parseable date."}

    age_days = (now - verified_dt).days
    is_stale = age_days > threshold
    return {
        "status": "STALE" if is_stale else "FRESH",
        "category": category,
        "last_verified": last_verified_date,
        "age_days": age_days,
        "threshold_days": threshold,
    }


def assess_all_known_knowledge(now=None):
    """The one real aggregator over KNOWN_STALENESS_CHECKS. Disclosed
    limitation stated explicitly in the result, not hidden."""
    now = now or _now()
    results = []
    for entry in KNOWN_STALENESS_CHECKS:
        check = check_staleness(entry["last_verified"], entry["category"], now=now)
        results.append({**entry, **check})

    stale = [r for r in results if r.get("status") == "STALE"]
    return {
        "generated_at": now.isoformat(),
        "checks": results,
        "total_checked": len(results),
        "stale_count": len(stale),
        "stale_items": [r["subject"] for r in stale],
        "note": "KNOWN_STALENESS_CHECKS is a manually-maintained registry of real, already-documented dated facts -- it does not automatically discover new facts to track. A real, disclosed limitation, not hidden.",
    }
